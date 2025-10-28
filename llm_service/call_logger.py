"""
Call Logging - Comprehensive logging of LLM calls with metadata tracking

Handles session management, cost tracking, and debug payload logging.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import logging
import uuid

# Import run_id tracking for integration with metadata system
try:
    from metadata.tracking import get_current_run_id
except ImportError:
    def get_current_run_id():
        return None


@dataclass
class CallMetadata:
    """Metadata for an LLM call"""
    timestamp: str
    session_id: str
    run_id: Optional[str]  # ADDED: Integration with e2e run tracking
    call_type: str
    model: str
    parameters: Dict[str, Any]
    tokens_used: Dict[str, int]  # prompt, completion, total
    cost_usd: float
    latency_ms: float
    success: bool
    retry_count: int
    error: Optional[str] = None

    # Debug payloads (optional, controlled by log level)
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    response_full: Optional[str] = None
    response_parsed: Optional[Any] = None


class CallLogger:
    """
    Logs LLM calls with configurable detail levels.

    Log Levels:
    - metadata: Session ID, model, tokens, cost, success only
    - prompts: Add system/user prompts (truncated)
    - responses: Add LLM responses (truncated)
    - full: Complete payloads (no truncation)
    """

    def __init__(
        self,
        log_directory: str = "logs/llm_calls",
        log_level: str = "metadata",
        truncate_prompts_chars: int = 500,
        truncate_responses_chars: int = 1000,
        rotation: str = "daily",
    ):
        """
        Initialize logger.

        Args:
            log_directory: Directory for log files
            log_level: One of: metadata, prompts, responses, full
            truncate_prompts_chars: Max chars for prompt truncation
            truncate_responses_chars: Max chars for response truncation
            rotation: Log rotation strategy (daily, weekly, size)
        """
        self.log_directory = Path(log_directory)
        self.log_level = log_level
        self.truncate_prompts_chars = truncate_prompts_chars
        self.truncate_responses_chars = truncate_responses_chars
        self.rotation = rotation

        # Create log directory
        self.log_directory.mkdir(parents=True, exist_ok=True)

        # Setup Python logger
        self.logger = logging.getLogger("llm_service")
        self.logger.setLevel(logging.INFO)

        # Session tracking
        self.current_session: Optional[SessionContext] = None
        self.call_count = 0
        self.total_cost = 0.0
        self.total_tokens = 0

    def log_call(
        self,
        call_type: str,
        model: str,
        parameters: Dict[str, Any],
        tokens_used: Dict[str, int],
        cost_usd: float,
        latency_ms: float,
        success: bool,
        retry_count: int = 0,
        error: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        response_full: Optional[str] = None,
        response_parsed: Optional[Any] = None,
    ) -> None:
        """
        Log an LLM call with metadata and optional debug payloads.

        Args:
            call_type: Type of call (populate_entity, generate_dialog, etc.)
            model: Model identifier
            parameters: Call parameters (temperature, max_tokens, etc.)
            tokens_used: Token counts dict
            cost_usd: Estimated cost in USD
            latency_ms: Call latency in milliseconds
            success: Whether call succeeded
            retry_count: Number of retries needed
            error: Error message if failed
            system_prompt: System prompt (for debug levels)
            user_prompt: User prompt (for debug levels)
            response_full: Full LLM response (for debug levels)
            response_parsed: Parsed response structure (for debug levels)
        """
        # Get session ID
        session_id = self.current_session.session_id if self.current_session else "no_session"

        # FIX BUG #3: Get run_id from thread-local tracking system
        run_id = get_current_run_id()

        # Build metadata
        metadata = CallMetadata(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            run_id=run_id,  # ADDED: Include run_id for e2e workflow tracking
            call_type=call_type,
            model=model,
            parameters=parameters,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            retry_count=retry_count,
            error=error,
        )

        # Add debug payloads based on log level
        if self.log_level in ["prompts", "responses", "full"]:
            metadata.system_prompt = self._truncate(system_prompt, self.truncate_prompts_chars)
            metadata.user_prompt = self._truncate(user_prompt, self.truncate_prompts_chars)

        if self.log_level in ["responses", "full"]:
            metadata.response_full = self._truncate(response_full, self.truncate_responses_chars)

        if self.log_level == "full":
            # No truncation for full level
            metadata.system_prompt = system_prompt
            metadata.user_prompt = user_prompt
            metadata.response_full = response_full
            metadata.response_parsed = response_parsed

        # Write to JSONL file
        self._write_jsonl(metadata)

        # Update statistics
        self.call_count += 1
        self.total_cost += cost_usd
        self.total_tokens += tokens_used.get('total', 0)

        # Update session statistics
        if self.current_session:
            self.current_session.calls_count += 1
            self.current_session.total_cost += cost_usd

        # Log to Python logger
        status = "✅" if success else "❌"
        self.logger.info(
            f"{status} {call_type} | {model} | "
            f"{tokens_used.get('total', 0)} tokens | "
            f"${cost_usd:.4f} | {latency_ms:.0f}ms"
        )

    def start_session(
        self,
        workflow: str = "unknown",
        user: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new logging session.

        Args:
            workflow: Workflow name (temporal_train, evaluate, etc.)
            user: User identifier
            metadata: Additional session metadata

        Returns:
            Session ID
        """
        session_id = f"llm_{uuid.uuid4().hex[:12]}"

        self.current_session = SessionContext(
            session_id=session_id,
            workflow=workflow,
            user=user,
            started_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        self.logger.info(f"📝 Started session {session_id} for workflow '{workflow}'")
        return session_id

    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        End the current session and return statistics.

        Returns:
            Session summary dict or None if no active session
        """
        if not self.current_session:
            return None

        session = self.current_session
        duration = (datetime.now() - datetime.fromisoformat(session.started_at)).total_seconds()

        summary = {
            "session_id": session.session_id,
            "workflow": session.workflow,
            "duration_seconds": duration,
            "calls_count": session.calls_count,
            "total_cost": session.total_cost,
            "metadata": session.metadata,
        }

        self.logger.info(
            f"📊 Session {session.session_id} complete: "
            f"{session.calls_count} calls, ${session.total_cost:.4f}, {duration:.1f}s"
        )

        self.current_session = None
        return summary

    def get_statistics(self) -> Dict[str, Any]:
        """Get cumulative logging statistics"""
        return {
            "total_calls": self.call_count,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "active_session": self.current_session.session_id if self.current_session else None,
        }

    def _truncate(self, text: Optional[str], max_chars: int) -> Optional[str]:
        """Truncate text to max characters"""
        if not text or self.log_level == "full":
            return text

        if len(text) <= max_chars:
            return text

        return text[:max_chars] + "... [truncated]"

    def _write_jsonl(self, metadata: CallMetadata) -> None:
        """Write metadata to JSONL log file"""
        # Determine log file path based on rotation strategy
        if self.rotation == "daily":
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_directory / f"llm_calls_{date_str}.jsonl"
        else:
            log_file = self.log_directory / "llm_calls.jsonl"

        # Convert to dict and write
        try:
            with open(log_file, 'a') as f:
                json_line = json.dumps(asdict(metadata), default=str)
                f.write(json_line + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write log file: {e}")


@dataclass
class SessionContext:
    """Context for a logging session"""
    session_id: str
    workflow: str
    user: str
    started_at: str
    calls_count: int = 0
    total_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
