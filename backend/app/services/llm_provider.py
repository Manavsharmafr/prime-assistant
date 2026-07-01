import os
import time
import requests
import json
from typing import Generator, Optional, Dict, Any, List
from app.core.config import settings

class LLMUsageTracker:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def add_usage(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += (prompt + completion)

    def get_summary(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

token_tracker = LLMUsageTracker()

class LLMProviderService:
    def __init__(self):
        # Configure providers based on active keys
        self.active_providers = []
        if settings.GEMINI_API_KEY:
            self.active_providers.append("gemini")
        if settings.OPENAI_API_KEY:
            self.active_providers.append("openai")
        if settings.ANTHROPIC_API_KEY:
            self.active_providers.append("anthropic")
        # Ollama is locally hosted; assume active if host set
        if settings.OLLAMA_HOST:
            self.active_providers.append("ollama")
        
        # Always allow offline fallback
        self.active_providers.append("offline")

    def get_preferred_provider(self, override: Optional[str] = None) -> str:
        """Select the preferred available LLM provider, cascading if keys are missing."""
        if override and override.lower() in self.active_providers:
            return override.lower()
        
        # Default hierarchy: Gemini -> OpenAI -> Anthropic -> Ollama -> Offline
        for provider in ["gemini", "openai", "anthropic", "ollama", "offline"]:
            if provider in self.active_providers:
                return provider
        return "offline"

    def execute_prompt(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        provider_override: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: float = 15.0
    ) -> str:
        """Execute a text prompt against the selected LLM provider with automatic cascading fallbacks on failure."""
        provider = self.get_preferred_provider(provider_override)
        errors = []

        # Cascade order beginning with selected provider
        providers_to_try = [provider] + [p for p in self.active_providers if p != provider]

        for p in providers_to_try:
            try:
                if p == "gemini":
                    return self._run_gemini(prompt, system_instruction, temperature, max_tokens, timeout)
                elif p == "openai":
                    return self._run_openai(prompt, system_instruction, temperature, max_tokens, timeout)
                elif p == "anthropic":
                    return self._run_anthropic(prompt, system_instruction, temperature, max_tokens, timeout)
                elif p == "ollama":
                    return self._run_ollama(prompt, system_instruction, temperature, max_tokens, timeout)
                elif p == "offline":
                    return self._run_offline(prompt, system_instruction)
            except Exception as e:
                err_msg = f"Provider '{p}' failed: {str(e)}"
                print(err_msg)
                errors.append(err_msg)
                # Keep looping to cascade fallback

        raise RuntimeError(f"All configured LLM providers failed. Details: {'; '.join(errors)}")

    def _run_gemini(
        self, prompt: str, system_instruction: Optional[str], temp: float, max_tokens: int, timeout: float
    ) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        config = genai.types.GenerationConfig(
            temperature=temp,
            max_output_tokens=max_tokens
        )
        
        # Instantiate model
        model_name = "gemini-1.5-flash"
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=config,
            system_instruction=system_instruction
        )
        
        response = model.generate_content(prompt, request_options={"timeout": timeout})
        
        # Heuristic token usage tracking (4 characters per token estimate)
        prompt_est = len(prompt) // 4
        comp_est = len(response.text) // 4
        token_tracker.add_usage(prompt_est, comp_est)
        
        return response.text

    def _run_openai(
        self, prompt: str, system_instruction: Optional[str], temp: float, max_tokens: int, timeout: float
    ) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        # Set default OpenAI chat completion model
        model = "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        token_tracker.add_usage(
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )
        return response.choices[0].message.content

    def _run_anthropic(
        self, prompt: str, system_instruction: Optional[str], temp: float, max_tokens: int, timeout: float
    ) -> str:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        messages = [{"role": "user", "content": prompt}]
        model = "claude-3-haiku-20240307"
        
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temp,
            "messages": messages,
            "timeout": timeout
        }
        if system_instruction:
            kwargs["system"] = system_instruction
            
        response = client.messages.create(**kwargs)
        
        token_tracker.add_usage(
            response.usage.input_tokens,
            response.usage.output_tokens
        )
        return response.content[0].text

    def _run_ollama(
        self, prompt: str, system_instruction: Optional[str], temp: float, max_tokens: int, timeout: float
    ) -> str:
        url = f"{settings.OLLAMA_HOST}/api/generate"
        
        system_prefix = f"System directive: {system_instruction}\n\n" if system_instruction else ""
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": f"{system_prefix}{prompt}",
            "options": {
                "temperature": temp,
                "num_predict": max_tokens
            },
            "stream": False
        }
        
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            res_json = resp.json()
            out_text = res_json.get("response", "")
            # Heuristic token usage tracking
            prompt_est = len(prompt) // 4
            comp_est = len(out_text) // 4
            token_tracker.add_usage(prompt_est, comp_est)
            return out_text
        raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

    def _run_offline(self, prompt: str, system_instruction: Optional[str]) -> str:
        """Deterministic offline fallback generator for testing or offline safety."""
        prompt_lower = prompt.lower()
        
        # 1. Handle structured Plan requests
        if "plan" in prompt_lower or "steps" in prompt_lower or "decompose" in prompt_lower:
            # Generate a structured plan for typical agent workflows
            if "search" in prompt_lower or "research" in prompt_lower:
                return json.dumps({
                    "plan": [
                        {"task": "research_topic", "tool": "research", "arguments": {"query": "React framework details"}},
                        {"task": "save_notes", "tool": "notes", "arguments": {"title": "React Research", "content": "React is a components library"}},
                        {"task": "log_execution", "tool": "terminal", "arguments": {"command": "echo 'Research workflow executed successfully'"}}
                    ],
                    "reasoning": "User requested research, notes, and task logging. Breaking into research, notes saving, and terminal log execution."
                })
            elif "del" in prompt_lower or "delete" in prompt_lower:
                return json.dumps({
                    "plan": [
                        {"task": "delete_file", "tool": "terminal", "arguments": {"command": "del workspace.code"}}
                    ],
                    "reasoning": "Delete operation requested. Running terminal delete command."
                })
            else:
                return json.dumps({
                    "plan": [
                        {"task": "execute_shell", "tool": "terminal", "arguments": {"command": "dir"}}
                    ],
                    "reasoning": "Standard shell query requested. Breaking into single terminal command task."
                })
        
        # 2. General Conversation answers
        return "I am Prime, running in local offline fallback mode. Configure API keys in `.env` to activate cloud reasoning capabilities."

llm_provider = LLMProviderService()
