"""
LLM-powered explanation generation for simulation monitoring.
"""

import os
from pathlib import Path
from typing import Optional
import requests
from datetime import datetime


class LLMExplainer:
    """Generate concise explanations of simulation state using LLM"""

    def __init__(
        self,
        model: str = "meta-llama/llama-3.1-8b-instruct:free",
        system_prompt_file: Optional[Path] = None,
        max_input_tokens: int = 4000,
        max_output_tokens: int = 150,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        # Load system prompt - default to built-in prompt file
        if system_prompt_file is None:
            # Use default system prompt file
            default_prompt_path = Path(__file__).parent / "prompts" / "system_prompt.txt"
            if default_prompt_path.exists():
                system_prompt_file = default_prompt_path

        if system_prompt_file and system_prompt_file.exists():
            with open(system_prompt_file) as f:
                self.system_prompt = f.read()
        else:
            # Fallback with strong anti-hallucination rules
            self.system_prompt = """You are monitoring a simulation. Provide concise 2-3 sentence summaries.

**CRITICAL**: ONLY report data that is EXPLICITLY present in the logs. NEVER make up run IDs, template numbers, mechanisms, percentages, or any other data. If information is not in the logs, say "not yet available" instead of inventing plausible-sounding values."""

    def generate_explanation(
        self,
        log_buffer: list[str],
        db_snapshot_text: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate LLM explanation from logs and database snapshot.

        Args:
            log_buffer: Recent log lines
            db_snapshot_text: Formatted database snapshot

        Returns:
            LLM-generated explanation or None if API call fails
        """
        if not self.api_key:
            return None

        # Build user message
        user_message = self._build_user_message(log_buffer, db_snapshot_text)

        # Truncate if too long
        if len(user_message) > self.max_input_tokens * 4:  # Rough char estimate
            user_message = user_message[:self.max_input_tokens * 4]

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/timepoint-ai/timepoint-pro",
                    "X-Title": "Timepoint Monitor"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "max_tokens": self.max_output_tokens,
                    "temperature": 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[LLM API Error: {response.status_code}]"

        except Exception as e:
            return f"[LLM Error: {str(e)[:100]}]"

    def generate_explanation_with_context(self, context: str) -> Optional[str]:
        """
        Generate LLM explanation from pre-formatted context.
        Used for chat responses where context is already built.

        Args:
            context: Pre-formatted context string

        Returns:
            LLM-generated explanation or None if API call fails
        """
        if not self.api_key:
            return None

        # Truncate if too long
        if len(context) > self.max_input_tokens * 4:
            context = context[:self.max_input_tokens * 4]

        try:
            # Use higher token limit for chat responses to allow more detailed answers
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/timepoint-ai/timepoint-pro",
                    "X-Title": "Timepoint Monitor Chat"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt + "\n\nYou are in CHAT mode. Answer the user's question based on the provided simulation state and logs. Be specific and helpful."},
                        {"role": "user", "content": context}
                    ],
                    "max_tokens": max(300, self.max_output_tokens),  # More tokens for chat
                    "temperature": 0.3
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[LLM API Error: {response.status_code}]"

        except Exception as e:
            return f"[LLM Error: {str(e)[:100]}]"

    def _build_user_message(
        self,
        log_buffer: list[str],
        db_snapshot_text: Optional[str]
    ) -> str:
        """Build user message from logs and database snapshot"""
        lines = []
        lines.append(f"=== TIMEPOINT MONITOR UPDATE ===")
        lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if log_buffer:
            lines.append("RECENT LOGS:")
            # Last 50 lines max
            for line in log_buffer[-50:]:
                lines.append(line)
            lines.append("")

        if db_snapshot_text:
            lines.append(db_snapshot_text)

        return "\n".join(lines)
