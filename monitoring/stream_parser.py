"""
Stream parser for run_all_mechanism_tests.py output.

Extracts key events and state from subprocess stdout/stderr.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedEvent:
    """An event extracted from the log stream"""
    event_type: str  # "template_start", "run_started", "progress", "success", "failure", etc.
    template_name: Optional[str] = None
    run_id: Optional[str] = None
    progress: Optional[tuple[int, int]] = None  # (current, total)
    cost: Optional[float] = None
    entities: Optional[int] = None
    timepoints: Optional[int] = None
    mechanisms: Optional[list[str]] = None
    error_message: Optional[str] = None
    raw_line: str = ""


class StreamParser:
    """
    Parse run_all_mechanism_tests.py output to extract key events and state.
    """

    # Regex patterns for key events
    PATTERNS = {
        # [1/15] template_name
        "progress": re.compile(r"\[(\d+)/(\d+)\]\s+(\S+)"),

        # Running: template_name
        "template_start": re.compile(r"^Running:\s+(\S+)"),

        # Run ID: run_20251101_143500_abc123
        "run_id": re.compile(r"Run ID:\s+(run_\w+)"),

        # Entities: 6, Timepoints: 12
        "stats": re.compile(r"Entities:\s+(\d+).*Timepoints:\s+(\d+)"),

        # Mechanisms: M1, M2, M3
        "mechanisms": re.compile(r"Mechanisms:\s+([\w\s,]+)"),

        # Cost: $0.08 or Estimated Cost: $15.23
        "cost": re.compile(r"(?:Cost|Estimated Cost):\s+\$([0-9.]+)"),

        # ✅ Success: template_name
        "success": re.compile(r"✅\s+(?:Success|PASSED):?\s+(\S+)"),

        # ❌ Failed: template_name
        "failure": re.compile(r"❌\s+(?:Failed|FAILED):?\s+(\S+)"),

        # Error: some error message
        "error": re.compile(r"(?:Error|ERROR):\s+(.+)"),

        # PHASE 1: Pre-Programmed Templates (15 templates)
        "total_templates": re.compile(r"PHASE 1:.*\((\d+)\s+templates\)"),

        # EXPENSIVE RUN CONFIRMATION REQUIRED
        "confirmation_prompt": re.compile(r"EXPENSIVE RUN CONFIRMATION REQUIRED"),
    }

    def __init__(self):
        self.current_template: Optional[str] = None
        self.current_run_id: Optional[str] = None
        self.templates_total: Optional[int] = None
        self.templates_completed: int = 0

    def parse_line(self, line: str) -> Optional[ParsedEvent]:
        """
        Parse a single line of output.

        Returns ParsedEvent if the line contains a significant event, None otherwise.
        """
        line = line.strip()
        if not line:
            return None

        # Try to match against each pattern
        event = None

        # Check for template start
        match = self.PATTERNS["template_start"].search(line)
        if match:
            self.current_template = match.group(1)
            event = ParsedEvent(
                event_type="template_start",
                template_name=self.current_template,
                raw_line=line
            )

        # Check for progress
        match = self.PATTERNS["progress"].search(line)
        if match and not event:
            current = int(match.group(1))
            total = int(match.group(2))
            template = match.group(3)
            self.current_template = template
            event = ParsedEvent(
                event_type="progress",
                template_name=template,
                progress=(current, total),
                raw_line=line
            )

        # Check for total templates
        match = self.PATTERNS["total_templates"].search(line)
        if match and not event:
            self.templates_total = int(match.group(1))
            event = ParsedEvent(
                event_type="total_templates",
                progress=(0, self.templates_total),
                raw_line=line
            )

        # Check for run ID
        match = self.PATTERNS["run_id"].search(line)
        if match and not event:
            self.current_run_id = match.group(1)
            event = ParsedEvent(
                event_type="run_started",
                run_id=self.current_run_id,
                template_name=self.current_template,
                raw_line=line
            )

        # Check for stats (entities/timepoints)
        match = self.PATTERNS["stats"].search(line)
        if match and not event:
            entities = int(match.group(1))
            timepoints = int(match.group(2))
            event = ParsedEvent(
                event_type="stats",
                entities=entities,
                timepoints=timepoints,
                template_name=self.current_template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for mechanisms
        match = self.PATTERNS["mechanisms"].search(line)
        if match and not event:
            mechanisms_str = match.group(1)
            mechanisms = [m.strip() for m in mechanisms_str.split(",")]
            event = ParsedEvent(
                event_type="mechanisms",
                mechanisms=mechanisms,
                template_name=self.current_template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for cost
        match = self.PATTERNS["cost"].search(line)
        if match and not event:
            cost = float(match.group(1))
            event = ParsedEvent(
                event_type="cost",
                cost=cost,
                template_name=self.current_template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for success
        match = self.PATTERNS["success"].search(line)
        if match and not event:
            template = match.group(1)
            self.templates_completed += 1
            event = ParsedEvent(
                event_type="success",
                template_name=template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for failure
        match = self.PATTERNS["failure"].search(line)
        if match and not event:
            template = match.group(1)
            self.templates_completed += 1
            event = ParsedEvent(
                event_type="failure",
                template_name=template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for error
        match = self.PATTERNS["error"].search(line)
        if match and not event:
            error_msg = match.group(1)
            event = ParsedEvent(
                event_type="error",
                error_message=error_msg,
                template_name=self.current_template,
                run_id=self.current_run_id,
                raw_line=line
            )

        # Check for confirmation prompt
        match = self.PATTERNS["confirmation_prompt"].search(line)
        if match and not event:
            event = ParsedEvent(
                event_type="confirmation_prompt",
                raw_line=line
            )

        return event

    def get_progress(self) -> tuple[int, Optional[int]]:
        """Get current progress (completed, total)"""
        return (self.templates_completed, self.templates_total)
