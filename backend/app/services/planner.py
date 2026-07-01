import json
from typing import Dict, Any, List, Optional
from app.services.llm_provider import llm_provider

class PlannerService:
    def __init__(self):
        self.system_instruction = (
            "You are the Prime Task Planner. Analyze the user request and decompose it into a sequence of steps using these available tools:\n"
            "- research: arguments {\"query\": str}\n"
            "- notes: arguments {\"title\": str, \"content\": str, \"tags\": list}\n"
            "- terminal: arguments {\"command\": str}\n"
            "- file: arguments {\"action\": \"read\"|\"write\"|\"list\", \"path\": str, \"content\": str}\n"
            "- browser: arguments {\"url\": str}\n"
            "- system: arguments {\"action\": \"stats\"|\"health\"|\"config\"}\n"
            "- memory: arguments {\"action\": \"search\"|\"save\", \"query\": str, \"content\": str, \"category\": str}\n\n"
            "You must return a valid JSON object conforming exactly to:\n"
            "{\n"
            "  \"plan\": [\n"
            "     { \"task\": \"description of step\", \"tool\": \"tool_name\", \"arguments\": { ... } }\n"
            "  ],\n"
            "  \"reasoning\": \"high-level justification of execution order\"\n"
            "}\n"
            "Do not return any markdown wrappers (like ```json), just the raw JSON string."
        )

    def generate_plan(self, prompt: str, provider_override: Optional[str] = None) -> Dict[str, Any]:
        """Call the LLM to structure a sequence of subtasks based on user intent."""
        try:
            llm_response = llm_provider.execute_prompt(
                prompt=f"Decompose this request: '{prompt}'",
                system_instruction=self.system_instruction,
                provider_override=provider_override,
                temperature=0.1 # Low temperature for structured output
            )
            # Remove possible markdown tags
            cleaned = llm_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except Exception as e:
            # Safe fallback: single terminal execution or direct conversation if parsing fails
            print(f"Planner failed to parse JSON response: {str(e)}")
            return {
                "plan": [
                    {
                        "task": f"Direct request execution fallback",
                        "tool": "terminal",
                        "arguments": {"command": f"echo '{prompt}'"}
                    }
                ],
                "reasoning": f"Fallback due to planner parse failure: {str(e)}"
            }

planner_service = PlannerService()
