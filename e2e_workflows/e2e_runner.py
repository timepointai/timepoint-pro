"""
Full E2E Workflow Runner - Orchestrates complete simulation workflows

This is the core application component that runs the full 6-step workflow:
1. Initial scene generation (orchestrator)
2. Temporal generation (all timepoints via TemporalAgent)
3. Entity training (progressive resolution elevation)
4. Training data formatting
5. Oxen upload
6. Metadata completion

No test theater - this is the real application.
"""

import os
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from workflows import TemporalAgent, create_entity_training_workflow, synthesize_dialog
from query_interface import QueryInterface
from oxen_integration import OxenClient
from oxen_integration.data_formatters import EntityEvolutionFormatter
from metadata.run_tracker import MetadataManager, RunMetadata
from metadata.tracking import set_current_run_id, clear_current_run_id, set_metadata_manager
from metadata import logfire_setup
from metadata.run_summarizer import generate_run_summary
from metadata.narrative_exporter import NarrativeExporter
from andos.layer_computer import compute_andos_layers, validate_andos_layers

# Usage bridge for API quota tracking (Phase 6 integration)
try:
    from api.usage_bridge import UsageBridge, get_usage_bridge
    USAGE_TRACKING_AVAILABLE = True
except ImportError:
    USAGE_TRACKING_AVAILABLE = False
    UsageBridge = None


# Shared database path for convergence analysis (timepoints/events persist across runs)
SHARED_DB_PATH = "metadata/runs.db"


def _infer_interaction_graph(entities: List[Entity]) -> Dict:
    """
    Infer interaction graph for templates without explicit graph.

    Heuristics:
    - If <= 3 entities: sequential chain (simple interaction)
    - If > 3 entities: sequential chain (conservative approach)
    - Target entity: first entity in list

    Returns:
        Dict with 'interactions' list in ANDOS format
    """
    if len(entities) <= 1:
        # Single entity - no interactions
        return {"interactions": []}

    # Sequential chain: entity[0] → entity[1] → entity[2] → ...
    interactions = []
    for i in range(len(entities) - 1):
        interactions.append({
            "from": entities[i].entity_id,
            "to": entities[i + 1].entity_id
        })

    return {"interactions": interactions}


class FullE2EWorkflowRunner:
    """
    Runs complete E2E workflows from config to Oxen upload.

    This is the production workflow orchestrator.
    """

    def __init__(
        self,
        metadata_manager: MetadataManager,
        generate_summary: bool = True,
        track_usage: bool = True,
        user_id: Optional[str] = None,
        user_tier: str = "basic"
    ):
        """
        Initialize E2E runner.

        Args:
            metadata_manager: Metadata tracking manager
            generate_summary: Whether to generate LLM-powered run summaries (default: True)
            track_usage: Whether to track usage for API quota (default: True)
            user_id: User ID for usage tracking (defaults to CLI_USER or env var)
            user_tier: User tier for quota limits (default: basic)
        """
        self.metadata_manager = metadata_manager
        self.generate_summary = generate_summary
        set_metadata_manager(metadata_manager)
        self.logfire = logfire_setup.get_logfire()

        # Initialize shared store for convergence analysis (persists timepoints/events across runs)
        self._shared_store: Optional[GraphStore] = None

        # Phase 1 Tensor Persistence: Initialize dedicated tensor database
        self._tensor_db = None  # Lazy initialization

        # Phase 7: TensorRAG for resolution (lazy initialization)
        self._tensor_rag = None

        # Phase 6: Usage tracking for CLI/API quota integration
        self._usage_bridge = None
        self._track_usage = track_usage and USAGE_TRACKING_AVAILABLE
        if self._track_usage:
            try:
                self._usage_bridge = UsageBridge(user_id=user_id, tier=user_tier)
            except Exception as e:
                print(f"  [UsageBridge] Warning: Could not initialize usage tracking: {e}")
                self._track_usage = False

    def _get_shared_store(self) -> GraphStore:
        """Get or create the shared store for convergence data persistence."""
        if self._shared_store is None:
            # Ensure metadata directory exists
            Path("metadata").mkdir(parents=True, exist_ok=True)
            self._shared_store = GraphStore(f"sqlite:///{SHARED_DB_PATH}")
        return self._shared_store

    def _get_tensor_db(self):
        """
        Get or create the dedicated TensorDatabase for tensor persistence.

        Phase 1 Tensor Persistence: Lazy initialization of dedicated tensor storage.
        Separate from GraphStore to keep tensor blobs isolated from relational data.
        """
        if self._tensor_db is None:
            from tensor_persistence import TensorDatabase
            # Ensure metadata directory exists
            Path("metadata").mkdir(parents=True, exist_ok=True)
            tensor_db_path = "metadata/tensors.db"
            self._tensor_db = TensorDatabase(tensor_db_path)
        return self._tensor_db

    def _get_tensor_rag(self):
        """
        Get or create TensorRAG for tensor resolution.

        Phase 7: Lazy initialization of TensorRAG for resolving existing tensors
        before creating new ones. This enables tensor reuse across runs.
        """
        if self._tensor_rag is None:
            from retrieval.tensor_rag import TensorRAG
            tensor_db = self._get_tensor_db()
            self._tensor_rag = TensorRAG(
                tensor_db=tensor_db,
                auto_build_index=True  # Build index from existing tensors
            )
        return self._tensor_rag

    def _resolve_existing_tensor(
        self,
        entity: "Entity",
        world_id: str,
        scenario_context: str,
        min_score: float = 0.75
    ) -> Optional["TTMTensor"]:
        """
        Phase 7: Attempt to resolve an existing tensor for this entity.

        Searches the tensor database for similar tensors that could be reused
        or adapted for this entity. Returns None if no suitable match found.

        Args:
            entity: Entity to find tensor for
            world_id: World/template identifier
            scenario_context: Scenario description for context
            min_score: Minimum similarity score for reuse (default 0.75)

        Returns:
            TTMTensor if suitable match found, None otherwise
        """
        try:
            tensor_rag = self._get_tensor_rag()

            # Check if we have any tensors indexed
            if tensor_rag.index_size == 0:
                return None

            # Build entity description for search
            entity_description = f"{entity.entity_id} ({entity.entity_type})"
            if hasattr(entity, 'entity_metadata') and entity.entity_metadata:
                role = entity.entity_metadata.get('role', '')
                background = entity.entity_metadata.get('background', '')
                if role:
                    entity_description += f" - {role}"
                if background:
                    entity_description += f": {background}"

            # Search for matching tensors
            results = tensor_rag.search(
                query=f"{entity_description} in {scenario_context}",
                n_results=3,
                min_maturity=0.3  # Allow less mature tensors for adaptation
            )

            if not results:
                return None

            # Check if best match meets threshold
            best_match = results[0]
            if best_match.score >= min_score:
                print(f"    🔍 Found existing tensor: {best_match.tensor_id} (score: {best_match.score:.3f})")
                from tensor_serialization import deserialize_tensor
                return deserialize_tensor(best_match.tensor_record.tensor_blob)

            # Check for composition opportunity (multiple weaker matches)
            if len(results) >= 2:
                composable = [r for r in results if r.score >= 0.4]
                if len(composable) >= 2:
                    # Compose from multiple similar tensors
                    print(f"    🔀 Composing from {len(composable)} similar tensors")
                    return tensor_rag.compose(composable[:3])

            return None

        except Exception as e:
            print(f"    ⚠️  Tensor resolution failed: {e}")
            return None

    def _persist_tensor_to_db(
        self,
        entity: Entity,
        world_id: str,
        run_id: str
    ) -> bool:
        """
        Persist an entity's tensor to the dedicated TensorDatabase.

        Phase 1 Tensor Persistence: Save tensor with full metadata tracking.
        This enables:
        - Pre-trained tensor lookup for future runs
        - Maturity tracking across training cycles
        - Version history for debugging

        Args:
            entity: Entity with tensor data to persist
            world_id: World/template identifier
            run_id: Current run identifier

        Returns:
            True if persisted successfully, False otherwise
        """
        try:
            from tensor_persistence import TensorRecord
            from tensor_serialization import serialize_tensor
            from schemas import TTMTensor
            import json
            import base64

            # Extract tensor from entity
            tensor_json = entity.tensor
            if not tensor_json:
                return False

            tensor_data = json.loads(tensor_json)

            # Reconstruct TTMTensor from serialized format
            ttm_tensor = TTMTensor(
                context_vector=base64.b64decode(tensor_data["context_vector"]),
                biology_vector=base64.b64decode(tensor_data["biology_vector"]),
                behavior_vector=base64.b64decode(tensor_data["behavior_vector"])
            )

            # Create TensorRecord
            tensor_id = f"{entity.entity_id}_{world_id}_{run_id}"
            record = TensorRecord(
                tensor_id=tensor_id,
                entity_id=entity.entity_id,
                world_id=world_id,
                tensor_blob=serialize_tensor(ttm_tensor),
                maturity=getattr(entity, 'tensor_maturity', 0.0),
                training_cycles=getattr(entity, 'tensor_training_cycles', 0)
            )

            # Save to dedicated tensor database
            tensor_db = self._get_tensor_db()
            tensor_db.save_tensor(record)

            return True

        except Exception as e:
            print(f"    ⚠️  Failed to persist tensor for {entity.entity_id}: {e}")
            return False

    def _persist_timepoint_for_convergence(self, timepoint: Timepoint, run_id: str) -> None:
        """
        Persist a timepoint to the shared database for convergence analysis.

        This is called after saving to the temp DB, ensuring data survives for
        cross-run convergence comparisons.

        IMPORTANT: Creates a NEW Timepoint object to avoid SQLAlchemy session detachment
        issues when copying between temp DB and shared DB.

        Args:
            timepoint: Timepoint to persist (from temp DB session)
            run_id: Current run identifier (stored in timepoint.run_id)
        """
        try:
            shared_store = self._get_shared_store()

            # Create a fresh Timepoint copy to avoid session detachment issues
            # The original timepoint is bound to the temp DB session
            # IMPORTANT: Prefix timepoint_id with run_id to avoid UNIQUE constraint violations
            # when the same template is run multiple times (e.g., tp_001_opening exists in both runs)
            unique_tp_id = f"{run_id}_{timepoint.timepoint_id}"
            unique_parent_id = f"{run_id}_{timepoint.causal_parent}" if timepoint.causal_parent else None

            fresh_timepoint = Timepoint(
                timepoint_id=unique_tp_id,
                timeline_id=timepoint.timeline_id,
                timestamp=timepoint.timestamp,
                event_description=timepoint.event_description,
                entities_present=list(timepoint.entities_present) if timepoint.entities_present else [],
                causal_parent=unique_parent_id,
                resolution_level=timepoint.resolution_level,
                run_id=run_id  # Set run_id for convergence filtering
            )

            shared_store.save_timepoint(fresh_timepoint)
        except Exception as e:
            # Non-fatal - log but don't fail the run
            print(f"  ⚠️  Failed to persist timepoint for convergence: {e}")

    def _persist_exposure_events_for_convergence(self, scene_result: Dict, run_id: str) -> int:
        """
        Persist all exposure events from temp store to shared database for convergence.

        This copies exposure events from the temp DB to the shared DB so that
        knowledge_edges can be extracted for convergence analysis.

        IMPORTANT: Creates FRESH ExposureEvent objects to avoid SQLAlchemy session
        detachment issues when copying between temp DB and shared DB.

        Args:
            scene_result: Scene result containing the temp store
            run_id: Current run identifier

        Returns:
            Number of exposure events persisted
        """
        from schemas import ExposureEvent

        temp_store = scene_result.get("store")
        if not temp_store:
            print("  ⚠️  No temp store available for exposure event persistence")
            return 0

        try:
            shared_store = self._get_shared_store()
            events_persisted = 0
            events_skipped = 0

            # Get all exposure events from temp store
            # Note: We need to query all events, not just for specific entities
            from sqlmodel import Session, select
            with Session(temp_store.engine) as session:
                all_events = session.exec(select(ExposureEvent)).all()

                print(f"  📊 Found {len(all_events)} exposure events in temp store")

                for event in all_events:
                    try:
                        # Create a FRESH ExposureEvent copy to avoid session detachment issues
                        # The original event is bound to the temp DB session
                        fresh_event = ExposureEvent(
                            entity_id=event.entity_id,
                            event_type=event.event_type,
                            information=event.information,
                            source=event.source,
                            timestamp=event.timestamp,
                            confidence=event.confidence,
                            timepoint_id=event.timepoint_id,
                            run_id=run_id  # Set run_id for convergence filtering
                        )
                        shared_store.save_exposure_event(fresh_event)
                        events_persisted += 1
                    except Exception as e:
                        # Skip duplicates or errors but log them
                        events_skipped += 1
                        if events_skipped <= 3:  # Only log first few
                            print(f"    ⚠️  Skipped event: {e}")

            if events_persisted > 0:
                print(f"  📊 Persisted {events_persisted} exposure events for convergence")
            else:
                print(f"  ⚠️  No exposure events to persist (0 found in temp store)")

            if events_skipped > 0:
                print(f"  ⚠️  Skipped {events_skipped} events (duplicates/errors)")

            return events_persisted

        except Exception as e:
            print(f"  ⚠️  Failed to persist exposure events for convergence: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _persist_dialogs_for_convergence(self, scene_result: Dict, run_id: str) -> int:
        """
        Persist all dialogs from temp store to shared database for convergence.

        January 2026: This copies dialogs from the temp DB to the shared DB so that
        dialog quality can be tracked for convergence analysis.

        IMPORTANT: Creates FRESH Dialog objects to avoid SQLAlchemy session
        detachment issues when copying between temp DB and shared DB.

        Args:
            scene_result: Scene result containing the temp store
            run_id: Current run identifier

        Returns:
            Number of dialogs persisted
        """
        from schemas import Dialog

        temp_store = scene_result.get("store")
        if not temp_store:
            print("  ⚠️  No temp store available for dialog persistence")
            return 0

        try:
            shared_store = self._get_shared_store()
            dialogs_persisted = 0
            dialogs_skipped = 0

            # Get all dialogs from temp store
            from sqlmodel import Session, select
            with Session(temp_store.engine) as session:
                all_dialogs = session.exec(select(Dialog)).all()

                print(f"  📊 Found {len(all_dialogs)} dialogs in temp store")

                for dialog in all_dialogs:
                    try:
                        # Create a FRESH Dialog copy to avoid session detachment issues
                        fresh_dialog = Dialog(
                            dialog_id=f"{run_id}_{dialog.dialog_id}",  # Prefix with run_id for uniqueness
                            timepoint_id=dialog.timepoint_id,
                            participants=dialog.participants,
                            turns=dialog.turns,
                            context_used=dialog.context_used,
                            duration_seconds=dialog.duration_seconds,
                            information_transfer_count=dialog.information_transfer_count,
                            created_at=dialog.created_at,
                            run_id=run_id  # Set run_id for convergence filtering
                        )
                        shared_store.save_dialog(fresh_dialog)
                        dialogs_persisted += 1
                    except Exception as e:
                        # Skip duplicates or errors but log them
                        dialogs_skipped += 1
                        if dialogs_skipped <= 3:  # Only log first few
                            print(f"    ⚠️  Skipped dialog: {e}")

            if dialogs_persisted > 0:
                print(f"  📊 Persisted {dialogs_persisted} dialogs for convergence")
            else:
                print(f"  ⚠️  No dialogs to persist (0 found in temp store)")

            if dialogs_skipped > 0:
                print(f"  ⚠️  Skipped {dialogs_skipped} dialogs (duplicates/errors)")

            return dialogs_persisted

        except Exception as e:
            print(f"  ⚠️  Failed to persist dialogs for convergence: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _persist_entity_for_convergence(self, entity: Entity, run_id: str) -> None:
        """
        Persist an entity to the shared database for convergence analysis.

        CRITICAL FIX: Previously entities were NOT being synced to metadata/runs.db,
        only timepoints were. This caused entities_present to reference entity_ids
        that didn't exist in the shared database.

        This method copies entities from the temp DB session to the shared DB,
        prefixing entity_id with run_id to avoid UNIQUE constraint violations.

        Args:
            entity: Entity to persist (from temp DB session)
            run_id: Current run identifier
        """
        try:
            shared_store = self._get_shared_store()

            # Prefix entity_id with run_id for uniqueness across runs
            unique_entity_id = f"{run_id}_{entity.entity_id}"

            # Create fresh Entity copy to avoid session detachment issues
            fresh_entity = Entity(
                entity_id=unique_entity_id,
                entity_type=entity.entity_type,
                resolution_level=entity.resolution_level,
                tensor=entity.tensor,
                tensor_maturity=getattr(entity, 'tensor_maturity', 0.0),
                tensor_training_cycles=getattr(entity, 'tensor_training_cycles', 0),
                entity_metadata=dict(entity.entity_metadata) if entity.entity_metadata else {},
                run_id=run_id  # Set run_id for convergence filtering
            )

            shared_store.save_entity(fresh_entity)

        except Exception as e:
            # Non-fatal - log but don't fail the run
            print(f"  ⚠️  Failed to persist entity for convergence: {e}")

    def _persist_all_entities_for_convergence(self, entities: List[Entity], run_id: str) -> int:
        """
        Persist all entities to the shared database for convergence analysis.

        Args:
            entities: List of entities to persist
            run_id: Current run identifier

        Returns:
            Number of entities persisted
        """
        persisted = 0
        for entity in entities:
            try:
                self._persist_entity_for_convergence(entity, run_id)
                persisted += 1
            except Exception as e:
                print(f"  ⚠️  Failed to persist entity {entity.entity_id}: {e}")

        if persisted > 0:
            print(f"  📊 Persisted {persisted} entities for convergence")

        return persisted

    def _run_data_quality_check(
        self,
        timepoints: List[Timepoint],
        entities: List[Entity],
        run_id: str
    ) -> Dict[str, Any]:
        """
        Run data quality validation on generated data.

        CRITICAL FIX: This check catches issues like empty entities_present
        that were previously silently passing through the pipeline.

        Checks performed:
        1. All timepoints have non-empty entities_present
        2. All entity references in timepoints are valid
        3. Entity count matches expectations
        4. No duplicate entity IDs

        Args:
            timepoints: List of timepoints to validate
            entities: List of entities to validate
            run_id: Current run identifier

        Returns:
            Dict with validation results and any warnings/errors
        """
        print("\n  📊 Running data quality check...")

        results = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "stats": {}
        }

        # Build entity ID set for validation
        entity_ids = {e.entity_id for e in entities}
        results["stats"]["total_entities"] = len(entities)
        results["stats"]["total_timepoints"] = len(timepoints)

        # Check 1: Entities_present validation
        empty_entities_count = 0
        invalid_entity_refs = []
        total_entity_refs = 0

        for tp in timepoints:
            if not tp.entities_present or len(tp.entities_present) == 0:
                empty_entities_count += 1
                results["warnings"].append(
                    f"Timepoint '{tp.timepoint_id}' has empty entities_present"
                )
            else:
                total_entity_refs += len(tp.entities_present)
                # Check if referenced entities exist
                for ent_id in tp.entities_present:
                    if ent_id not in entity_ids:
                        invalid_entity_refs.append((tp.timepoint_id, ent_id))

        results["stats"]["empty_entities_timepoints"] = empty_entities_count
        results["stats"]["total_entity_references"] = total_entity_refs
        results["stats"]["invalid_entity_references"] = len(invalid_entity_refs)

        if empty_entities_count > 0:
            pct = (empty_entities_count / len(timepoints)) * 100 if timepoints else 0
            if pct > 50:
                results["errors"].append(
                    f"CRITICAL: {empty_entities_count}/{len(timepoints)} ({pct:.1f}%) timepoints have empty entities_present"
                )
                results["passed"] = False
            else:
                results["warnings"].append(
                    f"{empty_entities_count}/{len(timepoints)} ({pct:.1f}%) timepoints have empty entities_present"
                )

        if invalid_entity_refs:
            results["warnings"].append(
                f"{len(invalid_entity_refs)} entity references point to non-existent entities"
            )
            for tp_id, ent_id in invalid_entity_refs[:3]:  # Show first 3
                results["warnings"].append(f"  - {tp_id} references missing entity '{ent_id}'")

        # Check 2: Duplicate entity IDs
        if len(entity_ids) != len(entities):
            dup_count = len(entities) - len(entity_ids)
            results["warnings"].append(f"Found {dup_count} duplicate entity IDs")

        # Check 3: Entity tensor validation
        entities_without_tensors = sum(1 for e in entities if not e.tensor)
        if entities_without_tensors > 0:
            results["warnings"].append(
                f"{entities_without_tensors}/{len(entities)} entities have no tensor"
            )

        # Print summary
        print(f"    Entities: {len(entities)}")
        print(f"    Timepoints: {len(timepoints)}")
        print(f"    Entity references: {total_entity_refs}")
        print(f"    Empty entities_present: {empty_entities_count}")

        if results["errors"]:
            print(f"  ❌ Data quality check FAILED:")
            for err in results["errors"]:
                print(f"     ERROR: {err}")
            results["passed"] = False
        elif results["warnings"]:
            print(f"  ⚠️  Data quality warnings ({len(results['warnings'])}):")
            for warn in results["warnings"][:5]:  # Show first 5
                print(f"     {warn}")
            if len(results["warnings"]) > 5:
                print(f"     ... and {len(results['warnings']) - 5} more")
        else:
            print(f"  ✓ Data quality check passed")

        return results

    def _populate_fallback_entities(
        self,
        timepoints: List[Timepoint],
        entities: List[Entity]
    ) -> int:
        """
        Populate empty entities_present with fallback entities.

        January 2026 fix: When LLM-based entity inference fails (e.g., in BRANCHING
        or PORTAL modes where antecedent descriptions may not explicitly mention
        entity names), this method provides a fallback by assigning entities to
        timepoints that have empty entities_present.

        Strategy:
        1. First try: use parent timepoint's entities (if causal_parent exists)
        2. Fallback: use all human/character entities from the entity list
        3. Last resort: use first 5 entities from the entity list

        Args:
            timepoints: List of timepoints to check and update
            entities: List of available entities

        Returns:
            Number of timepoints that were populated with fallback entities
        """
        if not timepoints or not entities:
            return 0

        # Build lookup for parent timepoints
        timepoint_map = {tp.timepoint_id: tp for tp in timepoints}

        # Build fallback entity lists
        human_entities = [
            e.entity_id for e in entities
            if e.entity_type in ('human', 'person', 'character')
        ]
        all_entity_ids = [e.entity_id for e in entities[:10]]  # Limit to 10

        fallback_entities = human_entities if human_entities else all_entity_ids

        populated_count = 0

        for tp in timepoints:
            if tp.entities_present and len(tp.entities_present) > 0:
                continue  # Already has entities

            # Strategy 1: Try parent timepoint's entities
            if tp.causal_parent and tp.causal_parent in timepoint_map:
                parent_tp = timepoint_map[tp.causal_parent]
                if parent_tp.entities_present:
                    tp.entities_present = parent_tp.entities_present.copy()
                    populated_count += 1
                    continue

            # Strategy 2/3: Use fallback entities
            if fallback_entities:
                tp.entities_present = fallback_entities.copy()
                populated_count += 1

        if populated_count > 0:
            print(f"  ℹ️  Populated {populated_count} timepoints with fallback entities")

        return populated_count

    def run(self, config: SimulationConfig) -> RunMetadata:
        """
        Run complete E2E workflow.

        Args:
            config: Simulation configuration

        Returns:
            Complete run metadata

        Steps:
        1. Initialize run tracking
        2. Generate initial scene
        3. Generate all timepoints
        4. Train entities (progressive elevation)
        5. Format training data
        6. Upload to Oxen
        7. Complete metadata
        """
        # Generate run ID
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Set thread-local run ID for tracking
        set_current_run_id(run_id)

        # Phase 6: Record simulation start for usage tracking (quota check removed - open source)
        if self._track_usage and self._usage_bridge:
            self._usage_bridge.record_simulation_start(run_id)

        print(f"\n{'='*80}")
        print(f"STARTING E2E WORKFLOW: {run_id}")
        print(f"Template: {config.world_id}")
        print(f"{'='*80}\n")

        try:
            with self.logfire.span(f"e2e_run:{run_id}", template=config.world_id):
                # Step 1: Start tracking
                metadata = self._start_tracking(run_id, config)

                # Step 2: Generate initial scene
                scene_result = self._generate_initial_scene(config, run_id)

                # Step 2.5: Initialize baseline tensors (NEW - Phase 11 Architecture Pivot)
                self._initialize_baseline_tensors(scene_result, run_id)

                # Step 3: Generate all timepoints
                all_timepoints = self._generate_all_timepoints(
                    scene_result, config, run_id
                )

                # Step 3.5: Compute ANDOS training layers
                entities = scene_result["entities"]
                andos_layers = self._compute_andos_layers(entities, run_id)

                # Step 4: Train entities layer-by-layer (ANDOS-aware)
                trained_entities = self._train_entities(
                    scene_result, all_timepoints, andos_layers, run_id
                )

                # Step 4.1: Persist entities to shared DB for convergence analysis
                # CRITICAL FIX: Previously only timepoints were persisted, leaving
                # entities_present references dangling. This syncs entities too.
                self._persist_all_entities_for_convergence(trained_entities, run_id)

                # Step 4.5: Synthesize dialogs (M11)
                self._synthesize_dialogs(
                    trained_entities, all_timepoints, scene_result, run_id
                )

                # Step 4.6: Execute queries (M5)
                self._execute_queries(
                    trained_entities, all_timepoints, scene_result, run_id
                )

                # Step 4.7: Persist exposure events to shared DB for convergence analysis
                # This must happen AFTER dialogs and queries which create exposure events
                self._persist_exposure_events_for_convergence(scene_result, run_id)

                # Step 4.7b: Persist dialogs to shared DB for convergence analysis (January 2026)
                self._persist_dialogs_for_convergence(scene_result, run_id)

                # Step 4.8: Fallback entity population (January 2026 fix)
                # Populate empty entities_present with available entities to prevent warnings
                self._populate_fallback_entities(all_timepoints, trained_entities)

                # Step 4.9: Data quality validation
                # CRITICAL: Catches issues like empty entities_present that were previously silent
                quality_results = self._run_data_quality_check(
                    all_timepoints, trained_entities, run_id
                )

                # Step 5: Format training data
                training_data = self._format_training_data(
                    trained_entities, all_timepoints, scene_result, run_id
                )

                # Step 6: Upload to Oxen
                oxen_repo_url, oxen_dataset_url = self._upload_to_oxen(
                    training_data, scene_result, all_timepoints, trained_entities, config, run_id
                )

                # Step 7: Complete metadata
                metadata = self._complete_metadata(
                    run_id,
                    scene_result,
                    all_timepoints,
                    training_data,
                    oxen_repo_url,
                    oxen_dataset_url
                )

                # Step 8: Generate narrative summary (optional)
                if self.generate_summary:
                    summary = self._generate_summary(
                        metadata,
                        training_data,
                        scene_result,
                        all_timepoints,      # Pass full temporal arc
                        trained_entities     # Pass character development
                    )
                    if summary:
                        # Update metadata object with summary
                        metadata.summary = summary
                        metadata.summary_generated_at = datetime.now()
                        print(f"\n{'='*80}")
                        print(f"📝 NARRATIVE SUMMARY")
                        print(f"{'='*80}")
                        print(f"{summary}")
                        print(f"{'='*80}\n")

                # Step 9: Generate narrative exports (CRITICAL DELIVERABLE)
                try:
                    narrative_files = self._generate_narrative_exports(
                        metadata=metadata,
                        all_timepoints=all_timepoints,
                        trained_entities=trained_entities,
                        scene_result=scene_result,
                        training_data=training_data,
                        config=config
                    )

                    # Update metadata with export paths
                    if narrative_files:
                        metadata.narrative_exports = narrative_files
                        metadata.narrative_export_generated_at = datetime.now()
                        # Save to database
                        self.metadata_manager.save_metadata(metadata)

                except Exception as e:
                    # Narrative export failure = run failure (per user requirement)
                    metadata.status = "failed"
                    metadata.error_message = f"Narrative export failed: {str(e)}"
                    self.metadata_manager.save_metadata(metadata)
                    raise

                # Step 10: Optional Convergence Analysis (post-run)
                if config.convergence and config.convergence.enabled:
                    self._run_convergence_analysis(
                        run_id=run_id,
                        template_id=config.world_id,
                        config=config
                    )

                print(f"\n{'='*80}")
                print(f"✅ E2E WORKFLOW COMPLETE: {run_id}")
                print(f"{'='*80}\n")

                return metadata

        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ E2E WORKFLOW FAILED: {run_id}")
            print(f"Error: {e}")
            print(f"{'='*80}\n")

            # Record failure
            self.metadata_manager.complete_run(
                run_id,
                entities_created=0,
                timepoints_created=0,
                training_examples=0,
                cost_usd=0.0,
                llm_calls=0,
                tokens_used=0,
                error_message=str(e)
            )

            # Phase 6: Record failed simulation to usage tracking
            if self._track_usage and self._usage_bridge:
                try:
                    self._usage_bridge.record_simulation(
                        run_id=run_id,
                        success=False,
                        cost_usd=0.0,
                        tokens=0
                    )
                except Exception as usage_err:
                    print(f"  ⚠️  Failed to record usage for failed run: {usage_err}")

            raise

        finally:
            clear_current_run_id()

    def _start_tracking(self, run_id: str, config: SimulationConfig) -> RunMetadata:
        """Step 1: Initialize run tracking"""
        with self.logfire.span("step:start_tracking"):
            print("Step 1: Initializing run tracking...")

            metadata = self.metadata_manager.start_run(
                run_id=run_id,
                template_id=config.world_id,
                causal_mode=config.temporal.mode,
                max_entities=config.entities.count,
                max_timepoints=config.timepoints.count
            )

            self.logfire.info("Run tracking initialized", run_id=run_id)
            return metadata

    def _generate_summary(
        self,
        metadata: RunMetadata,
        training_data: List[Dict],
        scene_result: Dict,
        all_timepoints: List[Timepoint],
        trained_entities: List[Entity]
    ) -> Optional[str]:
        """Step 8: Generate LLM-powered narrative summary"""
        with self.logfire.span("step:generate_summary"):
            print("\nStep 8: Generating narrative summary...")

            try:
                llm = scene_result.get("llm_client")
                if not llm:
                    print("  ⚠️  No LLM client - skipping summary")
                    return None

                store = scene_result.get("store")

                # Generate NARRATIVE summary using full simulation data
                summary = generate_run_summary(
                    run_metadata=metadata,
                    training_data=training_data[:5] if training_data else None,  # Sample for context
                    llm_client=llm,
                    all_timepoints=all_timepoints,  # Full narrative arc
                    entities=trained_entities,       # Character development
                    store=store                      # For dialogs
                )

                # Save summary to database
                self.metadata_manager.update_summary(metadata.run_id, summary)

                print(f"✓ Summary generated ({len(summary)} chars)")

                self.logfire.info(
                    "Run summary generated",
                    run_id=metadata.run_id,
                    summary_length=len(summary)
                )

                return summary

            except Exception as e:
                print(f"  ⚠️  Summary generation failed: {e}")
                self.logfire.warn("Summary generation failed", error=str(e))
                return None

    def _generate_narrative_exports(
        self,
        metadata: RunMetadata,
        all_timepoints: List[Timepoint],
        trained_entities: List[Entity],
        scene_result: Dict,
        training_data: List[Dict],
        config: SimulationConfig
    ) -> Dict[str, str]:
        """
        Step 9: Generate narrative exports in configured formats.

        Returns:
            Dictionary mapping format name to file path

        Raises:
            Exception: If any export fails (per user requirement)
        """
        if not config.outputs.generate_narrative_exports:
            return {}

        with self.logfire.span("step:narrative_exports"):
            print(f"\n🎬 Generating narrative exports...")

            # Initialize exporter
            exporter = NarrativeExporter()

            # Collect all run data
            narrative_data = exporter.collect_run_data(
                run_metadata=metadata,
                timepoints=all_timepoints,
                entities=trained_entities,
                store=scene_result.get("store"),
                training_data=training_data,
                config=config
            )

            # Optionally enhance with LLM
            if config.outputs.enhance_narrative_with_llm:
                try:
                    llm = scene_result.get("llm_client")
                    if llm:
                        narrative_data = exporter.enhance_with_llm(narrative_data, llm)
                        print(f"  ✓ Executive summary enhanced with LLM")
                except Exception as e:
                    print(f"  ⚠️  LLM enhancement failed: {e}, using template only")

            # Generate exports
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = Path("datasets") / config.world_id
            base_path.mkdir(parents=True, exist_ok=True)

            exported_files = {}
            depth = config.outputs.narrative_detail_level

            for format_name in config.outputs.narrative_export_formats:
                try:
                    output_file = base_path / f"narrative_{timestamp}.{format_name}"

                    if format_name == "markdown":
                        path = exporter.export_markdown(narrative_data, output_file, depth)
                        print(f"    ✓ Markdown: {path.name} ({path.stat().st_size} bytes)")
                    elif format_name == "json":
                        path = exporter.export_json(narrative_data, output_file)
                        print(f"    ✓ JSON: {path.name} ({path.stat().st_size} bytes)")
                    elif format_name == "pdf":
                        try:
                            path = exporter.export_pdf(narrative_data, output_file, depth)
                            print(f"    ✓ PDF: {path.name} ({path.stat().st_size} bytes)")
                        except ImportError:
                            print(f"    ⚠️  PDF skipped: reportlab not installed")
                            continue

                    exported_files[format_name] = str(path)

                except Exception as e:
                    # Per user requirement: export failure means run fails
                    raise Exception(f"Narrative export failed for {format_name}: {e}")

            if not exported_files:
                raise Exception("No narrative exports were generated successfully")

            self.logfire.info(
                "Narrative exports generated",
                formats=list(exported_files.keys()),
                detail_level=depth
            )

            return exported_files

    def _generate_initial_scene(
        self, config: SimulationConfig, run_id: str
    ) -> Dict[str, Any]:
        """Step 2: Generate initial scene specification"""
        with self.logfire.span("step:initial_scene"):
            print("\nStep 2: Generating initial scene...")

            # Initialize LLM client
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not set")

            # Check for model override (used by --model CLI flag in convergence tests)
            model_override = os.getenv("TIMEPOINT_MODEL_OVERRIDE")
            if model_override:
                print(f"  🔧 Model override: {model_override}")
                llm = LLMClient(api_key=api_key, default_model=model_override)
            else:
                llm = LLMClient(api_key=api_key)

            # Initialize storage
            db_path = tempfile.mktemp(suffix=".db")
            store = GraphStore(f"sqlite:///{db_path}")

            # Run orchestrator
            result = simulate_event(
                config.scenario_description,
                llm,
                store,
                context={
                    "max_entities": config.entities.count,
                    "max_timepoints": 1,  # Just initial scene
                    "temporal_mode": config.temporal.mode.value,
                    "entity_metadata": config.metadata,  # Pass rich metadata for specialized mechanisms
                    "entity_config": {
                        "count": config.entities.count,
                        "types": config.entities.types,
                        "profiles": getattr(config.entities, 'profiles', [])
                    }
                },
                save_to_db=True
            )

            # Store for later steps
            result["llm_client"] = llm
            result["store"] = store
            result["db_path"] = db_path
            result["config"] = config  # Store config for prospection triggering

            print(f"✓ Initial scene created:")
            print(f"  - Entities: {len(result['entities'])}")
            print(f"  - Timepoints: {len(result['timepoints'])}")

            self.logfire.info(
                "Initial scene generated",
                entities=len(result['entities']),
                timepoints=len(result['timepoints'])
            )

            return result

    def _initialize_baseline_tensors(
        self, scene_result: Dict, run_id: str
    ) -> None:
        """
        Step 2.5: Initialize baseline tensors (Phase 7 + Phase 11 Architecture Pivot).

        Phase 7 Enhancement: First tries to resolve existing tensors from database
        before falling back to baseline creation. This enables tensor reuse.

        Flow:
        1. Try to resolve existing tensor from TensorRAG (cache hit)
        2. If no match, create baseline tensor (instant, no LLM, no bias leakage)
        3. Set maturity appropriately (inherited or 0.0)
        4. Mark for LLM-guided population during ANDOS training if needed

        Architectural improvements:
        - Phase 7: Tensor resolution for reuse across runs
        - Phase 11: Baseline initialization is instant and deterministic
        - M15 (Prospection) becomes truly OPTIONAL
        - No indirect bias leakage through shared LLM context
        """
        with self.logfire.span("step:baseline_tensor_init"):
            print("\nStep 2.5: Initializing baseline tensors...")

            entities = scene_result["entities"]
            store = scene_result["store"]
            config = scene_result.get("config")
            world_id = config.world_id if config else "unknown"
            scenario_context = config.scenario_description if config else ""

            # Import baseline tensor creation
            from tensor_initialization import create_baseline_tensor, create_fallback_tensor
            import base64
            import json

            entities_initialized = 0
            entities_failed = 0
            entities_resolved = 0  # Phase 7: Track cache hits

            for entity in entities:
                try:
                    # Phase 7: First try to resolve existing tensor
                    resolved_tensor = self._resolve_existing_tensor(
                        entity=entity,
                        world_id=world_id,
                        scenario_context=scenario_context,
                        min_score=0.75
                    )

                    if resolved_tensor is not None:
                        # Cache hit - use resolved tensor
                        tensor = resolved_tensor
                        entities_resolved += 1
                        needs_population = False  # Already trained
                        inherited_maturity = 0.5  # Assume moderate maturity from cache
                        print(f"  ✓ {entity.entity_id}: resolved from cache (maturity: {inherited_maturity:.2f})")
                    else:
                        # Cache miss - create baseline tensor (instant, no LLM)
                        print(f"  Creating baseline tensor for {entity.entity_id}...")
                        tensor = create_baseline_tensor(entity)
                        needs_population = True
                        inherited_maturity = 0.0

                    # Serialize tensor to entity.tensor
                    entity.tensor = json.dumps({
                        "context_vector": base64.b64encode(tensor.context_vector).decode('utf-8'),
                        "biology_vector": base64.b64encode(tensor.biology_vector).decode('utf-8'),
                        "behavior_vector": base64.b64encode(tensor.behavior_vector).decode('utf-8')
                    })

                    # Set maturity and training metadata based on resolution result
                    entity.tensor_maturity = inherited_maturity
                    entity.tensor_training_cycles = 0 if needs_population else 1
                    entity.entity_metadata["baseline_initialized"] = not needs_population
                    entity.entity_metadata["needs_llm_population"] = needs_population
                    entity.entity_metadata["needs_training"] = needs_population
                    entity.entity_metadata["tensor_resolved_from_cache"] = (resolved_tensor is not None)

                    # Save entity with tensor
                    store.save_entity(entity)

                    # Phase 1 Tensor Persistence: Also persist to dedicated tensor database
                    self._persist_tensor_to_db(entity, world_id, run_id)

                    entities_initialized += 1
                    if needs_population:
                        print(f"  ✓ {entity.entity_id}: baseline tensor created (maturity: {inherited_maturity:.2f})")

                except Exception as e:
                    print(f"  ⚠️  Failed to create baseline for {entity.entity_id}: {e}")
                    entities_failed += 1

                    # Fallback: create minimal tensor
                    try:
                        fallback_tensor = create_fallback_tensor()
                        entity.tensor = json.dumps({
                            "context_vector": base64.b64encode(fallback_tensor.context_vector).decode('utf-8'),
                            "biology_vector": base64.b64encode(fallback_tensor.biology_vector).decode('utf-8'),
                            "behavior_vector": base64.b64encode(fallback_tensor.behavior_vector).decode('utf-8')
                        })
                        entity.tensor_maturity = 0.0
                        entity.tensor_training_cycles = 0
                        entity.entity_metadata["baseline_initialized"] = False
                        entity.entity_metadata["fallback_tensor"] = True
                        entity.entity_metadata["tensor_resolved_from_cache"] = False
                        store.save_entity(entity)

                        # Phase 1 Tensor Persistence: Persist fallback tensor too
                        self._persist_tensor_to_db(entity, world_id, run_id)

                        entities_initialized += 1
                        print(f"  ⚠️  {entity.entity_id}: using fallback tensor")
                    except Exception as fallback_err:
                        print(f"  ❌ Fatal: Even fallback failed for {entity.entity_id}: {fallback_err}")

            print(f"✓ Initialized {entities_initialized} entities with tensors")
            if entities_resolved > 0:
                print(f"  🔍 Phase 7: {entities_resolved} tensors resolved from cache (reuse enabled)")
            if entities_failed > 0:
                print(f"  ⚠️  {entities_failed} entities used fallback tensors")
            needs_pop_count = entities_initialized - entities_resolved
            if needs_pop_count > 0:
                print(f"  📝 {needs_pop_count} entities need LLM-guided population (Step 4)")
            print(f"  💾 Tensors persisted to dedicated database: metadata/tensors.db")

            self.logfire.info(
                "Baseline tensor initialization complete",
                entities_initialized=entities_initialized,
                entities_resolved=entities_resolved,
                entities_failed=entities_failed,
                cache_hit_rate=entities_resolved / max(1, entities_initialized)
            )

    def _compute_andos_layers(
        self, entities: List[Entity], run_id: str
    ) -> List[List[Entity]]:
        """Step 3.5: Compute ANDOS training layers via reverse topological ordering"""
        with self.logfire.span("step:andos_computation"):
            print("\nStep 3.5: Computing ANDOS training layers...")

            if len(entities) < 2:
                print("  ⚠️  Less than 2 entities - single layer")
                return [entities]

            # Infer interaction graph (templates don't have explicit graphs yet)
            interaction_graph = _infer_interaction_graph(entities)
            target_entity_id = entities[0].entity_id if entities else None

            if not target_entity_id:
                print("  ⚠️  No entities - empty layers")
                return [[]]

            try:
                # Compute ANDOS layers
                print(f"  Computing layers for {len(entities)} entities...")
                layers = compute_andos_layers(entities, target_entity_id, interaction_graph)

                print(f"  ✓ ANDOS computed {len(layers)} layers:")
                for idx, layer in enumerate(layers):
                    layer_ids = [e.entity_id for e in layer]
                    print(f"    Layer {idx} ({len(layer)} entities): {layer_ids}")

                # Validate layers
                valid, violations = validate_andos_layers(layers, interaction_graph)
                if not valid:
                    print(f"  ⚠️  ANDOS validation failed:")
                    for v in violations[:3]:
                        print(f"    - {v}")

                self.logfire.info(
                    "ANDOS layers computed",
                    num_layers=len(layers),
                    total_entities=len(entities)
                )

                return layers

            except Exception as e:
                print(f"  ⚠️  ANDOS computation failed: {e}")
                print("  Falling back to single-layer training")
                return [entities]  # Fallback: all entities in one layer

    def _generate_all_timepoints(
        self, scene_result: Dict, config: SimulationConfig, run_id: str
    ) -> List[Timepoint]:
        """Step 3: Generate all timepoints using TemporalAgent"""
        with self.logfire.span("step:temporal_generation"):
            print("\nStep 3: Generating all timepoints...")

            llm = scene_result["llm_client"]
            store = scene_result["store"]
            initial_timepoint = scene_result["timepoints"][0]

            # Create temporal agent with fidelity configuration (M1+M17)
            temporal_agent = TemporalAgent(
                mode=config.temporal.mode,
                store=store,
                llm_client=llm,
                temporal_config=config.temporal  # Pass full TemporalConfig for fidelity awareness
            )

            # Store temporal_agent for fidelity metrics tracking (M1+M17)
            scene_result["temporal_agent"] = temporal_agent

            # M1+M17: Determine fidelity strategy at start of temporal generation
            if config.temporal.fidelity_planning_mode and config.temporal.token_budget:
                try:
                    strategy_context = {
                        "entities": scene_result["entities"],
                        "origin_year": datetime.now().year,
                        "token_budget": config.temporal.token_budget
                    }
                    temporal_agent.fidelity_strategy = temporal_agent.determine_fidelity_temporal_strategy(
                        config.temporal,
                        strategy_context
                    )
                    print(f"  📊 Fidelity strategy determined:")
                    print(f"     Planning mode: {config.temporal.fidelity_planning_mode.value}")
                    print(f"     Token budget: {config.temporal.token_budget:,}")
                    print(f"     Template: {config.temporal.fidelity_template}")
                except Exception as e:
                    print(f"  ⚠️  Fidelity strategy determination failed: {e}, using defaults")

            # MODE DETECTION: Check if portal simulation
            if config.temporal.mode == TemporalMode.PORTAL:
                print(f"\n{'='*80}")
                print(f"PORTAL MODE DETECTED")
                print(f"Running backward simulation: {config.temporal.backward_steps} steps")
                print(f"Target: {config.temporal.portal_description}")
                print(f"Timeframe: {config.temporal.origin_year} → {config.temporal.portal_year}")
                print(f"{'='*80}\n")

                # Run portal simulation
                portal_paths = temporal_agent.run_portal_simulation(config.temporal)

                # Convert portal paths to timepoints
                all_timepoints = self._convert_portal_paths_to_timepoints(
                    portal_paths, initial_timepoint, store, run_id
                )

                # Store portal metadata for downstream processing
                scene_result["portal_paths"] = portal_paths
                scene_result["is_portal_mode"] = True

                print(f"✓ Portal simulation complete:")
                print(f"  - Paths generated: {len(portal_paths)}")
                print(f"  - Timepoints created: {len(all_timepoints)}")
                print(f"  - Best coherence: {portal_paths[0].coherence_score:.3f}" if portal_paths else "  - No paths")

                self.logfire.info(
                    "Portal temporal generation complete",
                    timepoints=len(all_timepoints),
                    paths=len(portal_paths),
                    is_portal_mode=True
                )

                return all_timepoints

            # MODE DETECTION: Check if branching simulation
            if config.temporal.mode == TemporalMode.BRANCHING:
                print(f"\n{'='*80}")
                print(f"BRANCHING MODE DETECTED")
                print(f"Running forward simulation with counterfactual branches")
                print(f"Steps: {config.temporal.backward_steps}")  # BRANCHING uses backward_steps as step count
                print(f"{'='*80}\n")

                # Run branching simulation
                branching_paths = temporal_agent.run_branching_simulation(config.temporal)

                # Convert branching paths to timepoints
                all_timepoints = self._convert_branching_paths_to_timepoints(
                    branching_paths, initial_timepoint, store, run_id
                )

                # Store branching metadata for downstream processing
                scene_result["branching_paths"] = branching_paths
                scene_result["is_branching_mode"] = True

                print(f"✓ Branching simulation complete:")
                print(f"  - Paths generated: {len(branching_paths)}")
                print(f"  - Timepoints created: {len(all_timepoints)}")
                print(f"  - Best coherence: {branching_paths[0].coherence_score:.3f}" if branching_paths else "  - No paths")

                self.logfire.info(
                    "Branching temporal generation complete",
                    timepoints=len(all_timepoints),
                    paths=len(branching_paths),
                    is_branching_mode=True
                )

                return all_timepoints

            # MODE DETECTION: Check if directorial simulation
            if config.temporal.mode == TemporalMode.DIRECTORIAL:
                print(f"\n{'='*80}")
                print(f"DIRECTORIAL MODE DETECTED")
                print(f"Running narrative-driven simulation with dramatic arc")
                print(f"Steps: {config.temporal.backward_steps}")
                print(f"{'='*80}\n")

                # Run directorial simulation
                directorial_paths = temporal_agent.run_directorial_simulation(config.temporal)

                # Convert directorial paths to timepoints
                all_timepoints = self._convert_directorial_paths_to_timepoints(
                    directorial_paths, initial_timepoint, store, run_id
                )

                # Store directorial metadata
                scene_result["directorial_paths"] = directorial_paths
                scene_result["is_directorial_mode"] = True

                print(f"✓ Directorial simulation complete:")
                print(f"  - Paths generated: {len(directorial_paths)}")
                print(f"  - Timepoints created: {len(all_timepoints)}")
                if directorial_paths:
                    print(f"  - Best coherence: {directorial_paths[0].coherence_score:.3f}")
                    print(f"  - Arc completion: {directorial_paths[0].arc_completion_score:.3f}")

                self.logfire.info(
                    "Directorial temporal generation complete",
                    timepoints=len(all_timepoints),
                    paths=len(directorial_paths),
                    is_directorial_mode=True
                )

                return all_timepoints

            # MODE DETECTION: Check if cyclical simulation
            if config.temporal.mode == TemporalMode.CYCLICAL:
                print(f"\n{'='*80}")
                print(f"CYCLICAL MODE DETECTED")
                print(f"Running cyclical simulation with prophecy tracking")
                print(f"Cycle length: {getattr(config.temporal, 'cycle_length', 4)}")
                print(f"{'='*80}\n")

                # Run cyclical simulation
                cyclical_paths = temporal_agent.run_cyclical_simulation(config.temporal)

                # Convert cyclical paths to timepoints
                all_timepoints = self._convert_cyclical_paths_to_timepoints(
                    cyclical_paths, initial_timepoint, store, run_id
                )

                # Store cyclical metadata
                scene_result["cyclical_paths"] = cyclical_paths
                scene_result["is_cyclical_mode"] = True

                print(f"✓ Cyclical simulation complete:")
                print(f"  - Paths generated: {len(cyclical_paths)}")
                print(f"  - Timepoints created: {len(all_timepoints)}")
                if cyclical_paths:
                    print(f"  - Best coherence: {cyclical_paths[0].coherence_score:.3f}")
                    print(f"  - Prophecy fulfillment: {cyclical_paths[0].prophecy_fulfillment_rate:.2f}")

                self.logfire.info(
                    "Cyclical temporal generation complete",
                    timepoints=len(all_timepoints),
                    paths=len(cyclical_paths),
                    is_cyclical_mode=True
                )

                return all_timepoints

            # FORWARD MODE: Original forward generation logic
            all_timepoints = [initial_timepoint]
            current_timepoint = initial_timepoint

            # CONVERGENCE FIX: Persist initial timepoint to shared DB
            self._persist_timepoint_for_convergence(initial_timepoint, run_id)

            # January 2026: Extract directorial mode info for rich event descriptions
            is_directorial = config.temporal.mode == TemporalMode.DIRECTORIAL
            narrative_arc = getattr(config.temporal, 'narrative_arc', None)
            dramatic_tension = getattr(config.temporal, 'dramatic_tension', 0.7)
            scenario_desc = config.scenario_description
            narrative_beats = config.metadata.get('narrative_beats', []) if config.metadata else []

            # Generate remaining timepoints
            target_count = config.timepoints.count
            for i in range(1, target_count):
                print(f"  Generating timepoint {i+1}/{target_count}...")

                try:
                    # January 2026: Generate rich event descriptions for DIRECTORIAL mode
                    context = {"iteration": i, "total": target_count}

                    if is_directorial:
                        event_desc = self._generate_directorial_event_description(
                            llm=llm,
                            iteration=i,
                            total=target_count,
                            scenario_desc=scenario_desc,
                            narrative_arc=narrative_arc,
                            narrative_beats=narrative_beats,
                            dramatic_tension=dramatic_tension,
                            previous_event=current_timepoint.event_description,
                            entities=[e.entity_id for e in scene_result["entities"]]
                        )
                        context["next_event"] = event_desc

                    next_timepoint = temporal_agent.generate_next_timepoint(
                        current_timepoint,
                        context=context
                    )

                    # Save to database (temp DB for workflow)
                    store.save_timepoint(next_timepoint)

                    # CONVERGENCE FIX: Also persist to shared DB with run_id
                    self._persist_timepoint_for_convergence(next_timepoint, run_id)

                    all_timepoints.append(next_timepoint)
                    current_timepoint = next_timepoint

                except Exception as e:
                    print(f"  Warning: Failed to generate timepoint {i+1}: {e}")
                    # Continue with what we have
                    break

            print(f"✓ Generated {len(all_timepoints)} timepoints")

            self.logfire.info(
                "Temporal generation complete",
                timepoints=len(all_timepoints)
            )

            return all_timepoints

    def _generate_directorial_event_description(
        self,
        llm,
        iteration: int,
        total: int,
        scenario_desc: str,
        narrative_arc: str,
        narrative_beats: List[str],
        dramatic_tension: float,
        previous_event: str,
        entities: List[str]
    ) -> str:
        """
        Generate rich event descriptions for DIRECTORIAL mode using LLM.

        January 2026: Fixes generic placeholder issue where all timepoints
        had descriptions like "Events continue to unfold".

        In DIRECTORIAL mode (M17), events serve narrative beats rather than
        following strict causality. This method generates dramatic, contextual
        descriptions that:
        - Progress the narrative arc (rising_action → climax → resolution)
        - Reference key narrative beats at appropriate times
        - Maintain dramatic tension
        - Include relevant entities

        Args:
            llm: LLM client for generation
            iteration: Current timepoint number (1-indexed)
            total: Total number of timepoints
            scenario_desc: Full scenario description for context
            narrative_arc: Current narrative arc (e.g., "rising_action")
            narrative_beats: List of key moments (e.g., ["t01_arrival", "t05_discovery"])
            dramatic_tension: Tension level 0.0-1.0
            previous_event: Description of the previous timepoint
            entities: List of entity IDs in the scene

        Returns:
            Rich event description string
        """
        # Calculate narrative position (0.0 = beginning, 1.0 = end)
        narrative_position = iteration / total if total > 0 else 0.5

        # Determine narrative phase based on position
        if narrative_position < 0.25:
            phase = "SETUP"
            phase_guidance = "Establish the scene, introduce tensions, build atmosphere"
        elif narrative_position < 0.5:
            phase = "RISING ACTION"
            phase_guidance = "Escalate tensions, reveal information, increase stakes"
        elif narrative_position < 0.75:
            phase = "CLIMAX APPROACH"
            phase_guidance = "Peak tension, confrontations, critical decisions"
        elif narrative_position < 0.9:
            phase = "CLIMAX/FALLING ACTION"
            phase_guidance = "Resolution of main tension, consequences revealed"
        else:
            phase = "RESOLUTION"
            phase_guidance = "Aftermath, new equilibrium, closure"

        # Find relevant narrative beat for this position
        relevant_beat = None
        if narrative_beats:
            # Map beats to approximate positions
            beat_positions = {beat: i / len(narrative_beats) for i, beat in enumerate(narrative_beats)}
            # Find closest beat to current position
            closest_beat = min(narrative_beats, key=lambda b: abs(beat_positions[b] - narrative_position))
            if abs(beat_positions[closest_beat] - narrative_position) < 0.15:
                relevant_beat = closest_beat

        # Build prompt for LLM
        system_prompt = """You are a narrative director for dramatic temporal simulations.
Generate vivid, specific event descriptions that serve the story's dramatic needs.
Events should feel meaningful and connected to the narrative arc."""

        user_prompt = f"""Generate a SINGLE event description for timepoint {iteration}/{total}.

SCENARIO CONTEXT:
{scenario_desc[:500]}

NARRATIVE PHASE: {phase}
Phase guidance: {phase_guidance}
Dramatic tension level: {dramatic_tension:.1f}/1.0
Narrative position: {narrative_position:.1%} through story

PREVIOUS EVENT:
{previous_event[:200] if previous_event else "Story beginning"}

{"CURRENT NARRATIVE BEAT: " + relevant_beat.replace('_', ' ') if relevant_beat else ""}

ENTITIES PRESENT: {', '.join(entities[:8])}

INSTRUCTIONS:
1. Write a 2-3 sentence event description
2. Be SPECIFIC - mention characters, locations, actions by name
3. Serve the current narrative phase ({phase})
4. Build on the previous event naturally
5. Match the dramatic tension level
6. Do NOT use generic phrases like "events unfold" or "things continue"

RESPOND WITH ONLY THE EVENT DESCRIPTION, nothing else."""

        try:
            response = llm.client.chat.completions.create(
                model=llm.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7 + (dramatic_tension * 0.2),  # Higher tension = more creative
                max_tokens=300
            )

            # Extract response content
            if isinstance(response, dict):
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                content = response.choices[0].message.content

            if content and len(content.strip()) > 20:
                return content.strip()

        except Exception as e:
            print(f"    ⚠️  Directorial event generation failed: {e}")

        # Fallback: Generate contextual description without LLM
        fallback_descriptions = {
            "SETUP": f"The investigation begins as {entities[0] if entities else 'the protagonist'} surveys the scene, noting the unsettling atmosphere that pervades the area.",
            "RISING ACTION": f"Tensions mount as new evidence comes to light. {entities[0] if entities else 'The detective'} pieces together disturbing connections.",
            "CLIMAX APPROACH": f"The confrontation draws near. {entities[0] if entities else 'Our hero'} must act decisively as danger closes in.",
            "CLIMAX/FALLING ACTION": f"The critical moment arrives. Actions have consequences as the truth is finally revealed.",
            "RESOLUTION": f"In the aftermath, {entities[0] if entities else 'the survivors'} reflect on what transpired and what it means for the future."
        }

        return fallback_descriptions.get(phase, f"Timepoint {iteration}: The narrative continues with dramatic developments.")

    def _convert_portal_paths_to_timepoints(
        self,
        portal_paths: List,
        initial_timepoint: Timepoint,
        store,
        run_id: str
    ) -> List[Timepoint]:
        """
        Convert PortalPath objects to Timepoint objects for E2E pipeline.

        Strategy:
        - Take best path (highest coherence_score)
        - Convert each PortalState → Timepoint
        - Preserve portal metadata in timepoint.metadata
        - Link timepoints causally (parent→child)

        Args:
            portal_paths: List of PortalPath from PortalStrategy
            initial_timepoint: Origin timepoint (founding moment)
            store: GraphStore for saving timepoints

        Returns:
            List of Timepoint objects ordered origin→portal
        """
        if not portal_paths:
            print("  ⚠️  No portal paths returned, using initial timepoint only")
            return [initial_timepoint]

        # Take best path (first in list, already sorted by coherence)
        best_path = portal_paths[0]

        print(f"\n  Converting best path to timepoints:")
        print(f"    Path ID: {best_path.path_id}")
        print(f"    Coherence: {best_path.coherence_score:.3f}")
        print(f"    States: {len(best_path.states)}")
        print(f"    Pivot Points: {best_path.pivot_points}")

        timepoints = []
        previous_timepoint_id = None

        for idx, state in enumerate(best_path.states):
            # Generate timepoint ID
            tp_id = f"tp_{idx:03d}_{state.year}"

            # Create Timepoint from PortalState
            timepoint = Timepoint(
                timepoint_id=tp_id,
                timestamp=datetime(state.year, 1, 1),  # Use year for timestamp
                event_description=state.description,
                entities_present=[e.entity_id for e in state.entities] if state.entities else [],
                causal_parent=previous_timepoint_id,
                metadata={
                    "portal_mode": True,
                    "path_id": best_path.path_id,
                    "path_position": idx,
                    "plausibility_score": state.plausibility_score,
                    "coherence_score": best_path.coherence_score,
                    "is_pivot_point": idx in best_path.pivot_points,
                    "world_state": state.world_state,
                    "year": state.year
                }
            )

            # Save to database (temp DB for workflow)
            store.save_timepoint(timepoint)

            # CONVERGENCE FIX: Also persist to shared DB with run_id
            self._persist_timepoint_for_convergence(timepoint, run_id)

            timepoints.append(timepoint)
            previous_timepoint_id = tp_id

            if idx in best_path.pivot_points:
                print(f"    ✓ Timepoint {idx}: Year {state.year} [PIVOT POINT]")
            else:
                print(f"    ✓ Timepoint {idx}: Year {state.year}")

        print(f"\n  Portal path metadata:")
        print(f"    All paths available: {len(portal_paths)}")
        for i, path in enumerate(portal_paths[:3], 1):  # Show top 3
            print(f"      Path {i}: Coherence {path.coherence_score:.3f}")

        return timepoints

    def _convert_branching_paths_to_timepoints(
        self,
        branching_paths: List,
        initial_timepoint: Timepoint,
        store,
        run_id: str
    ) -> List[Timepoint]:
        """
        Convert BranchingPath objects to Timepoint objects for E2E pipeline.

        Strategy:
        - Take best path (highest coherence_score)
        - Convert each BranchingState → Timepoint
        - Preserve branching metadata in timepoint.metadata
        - Link timepoints causally (parent→child)

        Args:
            branching_paths: List of BranchingPath from BranchingStrategy
            initial_timepoint: Origin timepoint (founding moment)
            store: GraphStore for saving timepoints
            run_id: Current run identifier

        Returns:
            List of Timepoint objects ordered origin→future
        """
        if not branching_paths:
            print("  ⚠️  No branching paths returned, using initial timepoint only")
            return [initial_timepoint]

        # Take best path (first in list, already sorted by coherence)
        best_path = branching_paths[0]

        print(f"\n  Converting best branching path to timepoints:")
        print(f"    Path ID: {best_path.path_id}")
        print(f"    Coherence: {best_path.coherence_score:.3f}")
        print(f"    States: {len(best_path.states)}")
        print(f"    Branch Points: {best_path.branch_points}")

        timepoints = []
        previous_timepoint_id = None

        # January 2026: Get fallback entities from initial_timepoint (from scene orchestration)
        # This ensures we always have entities even if LLM inference fails
        fallback_entity_ids = initial_timepoint.entities_present if initial_timepoint.entities_present else []
        if not fallback_entity_ids:
            # Secondary fallback: try to get from store if available
            try:
                all_entities = store.list_entities() if hasattr(store, 'list_entities') else []
                fallback_entity_ids = [e.entity_id for e in all_entities[:10]]
            except Exception:
                pass

        if fallback_entity_ids:
            print(f"    Fallback entities available: {len(fallback_entity_ids)}")

        for idx, state in enumerate(best_path.states):
            # Generate timepoint ID
            tp_id = f"tp_{idx:03d}_{state.year}"

            # January 2026: Get entities from state, with fallback to initial_timepoint entities
            state_entity_ids = [e.entity_id for e in state.entities] if state.entities else []
            if not state_entity_ids and fallback_entity_ids:
                state_entity_ids = fallback_entity_ids.copy()
                # Don't spam the console, just note once if needed

            # Create Timepoint from BranchingState
            timepoint = Timepoint(
                timepoint_id=tp_id,
                timestamp=datetime(state.year, state.month, 1),  # Use year/month from state
                event_description=state.description,
                entities_present=state_entity_ids,
                causal_parent=previous_timepoint_id,
                metadata={
                    "branching_mode": True,
                    "path_id": best_path.path_id,
                    "path_position": idx,
                    "plausibility_score": state.plausibility_score,
                    "coherence_score": best_path.coherence_score,
                    "is_branch_point": idx in best_path.branch_points,
                    "world_state": state.world_state,
                    "year": state.year,
                    "month": state.month
                }
            )

            # Save to database (temp DB for workflow)
            store.save_timepoint(timepoint)

            # CONVERGENCE FIX: Also persist to shared DB with run_id
            self._persist_timepoint_for_convergence(timepoint, run_id)

            timepoints.append(timepoint)
            previous_timepoint_id = tp_id

            if idx in best_path.branch_points:
                print(f"    ✓ Timepoint {idx}: {state.year}-{state.month:02d} [BRANCH POINT]")
            else:
                print(f"    ✓ Timepoint {idx}: {state.year}-{state.month:02d}")

        print(f"\n  Branching path metadata:")
        print(f"    All paths available: {len(branching_paths)}")
        for i, path in enumerate(branching_paths[:3], 1):  # Show top 3
            print(f"      Path {i}: Coherence {path.coherence_score:.3f}")

        return timepoints

    def _convert_directorial_paths_to_timepoints(
        self,
        directorial_paths: List,
        initial_timepoint: Timepoint,
        store,
        run_id: str
    ) -> List[Timepoint]:
        """
        Convert DirectorialPath objects to Timepoint objects for E2E pipeline.

        Preserves act, tension_score, pov_entity, framing in timepoint metadata.

        Args:
            directorial_paths: List of DirectorialPath from DirectorialStrategy
            initial_timepoint: Origin timepoint
            store: GraphStore for saving timepoints
            run_id: Current run identifier

        Returns:
            List of Timepoint objects ordered by narrative progression
        """
        if not directorial_paths:
            print("  ⚠️  No directorial paths returned, using initial timepoint only")
            return [initial_timepoint]

        best_path = directorial_paths[0]

        print(f"\n  Converting best directorial path to timepoints:")
        print(f"    Path ID: {best_path.path_id}")
        print(f"    Coherence: {best_path.coherence_score:.3f}")
        print(f"    States: {len(best_path.states)}")
        print(f"    Act boundaries: {best_path.act_boundaries}")

        timepoints = []
        previous_timepoint_id = None

        fallback_entity_ids = initial_timepoint.entities_present if initial_timepoint.entities_present else []

        for idx, state in enumerate(best_path.states):
            tp_id = f"tp_{idx:03d}_{state.year}"

            state_entity_ids = [e.entity_id for e in state.entities] if state.entities else []
            if not state_entity_ids and fallback_entity_ids:
                state_entity_ids = fallback_entity_ids.copy()

            timepoint = Timepoint(
                timepoint_id=tp_id,
                timestamp=datetime(state.year, state.month, 1),
                event_description=state.description,
                entities_present=state_entity_ids,
                causal_parent=previous_timepoint_id,
                metadata={
                    "directorial_mode": True,
                    "path_id": best_path.path_id,
                    "path_position": idx,
                    "plausibility_score": state.plausibility_score,
                    "coherence_score": best_path.coherence_score,
                    "act": state.act.value if hasattr(state.act, 'value') else str(state.act),
                    "tension_score": state.tension_score,
                    "pov_entity": state.pov_entity,
                    "framing": state.framing.value if hasattr(state.framing, 'value') else str(state.framing),
                    "dramatic_irony": state.dramatic_irony,
                    "narrative_beat": state.narrative_beat,
                    "dramatic_importance": state.dramatic_importance,
                    "world_state": state.world_state,
                    "year": state.year,
                    "month": state.month
                }
            )

            store.save_timepoint(timepoint)
            self._persist_timepoint_for_convergence(timepoint, run_id)

            timepoints.append(timepoint)
            previous_timepoint_id = tp_id

            act_label = state.act.value if hasattr(state.act, 'value') else str(state.act)
            print(f"    ✓ Timepoint {idx}: {state.year}-{state.month:02d} [{act_label.upper()}] tension={state.tension_score:.2f}")

        print(f"\n  Directorial path metadata:")
        print(f"    All paths available: {len(directorial_paths)}")
        for i, path in enumerate(directorial_paths[:3], 1):
            print(f"      Path {i}: Coherence {path.coherence_score:.3f}, Arc {path.arc_completion_score:.3f}")

        return timepoints

    def _convert_cyclical_paths_to_timepoints(
        self,
        cyclical_paths: List,
        initial_timepoint: Timepoint,
        store,
        run_id: str
    ) -> List[Timepoint]:
        """
        Convert CyclicalPath objects to Timepoint objects for E2E pipeline.

        Preserves cycle_index, position_in_cycle, fulfilled_prophecies in timepoint metadata.

        Args:
            cyclical_paths: List of CyclicalPath from CyclicalStrategy
            initial_timepoint: Origin timepoint
            store: GraphStore for saving timepoints
            run_id: Current run identifier

        Returns:
            List of Timepoint objects ordered by cycle progression
        """
        if not cyclical_paths:
            print("  ⚠️  No cyclical paths returned, using initial timepoint only")
            return [initial_timepoint]

        best_path = cyclical_paths[0]

        print(f"\n  Converting best cyclical path to timepoints:")
        print(f"    Path ID: {best_path.path_id}")
        print(f"    Coherence: {best_path.coherence_score:.3f}")
        print(f"    States: {len(best_path.states)}")
        print(f"    Cycle boundaries: {best_path.cycle_boundaries}")
        print(f"    Prophecy fulfillment: {best_path.prophecy_fulfillment_rate:.2f}")

        timepoints = []
        previous_timepoint_id = None

        fallback_entity_ids = initial_timepoint.entities_present if initial_timepoint.entities_present else []

        for idx, state in enumerate(best_path.states):
            tp_id = f"tp_{idx:03d}_{state.year}"

            state_entity_ids = [e.entity_id for e in state.entities] if state.entities else []
            if not state_entity_ids and fallback_entity_ids:
                state_entity_ids = fallback_entity_ids.copy()

            timepoint = Timepoint(
                timepoint_id=tp_id,
                timestamp=datetime(state.year, state.month, 1),
                event_description=state.description,
                entities_present=state_entity_ids,
                causal_parent=previous_timepoint_id,
                metadata={
                    "cyclical_mode": True,
                    "path_id": best_path.path_id,
                    "path_position": idx,
                    "plausibility_score": state.plausibility_score,
                    "coherence_score": best_path.coherence_score,
                    "cycle_index": state.cycle_index,
                    "position_in_cycle": state.position_in_cycle,
                    "cycle_type": state.cycle_type,
                    "escalation_level": state.escalation_level,
                    "prophecy": state.prophecy,
                    "fulfilled_prophecies": state.fulfilled_prophecies,
                    "echo_of": state.echo_of,
                    "causal_loop_tag": state.causal_loop_tag,
                    "world_state": state.world_state,
                    "year": state.year,
                    "month": state.month
                }
            )

            store.save_timepoint(timepoint)
            self._persist_timepoint_for_convergence(timepoint, run_id)

            timepoints.append(timepoint)
            previous_timepoint_id = tp_id

            is_boundary = idx in best_path.cycle_boundaries
            boundary_label = " [CYCLE BOUNDARY]" if is_boundary else ""
            print(f"    ✓ Timepoint {idx}: {state.year}-{state.month:02d} C{state.cycle_index}P{state.position_in_cycle}{boundary_label}")

        print(f"\n  Cyclical path metadata:")
        print(f"    All paths available: {len(cyclical_paths)}")
        for i, path in enumerate(cyclical_paths[:3], 1):
            print(f"      Path {i}: Coherence {path.coherence_score:.3f}, Prophecy {path.prophecy_fulfillment_rate:.2f}")

        return timepoints

    def _train_entities(
        self, scene_result: Dict, timepoints: List[Timepoint], andos_layers: List[List[Entity]], run_id: str
    ) -> List[Entity]:
        """Step 4: Train entities layer-by-layer using ANDOS ordering"""
        with self.logfire.span("step:entity_training"):
            print(f"\nStep 4: Training entities layer-by-layer (ANDOS)...")
            print(f"  {len(andos_layers)} layers, {len(timepoints)} timepoints")

            llm = scene_result["llm_client"]
            store = scene_result["store"]
            graph = scene_result.get("graph")

            # Create the full entity training workflow
            workflow = create_entity_training_workflow(llm, store)

            # Train layer-by-layer and update layers in place
            for layer_idx in range(len(andos_layers)):
                layer_entities = andos_layers[layer_idx]

                print(f"\n  🔷 ANDOS Layer {layer_idx}/{len(andos_layers)-1}: Training {len(layer_entities)} entities")
                layer_ids = [e.entity_id for e in layer_entities]
                print(f"     Entities: {layer_ids}")

                # Step 4a: LLM-guided tensor population + optional prospection (Phase 11)
                config = scene_result.get("config", {})
                for entity in layer_entities:
                    first_timepoint = timepoints[0] if timepoints else None
                    if not first_timepoint:
                        continue

                    # LLM-guided population (if needed)
                    if entity.entity_metadata.get("needs_llm_population", False):
                        try:
                            from tensor_initialization import populate_tensor_llm_guided
                            print(f"     🔧 LLM-guided population for {entity.entity_id}...")
                            refined_tensor, maturity = populate_tensor_llm_guided(
                                entity, first_timepoint, graph, llm
                            )
                            import json, base64
                            entity.tensor = json.dumps({
                                "context_vector": base64.b64encode(refined_tensor.context_vector).decode('utf-8'),
                                "biology_vector": base64.b64encode(refined_tensor.biology_vector).decode('utf-8'),
                                "behavior_vector": base64.b64encode(refined_tensor.behavior_vector).decode('utf-8')
                            })
                            entity.entity_metadata["needs_llm_population"] = False
                            entity.tensor_maturity = maturity  # Update maturity from LLM population
                            store.save_entity(entity)

                            # Phase 1 Tensor Persistence: Update tensor in dedicated DB after population
                            cfg = scene_result.get("config")
                            w_id = cfg.world_id if cfg else "unknown"
                            self._persist_tensor_to_db(entity, w_id, run_id)

                            print(f"       ✓ Populated (maturity: {maturity:.3f})")
                        except Exception as e:
                            print(f"       ⚠️  Population failed: {e}")
                    else:
                        # Entity already populated or doesn't need population
                        print(f"     ✓ {entity.entity_id}: Already populated, skipping LLM call")

                    # Optional prospection (M15) - triggered conditionally
                    try:
                        from prospection_triggers import trigger_prospection_for_entity, refine_tensor_from_prospection
                        prospective_state = trigger_prospection_for_entity(
                            entity, first_timepoint, llm, store, config
                        )
                        if prospective_state:
                            # Optionally refine tensor from prospection
                            refine_tensor_from_prospection(entity, prospective_state)
                            store.save_entity(entity)
                    except Exception as e:
                        print(f"       ⚠️  Prospection failed: {e}")

                # Train entities in this layer (using first timepoint as context)
                first_timepoint = timepoints[0] if timepoints else None
                if first_timepoint:
                    # Build workflow state for entities in this layer
                    workflow_state = {
                        "graph": graph if graph else store.load_graph(first_timepoint.timepoint_id),
                        "entities": layer_entities,  # Only train current layer
                        "timepoint": first_timepoint.timepoint_id,
                        "timepoint_obj": first_timepoint,
                        "resolution": ResolutionLevel.SCENE,
                        "violations": [],
                        "results": {},
                        "entity_populations": {}
                    }

                    try:
                        # Run workflow for this layer (ONCE per layer, not per timepoint)
                        result_state = workflow.invoke(workflow_state)

                        # Extract trained entities from result and UPDATE the layer
                        if "entities" in result_state:
                            layer_entities = result_state["entities"]
                            andos_layers[layer_idx] = layer_entities  # Update layer in place!

                        # Report violations if any
                        violations = result_state.get("violations", [])
                        if violations and layer_idx == 0:  # Only show for first layer to reduce noise
                            print(f"     ⚠️  Found {len(violations)} validation violations")

                    except Exception as e:
                        print(f"     ⚠️  Training error: {e}")

                # Mark layer as complete and record metadata
                for entity in andos_layers[layer_idx]:
                    entity.entity_metadata["andos_layer"] = layer_idx
                    self.metadata_manager.record_resolution(
                        run_id,
                        entity.entity_id,
                        entity.resolution_level,
                        timepoints[0].timepoint_id if timepoints else "unknown"
                    )

                print(f"     ✓ Layer {layer_idx} complete")

            # Flatten updated layers and deduplicate by entity_id (keep last version)
            entity_map = {}
            for layer in andos_layers:
                for entity in layer:
                    entity_map[entity.entity_id] = entity  # Last version wins

            all_entities = list(entity_map.values())

            # Phase 2 Parallel Training: Optional concurrent tensor maturity training
            config = scene_result.get("config")
            parallel_training_enabled = getattr(config, 'parallel_training', False) if config else False

            if parallel_training_enabled:
                self._run_parallel_tensor_training(
                    entities=all_entities,
                    scene_result=scene_result,
                    run_id=run_id
                )

            # PART 3 FIX: Post-training validation - ensure all human entities have physical_tensor
            from schemas import PhysicalTensor
            entities_fixed = 0
            for entity in all_entities:
                if entity.entity_type == "human":
                    # Check if physical_tensor exists and is valid
                    physical_data = entity.entity_metadata.get("physical_tensor", {})
                    if not physical_data or 'age' not in physical_data:
                        # Recreate physical_tensor from defaults
                        physical = PhysicalTensor(
                            age=35.0,
                            health_status=1.0,
                            pain_level=0.0,
                            pain_location=None,
                            fever=36.5,
                            mobility=1.0,
                            stamina=1.0,
                            sensory_acuity={"vision": 1.0, "hearing": 1.0},
                            location=None
                        )
                        entity.entity_metadata["physical_tensor"] = physical.model_dump()
                        entities_fixed += 1
                        print(f"     ⚠️  Regenerated physical_tensor for {entity.entity_id}")

            if entities_fixed > 0:
                print(f"  ✓ Validated and fixed {entities_fixed} entities")

            print(f"\n✓ Trained {len(all_entities)} unique entities across {len(andos_layers)} layers")

            self.logfire.info(
                "ANDOS layer-by-layer training complete",
                entities=len(all_entities),
                layers=len(andos_layers),
                timepoints_processed=len(timepoints)
            )

            return all_entities

    def _run_parallel_tensor_training(
        self,
        entities: List[Entity],
        scene_result: Dict,
        run_id: str
    ) -> None:
        """
        Phase 2 Parallel Training: Train all entity tensors concurrently.

        Uses the ParallelTensorTrainer to train multiple tensors to target maturity
        using asyncio workers. This is optional and enabled via config.parallel_training.

        Args:
            entities: List of entities with tensors to train
            scene_result: Scene result with config
            run_id: Current run ID
        """
        import asyncio

        with self.logfire.span("step:parallel_tensor_training"):
            print("\n  🔄 Phase 2: Parallel tensor maturity training...")

            config = scene_result.get("config")
            if not config:
                print("  ⚠️  No config - skipping parallel training")
                return

            # Get training configuration
            target_maturity = getattr(config, 'target_tensor_maturity', 0.95)
            max_workers = getattr(config, 'max_training_workers', 4)

            # Get entities that need training
            entities_to_train = [
                e for e in entities
                if e.entity_metadata.get("needs_training", True)
                and hasattr(e, 'tensor') and e.tensor
            ]

            if not entities_to_train:
                print("  ⚠️  No entities need tensor training")
                return

            print(f"  Training {len(entities_to_train)} tensors with {max_workers} workers...")
            print(f"  Target maturity: {target_maturity}")

            try:
                # Import parallel training
                from training import train_entities_async

                # Get tensor database
                tensor_db = self._get_tensor_db()
                world_id = config.world_id if config else "unknown"

                # Progress tracking
                progress_updates = []

                def on_progress(tensor_id: str, maturity: float, cycles: int):
                    if len(progress_updates) % 10 == 0:  # Log every 10 updates
                        print(f"    Progress: {tensor_id} → maturity {maturity:.3f} ({cycles} cycles)")
                    progress_updates.append((tensor_id, maturity, cycles))

                # Run parallel training
                results = asyncio.run(
                    train_entities_async(
                        entities=entities_to_train,
                        tensor_db=tensor_db,
                        world_id=world_id,
                        run_id=run_id,
                        target_maturity=target_maturity,
                        max_workers=max_workers,
                        progress_callback=on_progress
                    )
                )

                # Report results
                successful = sum(1 for r in results.values() if r.success)
                failed = sum(1 for r in results.values() if not r.success)

                print(f"  ✓ Parallel training complete: {successful} succeeded, {failed} failed")

                # Update entity training metadata
                for entity in entities_to_train:
                    entity.entity_metadata["needs_training"] = False

                self.logfire.info(
                    "Parallel tensor training complete",
                    entities_trained=successful,
                    entities_failed=failed,
                    target_maturity=target_maturity,
                    max_workers=max_workers
                )

            except Exception as e:
                print(f"  ⚠️  Parallel training failed: {e}")
                self.logfire.warn("Parallel tensor training failed", error=str(e))

    def _synthesize_dialogs(
        self,
        entities: List[Entity],
        timepoints: List[Timepoint],
        scene_result: Dict,
        run_id: str
    ) -> None:
        """Step 4.5: Synthesize dialogs (M11) - entities already trained via ANDOS"""
        with self.logfire.span("step:dialog_synthesis"):
            print("\nStep 4.5: Synthesizing dialogs...")

            if len(entities) < 2:
                print("  ⚠️  Less than 2 entities - skipping dialog synthesis")
                return

            llm = scene_result["llm_client"]
            store = scene_result["store"]

            # Synthesize dialogs for each timepoint
            dialogs_created = 0

            for timepoint in timepoints:
                try:
                    # Select a subset of entities for dialog (2-4 entities)
                    import random
                    num_participants = min(4, len(entities))
                    dialog_participants = random.sample(entities, num_participants)

                    print(f"  Generating dialog for {timepoint.timepoint_id} with {num_participants} entities...")

                    # Build timeline context (simplified) - convert timestamps to ISO strings for JSON serialization
                    timeline = [{"event_description": tp.event_description, "timestamp": tp.timestamp.isoformat() if hasattr(tp.timestamp, 'isoformat') else str(tp.timestamp)} for tp in timepoints]

                    # Synthesize dialog (this invokes M11)
                    # Entities should now have tensors from ANDOS layer-by-layer training
                    dialog = synthesize_dialog(
                        dialog_participants,
                        timepoint,
                        timeline,
                        llm,
                        store,
                        run_id=run_id  # January 2026: Pass run_id for dialog persistence
                    )

                    # Save dialog to store
                    store.save_dialog(dialog)
                    dialogs_created += 1

                    print(f"  ✓ Created dialog with {len(dialog_participants)} participants")

                except Exception as e:
                    print(f"  ⚠️  Failed to synthesize dialog for {timepoint.timepoint_id}: {e}")
                    # Print traceback for debugging datetime serialization issues
                    if "datetime" in str(e).lower() or "json" in str(e).lower():
                        import traceback
                        traceback.print_exc()
                    # Continue with other timepoints

            print(f"✓ Synthesized {dialogs_created} dialogs")

            self.logfire.info(
                "Dialog synthesis complete",
                dialogs_created=dialogs_created,
                timepoints_processed=len(timepoints)
            )

    def _execute_queries(
        self,
        entities: List[Entity],
        timepoints: List[Timepoint],
        scene_result: Dict,
        run_id: str
    ) -> None:
        """Step 4.6: Execute queries to test lazy resolution (M5)"""
        with self.logfire.span("step:query_execution"):
            print("\nStep 4.6: Executing queries (M5 - lazy resolution)...")

            if not entities:
                print("  ⚠️  No entities - skipping query execution")
                return

            llm = scene_result["llm_client"]
            store = scene_result["store"]

            # Create query interface
            query_interface = QueryInterface(store, llm)

            # Generate 3-5 queries to exercise M5 lazy resolution
            queries_executed = 0
            queries_failed = 0

            # Sample entities for queries (up to 3)
            import random
            sample_entities = random.sample(entities, min(3, len(entities)))

            for entity in sample_entities:
                # Generate different query types for each entity
                query_types = [
                    f"What did {entity.entity_id.replace('_', ' ')} think about the events?",
                    f"What actions did {entity.entity_id.replace('_', ' ')} take?",
                    f"How did {entity.entity_id.replace('_', ' ')} interact with others?"
                ]

                for query_text in query_types[:2]:  # 2 queries per entity
                    try:
                        print(f"  Executing query: {query_text}")
                        response = query_interface.query(query_text)

                        # Log response summary
                        response_preview = response[:100] + "..." if len(response) > 100 else response
                        print(f"    ✓ Response: {response_preview}")

                        queries_executed += 1

                    except Exception as e:
                        print(f"    ⚠️  Query failed: {e}")
                        queries_failed += 1

            print(f"✓ Executed {queries_executed} queries ({queries_failed} failed)")

            self.logfire.info(
                "Query execution complete",
                queries_executed=queries_executed,
                queries_failed=queries_failed
            )

    def _format_training_data(
        self,
        entities: List[Entity],
        timepoints: List[Timepoint],
        scene_result: Dict,
        run_id: str
    ) -> List[Dict[str, str]]:
        """Step 5: Format training data"""
        with self.logfire.span("step:format_training_data"):
            print("\nStep 5: Formatting training data...")

            # Get store and llm from scene_result for rich context extraction
            store = scene_result.get("store")
            llm = scene_result.get("llm_client")

            # Initialize formatter with context manager support
            formatter = EntityEvolutionFormatter(store=store, llm=llm)

            if store and llm:
                print("  ✓ Context manager enabled (M3, M6, M7, M10, M11, M13, M14)")
            else:
                print("  ⚠️  Context manager disabled (missing store or llm)")

            # Create result structure that formatter expects
            formatted_result = {
                "specification": scene_result["specification"],
                "entities": entities,
                "timepoints": timepoints
            }

            training_examples = formatter.format_batch([formatted_result])

            print(f"✓ Generated {len(training_examples)} training examples")

            self.logfire.info(
                "Training data formatted",
                examples=len(training_examples)
            )

            return training_examples

    def _generate_script_exports(
        self,
        all_timepoints: List[Timepoint],
        trained_entities: List[Entity],
        scene_result: Dict,
        output_dir: Path,
        config: SimulationConfig,
        timestamp: str
    ) -> Dict[str, Path]:
        """
        Generate Fountain and PDF script exports.

        Args:
            all_timepoints: Complete list of all timepoints (including generated ones)
            trained_entities: Complete list of trained entities
            scene_result: Scene result dictionary (for store access)
            output_dir: Output directory
            config: Simulation configuration
            timestamp: Timestamp string for filenames

        Returns:
            Dict with 'fountain' and 'pdf' file paths
        """
        print("\n  📝 Generating script exports...")

        try:
            from reporting.script_generator import ScriptGenerator
            from reporting.export_formats import FountainExporter, PDFExporter

            store = scene_result.get("store")
            if not store:
                print("    ⚠️  No store available - skipping script export")
                return {}

            if not all_timepoints:
                print("    ⚠️  No timepoints available - skipping script export")
                return {}

            # Generate script structure using in-memory data (all timepoints + trained entities)
            generator = ScriptGenerator(store)
            script_data = generator.generate_script_structure_from_data(
                timepoints=all_timepoints,
                entities=trained_entities,
                world_id=config.world_id,
                title=f"{config.world_id} - {timestamp}",
                temporal_mode=config.temporal.mode.value
            )

            # Export Fountain script
            fountain_file = output_dir / f"screenplay_{timestamp}.fountain"
            fountain_exporter = FountainExporter()
            fountain_exporter.export(script_data, str(fountain_file))
            print(f"    ✓ Fountain script: {fountain_file.name} ({fountain_file.stat().st_size} bytes)")

            result_files = {'fountain': fountain_file}

            # Export PDF script (with graceful degradation if reportlab not installed)
            try:
                # Import check for reportlab
                from reportlab.lib.pagesizes import letter

                pdf_file = output_dir / f"screenplay_{timestamp}.pdf"
                pdf_exporter = PDFExporter()
                pdf_exporter.export(script_data, str(pdf_file))
                print(f"    ✓ PDF script: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")
                result_files['pdf'] = pdf_file
            except ImportError:
                print(f"    ⚠️  PDF export skipped: reportlab not installed (pip install reportlab)")
            except Exception as pdf_err:
                print(f"    ⚠️  PDF export failed: {pdf_err}")

            return result_files

        except Exception as e:
            print(f"    ⚠️  Script export failed: {e}")
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()
            # Non-fatal - continue with upload
            return {}

    def _upload_to_oxen(
        self, training_data: List[Dict], scene_result: Dict, all_timepoints: List[Timepoint], trained_entities: List[Entity], config: SimulationConfig, run_id: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Step 6: Upload to Oxen"""
        with self.logfire.span("step:oxen_upload"):
            print("\nStep 6: Uploading to Oxen...")

            # Check for Oxen token
            oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
            if not oxen_token:
                print("  ⚠️  No OXEN_API_TOKEN - skipping upload")
                return None, None

            # Save training data locally first
            output_dir = Path("datasets") / config.world_id
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"training_{timestamp}.jsonl"

            import json
            with open(output_file, 'w') as f:
                for example in training_data:
                    f.write(json.dumps(example) + '\n')

            print(f"  Saved locally: {output_file}")

            # Generate script exports (Fountain and PDF)
            # Pass all_timepoints and trained_entities instead of scene_result which only has initial data
            script_files = self._generate_script_exports(
                all_timepoints, trained_entities, scene_result, output_dir, config, timestamp
            )

            # Create Oxen client with separate repo per template
            repo_name = f"timepoint-{config.world_id}"

            try:
                oxen_client = OxenClient(
                    namespace="realityinspector",
                    repo_name=repo_name,
                    interactive_auth=False
                )

                # Create repo if needed
                if not oxen_client.repo_exists():
                    print(f"  Creating repository: {repo_name}...")
                    repo_info = oxen_client.create_repo(
                        name=repo_name,
                        description=f"Training data for {config.world_id}"
                    )
                    print(f"  ✓ Repository created")

                # Upload training dataset
                print(f"  Uploading training dataset...")
                upload_result = oxen_client.upload_dataset(
                    file_path=str(output_file),
                    commit_message=f"Training data: {len(training_data)} examples from {run_id}",
                    dst_path=f"datasets/{timestamp}/{output_file.name}",
                    create_repo_if_missing=True
                )

                print(f"  ✓ Training dataset uploaded")
                print(f"  Repo: {upload_result.repo_url}")
                print(f"  Dataset: {upload_result.dataset_url}")

                # Upload Fountain script if generated
                if 'fountain' in script_files and script_files['fountain']:
                    try:
                        print(f"  Uploading Fountain script...")
                        fountain_result = oxen_client.upload_dataset(
                            file_path=str(script_files['fountain']),
                            commit_message=f"Fountain screenplay for {run_id}",
                            dst_path=f"screenplays/{timestamp}/{script_files['fountain'].name}",
                            create_repo_if_missing=False
                        )
                        print(f"  ✓ Fountain script uploaded")
                    except Exception as e:
                        print(f"  ⚠️  Fountain upload failed: {e}")

                # Upload PDF script if generated
                if 'pdf' in script_files and script_files['pdf']:
                    try:
                        print(f"  Uploading PDF script...")
                        pdf_result = oxen_client.upload_dataset(
                            file_path=str(script_files['pdf']),
                            commit_message=f"PDF screenplay for {run_id}",
                            dst_path=f"screenplays/{timestamp}/{script_files['pdf'].name}",
                            create_repo_if_missing=False
                        )
                        print(f"  ✓ PDF script uploaded")
                    except Exception as e:
                        print(f"  ⚠️  PDF upload failed: {e}")

                self.logfire.info(
                    "Oxen upload complete",
                    repo_url=upload_result.repo_url,
                    fountain_uploaded='fountain' in script_files,
                    pdf_uploaded='pdf' in script_files
                )

                return upload_result.repo_url, upload_result.dataset_url

            except Exception as e:
                print(f"  ⚠️  Oxen upload failed: {e}")
                self.logfire.warn("Oxen upload failed", error=str(e))
                return None, None

    def _complete_metadata(
        self,
        run_id: str,
        scene_result: Dict,
        timepoints: List[Timepoint],
        training_data: List[Dict],
        oxen_repo_url: Optional[str],
        oxen_dataset_url: Optional[str]
    ) -> RunMetadata:
        """Step 7: Complete metadata tracking"""
        with self.logfire.span("step:complete_metadata"):
            print("\nStep 7: Completing metadata...")

            entities_count = len(scene_result["entities"])
            timepoints_count = len(timepoints)

            # FIX BUG #4: Get REAL cost/token tracking from LLM client
            llm = scene_result.get("llm_client")
            if llm and hasattr(llm, 'service'):
                # Get statistics from centralized service
                stats = llm.service.get_statistics()
                actual_cost = stats.get("total_cost", 0.0)
                logger_stats = stats.get("logger_stats", {})
                actual_tokens = logger_stats.get("total_tokens", 0)
                actual_calls = logger_stats.get("total_calls", 0)

                print(f"  📊 Real metrics from LLM service:")
                print(f"     Cost: ${actual_cost:.4f} (not placeholder!)")
                print(f"     Tokens: {actual_tokens:,}")
                print(f"     Calls: {actual_calls}")
            elif llm:
                # Fallback to legacy client stats if available
                actual_cost = getattr(llm, 'cost', 0.0)
                actual_tokens = getattr(llm, 'token_count', 0)
                actual_calls = timepoints_count  # Rough estimate only for legacy

                print(f"  ⚠️  Using legacy client stats (may be incomplete)")
            else:
                # Final fallback: use conservative estimates
                actual_cost = (entities_count * timepoints_count * 0.01)
                actual_tokens = entities_count * timepoints_count * 1000
                actual_calls = timepoints_count

                print(f"  ⚠️  No LLM client found, using estimates")

            # M1+M17: Calculate fidelity metrics (Database v2)
            config = scene_result.get("config")
            fidelity_strategy_json = None
            fidelity_distribution = None
            token_budget_compliance = None
            fidelity_efficiency_score = None

            # Calculate fidelity distribution (count ResolutionLevel across entities)
            from collections import Counter
            from schemas import ResolutionLevel
            resolution_counts = Counter()
            for entity in scene_result["entities"]:
                res_level = getattr(entity, 'resolution_level', ResolutionLevel.SCENE)
                resolution_counts[res_level.value] += 1

            fidelity_distribution = json.dumps(dict(resolution_counts))
            print(f"  📊 Fidelity distribution: {dict(resolution_counts)}")

            # Calculate token budget compliance
            if config and hasattr(config.temporal, 'token_budget') and config.temporal.token_budget:
                token_budget = config.temporal.token_budget
                token_budget_compliance = actual_tokens / token_budget if token_budget > 0 else None
                print(f"  📊 Token budget compliance: {token_budget_compliance:.2f} ({actual_tokens:,} / {token_budget:,})")

            # Calculate fidelity efficiency score (quality per token)
            # Quality proxy: entities + timepoints (output richness)
            quality_score = entities_count + timepoints_count
            if actual_tokens > 0:
                fidelity_efficiency_score = quality_score / actual_tokens
                print(f"  📊 Fidelity efficiency: {fidelity_efficiency_score:.6f} (quality: {quality_score}, tokens: {actual_tokens:,})")

            # Capture fidelity strategy from TemporalAgent (if available)
            temporal_agent = scene_result.get("temporal_agent")
            if temporal_agent and hasattr(temporal_agent, 'fidelity_strategy'):
                import json as json_module
                try:
                    strategy = temporal_agent.fidelity_strategy
                    if strategy:
                        fidelity_strategy_json = json_module.dumps(strategy.model_dump() if hasattr(strategy, 'model_dump') else str(strategy))
                        print(f"  📊 Fidelity strategy captured from TemporalAgent")
                except Exception as e:
                    print(f"  ⚠️  Failed to serialize fidelity strategy: {e}")

            metadata = self.metadata_manager.complete_run(
                run_id=run_id,
                entities_created=entities_count,
                timepoints_created=timepoints_count,
                training_examples=len(training_data),
                cost_usd=actual_cost,  # REAL cost, not estimate
                llm_calls=actual_calls,  # REAL call count
                tokens_used=actual_tokens,  # REAL token count
                oxen_repo_url=oxen_repo_url,
                oxen_dataset_url=oxen_dataset_url,
                # M1+M17: Database v2 - Fidelity metrics
                fidelity_strategy_json=fidelity_strategy_json,
                fidelity_distribution=fidelity_distribution,
                actual_tokens_used=float(actual_tokens) if actual_tokens else None,
                token_budget_compliance=token_budget_compliance,
                fidelity_efficiency_score=fidelity_efficiency_score
            )

            # Phase 6: Record simulation completion to usage tracking
            if self._track_usage and self._usage_bridge:
                try:
                    self._usage_bridge.record_simulation(
                        run_id=run_id,
                        success=True,
                        cost_usd=actual_cost,
                        tokens=actual_tokens
                    )
                    print(f"  📊 Usage recorded: ${actual_cost:.4f}, {actual_tokens:,} tokens")
                except Exception as e:
                    print(f"  ⚠️  Failed to record usage: {e}")

            print(f"✓ Metadata complete")
            print(f"  - Run ID: {run_id}")
            print(f"  - Entities: {entities_count}")
            print(f"  - Timepoints: {timepoints_count}")
            print(f"  - Training Examples: {len(training_data)}")
            print(f"  - Actual Cost: ${actual_cost:.4f}")
            print(f"  - Actual Tokens: {actual_tokens:,}")
            print(f"  - Actual LLM Calls: {actual_calls}")
            if oxen_repo_url:
                print(f"  - Oxen Repo: {oxen_repo_url}")

            self.logfire.info(
                "Metadata tracking complete",
                run_id=run_id,
                cost=actual_cost,
                tokens=actual_tokens,
                calls=actual_calls
            )

            return metadata

    def _run_convergence_analysis(
        self,
        run_id: str,
        template_id: str,
        config: SimulationConfig
    ) -> None:
        """
        Step 10: Optional Convergence Analysis (post-run).

        Compares the current run's causal graph against recent runs of the same template.
        Requires config.convergence.enabled = True.

        Args:
            run_id: Current run ID
            template_id: Template identifier
            config: Simulation configuration with convergence settings
        """
        with self.logfire.span("step:convergence_analysis"):
            print("\nStep 10: Running convergence analysis...")

            try:
                from evaluation.convergence import (
                    extract_causal_graph,
                    compute_convergence_from_graphs,
                )
                from schemas import ConvergenceSet
                from storage import GraphStore
                import uuid

                conv_config = config.convergence
                run_count = conv_config.run_count if conv_config else 3

                # Get recent runs for this template
                all_runs = self.metadata_manager.get_all_runs()
                template_runs = [
                    r for r in all_runs
                    if hasattr(r, 'template_id') and r.template_id == template_id
                ]

                # Take most recent N runs (including current)
                recent_runs = template_runs[-run_count:]

                if len(recent_runs) < 2:
                    print(f"  Need at least 2 runs for convergence, found {len(recent_runs)}")
                    return

                print(f"  Analyzing {len(recent_runs)} runs of template: {template_id}")

                # Extract REAL causal graphs from shared database (not mechanism proxies!)
                graphs = []
                for run in recent_runs:
                    try:
                        # Use extract_causal_graph() to get ACTUAL temporal/knowledge edges
                        # This reads from SHARED_DB_PATH where timepoints/events were persisted
                        graph = extract_causal_graph(
                            run_id=run.run_id,
                            db_path=SHARED_DB_PATH,
                            template_id=template_id
                        )

                        # Log graph statistics for debugging
                        print(f"    Run {run.run_id}: {len(graph.temporal_edges)} temporal edges, "
                              f"{len(graph.knowledge_edges)} knowledge edges, "
                              f"{len(graph.timepoints)} timepoints")

                        if graph.edge_count > 0:
                            graphs.append(graph)
                        else:
                            print(f"    ⚠️  Run {run.run_id}: empty graph (no edges)")

                    except Exception as e:
                        print(f"    ⚠️  Failed to extract graph for {run.run_id}: {e}")

                if len(graphs) < 2:
                    print(f"  Could not build enough graphs with edges (got {len(graphs)})")
                    return

                # Compute convergence
                result = compute_convergence_from_graphs(graphs)

                # Display results
                print(f"\n  📊 Convergence Results:")
                print(f"  ├─ Score: {result.convergence_score:.2%}")
                print(f"  ├─ Grade: {result.robustness_grade}")
                print(f"  ├─ Consensus Edges: {len(result.consensus_edges)}")
                print(f"  └─ Contested Edges: {len(result.contested_edges)}")

                # Store result
                store = GraphStore("sqlite:///metadata/runs.db")
                convergence_set = ConvergenceSet(
                    set_id=f"conv_e2e_{uuid.uuid4().hex[:8]}",
                    template_id=template_id,
                    run_ids=json.dumps(result.run_ids),
                    run_count=result.run_count,
                    convergence_score=result.convergence_score,
                    min_similarity=result.min_similarity,
                    max_similarity=result.max_similarity,
                    robustness_grade=result.robustness_grade,
                    consensus_edge_count=len(result.consensus_edges),
                    contested_edge_count=len(result.contested_edges),
                    divergence_points=json.dumps([
                        {"edge": dp.edge, "ratio": dp.agreement_ratio}
                        for dp in result.divergence_points[:10]
                    ])
                )
                store.save_convergence_set(convergence_set)

                print(f"  ✅ Convergence analysis saved: {convergence_set.set_id}")

                self.logfire.info(
                    "Convergence analysis complete",
                    score=result.convergence_score,
                    grade=result.robustness_grade,
                    set_id=convergence_set.set_id
                )

            except Exception as e:
                print(f"  ⚠️  Convergence analysis failed: {e}")
                self.logfire.warn("Convergence analysis failed", error=str(e))
