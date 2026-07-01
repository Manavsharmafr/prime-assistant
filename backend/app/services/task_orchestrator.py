import asyncio
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import json

from app.services.conversation_manager import conversation_manager
from app.services.planner import planner_service
from app.services.tool_registry import tool_registry
from app.services.llm_provider import llm_provider
from app.services.task_manager import tasks_ws_manager

class TaskOrchestratorService:
    def _broadcast_agent_state(self, state: str, model: str, active_tool: Optional[str] = None, reasoning: Optional[str] = None, plan: Optional[List[Dict]] = None):
        """Broadcast live AI execution status telemetry to frontend clients."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(tasks_ws_manager.broadcast({
                "type": "agent_state",
                "state": state,         # 'idle', 'planning', 'executing', 'speaking'
                "model": model,
                "active_tool": active_tool,
                "reasoning": reasoning,
                "plan": plan
            }))
        except RuntimeError:
            pass

    async def execute_user_prompt(self, db: Session, prompt: str, conversation_id: str, provider_override: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrate a multi-step task execution plan matching user intent, invoking tools via registries."""
        preferred_model = provider_override or llm_provider.get_preferred_provider()
        
        # 1. State change -> Planning
        self._broadcast_agent_state(
            state="planning",
            model=preferred_model,
            reasoning="Decomposing user request into subtasks..."
        )

        # 2. Add user message to thread
        conversation_manager.add_message(db, conversation_id, "user", prompt)

        # 3. Generate plan
        plan_data = planner_service.generate_plan(prompt, provider_override)
        plan_steps = plan_data.get("plan", [])
        reasoning = plan_data.get("reasoning", "Executing planner output.")

        # 4. State change -> Executing (broadcast plan list to UI)
        self._broadcast_agent_state(
            state="executing",
            model=preferred_model,
            reasoning=reasoning,
            plan=plan_steps
        )

        results = []
        for step in plan_steps:
            tool_name = step.get("tool")
            task_desc = step.get("task", f"Executing {tool_name}")
            arguments = step.get("arguments", {})

            # State change -> Active tool running
            self._broadcast_agent_state(
                state="executing",
                model=preferred_model,
                active_tool=tool_name,
                reasoning=f"Task: {task_desc}",
                plan=plan_steps
            )

            # Invoke tool safely via ToolRegistry
            try:
                tool_res = await tool_registry.execute_tool(tool_name, db, arguments)
                
                # Check for security gates (cancellation required or blocked)
                if isinstance(tool_res, dict):
                    if tool_res.get("status") == "pending_approval":
                        self._broadcast_agent_state(state="idle", model=preferred_model)
                        return {
                            "status": "challenge_required",
                            "challenge_id": tool_res.get("request_id"),
                            "request_id": tool_res.get("request_id"),
                            "command": arguments.get("command"),
                            "description": task_desc,
                            "affected_files": tool_res.get("affected_files"),
                            "estimated_impact": tool_res.get("estimated_impact")
                        }
                    elif tool_res.get("status") == "blocked":
                        self._broadcast_agent_state(state="idle", model=preferred_model)
                        return {
                            "status": "blocked",
                            "command": arguments.get("command"),
                            "description": task_desc,
                            "result": tool_res.get("message"),
                            "speech_response": "That command was blocked by the safety policy.",
                            "message": tool_res.get("message")
                        }

                results.append({
                    "task": task_desc,
                    "tool": tool_name,
                    "status": "success",
                    "result": tool_res
                })
            except Exception as err:
                # Capture exception, do not crash backend, log to results
                results.append({
                    "task": task_desc,
                    "tool": tool_name,
                    "status": "failed",
                    "error": str(err)
                })

        # 5. Synthesize final consolidated summary
        summary_prompt = (
            f"You are the Prime Assistant. Review the user prompt and the executed tool results to formulate a concise consolidated response.\n\n"
            f"User Prompt: {prompt}\n"
            f"Executed Tool Steps:\n{json.dumps(results, indent=2)}"
        )
        
        final_answer = ""
        try:
            final_answer = llm_provider.execute_prompt(
                prompt=summary_prompt,
                system_instruction="Provide a clean summary response addressing the user's intent. Do not mention internal tools or JSON lists directly unless requested.",
                provider_override=provider_override
            )
        except Exception as e:
            final_answer = f"Executed {len(results)} steps. Direct summary compilation failed: {str(e)}."

        # Add assistant message to thread
        conversation_manager.add_message(db, conversation_id, "assistant", final_answer)

        # 6. State change -> Idle
        self._broadcast_agent_state(
            state="idle",
            model=preferred_model
        )

        return {
            "result": final_answer,
            "speech_response": final_answer[:150] + ("..." if len(final_answer) > 150 else ""),
            "steps": results,
            "reasoning": reasoning
        }

task_orchestrator = TaskOrchestratorService()
