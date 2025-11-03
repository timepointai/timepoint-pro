#!/usr/bin/env python3.10
"""
Simulation Monitor Runner

Main entry point for monitoring run_all_mechanism_tests.py with LLM-powered explanations.

Usage:
    python3.10 -m monitoring.monitor_runner -- python3.10 run_all_mechanism_tests.py --timepoint-all

    python3.10 -m monitoring.monitor_runner --mode llm --interval 120 -- python3.10 run_all_mechanism_tests.py --quick
"""

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import select

from monitoring.config import MonitorConfig, MonitorState, DisplayMode, OutputFormat
from monitoring.stream_parser import StreamParser
from monitoring.db_inspector import DBInspector
from monitoring.llm_explainer import LLMExplainer


class SimulationMonitor:
    """Main simulation monitor orchestrator"""

    def __init__(self, config: MonitorConfig):
        self.config = config
        self.state = MonitorState()
        self.parser = StreamParser()
        self.db_inspector = DBInspector(config.metadata_db_path, config.datasets_dir)
        self.llm_explainer = LLMExplainer(
            model=config.llm_model,
            system_prompt_file=config.system_prompt_file,
            max_input_tokens=config.max_input_tokens,
            max_output_tokens=config.max_output_tokens,
            api_key=config.openrouter_api_key
        )

        self.process: subprocess.Popen = None
        self.update_timer: threading.Timer = None
        self.lock = threading.Lock()
        self.chat_enabled = config.enable_chat
        self.stdin_thread = None

    def start(self):
        """Start monitoring the subprocess"""
        self.state.is_running = True
        self.state.start_time = time.time()

        print("=" * 80)
        print(f"TIMEPOINT MONITOR | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {self.config.display_mode.value.upper()} | Interval: {self.config.update_interval}s")
        if self.chat_enabled:
            print("Chat Mode: ENABLED (type messages and press Enter to ask questions)")
        print("=" * 80)
        print()

        # Start subprocess (keep stdin for interactive prompts)
        # If auto-confirm is enabled, use PIPE for stdin so we can write to it
        # If chat is enabled, we need PIPE to separate chat from subprocess input
        stdin_mode = subprocess.PIPE if (self.config.auto_confirm or self.chat_enabled) else sys.stdin

        # Set auto-confirm environment variable if enabled
        env = os.environ.copy()
        if self.config.auto_confirm:
            env["TIMEPOINT_AUTO_CONFIRM"] = "1"

        # Disable Python output buffering to get real-time output
        env["PYTHONUNBUFFERED"] = "1"

        self.process = subprocess.Popen(
            self.config.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=stdin_mode,
            text=True,
            bufsize=1,
            env=env
        )

        # Start chat listener thread if enabled
        if self.chat_enabled:
            self._start_chat_listener()

        # Schedule first LLM update
        if self.config.display_mode in [DisplayMode.LLM, DisplayMode.BOTH]:
            self._schedule_llm_update()

        # Read output line by line
        try:
            for line in self.process.stdout:
                self._process_line(line)

        except KeyboardInterrupt:
            print("\n\n[Monitor interrupted by user]")
            self._cleanup()
            sys.exit(0)

        # Wait for completion
        self.process.wait()
        self.state.is_running = False

        # Final LLM update
        if self.config.display_mode in [DisplayMode.LLM, DisplayMode.BOTH]:
            self._generate_llm_update()

        print("\n" + "=" * 80)
        print("MONITOR COMPLETE")
        print(f"Duration: {time.time() - self.state.start_time:.1f}s")
        print("=" * 80)

    def _process_line(self, line: str):
        """Process a single line of output"""
        line = line.rstrip()

        # Add to log buffer
        with self.lock:
            self.state.log_buffer.append(line)

        # Parse for events
        event = self.parser.parse_line(line)
        if event:
            self._handle_event(event)

        # Show raw output if enabled
        if self.config.display_mode in [DisplayMode.RAW, DisplayMode.BOTH]:
            print(f"[RAW] {line}")

    def _handle_event(self, event):
        """Handle parsed events"""
        with self.lock:
            if event.event_type == "run_started":
                self.state.current_run_id = event.run_id
                self.state.current_template = event.template_name

            elif event.event_type == "template_start":
                self.state.current_template = event.template_name

            elif event.event_type == "cost":
                self.state.total_cost_usd += event.cost

            elif event.event_type in ["success", "failure"]:
                self.state.templates_completed = self.parser.templates_completed

            elif event.event_type == "confirmation_prompt":
                # Note: Auto-confirmation is handled via TIMEPOINT_AUTO_CONFIRM environment variable
                # The subprocess will auto-confirm without needing stdin interaction
                if self.config.auto_confirm:
                    print("\n>>> AUTO-CONFIRMING (TIMEPOINT_AUTO_CONFIRM environment variable set) <<<\n")
                else:
                    # Alert user that input is needed
                    print("\n>>> USER INPUT REQUIRED: Type 'y' or 'n' and press Enter <<<\n")

    def _schedule_llm_update(self):
        """Schedule next LLM update"""
        if not self.state.is_running:
            return

        self.update_timer = threading.Timer(
            self.config.update_interval,
            self._generate_llm_update
        )
        self.update_timer.daemon = True
        self.update_timer.start()

    def _generate_llm_update(self):
        """Generate and display LLM explanation"""
        with self.lock:
            log_buffer = list(self.state.log_buffer)
            current_run_id = self.state.current_run_id
            self.state.log_buffer.clear()

        # Get database snapshot
        db_snapshot_text = None
        if self.config.enable_db_inspection and current_run_id:
            snapshot = self.db_inspector.get_run_snapshot(current_run_id)
            if snapshot:
                db_snapshot_text = self.db_inspector.format_snapshot_for_llm(snapshot)

        # Generate explanation
        explanation = self.llm_explainer.generate_explanation(log_buffer, db_snapshot_text)

        # Display
        if explanation:
            timestamp = datetime.now().strftime('%H:%M:%S')
            model_name = self.config.llm_model.split('/')[-1]
            print()
            print(f"--- LLM SUMMARY ({model_name} @ {timestamp}) ---")
            print(explanation)
            print()

        # Schedule next update
        if self.state.is_running:
            self._schedule_llm_update()

    def _start_chat_listener(self):
        """Start background thread to listen for user chat input"""
        def chat_loop():
            while self.state.is_running:
                # Use select to check if stdin has data (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    user_input = sys.stdin.readline().strip()
                    if user_input:
                        self._process_chat_message(user_input)

        self.stdin_thread = threading.Thread(target=chat_loop, daemon=True)
        self.stdin_thread.start()

    def _process_chat_message(self, message: str):
        """Process a chat message from the user"""
        # Get current state
        with self.lock:
            log_buffer = list(self.state.log_buffer)
            current_run_id = self.state.current_run_id

        # Get database snapshot
        db_snapshot_text = None
        if self.config.enable_db_inspection and current_run_id:
            snapshot = self.db_inspector.get_run_snapshot(current_run_id)
            if snapshot:
                db_snapshot_text = self.db_inspector.format_snapshot_for_llm(snapshot)

        # Build context for LLM with user question
        context_parts = []

        if log_buffer:
            context_parts.append("=== RECENT LOGS ===")
            context_parts.extend(log_buffer[-50:])  # Last 50 lines
            context_parts.append("")

        if db_snapshot_text:
            context_parts.append("=== SIMULATION STATE ===")
            context_parts.append(db_snapshot_text)
            context_parts.append("")

        context_parts.append(f"=== USER QUESTION ===")
        context_parts.append(message)

        context = "\n".join(context_parts)

        # Generate response using LLM
        try:
            response = self.llm_explainer.generate_explanation_with_context(context)

            # Display chat exchange
            timestamp = datetime.now().strftime('%H:%M:%S')
            print()
            print(f"--- CHAT ({timestamp}) ---")
            print(f"Q: {message}")
            print(f"A: {response}")
            print()
        except Exception as e:
            print(f"\n[CHAT ERROR] Failed to generate response: {e}\n")

    def _cleanup(self):
        """Clean up resources"""
        if self.update_timer:
            self.update_timer.cancel()
        if self.stdin_thread and self.stdin_thread.is_alive():
            # Thread will exit when is_running becomes False
            pass
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor run_all_mechanism_tests.py with LLM-powered explanations"
    )
    parser.add_argument(
        "command",
        nargs="+",
        help="Command to monitor (e.g., python3.10 run_all_mechanism_tests.py --quick)"
    )
    parser.add_argument(
        "--mode",
        choices=["raw", "llm", "both"],
        default="both",
        help="Display mode: raw logs, llm summaries, or both (default: both)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between LLM updates (default: 300 = 5 min)"
    )
    parser.add_argument(
        "--llm-model",
        default="meta-llama/llama-3.1-8b-instruct:free",
        help="OpenRouter model name (default: llama-3.1-8b-instruct:free)"
    )
    parser.add_argument(
        "--max-input-tokens",
        type=int,
        default=4000,
        help="Max tokens to send to LLM (default: 4000)"
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=150,
        help="Max tokens in LLM response (default: 150)"
    )
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="Custom system prompt file"
    )
    parser.add_argument(
        "--no-db-inspection",
        action="store_true",
        help="Disable database/narrative queries (faster but less detail)"
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Automatically confirm expensive runs (bypass confirmation prompts)"
    )
    parser.add_argument(
        "--enable-chat",
        action="store_true",
        help="Enable interactive chat mode (ask questions while monitoring)"
    )

    args = parser.parse_args()

    # Build config
    config = MonitorConfig(
        command=args.command,
        display_mode=DisplayMode(args.mode),
        llm_model=args.llm_model,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
        update_interval=args.interval,
        system_prompt_file=args.system_prompt_file,
        enable_db_inspection=not args.no_db_inspection,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        auto_confirm=args.auto_confirm,
        enable_chat=args.enable_chat
    )

    # Create and start monitor
    monitor = SimulationMonitor(config)
    monitor.start()


if __name__ == "__main__":
    main()
