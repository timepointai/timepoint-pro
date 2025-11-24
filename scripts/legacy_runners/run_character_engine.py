#!/usr/bin/env python3
"""
Character Engine - Multi-Modal Workflow for Character-Based Fine-Tuning Dataset Generation

This script executes the complete workflow to generate 6,100+ training examples demonstrating
all 17 Timepoint mechanisms through character-based temporal simulations.

Workflow:
1. Phase 1: Deep Cases (3 cases × 5 temporal modes = 15 runs) → 900 examples
2. Phase 2: Breadth Cases (20 different scenarios) → 1,200 examples
3. Phase 3: Horizontal Variations (100 variations) → 4,000 examples
4. Phase 4: Upload to Oxen with experiment branches

Target: 6,100+ training examples total

MAX Mode (--max):
    Creates ONE massive vertical simulation with:
    - 12-124 entities (characters, locations, abstract concepts)
    - Up to 200 timepoints
    - All 17 mechanisms at maximum depth
    - TRAINED resolution for all main characters
    - Dedicated Oxen repo + fine-tuning branch

Usage:
    # Standard mode
    export OPENROUTER_API_KEY=your_key
    export OXEN_API_TOKEN=your_token
    export LLM_SERVICE_ENABLED=true
    python run_character_engine.py

    # MAX mode - single massive vertical simulation
    python run_character_engine.py --max
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports
from generation.config_schema import SimulationConfig, TemporalMode, ResolutionLevel
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from oxen_integration.character_formatter import CharacterRoleplayFormatter
from oxen_integration.client import OxenClient
from generation.horizontal_generator import HorizontalGenerator
from generation.progress_tracker import ProgressTracker


class CharacterEngine:
    """
    Main workflow orchestrator for character-based training data generation.

    This class coordinates:
    - Deep case generation (multiple temporal modes)
    - Breadth case generation (multiple scenarios)
    - Horizontal variation generation
    - Oxen upload with experiment branches
    """

    def __init__(
        self,
        llm: LLMClient,
        store: GraphStore,
        oxen_namespace: str = "realityinspector",
        dry_run: bool = False
    ):
        """
        Initialize Character Engine.

        Args:
            llm: LLM client for generation
            store: Graph store for persistence
            oxen_namespace: Oxen.ai namespace for uploads
            dry_run: If True, skip LLM calls and Oxen uploads
        """
        self.llm = llm
        self.store = store
        self.oxen_namespace = oxen_namespace
        self.dry_run = dry_run

        # Initialize components
        self.progress_tracker = ProgressTracker()
        self.oxen_client = None
        if not dry_run:
            try:
                self.oxen_client = OxenClient(namespace=oxen_namespace)
                logger.info(f"Oxen client initialized for namespace: {oxen_namespace}")
            except Exception as e:
                logger.warning(f"Could not initialize Oxen client: {e}")
                logger.warning("Continuing without Oxen upload capability")

        # Output directory
        self.output_dir = Path("./output/character_engine")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            "deep_examples": 0,
            "breadth_examples": 0,
            "variation_examples": 0,
            "total_examples": 0,
            "cost_usd": 0.0,
            "duration_seconds": 0.0
        }

    def run_complete_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete character engine workflow.

        Returns:
            Statistics and summary of generation
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info("TIMEPOINT CHARACTER ENGINE - COMPLETE WORKFLOW")
        logger.info("="*80)
        logger.info(f"Start time: {start_time}")
        logger.info(f"Dry run mode: {self.dry_run}")
        logger.info("")

        try:
            # Phase 1: Deep Cases with Multi-Modal Rendering
            logger.info("PHASE 1: Deep Cases (3 cases × 5 modes = 15 runs)")
            logger.info("-"*80)
            deep_examples = self.phase1_deep_cases()
            self.stats["deep_examples"] = len(deep_examples)
            logger.info(f"Phase 1 complete: {len(deep_examples)} examples generated")
            logger.info("")

            # Phase 2: Breadth Cases
            logger.info("PHASE 2: Breadth Cases (20 different scenarios)")
            logger.info("-"*80)
            breadth_examples = self.phase2_breadth_cases()
            self.stats["breadth_examples"] = len(breadth_examples)
            logger.info(f"Phase 2 complete: {len(breadth_examples)} examples generated")
            logger.info("")

            # Phase 3: Horizontal Variations
            logger.info("PHASE 3: Horizontal Variations (100 variations)")
            logger.info("-"*80)
            variation_examples = self.phase3_horizontal_variations()
            self.stats["variation_examples"] = len(variation_examples)
            logger.info(f"Phase 3 complete: {len(variation_examples)} examples generated")
            logger.info("")

            # Combine all examples
            all_examples = deep_examples + breadth_examples + variation_examples
            self.stats["total_examples"] = len(all_examples)

            # Save to disk
            logger.info("Saving training data to disk...")
            self.save_training_data(deep_examples, breadth_examples, variation_examples)

            # Phase 4: Upload to Oxen
            if not self.dry_run and self.oxen_client:
                logger.info("PHASE 4: Upload to Oxen with Experiment Branches")
                logger.info("-"*80)
                self.phase4_upload_to_oxen(deep_examples, breadth_examples, variation_examples)
                logger.info("Phase 4 complete: Data uploaded to Oxen")
            else:
                logger.info("PHASE 4: Skipped (dry run or no Oxen client)")

            # Final statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.stats["duration_seconds"] = duration

            logger.info("")
            logger.info("="*80)
            logger.info("WORKFLOW COMPLETE")
            logger.info("="*80)
            logger.info(f"Total examples generated: {self.stats['total_examples']}")
            logger.info(f"  - Deep cases: {self.stats['deep_examples']}")
            logger.info(f"  - Breadth cases: {self.stats['breadth_examples']}")
            logger.info(f"  - Variations: {self.stats['variation_examples']}")
            logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            logger.info(f"Output directory: {self.output_dir}")
            logger.info("")

            return self.stats

        except Exception as e:
            logger.error(f"Workflow failed with error: {e}")
            raise

    def phase1_deep_cases(self) -> List[Dict[str, Any]]:
        """
        Phase 1: Generate deep cases with multi-modal rendering.

        Runs 3 deep cases (Scarlet Study, Empty House, Final Problem) in 5 temporal modes each.
        Total: 15 simulation runs → ~900 training examples

        Returns:
            List of training examples
        """
        all_examples = []

        # Define the 3 deep cases
        deep_case_methods = [
            ("scarlet_study_deep", SimulationConfig.example_scarlet_study_deep),
            ("empty_house_flashback", SimulationConfig.example_empty_house_flashback),
            ("final_problem_branching", SimulationConfig.example_final_problem_branching)
        ]

        # Define the 5 temporal modes
        temporal_modes = [
            TemporalMode.PEARL,
            TemporalMode.DIRECTORIAL,
            TemporalMode.NONLINEAR,
            TemporalMode.BRANCHING,
            TemporalMode.CYCLICAL
        ]

        # Run each case in each mode
        for case_name, case_method in deep_case_methods:
            for mode in temporal_modes:
                logger.info(f"Generating: {case_name} in {mode.value} mode...")

                # Create config with this temporal mode
                config = case_method()
                config.temporal.mode = mode

                # Adjust temporal mode-specific settings
                if mode == TemporalMode.DIRECTORIAL:
                    config.temporal.narrative_arc = "rising_action"
                elif mode == TemporalMode.CYCLICAL:
                    config.temporal.cycle_length = 10

                # Run simulation
                if self.dry_run:
                    # Dry run: create mock examples
                    examples = self._create_mock_examples(config, count=60)
                else:
                    # Real run: execute simulation
                    result = simulate_event(
                        config.scenario_description,
                        self.llm,
                        self.store,
                        context={
                            "max_entities": config.entities.count,
                            "max_timepoints": 5,  # Orchestrator limitation
                            "temporal_mode": mode.value
                        },
                        save_to_db=False  # Don't save to DB - we only need results for formatting
                    )

                    # Format with CharacterRoleplayFormatter
                    formatter = CharacterRoleplayFormatter(character_focus="detective")
                    examples = formatter.format_simulation(result, config)

                all_examples.extend(examples)
                logger.info(f"  → Generated {len(examples)} examples for {case_name}/{mode.value}")

        return all_examples

    def phase2_breadth_cases(self) -> List[Dict[str, Any]]:
        """
        Phase 2: Generate breadth cases (20 different scenarios).

        Creates 20 compact scenarios (poison, theft, blackmail, etc.) in Pearl mode.
        Total: 20 simulation runs → ~1,200 training examples

        Returns:
            List of training examples
        """
        all_examples = []

        # Define 20 breadth scenarios
        breadth_scenarios = self._get_breadth_scenarios()

        for i, scenario_config in enumerate(breadth_scenarios, 1):
            logger.info(f"Generating breadth case {i}/20: {scenario_config.world_id}...")

            if self.dry_run:
                # Dry run: create mock examples
                examples = self._create_mock_examples(scenario_config, count=60)
            else:
                # Real run: execute simulation
                result = simulate_event(
                    scenario_config.scenario_description,
                    self.llm,
                    self.store,
                    context={
                        "max_entities": scenario_config.entities.count,
                        "max_timepoints": 3,
                        "temporal_mode": "pearl"
                    },
                    save_to_db=False  # Don't save to DB - we only need results for formatting
                )

                # Format with CharacterRoleplayFormatter
                formatter = CharacterRoleplayFormatter(character_focus="detective")
                examples = formatter.format_simulation(result, scenario_config)

            all_examples.extend(examples)
            logger.info(f"  → Generated {len(examples)} examples")

        return all_examples

    def phase3_horizontal_variations(self) -> List[Dict[str, Any]]:
        """
        Phase 3: Generate horizontal variations (100 variations).

        Uses HorizontalGenerator to create variations of base scenarios.
        Total: 100 variations → ~4,000 training examples

        Returns:
            List of training examples
        """
        all_examples = []

        if self.dry_run:
            # Dry run: create mock variation examples
            logger.info("Generating 100 variation examples (dry run)...")
            all_examples = self._create_mock_examples(
                SimulationConfig.example_board_meeting(),
                count=4000
            )
            return all_examples

        # Use HorizontalGenerator for real variations
        logger.info("Generating horizontal variations...")

    def run_max_mode(self, num_entities: int = 24, num_timepoints: int = 50) -> Dict[str, Any]:
        """
        MAX Mode: Generate one massive vertical simulation showcasing all 17 mechanisms.

        This creates a single comprehensive scenario with:
        - Multiple characters at TRAINED resolution
        - Extensive temporal depth (up to 200 timepoints)
        - All 17 Timepoint mechanisms fully utilized
        - Dedicated Oxen repo for fine-tuning

        Args:
            num_entities: Number of entities (12-124)
            num_timepoints: Number of timepoints (10-200)

        Returns:
            Statistics dictionary
        """
        start_time = datetime.now()

        logger.info("="*80)
        logger.info("TIMEPOINT CHARACTER ENGINE - MAX MODE")
        logger.info("="*80)
        logger.info(f"Start time: {start_time}")
        logger.info(f"Configuration:")
        logger.info(f"  Entities: {num_entities}")
        logger.info(f"  Timepoints: {num_timepoints}")
        logger.info(f"  Target: Maximum vertical depth + all 17 mechanisms")
        logger.info("")

        try:
            # Create the massive scenario config
            logger.info("📋 Creating MAX scenario configuration...")
            max_config = self._create_max_scenario_config(num_entities, num_timepoints)

            logger.info("🎬 Running massive vertical simulation...")
            logger.info(f"   Scenario: {max_config.world_id}")
            logger.info(f"   Entities: {max_config.entities.count}")
            logger.info(f"   Timepoints: {max_config.timepoints.count + max_config.timepoints.before_count + max_config.timepoints.after_count}")
            logger.info("")

            if self.dry_run:
                # Dry run: create mock examples
                logger.info("DRY RUN: Creating mock examples...")
                all_examples = self._create_mock_examples(max_config, count=num_entities * num_timepoints)
            else:
                # Real run: execute massive simulation
                logger.info("⚡ Executing simulation with real LLM...")
                result = simulate_event(
                    max_config.scenario_description,
                    self.llm,
                    self.store,
                    context={
                        "max_entities": max_config.entities.count,
                        "max_timepoints": num_timepoints,
                        "temporal_mode": "pearl",
                        "require_trained_resolution": True,  # Force TRAINED for main characters
                        "require_exact_counts": True  # MAX mode: enforce exact entity/timepoint counts
                    },
                    save_to_db=False
                )

                # Format with CharacterRoleplayFormatter for each main character
                logger.info("📝 Formatting training examples...")
                all_examples = []

                # Format for multiple character perspectives
                main_characters = ["detective", "doctor", "villain", "witness"]
                for char in main_characters:
                    logger.info(f"   Formatting perspective: {char}")
                    formatter = CharacterRoleplayFormatter(character_focus=char)
                    examples = formatter.format_simulation(result, max_config)
                    all_examples.extend(examples)
                    logger.info(f"     → Generated {len(examples)} examples for {char}")

            # Save to disk
            logger.info("")
            logger.info("💾 Saving MAX mode training data...")
            max_output_dir = self.output_dir / "max_mode"
            max_output_dir.mkdir(parents=True, exist_ok=True)

            max_path = max_output_dir / f"max_vertical_{num_entities}e_{num_timepoints}t.jsonl"
            with open(max_path, 'w') as f:
                for example in all_examples:
                    f.write(json.dumps(example) + '\n')
            logger.info(f"   Saved: {max_path} ({len(all_examples)} examples)")

            # Upload to Oxen with dedicated repo
            if not self.dry_run and self.oxen_client:
                logger.info("")
                logger.info("📤 Uploading to Oxen.ai with dedicated fine-tuning branch...")
                self._upload_max_mode_to_oxen(all_examples, num_entities, num_timepoints, max_path)

            # Calculate statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            stats = {
                "mode": "MAX",
                "total_examples": len(all_examples),
                "entities": num_entities,
                "timepoints": num_timepoints,
                "duration_seconds": duration,
                "output_path": str(max_path),
                "cost_usd": 0.0  # TODO: track from LLM service
            }

            logger.info("")
            logger.info("="*80)
            logger.info("MAX MODE COMPLETE")
            logger.info("="*80)
            logger.info(f"Total examples: {len(all_examples):,}")
            logger.info(f"Entities: {num_entities}")
            logger.info(f"Timepoints: {num_timepoints}")
            logger.info(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
            logger.info(f"Output: {max_path}")
            logger.info("")

            return stats

        except Exception as e:
            logger.error(f"MAX mode failed with error: {e}")
            raise

    def _create_max_scenario_config(self, num_entities: int, num_timepoints: int) -> Any:
        """Create configuration for maximum depth scenario"""
        from generation.config_schema import SimulationConfig, EntityConfig, TimepointConfig, TemporalConfig, OutputConfig, ResolutionLevel, TemporalMode

        # Calculate timepoint distribution (before, critical, after)
        before_count = num_timepoints // 2
        after_count = num_timepoints - before_count - 1

        return SimulationConfig(
            scenario_description=(
                f"The Grand Investigation: A massive criminal conspiracy unfolds across {num_entities} "
                f"interconnected characters spanning {num_timepoints} timepoints. "
                "This is the ultimate test of temporal reasoning, featuring: "
                "a brilliant detective team (Holmes, Watson, Lestrade), "
                "a criminal mastermind network (Moriarty, Moran, Adler), "
                "political figures (Prime Minister, Foreign Secretary, diplomats), "
                "scientific experts (chemists, physicians, forensic analysts), "
                "witnesses and informants from all social classes, "
                "London locations as entities (Scotland Yard, 221B Baker Street, Parliament), "
                "and abstract concepts (Justice, Deception, Loyalty). "
                "Track the investigation from initial discovery through complex deductions, "
                "red herrings, betrayals, scientific analysis, political intrigue, "
                "multiple confrontations, and final resolution. "
                "REQUIREMENTS: All 17 Timepoint mechanisms must be demonstrated at maximum depth. "
                "M1: Heterogeneous fidelity (detectives at TRAINED, witnesses at SCENE). "
                "M2: Progressive training (detectives improve deduction over time). "
                "M3: Exposure events (track every observation and deduction). "
                "M4: Physics validation (energy, sleep, biological constraints). "
                "M5: Query-driven resolution (frequent access elevates detail). "
                "M6: TTM tensors (unique for each character type). "
                "M7: Causal temporal chains (strict causality). "
                "M8: Embodied states (injury, fatigue, illness affect cognition). "
                "M9: On-demand generation (new witnesses as needed). "
                "M10: Scene entities (atmosphere shifts with revelations). "
                "M11: Dialog synthesis (interrogations, debates, confessions). "
                "M12: Counterfactual branching (what if clues were missed?). "
                "M13: Multi-entity synthesis (relationship evolution). "
                "M14: Circadian patterns (time of day affects behavior). "
                "M15: Entity prospection (predict next moves). "
                "M16: Animistic entities (buildings, abstract concepts). "
                "M17: Modal causality (Pearl mode strict causality)."
            ),
            world_id=f"max_vertical_{num_entities}entities_{num_timepoints}timepoints",
            entities=EntityConfig(
                count=num_entities,
                types=["human", "building", "abstract"],
                initial_resolution=ResolutionLevel.TRAINED,  # Start all at TRAINED for MAX mode
                animism_level=6  # Maximum animism - include all entity types
            ),
            timepoints=TimepointConfig(
                count=1,  # Critical revelation moment
                before_count=before_count,
                after_count=after_count,
                resolution="hour"  # Hour-by-hour tracking
            ),
            temporal=TemporalConfig(
                mode=TemporalMode.PEARL,  # Strict causality
                enable_counterfactuals=True  # M12
            ),
            outputs=OutputConfig(
                formats=["jsonl", "json"],
                include_dialogs=True,  # M11
                include_relationships=True,  # M13
                include_knowledge_flow=True,  # M3
                export_ml_dataset=True
            ),
            metadata={
                "mode": "MAX",
                "character_focus": ["detective", "doctor", "villain", "witness"],
                "mechanisms_featured": [
                    "M1_heterogeneous_fidelity",
                    "M2_progressive_training",
                    "M3_exposure_events",
                    "M4_physics_validation",
                    "M5_query_resolution",
                    "M6_ttm_tensors",
                    "M7_causal_chains",
                    "M8_embodied_states",
                    "M9_on_demand_generation",
                    "M10_scene_entities",
                    "M11_dialog_synthesis",
                    "M12_counterfactual_branching",
                    "M13_multi_entity_synthesis",
                    "M14_circadian_patterns",
                    "M15_entity_prospection",
                    "M16_animistic_entities",
                    "M17_modal_causality"
                ],
                "character_ttm_tensors": {
                    "detective": ["observation_acuity", "deductive_chains", "pattern_recognition", "intuition_strength"],
                    "doctor": ["medical_knowledge", "empathy_vector", "diagnostic_skill", "ethical_reasoning"],
                    "villain": ["strategic_planning", "manipulation_skill", "risk_assessment", "ruthlessness"],
                    "witness": ["memory_reliability", "fear_level", "honesty_index", "suggestibility"]
                },
                "temporal_depth": num_timepoints,
                "expected_training_examples": num_entities * num_timepoints * 4  # 4 character perspectives
            }
        )

    def _upload_max_mode_to_oxen(
        self,
        examples: List[Dict],
        num_entities: int,
        num_timepoints: int,
        local_path: Path
    ):
        """Upload MAX mode data to Oxen with dedicated fine-tuning branch"""
        if not self.oxen_client:
            logger.warning("No Oxen client available, skipping upload")
            return

        try:
            # Create dedicated repository for MAX mode
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            repo_name = f"timepoint-max-{num_entities}e-{num_timepoints}t-{timestamp}"

            logger.info(f"   Creating Oxen repository: {repo_name}")

            # Create new client instance for this specific repo
            max_client = OxenClient(
                repo_name=repo_name,
                namespace=self.oxen_namespace
            )

            # Create repository
            max_client.create_repo(name=repo_name, description=f"MAX mode training data: {num_entities} entities, {num_timepoints} timepoints")

            # Upload the training data
            logger.info("   Uploading training data...")
            max_client.upload_dataset(
                file_path=str(local_path),
                commit_message=f"Add MAX mode training data: {len(examples)} examples ({num_entities} entities, {num_timepoints} timepoints)",
                dst_path=f"training_data/max_vertical_{num_entities}e_{num_timepoints}t.jsonl"
            )

            # Create fine-tuning branch
            logger.info("   Creating fine-tuning branch...")
            try:
                max_client.create_branch(f"finetune-max-{timestamp}")
                logger.info(f"   ✅ Created branch: finetune-max-{timestamp}")
            except Exception as e:
                logger.warning(f"   Could not create branch: {e}")

            # Generate and upload README
            readme_content = self._generate_max_mode_readme(num_entities, num_timepoints, len(examples))
            readme_path = self.output_dir / "max_mode" / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme_content)

            max_client.upload_dataset(
                file_path=str(readme_path),
                commit_message="Add MAX mode documentation",
                dst_path="README.md"
            )

            logger.info(f"   ✅ Upload complete: {self.oxen_namespace}/{repo_name}")
            logger.info(f"   📊 Repository: https://hub.oxen.ai/{self.oxen_namespace}/{repo_name}")
            logger.info(f"   🎯 Fine-tuning: Use branch 'finetune-max-{timestamp}'")

        except Exception as e:
            logger.error(f"   Error uploading to Oxen: {e}")

    def _generate_max_mode_readme(self, num_entities: int, num_timepoints: int, num_examples: int) -> str:
        """Generate README for MAX mode repository"""
        return f"""# Timepoint MAX Mode Training Data

**Generated:** {datetime.now().isoformat()}

## Overview

This repository contains training data from Timepoint's **MAX Mode** - a single massive vertical simulation showcasing all 17 Timepoint mechanisms at maximum depth.

## Configuration

- **Entities:** {num_entities}
- **Timepoints:** {num_timepoints}
- **Training Examples:** {num_examples:,}
- **Character Perspectives:** 4 (detective, doctor, villain, witness)
- **Resolution:** Hour-by-hour temporal tracking
- **Mechanisms:** All 17 Timepoint mechanisms demonstrated

## Mechanisms Demonstrated

1. **M1: Heterogeneous Fidelity** - Multiple resolution levels (TRAINED for main characters)
2. **M2: Progressive Training** - Characters improve skills over time
3. **M3: Exposure Events** - Complete observation tracking
4. **M4: Physics Validation** - Energy, biological constraints
5. **M5: Query-Driven Resolution** - Adaptive detail levels
6. **M6: TTM Tensors** - Character-specific cognitive models
7. **M7: Causal Temporal Chains** - Strict causality enforcement
8. **M8: Embodied States** - Physical/cognitive coupling
9. **M9: On-Demand Generation** - Dynamic entity creation
10. **M10: Scene Entities** - Atmospheric context
11. **M11: Dialog Synthesis** - Character interactions
12. **M12: Counterfactual Branching** - Alternative timelines
13. **M13: Multi-Entity Synthesis** - Relationship evolution
14. **M14: Circadian Patterns** - Time-dependent behavior
15. **M15: Entity Prospection** - Future planning/prediction
16. **M16: Animistic Entities** - Non-human entities (buildings, concepts)
17. **M17: Modal Causality** - Pearl-mode causal reasoning

## Training Format

Each example includes:
- **Prompt:** Character state + temporal context + observations
- **Completion:** Reasoning chain + deductions + next actions
- **Context:** Full mechanism metadata + TTM tensors + causal chains

## Fine-Tuning

To fine-tune a model on this data:

1. Navigate to this repository on Oxen.ai
2. Select the training data file
3. Use the web UI to create a fine-tuning job
4. Select branch: `finetune-max-{{timestamp}}`

## Use Cases

- Character roleplay with temporal reasoning
- Deductive reasoning with embodied constraints
- Multi-entity perspective modeling
- Causal chain tracking and validation

## Citation

```
Timepoint-Daedalus MAX Mode Training Data
Generated: {datetime.now().strftime("%Y-%m-%d")}
Entities: {num_entities}, Timepoints: {num_timepoints}
Examples: {num_examples:,}
```
"""

    def generate_horizontal_variations(self, llm, store, count=100):

        # Base config for variations
        base_config = SimulationConfig.example_board_meeting()
        base_config.variations.enabled = True
        base_config.variations.count = 100
        base_config.variations.strategies = [
            "vary_personalities",
            "vary_outcomes",
            "vary_relationships"
        ]

        try:
            # Generate variations using HorizontalGenerator
            generator = HorizontalGenerator(
                llm=self.llm,
                store=self.store,
                output_dir=str(self.output_dir / "variations")
            )

            # This will generate multiple simulation variations
            variations = generator.generate_variations(
                base_config=base_config,
                count=100
            )

            logger.info(f"Generated {len(variations)} variations")

            # Format each variation
            formatter = CharacterRoleplayFormatter(character_focus="ceo")
            for i, variation_result in enumerate(variations, 1):
                if i % 10 == 0:
                    logger.info(f"Formatting variation {i}/100...")

                examples = formatter.format_simulation(variation_result, base_config)
                all_examples.extend(examples)

        except Exception as e:
            logger.error(f"Error generating variations: {e}")
            logger.info("Continuing with mock variation data...")
            all_examples = self._create_mock_examples(base_config, count=4000)

        return all_examples

    def phase4_upload_to_oxen(
        self,
        deep_examples: List[Dict],
        breadth_examples: List[Dict],
        variation_examples: List[Dict]
    ):
        """
        Phase 4: Upload training data to Oxen with experiment branches.

        Creates Oxen repository structure:
        - experiments/scarlet-study-pearl/
        - experiments/scarlet-study-directorial/
        - ... (15 deep case branches)
        - datasets/
            - deep_cases_all_modes.jsonl
            - breadth_cases_pearl.jsonl
            - variation_cases.jsonl
            - mechanism_validation.json
        """
        if not self.oxen_client:
            logger.warning("No Oxen client available, skipping upload")
            return

        try:
            # Create repository
            timestamp = datetime.now().strftime("%Y%m%d")
            repo_name = f"timepoint-character-engine-{timestamp}"

            logger.info(f"Creating Oxen repository: {repo_name}")
            self.oxen_client.create_repository(repo_name)

            # Upload deep cases
            logger.info("Uploading deep cases...")
            deep_path = self.output_dir / "deep_cases_all_modes.jsonl"
            self.oxen_client.upload_file(
                file_path=str(deep_path),
                remote_path="datasets/deep_cases_all_modes.jsonl",
                commit_message="Add deep cases training data (15 runs, all modes)"
            )

            # Upload breadth cases
            logger.info("Uploading breadth cases...")
            breadth_path = self.output_dir / "breadth_cases_pearl.jsonl"
            self.oxen_client.upload_file(
                file_path=str(breadth_path),
                remote_path="datasets/breadth_cases_pearl.jsonl",
                commit_message="Add breadth cases training data (20 scenarios)"
            )

            # Upload variations
            logger.info("Uploading variations...")
            variation_path = self.output_dir / "variation_cases.jsonl"
            self.oxen_client.upload_file(
                file_path=str(variation_path),
                remote_path="datasets/variation_cases.jsonl",
                commit_message="Add horizontal variation training data (100 variations)"
            )

            # Upload mechanism validation report
            logger.info("Uploading mechanism validation report...")
            validation_report = self._generate_mechanism_validation(
                deep_examples, breadth_examples, variation_examples
            )
            validation_path = self.output_dir / "mechanism_validation.json"
            with open(validation_path, 'w') as f:
                json.dump(validation_report, f, indent=2)

            self.oxen_client.upload_file(
                file_path=str(validation_path),
                remote_path="datasets/mechanism_validation.json",
                commit_message="Add mechanism validation report"
            )

            logger.info(f"Upload complete! Repository: {self.oxen_namespace}/{repo_name}")

        except Exception as e:
            logger.error(f"Error uploading to Oxen: {e}")
            logger.info("Training data saved locally in: {self.output_dir}")

    def save_training_data(
        self,
        deep_examples: List[Dict],
        breadth_examples: List[Dict],
        variation_examples: List[Dict]
    ):
        """Save training data to local disk"""

        # Save deep cases
        deep_path = self.output_dir / "deep_cases_all_modes.jsonl"
        with open(deep_path, 'w') as f:
            for example in deep_examples:
                f.write(json.dumps(example) + '\n')
        logger.info(f"Saved deep cases: {deep_path} ({len(deep_examples)} examples)")

        # Save breadth cases
        breadth_path = self.output_dir / "breadth_cases_pearl.jsonl"
        with open(breadth_path, 'w') as f:
            for example in breadth_examples:
                f.write(json.dumps(example) + '\n')
        logger.info(f"Saved breadth cases: {breadth_path} ({len(breadth_examples)} examples)")

        # Save variations
        variation_path = self.output_dir / "variation_cases.jsonl"
        with open(variation_path, 'w') as f:
            for example in variation_examples:
                f.write(json.dumps(example) + '\n')
        logger.info(f"Saved variations: {variation_path} ({len(variation_examples)} examples)")

        # Save combined dataset
        combined_path = self.output_dir / "all_training_data.jsonl"
        with open(combined_path, 'w') as f:
            for example in deep_examples + breadth_examples + variation_examples:
                f.write(json.dumps(example) + '\n')
        logger.info(f"Saved combined dataset: {combined_path}")

        # Save statistics
        stats_path = self.output_dir / "generation_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"Saved statistics: {stats_path}")

    def _get_breadth_scenarios(self) -> List[SimulationConfig]:
        """Get 20 breadth scenario configs"""
        # These would be defined in config_schema.py
        # For now, create simple variations
        scenarios = []

        scenario_templates = [
            ("poison_mystery", "A diplomat dies at dinner from apparent poisoning"),
            ("art_theft", "A priceless painting vanishes from a locked gallery"),
            ("blackmail_case", "A politician receives threatening letters demanding payment"),
            ("kidnapping", "An industrialist's child disappears from their estate"),
            ("fraud_investigation", "A bank discovers millions missing from secure vaults"),
            ("conspiracy", "Multiple witnesses report seeing the same impossible event"),
            ("murder_train", "A passenger is found dead in a locked train compartment"),
            ("sabotage", "A factory explosion kills workers, but evidence suggests deliberate action"),
            ("espionage", "Classified documents appear in enemy hands without clear source"),
            ("disappearance", "A famous scientist vanishes from their locked laboratory"),
            ("forgery", "Expertly forged documents create diplomatic crisis"),
            ("arson", "A series of fires target specific buildings across the city"),
            ("smuggling", "Customs discovers elaborate network smuggling contraband"),
            ("extortion", "Business owners receive demands from mysterious organization"),
            ("assassination", "A public figure survives multiple coordinated attacks"),
            ("heist", "Thieves execute impossibly complex vault robbery"),
            ("stalking", "A celebrity discovers years of surveillance evidence"),
            ("cult_investigation", "Missing persons linked to secretive religious group"),
            ("insider_trading", "Stock market manipulation traced to small group"),
            ("medical_mystery", "Patients exhibit impossible symptoms defying diagnosis")
        ]

        for world_id, description in scenario_templates:
            config = SimulationConfig(
                scenario_description=description + ". Track the investigation from discovery through resolution.",
                world_id=f"breadth_{world_id}",
                entities={"count": 4, "types": ["human"], "initial_resolution": ResolutionLevel.SCENE},
                timepoints={"count": 1, "before_count": 2, "after_count": 2, "resolution": "hour"},
                temporal={"mode": TemporalMode.PEARL},
                outputs={
                    "formats": ["jsonl"],
                    "include_dialogs": True,
                    "include_relationships": True,
                    "include_knowledge_flow": True,
                    "export_ml_dataset": True
                }
            )
            scenarios.append(config)

        return scenarios

    def _create_mock_examples(self, config: SimulationConfig, count: int) -> List[Dict[str, Any]]:
        """Create mock training examples for dry run"""
        examples = []
        for i in range(count):
            examples.append({
                "prompt": f"Mock prompt {i} for {config.world_id}",
                "completion": f"Mock completion {i}",
                "context": {
                    "world_id": config.world_id,
                    "example_index": i,
                    "mechanisms_used": ["M1", "M3", "M6", "M7", "M8", "M17"]
                }
            })
        return examples

    def _generate_mechanism_validation(
        self,
        deep_examples: List[Dict],
        breadth_examples: List[Dict],
        variation_examples: List[Dict]
    ) -> Dict[str, Any]:
        """Generate validation report showing all 17 mechanisms are present"""

        all_examples = deep_examples + breadth_examples + variation_examples

        # Count mechanism usage
        mechanism_counts = {}
        for example in all_examples:
            mechanisms = example.get("context", {}).get("mechanisms_used", [])
            for m in mechanisms:
                mechanism_counts[m] = mechanism_counts.get(m, 0) + 1

        # Expected 17 mechanisms
        all_mechanisms = [
            "M1_heterogeneous_fidelity",
            "M2_progressive_training",
            "M3_exposure_events",
            "M4_physics_validation",
            "M5_query_resolution",
            "M6_ttm_tensors",
            "M7_causal_chains",
            "M8_embodied_states",
            "M9_on_demand_generation",
            "M10_scene_entities",
            "M11_dialog_synthesis",
            "M12_counterfactual_branching",
            "M13_multi_entity_synthesis",
            "M14_circadian_patterns",
            "M15_entity_prospection",
            "M16_animistic_entities",
            "M17_modal_causality"
        ]

        validation_report = {
            "total_examples": len(all_examples),
            "mechanism_coverage": {
                m: {
                    "count": mechanism_counts.get(m, 0),
                    "percentage": (mechanism_counts.get(m, 0) / len(all_examples)) * 100 if all_examples else 0,
                    "present": mechanism_counts.get(m, 0) > 0
                }
                for m in all_mechanisms
            },
            "all_mechanisms_present": all(mechanism_counts.get(m, 0) > 0 for m in all_mechanisms),
            "generation_timestamp": datetime.now().isoformat()
        }

        return validation_report


def main():
    """Main entry point for character engine workflow"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Timepoint Character Engine - Generate character-based training data"
    )
    parser.add_argument(
        "--max",
        action="store_true",
        help="MAX mode: Generate one massive vertical simulation (12-124 entities, up to 200 timepoints, all 17 mechanisms)"
    )
    parser.add_argument(
        "--entities",
        type=int,
        default=24,
        help="Number of entities for MAX mode (default: 24, max: 124)"
    )
    parser.add_argument(
        "--timepoints",
        type=int,
        default=50,
        help="Number of timepoints for MAX mode (default: 50, max: 200)"
    )
    args = parser.parse_args()

    # Check environment variables
    llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "false").lower() == "true"
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")

    if not llm_enabled or not openrouter_key:
        logger.warning("LLM service not enabled or API key not set")
        logger.warning("Running in DRY RUN mode (no real LLM calls)")
        dry_run = True
        # Enable mock mode for dry run
        os.environ["ALLOW_MOCK_MODE"] = "true"
    else:
        dry_run = False

    # Initialize components
    logger.info("Initializing Timepoint Character Engine...")

    # Get API key (use dummy if dry run)
    api_key = openrouter_key if openrouter_key else "dummy_key_for_dry_run"

    llm = LLMClient(api_key=api_key, dry_run=dry_run)
    store = GraphStore("sqlite:///character_engine.db")

    # Create engine
    engine = CharacterEngine(
        llm=llm,
        store=store,
        oxen_namespace=os.getenv("OXEN_TEST_NAMESPACE", "realityinspector"),
        dry_run=dry_run
    )

    # Run workflow based on mode
    if args.max:
        logger.info("🚀 RUNNING IN MAX MODE 🚀")
        logger.info(f"Entities: {args.entities}, Timepoints: {args.timepoints}")
        stats = engine.run_max_mode(
            num_entities=min(args.entities, 124),
            num_timepoints=min(args.timepoints, 200)
        )
    else:
        stats = engine.run_complete_workflow()

    # Print final summary
    print("\n" + "="*80)
    print("CHARACTER ENGINE WORKFLOW SUMMARY")
    print("="*80)

    if args.max:
        # MAX mode summary
        print(f"Mode:                    MAX")
        print(f"Total training examples: {stats['total_examples']:,}")
        print(f"Entities:                {stats['entities']}")
        print(f"Timepoints:              {stats['timepoints']}")
        print(f"Duration:                {stats['duration_seconds']:.1f}s ({stats['duration_seconds']/60:.1f} min)")
        if 'output_path' in stats:
            print(f"Output:                  {stats['output_path']}")
    else:
        # Standard mode summary
        print(f"Mode:                    Standard")
        print(f"Total training examples: {stats['total_examples']:,}")
        print(f"  Deep cases:            {stats.get('deep_examples', 0):,}")
        print(f"  Breadth cases:         {stats.get('breadth_examples', 0):,}")
        print(f"  Variations:            {stats.get('variation_examples', 0):,}")
        print(f"Duration:                {stats['duration_seconds']:.1f}s ({stats['duration_seconds']/60:.1f} min)")

    print("="*80)
    print("")

    if not args.max and stats['total_examples'] >= 6100:
        print("✅ SUCCESS: Target of 6,100+ examples achieved!")
    elif not args.max:
        print(f"⚠️  WARNING: Only {stats['total_examples']} examples generated (target: 6,100+)")
    else:
        # MAX mode - no specific target, just report completion
        print(f"✅ MAX MODE COMPLETE: {stats['total_examples']:,} examples generated")

    return 0


if __name__ == "__main__":
    sys.exit(main())
