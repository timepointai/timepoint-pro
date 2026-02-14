"""
Quantitative State Engine (QSE)

Deterministic resource propagation for entity state across timepoints.
This replaces LLM-hallucinated numbers with computed values.

The engine maintains a typed state vector per entity per timepoint:
- resource_levels: consumable quantities (O2, food, water, power)
- physical_metrics: continuous measurements (hull integrity, radiation dose, temperature)
- consumption_rates: per-timestep delta functions
- constraints: min/max bounds and depletion triggers

Propagation is deterministic: state[t+1] = propagate(state[t], events[t], rates).
The LLM receives computed state as context for narrative decisions — it doesn't
hallucinate O2 levels; the engine computes them.

Templates define initial resource pools, consumption rates, and constraint triggers
via the `quantitative_tracking` field in template JSON.
"""

import logging
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from metadata.tracking import track_mechanism

logger = logging.getLogger(__name__)


@dataclass
class ResourceConstraint:
    """A constraint on a quantitative resource."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    critical_threshold: Optional[float] = None
    trigger_event: Optional[str] = None  # Event description when threshold is hit

    def check(self, value: float, resource_name: str) -> List[str]:
        """Return list of violation messages, empty if OK."""
        violations = []
        if self.min_value is not None and value < self.min_value:
            violations.append(f"{resource_name} ({value:.1f}) below minimum ({self.min_value})")
        if self.max_value is not None and value > self.max_value:
            violations.append(f"{resource_name} ({value:.1f}) above maximum ({self.max_value})")
        return violations

    def is_critical(self, value: float) -> bool:
        """Check if resource has hit critical threshold."""
        if self.critical_threshold is not None:
            return value <= self.critical_threshold
        return False


@dataclass
class ResourceDefinition:
    """Definition of a trackable resource from template config."""
    name: str
    unit: str
    initial_value: float
    rate_per_step: float = 0.0  # Negative = consumption, positive = regeneration
    constraint: ResourceConstraint = field(default_factory=ResourceConstraint)
    affects_entities: List[str] = field(default_factory=list)  # Empty = affects all


@dataclass
class EntityResourceState:
    """Quantitative state for a single entity at a single timepoint."""
    entity_id: str
    timepoint_id: str
    resources: Dict[str, float] = field(default_factory=dict)
    critical_alerts: List[str] = field(default_factory=list)
    constraint_violations: List[str] = field(default_factory=list)

    def to_context_dict(self) -> Dict[str, Any]:
        """Format for injection into LLM context."""
        result = {}
        for name, value in self.resources.items():
            result[name] = round(value, 2)
        if self.critical_alerts:
            result["_critical_alerts"] = self.critical_alerts
        return result


@dataclass
class PropagationResult:
    """Result of propagating state from one timepoint to the next."""
    entity_states: Dict[str, EntityResourceState]
    triggered_events: List[str]
    constraint_violations: List[str]
    global_resources: Dict[str, float]


class QuantitativeStateEngine:
    """
    Deterministic resource propagation engine.

    Loads resource definitions from template config and propagates
    them across timepoints with explicit consumption functions.

    Usage:
        engine = QuantitativeStateEngine()
        engine.load_from_template(template_config)
        # At each timepoint:
        result = engine.propagate(timepoint_id, events, entity_ids)
        # Inject computed state into LLM context:
        for entity_id, state in result.entity_states.items():
            context[entity_id]["resource_state"] = state.to_context_dict()
    """

    def __init__(self):
        self.resource_definitions: Dict[str, ResourceDefinition] = {}
        self.global_state: Dict[str, float] = {}  # Shared resources (O2, hull)
        self.entity_states: Dict[str, Dict[str, float]] = {}  # Per-entity resources
        self.history: List[PropagationResult] = []
        self._step_count: int = 0
        self._entity_count: int = 0

    def load_from_template(self, template_config: Dict[str, Any]) -> None:
        """
        Initialize resource definitions from template configuration.

        Reads the `quantitative_tracking` field from template metadata
        and creates ResourceDefinition objects for each tracked resource.

        Args:
            template_config: Full template configuration dict
        """
        metadata = template_config.get("metadata", template_config)
        tracking = metadata.get("quantitative_tracking", {})

        if not tracking:
            logger.debug("No quantitative_tracking in template, QSE inactive")
            return

        for resource_name, config in tracking.items():
            initial = _parse_numeric(config.get("initial", 0))
            rate = _parse_rate(config.get("depletion_rate", config.get("consumption_rate", 0)),
                              config.get("degradation_rate", 0))

            constraint = ResourceConstraint(
                min_value=config.get("min", 0.0 if "percentage" not in config.get("unit", "") else 0.0),
                max_value=config.get("max", None),
                critical_threshold=_parse_numeric(config.get("critical_threshold")),
                trigger_event=config.get("trigger_event", f"{resource_name} critical")
            )

            self.resource_definitions[resource_name] = ResourceDefinition(
                name=resource_name,
                unit=config.get("unit", "units"),
                initial_value=initial,
                rate_per_step=rate,
                constraint=constraint,
                affects_entities=config.get("affects_entities", [])
            )

            # Initialize global state
            self.global_state[resource_name] = initial

        logger.info(f"[QSE] Loaded {len(self.resource_definitions)} resource definitions: "
                    f"{list(self.resource_definitions.keys())}")

    def initialize_entity(self, entity_id: str, entity_config: Optional[Dict] = None) -> None:
        """
        Initialize resource state for a single entity.

        Args:
            entity_id: Entity identifier
            entity_config: Optional per-entity resource overrides from entity_roster
        """
        entity_resources = {}
        for name, defn in self.resource_definitions.items():
            # Check if resource applies to this entity
            if defn.affects_entities and entity_id not in defn.affects_entities:
                continue
            # Use per-entity override if available
            if entity_config and name in entity_config:
                entity_resources[name] = _parse_numeric(entity_config[name])
            else:
                entity_resources[name] = defn.initial_value

        self.entity_states[entity_id] = entity_resources
        self._entity_count = len(self.entity_states)

    @track_mechanism("M4", "constraint_enforcement")
    def propagate(
        self,
        timepoint_id: str,
        entity_ids: List[str],
        events: Optional[List[Dict[str, Any]]] = None,
        event_modifiers: Optional[Dict[str, float]] = None
    ) -> PropagationResult:
        """
        Propagate quantitative state from current step to next.

        Deterministic: state[t+1] = state[t] + rate + event_modifiers.
        The LLM does not influence these numbers — they are computed.

        Args:
            timepoint_id: Current timepoint identifier
            entity_ids: Entities present at this timepoint
            events: Optional list of event dicts that affect resource state
            event_modifiers: Optional dict of {resource_name: delta} from events

        Returns:
            PropagationResult with updated states, triggered events, violations
        """
        self._step_count += 1
        triggered_events = []
        constraint_violations = []
        entity_results = {}

        # Apply global consumption rates
        for resource_name, defn in self.resource_definitions.items():
            if resource_name in self.global_state:
                old_value = self.global_state[resource_name]

                # Apply base rate (scaled by entity count for shared resources)
                entity_factor = len(entity_ids) if defn.affects_entities == [] else 1
                delta = defn.rate_per_step * entity_factor
                new_value = old_value + delta

                # Apply event modifiers
                if event_modifiers and resource_name in event_modifiers:
                    new_value += event_modifiers[resource_name]

                # Enforce constraints
                if defn.constraint.min_value is not None:
                    new_value = max(defn.constraint.min_value, new_value)
                if defn.constraint.max_value is not None:
                    new_value = min(defn.constraint.max_value, new_value)

                self.global_state[resource_name] = new_value

                # Check for critical threshold
                if defn.constraint.is_critical(new_value) and not defn.constraint.is_critical(old_value):
                    event_desc = defn.constraint.trigger_event or f"{resource_name} reached critical level"
                    triggered_events.append(event_desc)
                    logger.warning(f"[QSE] CRITICAL: {resource_name} = {new_value:.1f} "
                                 f"(threshold: {defn.constraint.critical_threshold})")

                # Check constraint violations
                violations = defn.constraint.check(new_value, resource_name)
                constraint_violations.extend(violations)

        # Build per-entity state snapshots
        for entity_id in entity_ids:
            if entity_id not in self.entity_states:
                self.initialize_entity(entity_id)

            # Entity gets a view of all global resources plus their own
            entity_resources = dict(self.global_state)
            entity_resources.update(self.entity_states.get(entity_id, {}))

            alerts = []
            for resource_name, value in entity_resources.items():
                defn = self.resource_definitions.get(resource_name)
                if defn and defn.constraint.is_critical(value):
                    alerts.append(f"{resource_name} at {value:.1f} {defn.unit} (critical)")

            entity_results[entity_id] = EntityResourceState(
                entity_id=entity_id,
                timepoint_id=timepoint_id,
                resources=entity_resources,
                critical_alerts=alerts,
                constraint_violations=[v for v in constraint_violations
                                      if not self.resource_definitions.get(
                                          v.split(" (")[0], ResourceDefinition("", "", 0)
                                      ).affects_entities or
                                      entity_id in self.resource_definitions.get(
                                          v.split(" (")[0], ResourceDefinition("", "", 0)
                                      ).affects_entities]
            )

        result = PropagationResult(
            entity_states=entity_results,
            triggered_events=triggered_events,
            constraint_violations=constraint_violations,
            global_resources=dict(self.global_state)
        )
        self.history.append(result)

        if triggered_events:
            logger.info(f"[QSE] Step {self._step_count} triggered: {triggered_events}")

        return result

    def get_state_summary(self) -> Dict[str, Any]:
        """Get current global resource state as a summary dict."""
        summary = {}
        for name, value in self.global_state.items():
            defn = self.resource_definitions.get(name)
            if defn:
                summary[name] = {
                    "value": round(value, 2),
                    "unit": defn.unit,
                    "critical": defn.constraint.is_critical(value),
                    "rate_per_step": defn.rate_per_step
                }
        return summary

    def get_entity_context(self, entity_id: str) -> Dict[str, Any]:
        """
        Get resource context for a specific entity, suitable for LLM prompt injection.

        Returns a dict like:
        {
            "o2_reserves": 288.0,
            "food_rations": 167.4,
            "hull_integrity": 61.4,
            "_critical_alerts": ["o2_reserves at 48.0 hours (critical)"]
        }
        """
        state = self.entity_states.get(entity_id, {})
        context = {}
        alerts = []

        for name, value in {**self.global_state, **state}.items():
            context[name] = round(value, 2)
            defn = self.resource_definitions.get(name)
            if defn and defn.constraint.is_critical(value):
                alerts.append(f"{name} at {value:.1f} {defn.unit} (critical)")

        if alerts:
            context["_critical_alerts"] = alerts
        return context

    def get_trajectory(self, resource_name: str) -> List[float]:
        """Get the value of a resource at each step."""
        trajectory = []
        for result in self.history:
            value = result.global_resources.get(resource_name)
            if value is not None:
                trajectory.append(value)
        return trajectory

    @property
    def is_active(self) -> bool:
        """Whether the engine has resource definitions loaded."""
        return len(self.resource_definitions) > 0


def _parse_numeric(value: Any) -> Optional[float]:
    """Parse a numeric value from template config, handling strings and None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Try to extract leading number from strings like "6_crew * 0.84_kg_per_hour"
        try:
            return float(value.split()[0].replace("_", ""))
        except (ValueError, IndexError):
            return 0.0
    return 0.0


def _parse_rate(depletion_config: Any, degradation_config: Any = 0) -> float:
    """
    Parse a consumption/degradation rate from template config.

    Rates are negative (consumption) by default. Returns per-step delta.
    Handles string expressions like "6_crew * 0.84_kg_per_hour" by extracting
    numeric components and computing the product.
    """
    if depletion_config and isinstance(depletion_config, str):
        # Parse expressions like "6_crew * 0.84_kg_per_hour"
        parts = depletion_config.replace("_", " ").split("*")
        try:
            rate = 1.0
            for part in parts:
                # Extract first number from each part
                nums = [float(s) for s in part.split() if _is_number(s)]
                if nums:
                    rate *= nums[0]
            return -abs(rate)  # Consumption is negative
        except (ValueError, IndexError):
            pass

    if degradation_config and isinstance(degradation_config, str):
        parts = degradation_config.replace("_", " ").split("*")
        try:
            rate = 1.0
            for part in parts:
                nums = [float(s) for s in part.split() if _is_number(s)]
                if nums:
                    rate *= nums[0]
            return -abs(rate)
        except (ValueError, IndexError):
            pass

    # Direct numeric
    val = _parse_numeric(depletion_config) or _parse_numeric(degradation_config) or 0
    if val > 0:
        val = -val  # Consumption rates are negative
    return val


def _is_number(s: str) -> bool:
    """Check if a string represents a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False
