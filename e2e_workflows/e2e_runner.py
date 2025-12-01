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

    def __init__(self, metadata_manager: MetadataManager, generate_summary: bool = True):
        """
        Initialize E2E runner.

        Args:
            metadata_manager: Metadata tracking manager
            generate_summary: Whether to generate LLM-powered run summaries (default: True)
        """
        self.metadata_manager = metadata_manager
        self.generate_summary = generate_summary
        set_metadata_manager(metadata_manager)
        self.logfire = logfire_setup.get_logfire()

        # Initialize shared store for convergence analysis (persists timepoints/events across runs)
        self._shared_store: Optional[GraphStore] = None

    def _get_shared_store(self) -> GraphStore:
        """Get or create the shared store for convergence data persistence."""
        if self._shared_store is None:
            # Ensure metadata directory exists
            Path("metadata").mkdir(parents=True, exist_ok=True)
            self._shared_store = GraphStore(f"sqlite:///{SHARED_DB_PATH}")
        return self._shared_store

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
        Step 2.5: Initialize baseline tensors (NEW - Phase 11 Architecture Pivot).

        This replaces prospection-based initialization with baseline + LLM-guided approach:
        1. Create baseline tensors (instant, no LLM, no bias leakage)
        2. Set maturity to 0.0
        3. Mark for LLM-guided population during ANDOS training

        Architectural improvements:
        - OLD: Prospection was MANDATORY for initialization (mechanism theater)
        - NEW: Baseline initialization is instant and deterministic
        - M15 (Prospection) becomes truly OPTIONAL again
        - No indirect bias leakage through shared LLM context
        - LLM-guided population happens DURING ANDOS training (per-entity isolation)
        """
        with self.logfire.span("step:baseline_tensor_init"):
            print("\nStep 2.5: Initializing baseline tensors...")

            entities = scene_result["entities"]
            store = scene_result["store"]

            # Import baseline tensor creation
            from tensor_initialization import create_baseline_tensor, create_fallback_tensor
            import base64
            import json

            entities_initialized = 0
            entities_failed = 0

            for entity in entities:
                try:
                    print(f"  Creating baseline tensor for {entity.entity_id}...")

                    # Create baseline tensor (instant, no LLM)
                    tensor = create_baseline_tensor(entity)

                    # Serialize tensor to entity.tensor
                    entity.tensor = json.dumps({
                        "context_vector": base64.b64encode(tensor.context_vector).decode('utf-8'),
                        "biology_vector": base64.b64encode(tensor.biology_vector).decode('utf-8'),
                        "behavior_vector": base64.b64encode(tensor.behavior_vector).decode('utf-8')
                    })

                    # Set maturity and training metadata
                    entity.tensor_maturity = 0.0  # Baseline only, needs population + training
                    entity.tensor_training_cycles = 0
                    entity.entity_metadata["baseline_initialized"] = True
                    entity.entity_metadata["needs_llm_population"] = True
                    entity.entity_metadata["needs_training"] = True

                    # Save entity with baseline tensor
                    store.save_entity(entity)

                    entities_initialized += 1
                    print(f"  ✓ {entity.entity_id}: baseline tensor created (maturity: 0.0)")

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
                        store.save_entity(entity)
                        entities_initialized += 1
                        print(f"  ⚠️  {entity.entity_id}: using fallback tensor")
                    except Exception as fallback_err:
                        print(f"  ❌ Fatal: Even fallback failed for {entity.entity_id}: {fallback_err}")

            print(f"✓ Initialized {entities_initialized} entities with baseline tensors")
            if entities_failed > 0:
                print(f"  ⚠️  {entities_failed} entities used fallback tensors")
            print(f"  📝 Note: LLM-guided population happens during ANDOS training (Step 4)")

            self.logfire.info(
                "Baseline tensor initialization complete",
                entities_initialized=entities_initialized,
                entities_failed=entities_failed
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

            # FORWARD MODE: Original forward generation logic
            all_timepoints = [initial_timepoint]
            current_timepoint = initial_timepoint

            # CONVERGENCE FIX: Persist initial timepoint to shared DB
            self._persist_timepoint_for_convergence(initial_timepoint, run_id)

            # Generate remaining timepoints
            target_count = config.timepoints.count
            for i in range(1, target_count):
                print(f"  Generating timepoint {i+1}/{target_count}...")

                try:
                    next_timepoint = temporal_agent.generate_next_timepoint(
                        current_timepoint,
                        context={"iteration": i, "total": target_count}
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
                            store.save_entity(entity)
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
                        store
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
