# ============================================================================
# workflows/clockchain_grounding.py - M20 Clockchain Grounding (Interface Only)
# ============================================================================
"""
Anchor entities to canonical historical events via Clockchain graph lookup.

This is the public interface for M20 Clockchain Grounding. The actual grounding
logic (web search, entity enrichment, Clockchain figure resolution) lives in
the cloud layer (timepoint-pro-cloud-private).

M20 enriches simulation entities with real-world data so that a grounded entity
carries verified facts, documented positions, and recent activity rather than
LLM hallucinations. Grounding flows through the Flash pipeline's
EntityGroundingAgent, which calls search providers and stores structured
GroundingProfile results.

Integration points:
- KnowledgeSeeder: Grounded facts injected as ExposureEvents (M3)
- Entity roster: Templates with entity_roster receive enriched profiles
- Clockchain figures: Grounding status/metadata stored on figure records

See MECHANICS.md M20 section for architectural details.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data models (interface contracts — populated by cloud layer)
# ============================================================================


class GroundingSource(BaseModel):
    """A single source used during entity grounding."""

    url: str
    title: str = ""
    snippet: str = ""
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)


class GroundingProfile(BaseModel):
    """
    Grounded entity profile produced by the EntityGroundingAgent.

    Contains verified real-world data for a simulation entity, anchoring
    the entity to canonical facts rather than LLM-generated assumptions.

    Populated by: timepoint-pro-cloud-private GroundingAugmenter
    Consumed by: KnowledgeSeeder (M3), CharacterBioAgent, entity_roster
    """

    entity_name: str
    entity_id: Optional[str] = None  # Clockchain figure ID, if resolved
    grounding_model: str = ""  # e.g. "perplexity/sonar"
    grounded_at: Optional[datetime] = None
    biography_summary: str = ""
    appearance_description: str = ""
    known_affiliations: list[str] = Field(default_factory=list)
    recent_activity_summary: str = ""
    source_citations: list[str] = Field(default_factory=list)
    sources: list[GroundingSource] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_status: str = "ungrounded"  # ungrounded | grounded | failed | skipped


class GroundingRequest(BaseModel):
    """Request to ground one or more entities against real-world data."""

    entity_names: list[str]
    entity_ids: Optional[list[str]] = None  # Pre-resolved Clockchain figure IDs
    scene_context: str = ""  # Scene description for relevance filtering
    temporal_scope: Optional[str] = None  # ISO date or range for temporal relevance
    include_x_search: bool = False  # Whether to include X/Twitter data
    x_handles: Optional[list[str]] = None  # Specific X handles to search


class GroundingResult(BaseModel):
    """Result of a grounding operation across multiple entities."""

    profiles: dict[str, GroundingProfile] = Field(default_factory=dict)  # name -> profile
    grounded_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_sources: int = 0


# ============================================================================
# M20 Mechanism Interface
# ============================================================================


class M20GroundingMechanism:
    """
    Anchor to canonical historical events. Implementation in cloud layer.

    M20 Clockchain Grounding enriches simulation entities with verified
    real-world data from web search, X/Twitter, and the Clockchain temporal
    graph. This mechanism ensures entities carry factual context rather than
    hallucinated backgrounds.

    This class defines the public interface. All methods raise
    NotImplementedError — the actual grounding logic is proprietary and
    lives in timepoint-pro-cloud-private (GroundingAugmenter service).

    Per-mode injection points:
        FORWARD:     KnowledgeSeeder.seed_knowledge() — initial facts at start date
        DIRECTORIAL: entity_roster voice_guide — character voice + psychology
        PORTAL:      entity_roster + _score_antecedent — capabilities at both endpoints
        BRANCHING:   intervention.parameters — capability ceiling at branch points
        CYCLICAL:    _generate_archetype_cycle entity_metadata — domain facts
    """

    def __init__(self, store: Any = None, config: Optional[dict] = None):
        """
        Initialize the grounding mechanism.

        Args:
            store: GraphStore instance for entity/exposure event persistence.
            config: Optional configuration dict (grounding model, search
                    provider settings, rate limits, etc.).
        """
        self.store = store
        self.config = config or {}

    def ground_entities(
        self, request: GroundingRequest
    ) -> GroundingResult:
        """
        Ground a set of entities against real-world data sources.

        Resolves entity names against Clockchain figures, performs web search
        and optional X/Twitter lookup, and produces GroundingProfile objects
        for downstream consumption by KnowledgeSeeder (M3) and
        CharacterBioAgent.

        Args:
            request: GroundingRequest specifying entities and search parameters.

        Returns:
            GroundingResult with profiles keyed by entity name.

        Raises:
            NotImplementedError: Always. Implementation in cloud layer.
        """
        raise NotImplementedError(
            "M20 Clockchain Grounding implementation is in "
            "timepoint-pro-cloud-private. This is the public interface only."
        )

    def ground_entity(
        self, entity_name: str, entity_id: Optional[str] = None, **kwargs
    ) -> GroundingProfile:
        """
        Ground a single entity by name or Clockchain figure ID.

        Convenience wrapper around ground_entities() for single-entity use.

        Args:
            entity_name: Display name of the entity to ground.
            entity_id: Optional Clockchain figure ID (skips name resolution).
            **kwargs: Additional parameters forwarded to GroundingRequest.

        Returns:
            GroundingProfile for the entity.

        Raises:
            NotImplementedError: Always. Implementation in cloud layer.
        """
        raise NotImplementedError(
            "M20 Clockchain Grounding implementation is in "
            "timepoint-pro-cloud-private. This is the public interface only."
        )

    def inject_grounding_as_exposure_events(
        self,
        profile: GroundingProfile,
        entity_id: str,
        timestamp: Optional[datetime] = None,
    ) -> list[Any]:
        """
        Convert a GroundingProfile into ExposureEvent records (M3 integration).

        Each grounded fact becomes an ExposureEvent with source="clockchain_grounding",
        establishing causal provenance for the entity's real-world knowledge.

        Args:
            profile: Grounded profile to convert.
            entity_id: Target entity ID for exposure events.
            timestamp: Event timestamp (defaults to before scene start).

        Returns:
            List of ExposureEvent objects created.

        Raises:
            NotImplementedError: Always. Implementation in cloud layer.
        """
        raise NotImplementedError(
            "M20 Clockchain Grounding implementation is in "
            "timepoint-pro-cloud-private. This is the public interface only."
        )

    def enrich_entity_roster(
        self, roster: list[dict], scene_context: str = ""
    ) -> list[dict]:
        """
        Enrich a template entity_roster with grounded profiles.

        For templates that define entity_roster (e.g. mars_mission_portal,
        jefferson_dinner), this method grounds each roster entity and injects
        verified data into initial_knowledge, personality_traits, and
        voice_guide fields.

        Args:
            roster: List of entity roster dicts from template configuration.
            scene_context: Scene description for search relevance filtering.

        Returns:
            Enriched roster with grounded data merged in.

        Raises:
            NotImplementedError: Always. Implementation in cloud layer.
        """
        raise NotImplementedError(
            "M20 Clockchain Grounding implementation is in "
            "timepoint-pro-cloud-private. This is the public interface only."
        )

    def check_grounding_status(self, entity_id: str) -> Optional[GroundingProfile]:
        """
        Check if an entity has been previously grounded via Clockchain.

        Queries the Clockchain figures table for existing grounding metadata.
        If the entity is already grounded, returns the cached profile to
        avoid redundant search API calls.

        Args:
            entity_id: Clockchain figure ID to look up.

        Returns:
            GroundingProfile if previously grounded, None otherwise.

        Raises:
            NotImplementedError: Always. Implementation in cloud layer.
        """
        raise NotImplementedError(
            "M20 Clockchain Grounding implementation is in "
            "timepoint-pro-cloud-private. This is the public interface only."
        )
