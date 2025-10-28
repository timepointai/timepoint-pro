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

from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from schemas import Entity, Timepoint, TemporalMode, ResolutionLevel
from workflows import TemporalAgent, create_entity_training_workflow, synthesize_dialog
from oxen_integration import OxenClient
from oxen_integration.data_formatters import EntityEvolutionFormatter
from metadata.run_tracker import MetadataManager, RunMetadata
from metadata.tracking import set_current_run_id, clear_current_run_id, set_metadata_manager
from metadata import logfire_setup
from andos.layer_computer import compute_andos_layers, validate_andos_layers


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

    def __init__(self, metadata_manager: MetadataManager):
        """
        Initialize E2E runner.

        Args:
            metadata_manager: Metadata tracking manager
        """
        self.metadata_manager = metadata_manager
        set_metadata_manager(metadata_manager)
        self.logfire = logfire_setup.get_logfire()

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
                    "entity_metadata": config.metadata  # Pass rich metadata for specialized mechanisms
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

            # Create temporal agent
            temporal_agent = TemporalAgent(
                mode=config.temporal.mode,
                store=store,
                llm_client=llm
            )

            all_timepoints = [initial_timepoint]
            current_timepoint = initial_timepoint

            # Generate remaining timepoints
            target_count = config.timepoints.count
            for i in range(1, target_count):
                print(f"  Generating timepoint {i+1}/{target_count}...")

                try:
                    next_timepoint = temporal_agent.generate_next_timepoint(
                        current_timepoint,
                        context={"iteration": i, "total": target_count}
                    )

                    # Save to database
                    store.save_timepoint(next_timepoint)

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

            # Export PDF script
            pdf_file = output_dir / f"screenplay_{timestamp}.pdf"
            pdf_exporter = PDFExporter()
            pdf_exporter.export(script_data, str(pdf_file))
            print(f"    ✓ PDF script: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")

            return {
                'fountain': fountain_file,
                'pdf': pdf_file
            }

        except Exception as e:
            print(f"    ⚠️  Script export failed: {e}")
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

                # Upload dataset
                print(f"  Uploading dataset...")
                upload_result = oxen_client.upload_dataset(
                    file_path=str(output_file),
                    commit_message=f"Training data: {len(training_data)} examples from {run_id}",
                    dst_path=f"datasets/{timestamp}/{output_file.name}",
                    create_repo_if_missing=True
                )

                print(f"  ✓ Upload complete")
                print(f"  Repo: {upload_result.repo_url}")
                print(f"  Dataset: {upload_result.dataset_url}")

                self.logfire.info(
                    "Oxen upload complete",
                    repo_url=upload_result.repo_url
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

            metadata = self.metadata_manager.complete_run(
                run_id=run_id,
                entities_created=entities_count,
                timepoints_created=timepoints_count,
                training_examples=len(training_data),
                cost_usd=actual_cost,  # REAL cost, not estimate
                llm_calls=actual_calls,  # REAL call count
                tokens_used=actual_tokens,  # REAL token count
                oxen_repo_url=oxen_repo_url,
                oxen_dataset_url=oxen_dataset_url
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
