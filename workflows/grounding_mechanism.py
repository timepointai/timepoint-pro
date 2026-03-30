# ============================================================================
# workflows/grounding_mechanism.py - M20 Clockchain Grounding (Interface)
# ============================================================================
"""
M20: Clockchain Grounding — anchor entities to canonical historical events.

This module defines the public interface for M20. The actual implementation
lives in the cloud layer (timepoint-pro-cloud-private) and is never shipped
in this open-source repository.

Callers in this repo should catch NotImplementedError and degrade gracefully.
"""

from typing import Any


class M20GroundingMechanism:
    """Anchor to canonical historical events. Implementation in cloud layer."""

    def ground_entities(self, spec: Any) -> Any:
        """
        Augment entity initial_knowledge with grounded facts from web search.

        For each entity in the scene specification, resolves canonical real-world
        data and injects verified facts as initial knowledge before the simulation
        begins. Grounded facts are tagged with source="web_grounding" on the
        resulting ExposureEvents.

        Args:
            spec: SceneSpecification containing the entity roster to ground.

        Returns:
            The same spec with entities enriched with grounded initial_knowledge.

        Raises:
            NotImplementedError: Always — implementation is in the cloud layer.
        """
        raise NotImplementedError(
            "M20 grounding implementation is in the cloud layer (timepoint-pro-cloud-private). "
            "This public interface defines method signatures only."
        )

    def ground_portal_config(self, config: Any) -> Any:
        """
        Ground entity capabilities at both portal endpoints.

        Enriches the entity_roster with capability facts sourced from web search,
        and provides historical_precedent facts used by portal scoring.

        Args:
            config: PortalConfig or equivalent portal-mode configuration object.

        Returns:
            The same config with entity_roster augmented by grounded capability
            facts and historical precedent data.

        Raises:
            NotImplementedError: Always — implementation is in the cloud layer.
        """
        raise NotImplementedError(
            "M20 grounding implementation is in the cloud layer (timepoint-pro-cloud-private). "
            "This public interface defines method signatures only."
        )

    def ground_branching_config(self, config: Any) -> Any:
        """
        Ground entity capability ceilings at branch points.

        Provides realistic upper bounds for entity capabilities in counterfactual
        branches, ensuring branch outcomes remain historically plausible.

        Args:
            config: BranchingConfig or equivalent branching-mode configuration.

        Returns:
            The same config with entity capability ceilings grounded by
            real-world evidence.

        Raises:
            NotImplementedError: Always — implementation is in the cloud layer.
        """
        raise NotImplementedError(
            "M20 grounding implementation is in the cloud layer (timepoint-pro-cloud-private). "
            "This public interface defines method signatures only."
        )
