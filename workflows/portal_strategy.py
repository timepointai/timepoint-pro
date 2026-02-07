"""
Portal Strategy - Backward simulation from fixed endpoint to origin

This module implements PORTAL mode temporal reasoning, where simulations work
backward from a known endpoint (portal) to a known starting point (origin),
discovering plausible paths that connect them.

Example:
    Portal: "John Doe elected President in 2040"
    Origin: "John Doe is VP of Engineering in 2025"
    Goal: Find the most plausible paths from 2025→2040

Architecture:
    - Dual-layer design: PortalStrategy (workflow) + PORTAL TemporalMode (causality rules)
    - Adaptive exploration: system chooses strategy based on complexity
    - Hybrid scoring: LLM + historical + causal + capability + context
    - Forward validation: backward-generated paths must make forward sense
"""

from typing import List, Dict, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
import threading
import numpy as np
import uuid

from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from generation.config_schema import TemporalConfig
from llm_service.model_selector import (
    ActionType,
    TokenBudgetEstimator,
    get_token_estimator
)


class ExplorationMode(str, Enum):
    """Strategies for exploring backward paths"""
    REVERSE_CHRONOLOGICAL = "reverse_chronological"  # 100→99→98→...→1
    OSCILLATING = "oscillating"  # 100→1→99→2→98→3→...
    RANDOM = "random"  # Random step order
    ADAPTIVE = "adaptive"  # System decides based on complexity


# Entity names that should be rejected (common false positives from regex extraction)
ENTITY_BLACKLIST = {
    # Common words that get falsely extracted as entities
    "arr", "series", "series_c", "series_a", "series_b", "revenue", "company",
    "market", "product", "customer", "team", "meeting", "board", "investor",
    "growth", "funding", "round", "deal", "startup", "business", "year",
    "quarter", "month", "week", "day", "time", "we", "they", "the", "this",
    "that", "what", "when", "where", "how", "why", "who", "i", "you",
    # Common business abbreviations that aren't entities
    "arr", "mrr", "saas", "b2b", "b2c", "cac", "ltv", "roi", "kpi",
}


def _validate_entity_id(entity_id: str) -> bool:
    """
    Validate whether an entity ID is legitimate.

    Args:
        entity_id: The entity ID to validate

    Returns:
        True if the entity ID appears valid, False if it should be rejected
    """
    if not entity_id:
        return False

    entity_lower = entity_id.lower().replace("_", "").replace("-", "")

    # Reject blacklisted names
    if entity_lower in ENTITY_BLACKLIST:
        return False

    # Reject very short IDs (likely abbreviations or fragments)
    if len(entity_id) < 3:
        return False

    # Reject purely numeric IDs
    if entity_id.replace("_", "").replace("-", "").isdigit():
        return False

    # Reject IDs that are just repeated characters
    if len(set(entity_lower)) <= 2 and len(entity_lower) > 2:
        return False

    return True


def _filter_entities_by_relevance(
    entities: List[Entity],
    event_description: str,
    known_entity_ids: Optional[set] = None
) -> List[Entity]:
    """
    Filter entities to only include those relevant to an event description.

    This prevents entity hallucination by:
    1. Checking if entity name appears in the description (or known registry)
    2. Validating entity IDs against blacklist
    3. Prioritizing entities with established metadata

    Args:
        entities: List of entities to filter
        event_description: Description of the event/state
        known_entity_ids: Optional set of known valid entity IDs from registry

    Returns:
        Filtered list of relevant entities
    """
    if not entities:
        return []

    description_lower = event_description.lower() if event_description else ""
    filtered = []

    for entity in entities:
        # Validate entity ID
        if not _validate_entity_id(entity.entity_id):
            continue

        # Check if entity is in known registry (if provided)
        if known_entity_ids and entity.entity_id in known_entity_ids:
            filtered.append(entity)
            continue

        # Check if entity name/id appears in description
        entity_name = entity.entity_metadata.get("name", entity.entity_id)
        entity_name_lower = entity_name.lower() if entity_name else ""
        entity_id_lower = entity.entity_id.lower()

        # Check for presence in description
        name_in_desc = entity_name_lower and entity_name_lower in description_lower
        id_in_desc = entity_id_lower in description_lower

        # Check for partial name match (first name, last name)
        name_parts = entity_name_lower.split() if entity_name_lower else []
        partial_match = any(part in description_lower for part in name_parts if len(part) > 3)

        # Include if explicitly mentioned or has strong metadata
        has_role = entity.entity_metadata.get("role")
        has_traits = entity.entity_metadata.get("personality_traits")

        if name_in_desc or id_in_desc or partial_match:
            filtered.append(entity)
        elif has_role or has_traits:
            # Include entities with established metadata (likely important)
            filtered.append(entity)

    return filtered


class FailureResolution(str, Enum):
    """Strategies for handling incoherent paths"""
    PRUNE = "prune"  # Kill invalid path immediately
    BACKTRACK = "backtrack"  # Go back N steps, try different antecedent
    MARK = "mark"  # Flag but continue with path
    RELAX_PORTAL = "relax_portal"  # Modify endpoint slightly


@dataclass
class PortalState:
    """A state at a specific point in the backward simulation"""
    year: int
    description: str
    entities: List[Entity]
    world_state: Dict[str, Any]
    plausibility_score: float = 0.0
    parent_state: Optional['PortalState'] = None  # The state this came from (T+1)
    children_states: List['PortalState'] = field(default_factory=list)  # Possible T-1 states
    month: int = 1  # Month (1-12), defaults to January for backward compatibility
    resolution_level: 'ResolutionLevel' = None  # NEW: Fidelity level for this state

    def __post_init__(self):
        """Ensure children_states is a list, month is valid, resolution defaults to SCENE"""
        if self.children_states is None:
            self.children_states = []
        # Validate month
        if not (1 <= self.month <= 12):
            self.month = 1
        # Default resolution to SCENE if not specified
        if self.resolution_level is None:
            self.resolution_level = ResolutionLevel.SCENE

    def to_year_month_str(self) -> str:
        """Return human-readable year-month string"""
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{month_names[self.month-1]} {self.year}"

    def to_total_months(self) -> int:
        """Convert year + month to total months since year 0"""
        return self.year * 12 + self.month

    @classmethod
    def from_total_months(cls, total_months: int, **kwargs) -> 'PortalState':
        """Create PortalState from total months count"""
        year = total_months // 12
        month = total_months % 12
        if month == 0:  # Handle month 0 → December of previous year
            year -= 1
            month = 12
        return cls(year=year, month=month, **kwargs)


@dataclass
class PortalPath:
    """Complete path from origin to portal"""
    path_id: str
    states: List[PortalState]  # Ordered origin→portal
    coherence_score: float
    pivot_points: List[int] = field(default_factory=list)  # Indices of critical decision states
    explanation: str = ""
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure collections are initialized"""
        if self.pivot_points is None:
            self.pivot_points = []
        if self.validation_details is None:
            self.validation_details = {}


class PortalStrategy:
    """
    Backward simulation strategy for portal-anchored scenarios.

    Process:
    1. Generate portal state from description
    2. Step backward, generating N candidate antecedents per step
    3. Score and rank antecedents using hybrid scoring
    4. Adaptively choose exploration strategy based on complexity
    5. Validate complete paths (origin→portal forward coherence)
    6. Return top K ranked paths with explanations

    Attributes:
        config: TemporalConfig with portal mode settings
        llm: LLM client for state generation and scoring
        store: GraphStore for data persistence
        paths: List of discovered portal paths
    """

    def __init__(self, config: TemporalConfig, llm_client, store):
        """
        Initialize portal strategy.

        Args:
            config: TemporalConfig with mode=PORTAL
            llm_client: LLM client for generation and scoring
            store: GraphStore for persistence
        """
        if config.mode != TemporalMode.PORTAL:
            raise ValueError(f"PortalStrategy requires mode=PORTAL, got {config.mode}")

        self.config = config
        self.llm = llm_client
        self.store = store
        self.paths: List[PortalPath] = []  # Top-ranked paths (backward compatible)
        self.all_paths: List[PortalPath] = []  # ALL generated paths for exploration

        # Validate configuration
        if not config.portal_description:
            raise ValueError("portal_description is required for PORTAL mode")
        if not config.portal_year or not config.origin_year:
            raise ValueError("portal_year and origin_year are required for PORTAL mode")

    def run(self) -> List[PortalPath]:
        """
        Execute portal-anchored backward simulation.

        Returns:
            List of PortalPath objects, ranked by coherence score
        """
        print(f"\n{'='*80}")
        print(f"PORTAL MODE: Backward Simulation")
        print(f"Portal: {self.config.portal_description} ({self.config.portal_year})")
        print(f"Origin: {self.config.origin_year}")
        print(f"Steps: {self.config.backward_steps}")
        print(f"{'='*80}\n")

        # Step 1: Generate portal state
        print("Step 1: Generating portal endpoint state...")
        portal = self._generate_portal_state()
        print(f"✓ Portal state generated: {portal.year}")

        # Step 2: Determine exploration strategy adaptively
        print("\nStep 2: Selecting exploration strategy...")
        strategy = self._select_exploration_strategy()
        print(f"✓ Strategy: {strategy.value}")

        # Step 3: Generate backward paths
        print(f"\nStep 3: Exploring backward paths (generating {self.config.path_count} paths)...")
        candidate_paths = self._explore_backward_paths(portal, strategy)
        print(f"✓ Generated {len(candidate_paths)} candidate paths")

        # Step 4: Validate forward coherence
        print("\nStep 4: Validating forward coherence...")
        valid_paths = self._validate_forward_coherence(candidate_paths)
        print(f"✓ {len(valid_paths)} paths passed coherence threshold ({self.config.coherence_threshold})")

        # Step 5: Rank by hybrid scoring
        print("\nStep 5: Ranking paths by plausibility...")
        ranked_paths = self._rank_paths(valid_paths)

        # Step 6: Compute path divergence analysis FIRST (needed for pivot detection)
        print("\nStep 6: Computing path divergence...")
        divergence_analysis = self._compute_path_divergence(ranked_paths)

        # Step 7: Detect pivot points for ALL paths using divergence data
        print("\nStep 7: Detecting pivot points...")
        for i, path in enumerate(ranked_paths):
            path.pivot_points = self._detect_pivot_points(path, divergence_analysis)
            if i < 5:  # Only log first 5 to avoid spam
                print(f"  Path {i+1}: {len(path.pivot_points)} pivot points detected")
        if len(ranked_paths) > 5:
            print(f"  ... and {len(ranked_paths) - 5} more paths analyzed")

        # Store ALL paths for exploration (the key feature!)
        self.all_paths = ranked_paths

        # Keep top N for backward compatibility
        self.paths = ranked_paths[:self.config.path_count]

        # Attach divergence metadata to all paths
        for path in self.all_paths:
            path.validation_details['divergence'] = divergence_analysis.get(path.path_id, {})

        # Determine what to return based on preserve_all_paths config
        preserve_all = getattr(self.config, 'preserve_all_paths', True)
        return_paths = self.all_paths if preserve_all else self.paths

        print(f"\n{'='*80}")
        print(f"PORTAL SIMULATION COMPLETE")
        print(f"Total paths generated: {len(self.all_paths)}")
        if preserve_all:
            print(f"Returning ALL {len(return_paths)} paths (preserve_all_paths=True)")
        else:
            print(f"Returning top {len(return_paths)} paths (use .all_paths for full list)")
        if divergence_analysis:
            key_divergences = divergence_analysis.get('key_divergence_points', [])
            if key_divergences:
                print(f"Key divergence points: {key_divergences[:5]}")
        # Summarize pivot points across paths
        total_pivots = sum(len(p.pivot_points) for p in return_paths)
        if total_pivots > 0:
            print(f"Total pivot points detected: {total_pivots} across {len(return_paths)} paths")
        print(f"{'='*80}\n")

        return return_paths

    def _generate_portal_state(self) -> PortalState:
        """Generate the endpoint state from description, including entity inference."""
        # Extract entities from portal description using LLM
        entities = self._infer_entities_from_description(self.config.portal_description)

        return PortalState(
            year=self.config.portal_year,
            description=self.config.portal_description,
            entities=entities,
            world_state={"placeholder": True},
            plausibility_score=1.0  # Portal is given, score is 1.0
        )

    def _infer_entities_from_description(self, description: str) -> List[Entity]:
        """
        Infer entities that should exist from a state description.

        Uses LLM to identify entity names and creates placeholder Entity objects.
        Validates entity IDs against blacklist to prevent hallucination.

        Args:
            description: State description text

        Returns:
            List of Entity objects inferred from description (validated)
        """
        if not self.llm:
            # Fallback: extract capitalized names from description
            import re
            potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', description)
            entities = []
            seen = set()
            for name in potential_names[:10]:
                entity_id = name.lower().replace(' ', '_')
                # Validate entity ID before adding
                if entity_id not in seen and _validate_entity_id(entity_id):
                    seen.add(entity_id)
                    entities.append(Entity(
                        entity_id=entity_id,
                        entity_type="person",  # Default type
                        entity_metadata={"name": name, "source": "inferred_from_description"}
                    ))
            return entities

        # Use LLM to infer entities
        try:
            system_prompt = "You are an expert at identifying key entities in narrative descriptions."
            user_prompt = f"""Identify the key entities (people, organizations, places) mentioned or implied in this description.

DESCRIPTION:
{description[:500]}

Return a JSON object with format:
{{"entities": [
  {{"name": "Entity Name", "type": "person|organization|place|concept", "role": "brief role description"}}
]}}

Include 3-10 relevant entities."""

            from pydantic import BaseModel
            from typing import List as TypingList

            class EntityInfo(BaseModel):
                name: str
                type: str
                role: str

            class EntityList(BaseModel):
                entities: TypingList[EntityInfo]

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=EntityList,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=500
            )

            # Convert to Entity objects
            entities = []
            for info in result.entities[:10]:
                entity_id = info.name.lower().replace(' ', '_').replace("'", "")
                entities.append(Entity(
                    entity_id=entity_id,
                    entity_type=info.type,
                    entity_metadata={
                        "name": info.name,
                        "role": info.role,
                        "source": "inferred_from_portal"
                    }
                ))
            return entities

        except Exception as e:
            print(f"    ⚠️  Entity inference from description failed: {e}")
            # Fallback to regex extraction
            import re
            potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', description)
            entities = []
            seen = set()
            for name in potential_names[:10]:
                entity_id = name.lower().replace(' ', '_')
                if entity_id not in seen and len(entity_id) > 2:
                    seen.add(entity_id)
                    entities.append(Entity(
                        entity_id=entity_id,
                        entity_type="person",
                        entity_metadata={"name": name, "source": "fallback_regex"}
                    ))
            return entities

    def _select_exploration_strategy(self) -> ExplorationMode:
        """Adaptively choose exploration strategy based on complexity"""
        if self.config.exploration_mode == "adaptive":
            if self.config.backward_steps > self.config.oscillation_complexity_threshold:
                return ExplorationMode.OSCILLATING
            else:
                return ExplorationMode.REVERSE_CHRONOLOGICAL
        return ExplorationMode(self.config.exploration_mode)

    def _explore_backward_paths(
        self,
        portal: PortalState,
        strategy: ExplorationMode
    ) -> List[PortalPath]:
        """Explore multiple backward paths using selected strategy"""
        if strategy == ExplorationMode.REVERSE_CHRONOLOGICAL:
            return self._explore_reverse_chronological(portal)
        elif strategy == ExplorationMode.OSCILLATING:
            return self._explore_oscillating(portal)
        elif strategy == ExplorationMode.RANDOM:
            return self._explore_random_sampling(portal)
        else:
            raise ValueError(f"Unknown exploration mode: {strategy}")

    def _explore_reverse_chronological(self, portal: PortalState) -> List[PortalPath]:
        """Standard backward stepping: T_n → T_n-1 → ... → T_0

        Uses month-based calculation to support sub-year granularity.
        Ensures smooth temporal progression even when backward_steps > year_range.
        """
        from workflows import TemporalAgent
        from schemas import FidelityPlanningMode

        paths = []
        current_states = [portal]

        # NEW CODE - Query TemporalAgent for strategy:
        # Create temporal agent for this simulation
        temporal_agent = TemporalAgent(mode=self.config.mode, store=self.store, llm_client=self.llm)

        # Get comprehensive fidelity-temporal strategy
        strategy = temporal_agent.determine_fidelity_temporal_strategy(
            config=self.config,
            context={
                'portal_state': portal,
                'origin_year': self.config.origin_year,
                'entities': portal.entities
            }
        )

        print(f"  Fidelity-Temporal Strategy:")
        print(f"    Planning mode: {strategy.planning_mode}")
        print(f"    Budget mode: {strategy.budget_mode}")
        print(f"    Token budget: {strategy.token_budget}")
        print(f"    Timepoints: {strategy.timepoint_count}")
        print(f"    Estimated tokens: {strategy.estimated_tokens}")
        print(f"    Rationale: {strategy.allocation_rationale}")

        # Initialize tracking for month calculation
        portal_month_total = portal.to_total_months()

        for step in range(strategy.timepoint_count):
            next_states = []

            # Determine fidelity and temporal step for this iteration
            if strategy.planning_mode in [FidelityPlanningMode.PROGRAMMATIC]:
                # Use pre-planned schedule
                if step < len(strategy.temporal_steps):
                    month_step = strategy.temporal_steps[step]
                    target_resolution = strategy.fidelity_schedule[step]
                else:
                    # Fallback
                    month_step = 3
                    target_resolution = ResolutionLevel.SCENE
            else:
                # Query agent for adaptive decision
                month_step, target_resolution = temporal_agent.determine_next_step_fidelity_and_time(
                    current_state=current_states[0] if current_states else portal,
                    strategy=strategy,
                    step_num=step,
                    context={
                        'entities': current_states[0].entities if current_states else portal.entities,
                        'importance_score': 0.5,  # TODO: compute from state
                        'state_complexity': 0.5,  # TODO: compute from state
                        'pivot_detected': False  # TODO: detect pivot points
                    }
                )

            # Calculate target month count
            if step == 0:
                portal_month_total = portal.to_total_months()
            step_month_total = portal_month_total - month_step
            portal_month_total = step_month_total  # Update for next iteration

            # Convert to year and month
            step_year = step_month_total // 12
            step_month = step_month_total % 12
            if step_month == 0:  # Handle month 0 → December of previous year
                step_year -= 1
                step_month = 12

            # Create temporary state for logging
            temp_state = PortalState(year=step_year, month=step_month, description="", entities=[], world_state={})
            print(f"  Backward step {step+1}/{strategy.timepoint_count}: {temp_state.to_year_month_str()} @ {target_resolution}")

            # Get parallelization settings
            max_antecedent_workers = getattr(self.config, 'max_antecedent_workers', 3)

            # Process states - parallel if multiple states, sequential if just one
            if len(current_states) > 1 and max_antecedent_workers > 1:
                # Parallel state processing
                print(f"    Processing {len(current_states)} states in parallel ({max_antecedent_workers} workers)...")

                def process_single_state(state: PortalState) -> List[PortalState]:
                    """Process a single state: generate antecedents, score, return top candidates."""
                    antecedents = self._generate_antecedents(
                        state,
                        target_year=step_year,
                        target_month=step_month,
                        target_resolution=target_resolution
                    )
                    scored = self._score_antecedents(antecedents, state)
                    return scored[:self.config.candidate_antecedents_per_step]

                with ThreadPoolExecutor(max_workers=max_antecedent_workers) as executor:
                    futures = [executor.submit(process_single_state, state) for state in current_states]
                    for future in as_completed(futures):
                        try:
                            top_antecedents = future.result()
                            next_states.extend(top_antecedents)
                        except Exception as e:
                            print(f"    ⚠️  State processing failed: {e}")
            else:
                # Sequential processing for single state or disabled parallelism
                for state in current_states:
                    # Generate N candidate antecedents for this state
                    antecedents = self._generate_antecedents(
                        state,
                        target_year=step_year,
                        target_month=step_month,
                        target_resolution=target_resolution
                    )

                    # Score and filter
                    scored = self._score_antecedents(antecedents, state)
                    top_antecedents = scored[:self.config.candidate_antecedents_per_step]

                    next_states.extend(top_antecedents)

            current_states = next_states

            # Prune if too many paths
            if len(current_states) > self.config.path_count * 3:
                current_states = self._prune_low_scoring_paths(current_states)
                print(f"    Pruned to {len(current_states)} states")

        # Convert to complete paths
        for final_state in current_states:
            path = self._reconstruct_path(final_state)
            paths.append(path)

        return paths

    def _explore_oscillating(self, portal: PortalState) -> List[PortalPath]:
        """Oscillating strategy: Fill from both ends inward (100→1→99→2→98→3...)"""
        # TODO: Implement oscillating exploration
        # For now, fall back to reverse chronological
        print("  (Oscillating not yet implemented, using reverse chronological)")
        return self._explore_reverse_chronological(portal)

    def _explore_random_sampling(self, portal: PortalState) -> List[PortalPath]:
        """Random sampling strategy: Fill steps in random order"""
        # TODO: Implement random sampling
        # For now, fall back to reverse chronological
        print("  (Random sampling not yet implemented, using reverse chronological)")
        return self._explore_reverse_chronological(portal)

    def _generate_antecedents(
        self,
        current_state: PortalState,
        target_year: int = None,
        target_month: int = None,
        target_resolution: ResolutionLevel = None,  # NEW
        count: int = None
    ) -> List[PortalState]:
        """
        Generate N plausible previous states using LLM.

        Creates diverse candidate antecedent states that could lead to the consequent.
        Uses structured LLM generation to ensure realistic, varied backward paths.

        Args:
            current_state: The consequent state to work backward from
            target_year: Target year for antecedent states
            target_month: Target month (1-12) for antecedent states
            target_resolution: Target fidelity level for antecedent states
            count: Number of candidates to generate

        Returns:
            List of PortalState objects representing plausible antecedents
        """
        count = count or self.config.candidate_antecedents_per_step
        target_year = target_year or (current_state.year - 1)
        target_month = target_month or 1  # Default to January

        # If no LLM client, fall back to placeholder
        if not self.llm:
            print("    ⚠️  No LLM client available, using placeholder antecedents")
            return self._generate_placeholder_antecedents(current_state, target_year, target_month, target_resolution, count)

        # Build LLM prompt for antecedent generation
        system_prompt = "You are an expert at backward temporal reasoning and counterfactual analysis."

        # Extract key entities with role/description context for better anchoring
        entity_names = [e.entity_id for e in current_state.entities[:10]] if current_state.entities else []
        entity_summary = f"{len(current_state.entities)} entities" if current_state.entities else "No entities yet"
        if current_state.entities:
            entity_details = []
            for e in current_state.entities[:10]:
                name = e.entity_id
                role = e.entity_metadata.get("role", "")
                desc = e.entity_metadata.get("description", "")
                knowledge = e.entity_metadata.get("initial_knowledge", [])
                traits = e.entity_metadata.get("personality_traits", [])
                detail = name
                if role:
                    detail += f" ({role})"
                if desc:
                    detail += f" - {desc}"
                elif knowledge:
                    detail += f" - knows: {', '.join(str(k) for k in knowledge[:3])}"
                if traits:
                    detail += f" [traits: {', '.join(str(t) for t in traits[:3])}]"
                entity_details.append(detail)
            entity_summary = "ENTITIES (use these specific characters in antecedent narratives):\n" + "\n".join(f"  - {d}" for d in entity_details)

        # Create human-readable target time string
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        target_time_str = f"{month_names[target_month-1]} {target_year}"

        user_prompt = f"""Generate {count} DIVERSE and DISTINCT plausible antecedent states that could naturally lead to this consequent state.

CONSEQUENT STATE ({current_state.to_year_month_str()}):
{current_state.description}

{entity_summary}

World Context: {current_state.world_state}

TARGET TIME FOR ANTECEDENTS: {target_time_str}

INSTRUCTIONS:
1. Generate {count} DIFFERENT possible states for {target_time_str}
2. Each should represent a distinct path/strategy/decision that could lead to the consequent
3. Vary the approaches: some gradual, some pivotal moments, some lucky breaks
4. Ensure each is historically/causally plausible
5. Consider: entity capabilities, resource constraints, time requirements, external events
6. CRITICAL: Antecedent narratives MUST feature the SPECIFIC entities listed above by name. Do not invent new characters or drift to unrelated organizations. The story is about THESE people and their decisions.

SPECIFICITY REQUIREMENTS (CRITICAL):
- Use CONCRETE numbers: "$5M Series A" not "raised funding", "42 employees" not "grew team"
- Name SPECIFIC people/companies when plausible: "partnered with Acme Corp" not "found a partner"
- Include TRADE-OFFS: "chose rapid growth over profitability" not just "grew quickly"
- State METRICS: "20% month-over-month growth", "NPS score of 65", "3-month runway"
- Mention ALTERNATIVES rejected: "turned down acquisition offer to pursue IPO path"
- Reference EXTERNAL factors: "benefited from competitor's security breach", "timed launch with industry conference"

For EACH antecedent, provide:
- description: Detailed narrative of what's happening in {target_time_str} (3-4 sentences with specific details)
- key_events: A flat array of 3-5 SHORT STRINGS (not objects). Each string is a one-sentence event description.
  CORRECT: ["NASA approves $200M budget increase in March", "Lin Zhang detects O2 generator anomaly"]
  WRONG: [{"date": "March 2030", "description": "NASA approves budget"}]  ← Do NOT use objects
- entity_changes: Dict mapping entity names to QUANTIFIED changes (skills gained, relationships formed, resources +/-)
- world_context: Dict of contextual factors with SPECIFIC references (market conditions, competitor moves, regulatory changes)
- causal_link: 2-3 sentence explanation connecting this state to the consequent with SPECIFIC causal mechanisms

Return as JSON with an "antecedents" array containing {count} antecedent objects."""

        try:
            # Define schema for structured output
            from pydantic import BaseModel

            class AntecedentSchema(BaseModel):
                description: str
                key_events: List[str]
                entity_changes: Dict[str, Any]  # Changed from Dict[str, str] to accept nested dicts
                world_context: Dict[str, Any]
                causal_link: str

            class AntecedentList(BaseModel):
                """Wrapper for list of antecedents"""
                antecedents: List[AntecedentSchema]

            # Get adaptive token budget based on action type and context
            token_estimator = get_token_estimator()
            token_estimate = token_estimator.estimate(
                ActionType.PORTAL_BACKWARD_REASONING,
                context={"candidate_count": count},
                prompt_length=len(user_prompt)
            )

            # Retry loop for truncation handling
            max_retries = 2
            current_max_tokens = token_estimate.recommended_tokens
            result = None

            for attempt in range(max_retries + 1):
                try:
                    # Call LLM with adaptive token budget
                    result = self.llm.generate_structured(
                        prompt=user_prompt,
                        response_model=AntecedentList,
                        system_prompt=system_prompt,
                        temperature=0.8,  # Higher temp for diversity
                        max_tokens=current_max_tokens
                    )

                    # Check if we got enough antecedents
                    antecedent_data = result.antecedents if hasattr(result, 'antecedents') else []
                    if len(antecedent_data) >= count:
                        # Success - got all requested antecedents
                        if attempt > 0:
                            print(f"    ✓ Retry {attempt} succeeded with {current_max_tokens} tokens")
                        break

                    # Got fewer than expected - might be truncation
                    if attempt < max_retries:
                        current_max_tokens = token_estimator.get_retry_budget(token_estimate, attempt + 1)
                        print(f"    ⚠️  Only got {len(antecedent_data)}/{count} antecedents, retrying with {current_max_tokens} tokens...")
                    else:
                        # Final attempt, use what we got
                        break

                except Exception as e:
                    if attempt < max_retries:
                        # Retry with more tokens on parse errors (likely truncation)
                        current_max_tokens = token_estimator.get_retry_budget(token_estimate, attempt + 1)
                        print(f"    ⚠️  LLM call failed ({e}), retrying with {current_max_tokens} tokens...")
                    else:
                        raise  # Re-raise on final attempt

            # Extract list from wrapper
            antecedent_data = result.antecedents if (result and hasattr(result, 'antecedents')) else []

            # Convert to PortalState objects
            antecedents = []
            for i, data in enumerate(antecedent_data[:count]):  # Limit to requested count
                # Create antecedent state with filtered entities (prevent hallucination)
                # Filter entities to those relevant to this specific antecedent description
                filtered_entities = _filter_entities_by_relevance(
                    current_state.entities,
                    data.description,
                    known_entity_ids=None  # Let validation rules apply
                )

                # FALLBACK: If filtering returned empty, inherit all parent entities
                # This prevents empty entities_present warnings on backward-generated timepoints
                if not filtered_entities and current_state.entities:
                    filtered_entities = current_state.entities

                state = PortalState(
                    year=target_year,
                    month=target_month,
                    resolution_level=target_resolution or ResolutionLevel.SCENE,  # NEW
                    description=data.description,
                    entities=filtered_entities,  # Use filtered entities, not blind copy
                    world_state=data.world_context,
                    plausibility_score=0.0,  # Will be scored later
                    parent_state=current_state
                )

                # Store metadata about this antecedent
                state.world_state['key_events'] = data.key_events
                state.world_state['entity_changes'] = data.entity_changes
                state.world_state['causal_link'] = data.causal_link

                antecedents.append(state)

            # If we got fewer than requested, pad with placeholders
            if len(antecedents) < count:
                print(f"    ⚠️  LLM returned {len(antecedents)}/{count} antecedents, padding with placeholders")
                placeholders = self._generate_placeholder_antecedents(
                    current_state, target_year, target_month, target_resolution, count - len(antecedents)
                )
                antecedents.extend(placeholders)

            return antecedents

        except Exception as e:
            print(f"    ⚠️  LLM generation failed: {e}")
            print(f"    Falling back to placeholder antecedents")
            return self._generate_placeholder_antecedents(current_state, target_year, target_month, target_resolution, count)

    def _generate_placeholder_antecedents(
        self,
        current_state: PortalState,
        target_year: int,
        target_month: int,
        target_resolution: ResolutionLevel = None,  # NEW
        count: int = 1
    ) -> List[PortalState]:
        """Generate placeholder antecedents when LLM is unavailable"""
        antecedents = []
        for i in range(count):
            placeholder_desc = f"Antecedent {i+1} for {current_state.description}"
            # Filter entities even for placeholders to prevent hallucination propagation
            filtered_entities = _filter_entities_by_relevance(
                current_state.entities,
                placeholder_desc,
                known_entity_ids=None
            )
            # FALLBACK: If filtering returned empty, inherit all parent entities
            # This prevents empty entities_present warnings on backward-generated timepoints
            if not filtered_entities and current_state.entities:
                filtered_entities = current_state.entities
            antecedent = PortalState(
                year=target_year,
                month=target_month,
                resolution_level=target_resolution or ResolutionLevel.SCENE,  # NEW
                description=placeholder_desc,
                entities=filtered_entities,  # Use filtered entities
                world_state=current_state.world_state.copy(),
                plausibility_score=0.0,
                parent_state=current_state
            )
            antecedents.append(antecedent)
        return antecedents

    def _run_mini_simulation(
        self,
        candidate_state: PortalState,
        steps: int = None
    ) -> Dict[str, Any]:
        """
        Run forward mini-simulation from candidate state to validate realism.

        This executes a lightweight forward simulation including:
        - State progression (candidate → T+1 → T+2 → ...)
        - Dialog generation between entities (if enabled)
        - Knowledge flow tracking
        - Coherence metrics computation

        The simulation results are used by the judge LLM to evaluate which
        candidate antecedent produces the most realistic forward path.

        TIMEOUT PROTECTION: Uses ThreadPoolExecutor with configurable timeout
        to prevent hangs during LLM calls.

        Args:
            candidate_state: Starting state to simulate forward from
            steps: Number of forward steps (default: config.simulation_forward_steps)

        Returns:
            Dict with:
            - states: List[PortalState] - forward progression
            - dialogs: List[Dict] - generated conversations (if enabled)
            - coherence_metrics: Dict - internal consistency scores
            - simulation_narrative: str - human-readable summary
            - emergent_events: List[str] - unexpected but plausible developments
        """
        steps = steps or self.config.simulation_forward_steps

        # Get timeout from config (with defaults for backward compatibility)
        simulation_timeout = getattr(self.config, 'simulation_timeout_seconds', 180)
        step_timeout = getattr(self.config, 'simulation_step_timeout_seconds', 60)

        def _execute_simulation() -> Dict[str, Any]:
            """Inner function containing simulation logic, wrapped with timeout."""
            # Initialize simulation results
            simulated_states = [candidate_state]
            dialogs = []
            emergent_events = []

            # Limit entities for performance
            max_entities = self.config.simulation_max_entities
            active_entities = candidate_state.entities[:max_entities] if candidate_state.entities else []

            # Calculate month step size based on backward_steps configuration
            portal_month_total = self.config.portal_year * 12 + 1
            origin_month_total = self.config.origin_year * 12 + 1
            total_months = portal_month_total - origin_month_total
            month_step = max(1, total_months // self.config.backward_steps)

            # Simulate forward steps with progress logging
            for step in range(steps):
                current = simulated_states[-1]

                # Calculate next time point using month-based stepping
                current_month_total = current.to_total_months()
                next_month_total = current_month_total + month_step
                next_year = next_month_total // 12
                next_month = next_month_total % 12
                if next_month == 0:  # Handle month 0 → December of previous year
                    next_year -= 1
                    next_month = 12

                # Progress logging
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                next_time_str = f"{month_names[next_month-1]} {next_year}"
                print(f"        Step {step+1}/{steps}: Generating state for {next_time_str}...")

                # Generate next state description using LLM with step-level timeout
                if self.llm:
                    try:
                        # Use ThreadPoolExecutor for step-level timeout
                        with ThreadPoolExecutor(max_workers=1) as step_executor:
                            future = step_executor.submit(
                                self._generate_forward_state, current, next_year, next_month
                            )
                            try:
                                next_state_description = future.result(timeout=step_timeout)
                            except FuturesTimeoutError:
                                print(f"        ⚠️  Step {step+1} timed out after {step_timeout}s, using fallback")
                                next_state_description = f"{next_time_str}: Continuation of {current.description[:50]}..."
                    except Exception as e:
                        print(f"        ⚠️  Forward state generation failed: {e}")
                        next_state_description = f"{next_time_str}: Continuation of {current.description[:50]}..."
                else:
                    next_state_description = f"{next_time_str}: Continuation of {current.description[:50]}..."

                # Create next state
                next_state = PortalState(
                    year=next_year,
                    month=next_month,
                    description=next_state_description,
                    entities=active_entities.copy(),
                    world_state=current.world_state.copy(),
                    plausibility_score=0.0
                )
                simulated_states.append(next_state)

                # Generate dialog if enabled and we have entities
                if self.config.simulation_include_dialog and len(active_entities) >= 2 and self.llm:
                    try:
                        # Use ThreadPoolExecutor for dialog timeout
                        with ThreadPoolExecutor(max_workers=1) as dialog_executor:
                            future = dialog_executor.submit(
                                self._generate_simulation_dialog,
                                current, next_state, active_entities[:3]
                            )
                            try:
                                dialog_data = future.result(timeout=step_timeout)
                                dialogs.append(dialog_data)
                            except FuturesTimeoutError:
                                print(f"        ⚠️  Dialog generation timed out after {step_timeout}s")
                    except Exception as e:
                        print(f"        ⚠️  Dialog generation failed: {e}")

            # Compute coherence metrics
            coherence_metrics = self._compute_simulation_coherence(simulated_states)

            # Generate narrative summary
            narrative = self._generate_simulation_narrative(simulated_states, dialogs)

            return {
                "states": simulated_states,
                "dialogs": dialogs,
                "coherence_metrics": coherence_metrics,
                "simulation_narrative": narrative,
                "emergent_events": emergent_events,
                "candidate_year": candidate_state.year,
                "simulation_end_year": simulated_states[-1].year if simulated_states else candidate_state.year
            }

        # Execute simulation with overall timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_simulation)
            try:
                return future.result(timeout=simulation_timeout)
            except FuturesTimeoutError:
                print(f"      ⚠️  Simulation timed out after {simulation_timeout}s")
                # Return a minimal result to allow graceful degradation
                return {
                    "states": [candidate_state],
                    "dialogs": [],
                    "coherence_metrics": {"coherence": 0.3, "continuity": 0.3, "plausibility": 0.3},
                    "simulation_narrative": f"Simulation timed out after {simulation_timeout}s",
                    "emergent_events": [],
                    "candidate_year": candidate_state.year,
                    "simulation_end_year": candidate_state.year,
                    "timed_out": True
                }

    def _generate_forward_state(self, current_state: PortalState, next_year: int, next_month: int) -> str:
        """Generate description of next state in forward simulation"""
        system_prompt = "You are an expert at forward temporal simulation and causal reasoning."

        # Create human-readable time strings
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_time_str = current_state.to_year_month_str()
        next_time_str = f"{month_names[next_month-1]} {next_year}"

        user_prompt = f"""Given this state, generate a plausible description of what happens at the next time point.

CURRENT STATE ({current_time_str}):
{current_state.description}

World Context: {current_state.world_state}

Generate a concise (2-3 sentences) description of what happens in {next_time_str}.
Consider:
- Natural progression of events from current state
- Realistic timeframes for change
- Entity capabilities and resources
- External factors and constraints

Return only the description text, no extra formatting."""

        try:
            response = self.llm.service.call(
                system=system_prompt,
                user=user_prompt,
                temperature=0.7,
                max_tokens=300,
                call_type="forward_state_generation"
            )
            return response.content.strip()
        except:
            return f"{next_time_str}: Natural continuation of events from {current_time_str}"

    def _generate_simulation_dialog(
        self,
        current_state: PortalState,
        next_state: PortalState,
        entities: List[Entity]
    ) -> Dict[str, Any]:
        """Generate dialog for mini-simulation"""
        if not entities or len(entities) < 2:
            return {}

        # Build simplified dialog prompt
        entity_names = [e.entity_id for e in entities]

        prompt = f"""Generate a brief 2-3 turn dialog between entities during this transition.

FROM ({current_state.to_year_month_str()}): {current_state.description[:200]}

TO ({next_state.to_year_month_str()}): {next_state.description[:200]}

Participants: {', '.join(entity_names[:3])}

Generate realistic dialog showing how entities discuss or react to this transition.
Keep it brief (2-3 turns total) and focused on the key developments."""

        try:
            dialog_data = self.llm.generate_dialog(
                prompt=prompt,
                max_tokens=500,
                model=None  # Use default
            )
            return {
                "year": current_state.year,
                "turns": len(dialog_data.turns) if hasattr(dialog_data, 'turns') else 0,
                "participants": entity_names,
                "summary": f"Dialog between {', '.join(entity_names[:2])} about transition to {next_state.year}"
            }
        except:
            return {
                "year": current_state.year,
                "turns": 0,
                "participants": entity_names,
                "summary": "Dialog generation unavailable"
            }

    def _compute_simulation_coherence(self, states: List[PortalState]) -> Dict[str, float]:
        """Compute coherence metrics for simulation"""
        if len(states) < 2:
            return {"coherence": 1.0, "continuity": 1.0, "plausibility": 1.0}

        # Simple heuristics for coherence
        # In production, these would be more sophisticated

        # Continuity: Do states flow logically?
        continuity = 0.8  # Placeholder

        # Plausibility: Are individual states realistic?
        avg_plausibility = sum(s.plausibility_score for s in states) / len(states) if states else 0.5

        # Overall coherence
        coherence = (continuity + avg_plausibility) / 2

        return {
            "coherence": coherence,
            "continuity": continuity,
            "plausibility": avg_plausibility,
            "state_count": len(states)
        }

    def _generate_simulation_narrative(
        self,
        states: List[PortalState],
        dialogs: List[Dict]
    ) -> str:
        """Generate human-readable narrative summary of simulation"""
        if not states:
            return "Empty simulation"

        start_year = states[0].year
        end_year = states[-1].year
        dialog_count = len(dialogs)

        # Build narrative
        narrative_parts = [
            f"Simulation from {start_year} to {end_year} ({len(states)} states):"
        ]

        # Add key state transitions
        for i, state in enumerate(states):
            if i == 0:
                narrative_parts.append(f"  Start ({state.year}): {state.description[:100]}...")
            elif i == len(states) - 1:
                narrative_parts.append(f"  End ({state.year}): {state.description[:100]}...")

        # Add dialog summary
        if dialog_count > 0:
            narrative_parts.append(f"  Generated {dialog_count} dialog exchanges")

        return "\n".join(narrative_parts)

    def _judge_simulation_realism(
        self,
        candidate_antecedents: List[PortalState],
        simulation_results: List[Dict[str, Any]],
        consequent_state: PortalState
    ) -> List[float]:
        """
        Use judge LLM to evaluate which simulation is most realistic.

        Presents N simulations to judge and asks: "Which of these backward-then-forward
        paths is most plausible?" Judge evaluates based on:
        - Forward simulation coherence
        - Dialog realism (if generated)
        - Internal consistency
        - Natural progression to target state

        Args:
            candidate_antecedents: The N candidate previous states
            simulation_results: Results from _run_mini_simulation() for each
            consequent_state: The state we're trying to reach

        Returns:
            List of scores (0.0-1.0) for each candidate
        """
        if not self.llm or not candidate_antecedents:
            # Fall back to uniform random scores
            return [np.random.uniform(0.5, 1.0) for _ in candidate_antecedents]

        # Build judge prompt
        system_prompt = """You are an expert judge evaluating the realism and plausibility of temporal simulations.

Your task: Rate how realistic each candidate backward path is, based on:
1. Forward simulation coherence - Do events flow logically?
2. Dialog realism - Are conversations natural and contextually appropriate?
3. Internal consistency - Are there contradictions or impossibilities?
4. Causal necessity - Does the antecedent naturally lead to the consequent?
5. Entity capabilities - Can entities actually accomplish what's described?

Rate each candidate 0.0-1.0 where:
- 1.0 = Highly realistic, all aspects coherent
- 0.7 = Plausible with minor issues
- 0.5 = Possible but several concerns
- 0.3 = Implausible, major problems
- 0.0 = Impossible or completely incoherent"""

        # Build candidate descriptions
        candidate_descriptions = []
        for i, (candidate, sim_result) in enumerate(zip(candidate_antecedents, simulation_results)):
            # Extract key information
            candidate_year = candidate.year
            candidate_desc = candidate.description
            narrative = sim_result.get("simulation_narrative", "No narrative")
            coherence = sim_result.get("coherence_metrics", {})
            dialogs = sim_result.get("dialogs", [])

            # Build candidate block
            candidate_block = f"""
CANDIDATE {i+1}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Antecedent Time: {candidate.to_year_month_str()}
Antecedent State: {candidate_desc[:300]}

Forward Simulation:
{narrative}

Coherence Metrics:
- Overall coherence: {coherence.get('coherence', 0.0):.2f}
- Continuity: {coherence.get('continuity', 0.0):.2f}
- State plausibility: {coherence.get('plausibility', 0.0):.2f}

Dialog Summary: {len(dialogs)} conversations generated
{self._format_dialog_summary(dialogs)}

Causal Link: {candidate.world_state.get('causal_link', 'Not specified')}
"""
            candidate_descriptions.append(candidate_block)

        # Combine into full prompt
        user_prompt = f"""Evaluate the realism of these {len(candidate_antecedents)} backward temporal paths.

TARGET STATE (What we need to reach):
Time: {consequent_state.to_year_month_str()}
Description: {consequent_state.description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CANDIDATES TO EVALUATE:

{"".join(candidate_descriptions)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK: Rate each candidate 0.0-1.0 based on realism and plausibility.

Return JSON with:
{{
  "scores": [score1, score2, score3, ...],
  "reasoning": "Brief explanation of your ratings",
  "best_candidate": candidate_number (1-indexed),
  "key_concerns": ["concern1", "concern2", ...]
}}

Focus on: forward coherence, dialog realism, causal necessity, internal consistency."""

        try:
            # Call judge LLM
            from pydantic import BaseModel

            class JudgeResult(BaseModel):
                scores: List[float]
                reasoning: str
                best_candidate: int
                key_concerns: List[str]

            result = self.llm.generate_structured(
                prompt=user_prompt,
                response_model=JudgeResult,
                system_prompt=system_prompt,
                temperature=self.config.judge_temperature,
                max_tokens=1000,
                model=self.config.judge_model
            )

            # Validate and normalize scores
            scores = result.scores[:len(candidate_antecedents)]  # Trim to match candidates

            # Ensure scores are in valid range
            scores = [max(0.0, min(1.0, s)) for s in scores]

            # If we got fewer scores than candidates, pad with average
            if len(scores) < len(candidate_antecedents):
                avg_score = sum(scores) / len(scores) if scores else 0.5
                scores.extend([avg_score] * (len(candidate_antecedents) - len(scores)))

            # Log judge reasoning
            print(f"      Judge: Best candidate #{result.best_candidate}, Reasoning: {result.reasoning[:100]}...")

            return scores

        except Exception as e:
            print(f"      ⚠️  Judge LLM failed: {e}")
            print(f"      Falling back to coherence-based scoring")

            # Fall back to coherence metrics from simulations
            scores = []
            for sim_result in simulation_results:
                coherence = sim_result.get("coherence_metrics", {}).get("coherence", 0.5)
                scores.append(coherence)

            return scores

    def _format_dialog_summary(self, dialogs: List[Dict]) -> str:
        """Format dialog summary for judge prompt"""
        if not dialogs:
            return "  No dialogs generated"

        summaries = []
        for dialog in dialogs[:3]:  # Limit to first 3
            year = dialog.get("year", "?")
            turns = dialog.get("turns", 0)
            summary = dialog.get("summary", "Dialog")
            summaries.append(f"  - Year {year}: {turns} turns - {summary}")

        if len(dialogs) > 3:
            summaries.append(f"  ... and {len(dialogs) - 3} more dialogs")

        return "\n".join(summaries) if summaries else "  No dialog details"

    def _score_antecedents(
        self,
        antecedents: List[PortalState],
        consequent: PortalState
    ) -> List[PortalState]:
        """
        Score antecedents using either simulation judging or static hybrid scoring.

        If use_simulation_judging is enabled, runs forward mini-simulations and uses
        a judge LLM to evaluate realism. Otherwise, uses traditional static scoring.

        Args:
            antecedents: Candidate antecedent states to score
            consequent: The consequent state we're trying to reach

        Returns:
            Sorted list of antecedents by plausibility score (descending)
        """
        # Check if simulation judging is enabled
        if self.config.use_simulation_judging:
            return self._score_antecedents_with_simulation(antecedents, consequent)

        # Traditional static scoring
        scored = []

        for ant in antecedents:
            scores = {
                "llm": self._llm_score(ant, consequent),
                "historical": self._historical_precedent_score(ant, consequent),
                "causal": self._causal_necessity_score(ant, consequent),
                "capability": self._entity_capability_score(ant, consequent),
                "dynamic_context": self._dynamic_context_score(ant, consequent)
            }

            # Weighted average
            total_score = (
                scores["llm"] * self.config.llm_scoring_weight +
                scores["historical"] * self.config.historical_precedent_weight +
                scores["causal"] * self.config.causal_necessity_weight +
                scores["capability"] * self.config.entity_capability_weight +
                scores["dynamic_context"] * 0.1  # Dynamic context as tiebreaker
            )

            ant.plausibility_score = total_score
            scored.append(ant)

        # Sort by score descending
        return sorted(scored, key=lambda s: s.plausibility_score, reverse=True)

    def _score_antecedents_with_simulation(
        self,
        antecedents: List[PortalState],
        consequent: PortalState
    ) -> List[PortalState]:
        """
        Score antecedents by running forward mini-simulations and using judge LLM.

        This is the SIMULATION-BASED JUDGING approach where we:
        1. Run forward simulation from each candidate antecedent
        2. Generate non-deterministic dialog and interactions
        3. Use judge LLM to evaluate which simulation is most realistic
        4. Score based on judge's holistic assessment

        This is computationally expensive but produces much higher quality paths
        than static scoring alone.

        Args:
            antecedents: Candidate antecedent states to evaluate
            consequent: The consequent state we're trying to reach

        Returns:
            Sorted list of antecedents by judge scores (descending)
        """
        if not antecedents:
            return []

        # Get parallelization settings with defaults for backward compatibility
        max_workers = getattr(self.config, 'max_simulation_workers', 4)

        print(f"    🎬 SIMULATION JUDGING MODE (PARALLEL: {max_workers} workers)")
        print(f"    Running mini-simulations for {len(antecedents)} candidates...")
        print(f"    Each simulation: {self.config.simulation_forward_steps} forward steps")
        if self.config.simulation_include_dialog:
            print(f"    Dialog generation: ENABLED")

        # Thread-safe progress tracking
        progress_lock = threading.Lock()
        completed_count = [0]  # Using list to allow mutation in closure

        def run_simulation_with_progress(idx: int, ant: PortalState) -> Tuple[int, Dict[str, Any]]:
            """Run a single simulation and return (index, result) for ordering."""
            try:
                sim_result = self._run_mini_simulation(ant, self.config.simulation_forward_steps)
                with progress_lock:
                    completed_count[0] += 1
                    print(f"      ✓ Candidate {idx+1} complete ({completed_count[0]}/{len(antecedents)}) - year {ant.year}")
                return (idx, sim_result)
            except Exception as e:
                with progress_lock:
                    completed_count[0] += 1
                    print(f"      ⚠️  Candidate {idx+1} failed ({completed_count[0]}/{len(antecedents)}): {e}")
                return (idx, {
                    "states": [ant],
                    "dialogs": [],
                    "coherence_metrics": {"coherence": 0.3},
                    "simulation_narrative": f"Simulation failed: {e}",
                    "emergent_events": [],
                    "candidate_year": ant.year,
                    "simulation_end_year": ant.year
                })

        # Run simulations in parallel
        simulation_results = [None] * len(antecedents)  # Pre-allocate for ordered results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all simulations
            futures = {
                executor.submit(run_simulation_with_progress, i, ant): i
                for i, ant in enumerate(antecedents)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                idx, result = future.result()
                simulation_results[idx] = result

        # Judge all simulations
        print(f"    ⚖️  Judge LLM evaluating realism of {len(antecedents)} simulations...")
        scores = self._judge_simulation_realism(antecedents, simulation_results, consequent)

        # Assign scores to antecedents
        for ant, score in zip(antecedents, scores):
            ant.plausibility_score = score

        # Sort by score descending
        sorted_antecedents = sorted(antecedents, key=lambda s: s.plausibility_score, reverse=True)

        # Print summary
        print(f"    ✓ Simulation judging complete")
        print(f"      Best score: {sorted_antecedents[0].plausibility_score:.3f}")
        print(f"      Score range: {sorted_antecedents[-1].plausibility_score:.3f} - {sorted_antecedents[0].plausibility_score:.3f}")

        return sorted_antecedents

    def _llm_score(self, antecedent: PortalState, consequent: PortalState) -> float:
        """Ask LLM to rate plausibility that antecedent leads to consequent (0-1)"""
        try:
            from pydantic import BaseModel

            class PlausibilityScore(BaseModel):
                score: float
                reasoning: str

            prompt = f"""Rate the plausibility that this earlier state leads to the later state.

EARLIER STATE ({antecedent.year}):
{antecedent.description[:300]}

LATER STATE ({consequent.year}):
{consequent.description[:300]}

Rate plausibility from 0.0 (impossible) to 1.0 (highly plausible).
Consider: Are the causal connections logical? Is the timeline realistic?"""

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=PlausibilityScore,
                system_prompt="You are an expert at evaluating causal plausibility between historical states.",
                temperature=0.3,
                max_tokens=300
            )
            return max(0.0, min(1.0, result.score))
        except Exception as e:
            print(f"    ⚠️  LLM plausibility scoring failed: {e}")
            return np.random.uniform(0.5, 1.0)

    def _historical_precedent_score(self, ant: PortalState, cons: PortalState) -> float:
        """Check if similar transitions have historical precedent"""
        try:
            from pydantic import BaseModel
            from typing import List as TypingList

            class PrecedentScore(BaseModel):
                score: float
                historical_examples: TypingList[str]

            prompt = f"""Has a transition like the following occurred in real history?

FROM ({ant.year}): {ant.description[:250]}
TO ({cons.year}): {cons.description[:250]}

Rate historical precedent from 0.0 (never happened) to 1.0 (well-documented pattern).
Cite up to 3 brief historical examples if any exist."""

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=PrecedentScore,
                system_prompt="You are a historian evaluating whether state transitions have real-world precedent.",
                temperature=0.3,
                max_tokens=400
            )
            return max(0.0, min(1.0, result.score))
        except Exception as e:
            print(f"    ⚠️  Historical precedent scoring failed: {e}")
            return 0.7

    def _causal_necessity_score(self, ant: PortalState, cons: PortalState) -> float:
        """Score how logically REQUIRED the antecedent is for the consequent"""
        try:
            from pydantic import BaseModel
            from typing import List as TypingList

            class NecessityScore(BaseModel):
                score: float
                reasoning: str
                alternatives: TypingList[str]

            prompt = f"""Is the earlier state logically REQUIRED for the later state to occur?

EARLIER STATE ({ant.year}): {ant.description[:250]}
LATER STATE ({cons.year}): {cons.description[:250]}

Rate causal necessity from 0.0 (completely unnecessary, many alternatives) to 1.0 (absolutely required, no alternatives).
List up to 3 alternative paths that could also lead to the later state."""

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=NecessityScore,
                system_prompt="You are an expert in causal reasoning and counterfactual analysis.",
                temperature=0.3,
                max_tokens=400
            )
            return max(0.0, min(1.0, result.score))
        except Exception as e:
            print(f"    ⚠️  Causal necessity scoring failed: {e}")
            return 0.8

    def _entity_capability_score(self, ant: PortalState, cons: PortalState) -> float:
        """Validate that entities can plausibly achieve what the consequent describes"""
        try:
            from pydantic import BaseModel

            class CapabilityScore(BaseModel):
                score: float
                entity_assessments: Dict[str, str]

            # Build entity context
            ant_entities = ", ".join(e.entity_id for e in ant.entities[:8]) if ant.entities else "unknown entities"
            cons_entities = ", ".join(e.entity_id for e in cons.entities[:8]) if cons.entities else "unknown entities"

            prompt = f"""Can the entities in the earlier state plausibly achieve what the later state describes?

EARLIER STATE ({ant.year}): {ant.description[:200]}
Entities: {ant_entities}

LATER STATE ({cons.year}): {cons.description[:200]}
Entities: {cons_entities}

Rate entity capability from 0.0 (impossible given their skills/resources) to 1.0 (well within their capabilities).
Assess key entities briefly."""

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=CapabilityScore,
                system_prompt="You are an expert at assessing whether actors have the skills, resources, and relationships to achieve outcomes.",
                temperature=0.3,
                max_tokens=400
            )
            return max(0.0, min(1.0, result.score))
        except Exception as e:
            print(f"    ⚠️  Entity capability scoring failed: {e}")
            return 0.9

    def _dynamic_context_score(self, ant: PortalState, cons: PortalState) -> float:
        """Score plausibility given economic, political, and technological context"""
        try:
            from pydantic import BaseModel

            class ContextScore(BaseModel):
                score: float
                context_factors: Dict[str, str]

            prompt = f"""Is this transition plausible given the broader world context of the time period?

FROM ({ant.year}): {ant.description[:200]}
TO ({cons.year}): {cons.description[:200]}

Consider economic conditions, political environment, technological capabilities, and social norms of {ant.year}-{cons.year}.
Rate contextual plausibility from 0.0 (anachronistic/impossible for the era) to 1.0 (perfectly fits the period)."""

            result = self.llm.generate_structured(
                prompt=prompt,
                response_model=ContextScore,
                system_prompt="You are a historian specializing in contextual analysis of events within their time periods.",
                temperature=0.3,
                max_tokens=400
            )
            return max(0.0, min(1.0, result.score))
        except Exception as e:
            print(f"    ⚠️  Dynamic context scoring failed: {e}")
            return 0.7

    def _prune_low_scoring_paths(self, states: List[PortalState]) -> List[PortalState]:
        """Prune states below threshold to manage path explosion"""
        sorted_states = sorted(states, key=lambda s: s.plausibility_score, reverse=True)
        return sorted_states[:self.config.path_count * 2]

    def _reconstruct_path(self, leaf_state: PortalState) -> PortalPath:
        """Reconstruct complete path from leaf state to portal"""
        states = []
        current = leaf_state

        # Walk backward to collect all states
        while current is not None:
            states.append(current)
            current = current.parent_state

        # Reverse to get origin→portal order
        states.reverse()

        return PortalPath(
            path_id=f"portal_path_{uuid.uuid4().hex[:8]}",
            states=states,
            coherence_score=0.0,  # Will be computed in validation
            pivot_points=[],
            explanation=""
        )

    def _validate_forward_coherence(self, paths: List[PortalPath]) -> List[PortalPath]:
        """Check if backward-generated paths make sense forward"""
        valid_paths = []

        for path in paths:
            # Simulate forward: Does origin → portal via path make sense?
            coherence = self._check_forward_simulation(path)

            if coherence >= self.config.coherence_threshold:
                path.coherence_score = coherence
                valid_paths.append(path)
            else:
                # Adaptive failure handling
                resolution = self._decide_failure_resolution(path, coherence)

                if resolution == FailureResolution.BACKTRACK:
                    fixed_path = self._attempt_backtrack_fix(path)
                    if fixed_path and fixed_path.coherence_score >= self.config.coherence_threshold:
                        valid_paths.append(fixed_path)

                elif resolution == FailureResolution.MARK:
                    # Include but flag issues
                    path.coherence_score = coherence
                    path.explanation += "\n⚠️ LOW COHERENCE - Review recommended"
                    valid_paths.append(path)

        return valid_paths

    def _check_forward_simulation(self, path: PortalPath) -> float:
        """Simulate forward to check coherence"""
        # TODO: Implement forward simulation validation
        # For now, return weighted average of state plausibility scores
        if not path.states:
            return 0.0

        avg_score = sum(s.plausibility_score for s in path.states) / len(path.states)
        return avg_score

    def _decide_failure_resolution(self, path: PortalPath, coherence: float) -> FailureResolution:
        """Adaptively decide how to handle failed path"""
        if coherence < 0.3:
            return FailureResolution.PRUNE
        elif coherence < 0.5 and self.config.max_backtrack_depth > 0:
            return FailureResolution.BACKTRACK
        elif coherence < self.config.coherence_threshold:
            return FailureResolution.MARK
        else:
            return FailureResolution.PRUNE

    def _attempt_backtrack_fix(self, path: PortalPath) -> Optional[PortalPath]:
        """Try to fix path by backtracking and retrying"""
        # TODO: Implement backtracking
        return None  # Placeholder

    def _rank_paths(self, paths: List[PortalPath]) -> List[PortalPath]:
        """Final ranking by coherence score"""
        return sorted(paths, key=lambda p: p.coherence_score, reverse=True)

    def _detect_pivot_points(
        self,
        path: PortalPath,
        divergence_analysis: Dict[str, Any] = None
    ) -> List[int]:
        """
        Identify critical decision moments (pivot points) in a path.

        Detection strategies:
        1. Divergence-based: Steps where paths diverge significantly (from divergence_analysis)
        2. Keyword-based: State descriptions containing pivot-related language
        3. Event-based: States with key_events indicating inflection points
        4. Score-variance: States with unusually high or low plausibility scores

        Args:
            path: The PortalPath to analyze
            divergence_analysis: Optional pre-computed divergence data from _compute_path_divergence()

        Returns:
            List of state indices that represent pivot points
        """
        pivot_points = set()  # Use set to avoid duplicates

        # --- Strategy 1: Divergence-based detection ---
        # Use key_divergence_points if available (steps where >50% of paths have unique narratives)
        if divergence_analysis:
            key_divergence_steps = divergence_analysis.get('key_divergence_points', [])
            for step_idx in key_divergence_steps:
                if step_idx < len(path.states):
                    pivot_points.add(step_idx)

            # Also check per-step divergence scores for high divergence
            divergence_by_step = divergence_analysis.get('divergence_by_step', [])
            for step_data in divergence_by_step:
                step_idx = step_data.get('step', -1)
                divergence = step_data.get('divergence', 0)
                # Lower threshold: flag steps with >30% unique narratives as potential pivots
                if divergence > 0.3 and step_idx < len(path.states):
                    pivot_points.add(step_idx)

        # --- Strategy 2: Keyword-based detection ---
        # Look for pivot-related language in state descriptions
        pivot_keywords = {
            # Decision language
            'decision', 'decided', 'chose', 'choose', 'choice', 'pivotal', 'pivot',
            'turning point', 'inflection', 'crossroads', 'fork',
            # Strategic actions
            'launched', 'founded', 'acquired', 'merged', 'raised', 'funding', 'series a',
            'series b', 'ipo', 'went public', 'exit',
            # Major changes
            'breakthrough', 'breakthrough', 'transformed', 'revolutionized', 'disrupted',
            'scaled', 'expanded', 'pivoted', 'repositioned',
            # Challenges
            'crisis', 'failed', 'survived', 'recovered', 'overcame',
        }

        for i, state in enumerate(path.states):
            desc_lower = state.description.lower() if state.description else ""

            # Check for keyword matches
            for keyword in pivot_keywords:
                if keyword in desc_lower:
                    pivot_points.add(i)
                    break  # One keyword match is enough per state

        # --- Strategy 3: Event-based detection ---
        # Look for key_events in world_state that indicate inflection points
        for i, state in enumerate(path.states):
            key_events = state.world_state.get('key_events', [])
            if key_events:
                # Check if any key event sounds like a pivot
                for event in key_events:
                    event_lower = str(event).lower() if event else ""
                    # Major event indicators
                    if any(kw in event_lower for kw in ['launch', 'fund', 'acquire', 'hire', 'scale', 'pivot', 'decision']):
                        pivot_points.add(i)
                        break

            # Check entity_changes for significant shifts
            entity_changes = state.world_state.get('entity_changes', {})
            if entity_changes and len(entity_changes) > 2:  # Multiple entity changes = potential pivot
                pivot_points.add(i)

        # --- Strategy 4: Score variance detection ---
        # Flag states with unusually high or low plausibility relative to neighbors
        if len(path.states) >= 3:
            scores = [s.plausibility_score for s in path.states]
            avg_score = sum(scores) / len(scores) if scores else 0.5

            for i, state in enumerate(path.states):
                # Skip edge states for neighbor comparison
                if 0 < i < len(path.states) - 1:
                    prev_score = path.states[i - 1].plausibility_score
                    next_score = path.states[i + 1].plausibility_score
                    curr_score = state.plausibility_score

                    # Large score drop from neighbors suggests uncertainty/pivotal moment
                    if abs(curr_score - prev_score) > 0.2 or abs(curr_score - next_score) > 0.2:
                        pivot_points.add(i)

                # States significantly below average may represent risky/pivotal decisions
                if state.plausibility_score < avg_score - 0.15:
                    pivot_points.add(i)

        # Convert to sorted list
        return sorted(list(pivot_points))

    def _compute_path_divergence(self, paths: List[PortalPath]) -> Dict[str, Any]:
        """
        Compute divergence analysis between all paths.

        Identifies:
        - Key divergence points (where paths differ most)
        - Path clusters (similar vs different paths)
        - Narrative theme differences

        Args:
            paths: List of all ranked paths

        Returns:
            Dict with divergence analysis metadata
        """
        if len(paths) < 2:
            return {'key_divergence_points': [], 'path_clusters': [], 'total_paths': len(paths)}

        # Find divergence points by comparing state descriptions at each timepoint
        divergence_scores = []
        max_states = max(len(p.states) for p in paths)

        for step_idx in range(max_states):
            descriptions_at_step = []
            for path in paths:
                if step_idx < len(path.states):
                    descriptions_at_step.append(path.states[step_idx].description[:100])

            # Simple divergence: count unique descriptions
            unique_count = len(set(descriptions_at_step))
            divergence_ratio = unique_count / max(len(descriptions_at_step), 1)
            divergence_scores.append({
                'step': step_idx,
                'divergence': divergence_ratio,
                'unique_narratives': unique_count,
                'total_paths': len(descriptions_at_step)
            })

        # Find key divergence points (high divergence ratio)
        key_divergence_points = [
            d['step'] for d in divergence_scores
            if d['divergence'] > 0.5  # More than 50% unique narratives = key divergence
        ]

        # Simple path clustering by coherence score ranges
        high_coherence = [p.path_id for p in paths if p.coherence_score >= 0.8]
        medium_coherence = [p.path_id for p in paths if 0.5 <= p.coherence_score < 0.8]
        low_coherence = [p.path_id for p in paths if p.coherence_score < 0.5]

        path_clusters = []
        if high_coherence:
            path_clusters.append({'label': 'high_coherence', 'paths': high_coherence})
        if medium_coherence:
            path_clusters.append({'label': 'medium_coherence', 'paths': medium_coherence})
        if low_coherence:
            path_clusters.append({'label': 'low_coherence', 'paths': low_coherence})

        # Build per-path divergence info
        per_path_divergence = {}
        for path in paths:
            per_path_divergence[path.path_id] = {
                'rank': paths.index(path) + 1,
                'coherence': path.coherence_score,
                'pivot_count': len(path.pivot_points),
                'state_count': len(path.states)
            }

        result = {
            'key_divergence_points': key_divergence_points,
            'path_clusters': path_clusters,
            'total_paths': len(paths),
            'divergence_by_step': divergence_scores,
            'best_path_id': paths[0].path_id if paths else None,
            'score_range': {
                'min': paths[-1].coherence_score if paths else 0,
                'max': paths[0].coherence_score if paths else 0
            }
        }

        # Merge per-path info
        result.update(per_path_divergence)

        print(f"  ✓ Analyzed {len(paths)} paths")
        print(f"  Key divergence at steps: {key_divergence_points[:5]}")
        print(f"  Clusters: {len(path_clusters)} ({', '.join(c['label'] for c in path_clusters)})")

        return result
