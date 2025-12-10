"""
Event Emission for Synth-Style Monitoring

Part of the SynthasAIzer control paradigm.
See SYNTH.md for full specification.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


class SynthEvent(Enum):
    """
    Event types for synth-style monitoring.

    These events are emitted at key workflow points to enable
    visualization and monitoring tools.
    """
    # Lifecycle events
    RUN_START = "run_start"
    RUN_COMPLETE = "run_complete"
    RUN_ERROR = "run_error"

    # Entity events
    ENTITY_CREATED = "entity_created"
    ENTITY_INTENSITY_CHANGE = "entity_intensity_change"
    ENTITY_RESOLUTION_CHANGE = "entity_resolution_change"
    ENTITY_VOICE_CHANGE = "entity_voice_change"

    # Timepoint events
    TIMEPOINT_START = "timepoint_start"
    TIMEPOINT_COMPLETE = "timepoint_complete"

    # Dialog events
    DIALOG_START = "dialog_start"
    DIALOG_TURN = "dialog_turn"
    DIALOG_COMPLETE = "dialog_complete"

    # Knowledge events
    EXPOSURE_EVENT = "exposure_event"
    KNOWLEDGE_TRANSFER = "knowledge_transfer"

    # Envelope events
    ENVELOPE_PHASE_CHANGE = "envelope_phase_change"


@dataclass
class SynthEventData:
    """
    Data structure for emitted events.

    Contains all information about a single event occurrence.
    """
    event_type: SynthEvent
    timestamp: float
    run_id: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "event": self.event_type.value,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SynthEventData":
        """Create from dictionary."""
        return cls(
            event_type=SynthEvent(d["event"]),
            timestamp=d["timestamp"],
            run_id=d["run_id"],
            data=d.get("data", {})
        )


# Type alias for event listeners
EventListener = Callable[[SynthEventData], None]


class SynthEventEmitter:
    """
    Emits events for synth-style monitoring.

    Disabled by default for backward compatibility.
    Enable explicitly when monitoring is needed.

    Example:
        emitter = SynthEventEmitter(enabled=True)

        # Add a listener
        def my_listener(event):
            print(f"Event: {event.event_type.value}")

        emitter.add_listener(my_listener)

        # Emit events
        emitter.emit(SynthEvent.RUN_START, "run_123", {"template": "board_meeting"})
    """

    def __init__(self, enabled: bool = False):
        """
        Initialize the emitter.

        Args:
            enabled: Whether to actually emit events (default False for backward compat)
        """
        self.enabled = enabled
        self.listeners: List[EventListener] = []
        self._event_history: List[SynthEventData] = []
        self._max_history = 1000  # Prevent unbounded growth

    def add_listener(self, listener: EventListener):
        """Register a listener for events."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: EventListener):
        """Remove a registered listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)

    def emit(self, event_type: SynthEvent, run_id: str, data: Optional[Dict[str, Any]] = None):
        """
        Emit an event to all listeners.

        Args:
            event_type: The type of event
            run_id: The current run ID
            data: Additional event data

        Note:
            Listener errors are caught and logged but don't break the workflow.
        """
        if not self.enabled:
            return

        event = SynthEventData(
            event_type=event_type,
            timestamp=time.time(),
            run_id=run_id,
            data=data or {}
        )

        # Store in history (with limit)
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Notify listeners
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                # Don't let listener errors break the workflow
                logger.warning(f"Event listener error: {e}")

    def get_history(self, event_type: Optional[SynthEvent] = None) -> List[SynthEventData]:
        """
        Get event history, optionally filtered by type.

        Args:
            event_type: Filter to specific event type (None = all)

        Returns:
            List of events in chronological order
        """
        if event_type is None:
            return list(self._event_history)
        return [e for e in self._event_history if e.event_type == event_type]

    def clear_history(self):
        """Clear the event history."""
        self._event_history.clear()

    def enable(self):
        """Enable event emission."""
        self.enabled = True

    def disable(self):
        """Disable event emission."""
        self.enabled = False


def logging_listener(event: SynthEventData):
    """
    Default listener that logs events.

    Can be used for debugging or simple monitoring.

    Example:
        emitter = SynthEventEmitter(enabled=True)
        emitter.add_listener(logging_listener)
    """
    logger.debug(f"[SYNTH] {event.event_type.value}: {event.data}")


def console_listener(event: SynthEventData):
    """
    Simple listener that prints to console.

    Useful for development and debugging.
    """
    print(f"[SYNTH {event.timestamp:.3f}] {event.event_type.value}: {event.data}")


# Global emitter instance (disabled by default)
_global_emitter: Optional[SynthEventEmitter] = None


def get_emitter() -> SynthEventEmitter:
    """Get the global event emitter (creates one if needed)."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = SynthEventEmitter(enabled=False)
    return _global_emitter


def set_emitter(emitter: SynthEventEmitter):
    """Set the global event emitter."""
    global _global_emitter
    _global_emitter = emitter
