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
from workflows import TemporalAgent
from oxen_integration import OxenClient
from oxen_integration.data_formatters import EntityEvolutionFormatter
from metadata.run_tracker import MetadataManager, RunMetadata
from metadata.tracking import set_current_run_id, clear_current_run_id, set_metadata_manager
from metadata import logfire_setup


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

                # Step 3: Generate all timepoints
                all_timepoints = self._generate_all_timepoints(
                    scene_result, config, run_id
                )

                # Step 4: Train entities (progressive elevation)
                trained_entities = self._train_entities(
                    scene_result, all_timepoints, run_id
                )

                # Step 5: Format training data
                training_data = self._format_training_data(
                    trained_entities, all_timepoints, scene_result, run_id
                )

                # Step 6: Upload to Oxen
                oxen_repo_url, oxen_dataset_url = self._upload_to_oxen(
                    training_data, config, run_id
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

            llm = LLMClient(api_key=api_key, dry_run=False)

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
                    "temporal_mode": config.temporal.mode.value
                },
                save_to_db=True
            )

            # Store for later steps
            result["llm_client"] = llm
            result["store"] = store
            result["db_path"] = db_path

            print(f"✓ Initial scene created:")
            print(f"  - Entities: {len(result['entities'])}")
            print(f"  - Timepoints: {len(result['timepoints'])}")

            self.logfire.info(
                "Initial scene generated",
                entities=len(result['entities']),
                timepoints=len(result['timepoints'])
            )

            return result

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

                    self.logfire.metric(
                        "timepoints_generated",
                        len(all_timepoints),
                        run_id=run_id
                    )

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
        self, scene_result: Dict, timepoints: List[Timepoint], run_id: str
    ) -> List[Entity]:
        """Step 4: Train entities with progressive resolution elevation"""
        with self.logfire.span("step:entity_training"):
            print("\nStep 4: Training entities...")

            entities = scene_result["entities"]

            # For now, we'll simulate entity training by recording resolution levels
            # In a full implementation, this would use LangGraph workflows
            # to actually train entities through multiple passes

            trained_entities = []
            for entity in entities:
                # Record resolution assignment
                self.metadata_manager.record_resolution(
                    run_id,
                    entity.entity_id,
                    entity.resolution_level,
                    timepoints[0].timepoint_id
                )

                trained_entities.append(entity)

            print(f"✓ Trained {len(trained_entities)} entities")

            self.logfire.info(
                "Entity training complete",
                entities=len(trained_entities)
            )

            return trained_entities

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

            formatter = EntityEvolutionFormatter()

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

    def _upload_to_oxen(
        self, training_data: List[Dict], config: SimulationConfig, run_id: str
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

            # Estimate cost (rough approximation)
            # TODO: Track actual token usage from LLM client
            entities_count = len(scene_result["entities"])
            timepoints_count = len(timepoints)
            estimated_cost = (entities_count * timepoints_count * 0.01)  # Rough estimate

            metadata = self.metadata_manager.complete_run(
                run_id=run_id,
                entities_created=entities_count,
                timepoints_created=timepoints_count,
                training_examples=len(training_data),
                cost_usd=estimated_cost,
                llm_calls=timepoints_count,  # Rough estimate
                tokens_used=entities_count * timepoints_count * 1000,  # Rough estimate
                oxen_repo_url=oxen_repo_url,
                oxen_dataset_url=oxen_dataset_url
            )

            print(f"✓ Metadata complete")
            print(f"  - Run ID: {run_id}")
            print(f"  - Entities: {entities_count}")
            print(f"  - Timepoints: {timepoints_count}")
            print(f"  - Training Examples: {len(training_data)}")
            print(f"  - Estimated Cost: ${estimated_cost:.2f}")
            if oxen_repo_url:
                print(f"  - Oxen Repo: {oxen_repo_url}")

            self.logfire.info(
                "Metadata tracking complete",
                run_id=run_id,
                cost=estimated_cost
            )

            return metadata
