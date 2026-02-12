#!/usr/bin/env python3
"""
persona_chat.py - Chat with testing personas using arbitrary context files.

Uses OpenRouterClient from llm.py. System prompt = persona markdown + context blobs.

Usage:
    python persona_chat.py --persona AGENT1 --context README.md MECHANICS.md --max-tokens 500
    python persona_chat.py --persona AGENT2 --context output/simulations/summary_*.json --batch "What concerns you?"
    python persona_chat.py --persona AGENT3 --max-tokens 300 --model anthropic/claude-opus-4-6
    python persona_chat.py --persona AGENT4 --context MECHANICS.md

Interactive mode (no --batch): stdin/stdout loop. Ctrl+C to exit.
Batch mode (--batch): ask one question per flag, print answer, exit.
"""

import argparse
import os
import sys
from pathlib import Path

from llm import OpenRouterClient


def load_persona(agent_id: str) -> str:
    """Load persona markdown from docs/testing_personas/AGENT{N}.md."""
    path = Path(__file__).parent / "docs" / "testing_personas" / f"{agent_id}.md"
    if not path.exists():
        print(f"Error: Persona file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text()


def load_context_files(paths: list[str]) -> list[tuple[str, str]]:
    """Load context files, returning list of (filename, contents)."""
    results = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"Warning: Context file not found, skipping: {p}", file=sys.stderr)
            continue
        try:
            results.append((path.name, path.read_text()))
        except Exception as e:
            print(f"Warning: Could not read {p}: {e}", file=sys.stderr)
    return results


def build_system_prompt(persona_text: str, context_files: list[tuple[str, str]]) -> str:
    """Build system prompt from persona + context blobs."""
    parts = [
        "You are roleplaying as the following person. Stay in character.",
        "Respond from their perspective, with their concerns, biases, and expertise.",
        "",
        "--- PERSONA ---",
        persona_text,
    ]

    if context_files:
        parts.append("")
        parts.append("--- CONTEXT ---")
        parts.append("The following documents have been provided for your review:")
        parts.append("")
        for filename, contents in context_files:
            parts.append(f"[{filename}]:")
            parts.append(contents)
            parts.append("")

    return "\n".join(parts)


def chat_once(client: OpenRouterClient, model: str, messages: list[dict],
              max_tokens: int, temperature: float) -> str:
    """Send messages to the LLM and return the assistant response text."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response["choices"][0]["message"]["content"]


def run_batch(client: OpenRouterClient, model: str, system_prompt: str,
              questions: list[str], max_tokens: int, temperature: float):
    """Ask each question independently, print answer, exit."""
    for question in questions:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        answer = chat_once(client, model, messages, max_tokens, temperature)
        if len(questions) > 1:
            print(f"\n>> {question}")
        print(answer)


def run_interactive(client: OpenRouterClient, model: str, system_prompt: str,
                    max_tokens: int, temperature: float):
    """Interactive stdin/stdout loop. Conversation history accumulates."""
    messages = [{"role": "system", "content": system_prompt}]
    print("Persona chat ready. Type your message (Ctrl+C to exit).\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})
            answer = chat_once(client, model, messages, max_tokens, temperature)
            messages.append({"role": "assistant", "content": answer})
            print(f"\n{answer}\n")
    except KeyboardInterrupt:
        print("\n\nExiting.")


def main():
    parser = argparse.ArgumentParser(
        description="Chat with testing personas using arbitrary context files."
    )
    parser.add_argument(
        "--persona", required=True,
        choices=["AGENT1", "AGENT2", "AGENT3", "AGENT4"],
        help="Persona to chat with (loads docs/testing_personas/AGENT{N}.md)"
    )
    parser.add_argument(
        "--context", nargs="*", default=[],
        help="Context files to include in system prompt"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=1000,
        help="Max tokens per response (default: 1000)"
    )
    parser.add_argument(
        "--model", default="anthropic/claude-opus-4-6",
        help="Model to use (default: anthropic/claude-opus-4-6)"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7,
        help="Temperature (default: 0.7)"
    )
    parser.add_argument(
        "--batch", action="append", default=[],
        help="Ask one question, print answer, exit (repeatable)"
    )

    args = parser.parse_args()

    # Load API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set in environment or .env file", file=sys.stderr)
        sys.exit(1)

    # Build system prompt
    persona_text = load_persona(args.persona)
    context_files = load_context_files(args.context)
    system_prompt = build_system_prompt(persona_text, context_files)

    # Create client
    client = OpenRouterClient(api_key=api_key)

    if args.batch:
        run_batch(client, args.model, system_prompt, args.batch, args.max_tokens, args.temperature)
    else:
        run_interactive(client, args.model, system_prompt, args.max_tokens, args.temperature)


if __name__ == "__main__":
    main()
