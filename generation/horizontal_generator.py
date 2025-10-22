"""
Horizontal Data Generation - Scenario Variations

Generate N variations of the same base scenario with meaningful differences:
- Apply variation strategies to create diverse configurations
- Ensure variations are meaningfully different (deduplication)
- Support parallel generation for efficiency
- Track variation metadata for analysis
"""

from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from datetime import datetime
from copy import deepcopy

from .variation_strategies import VariationStrategyFactory, VariationStrategy
from .config_schema import SimulationConfig


class VariationDeduplicator:
    """Detect and remove near-identical variations"""

    def __init__(self, similarity_threshold: float = 0.9):
        """
        Args:
            similarity_threshold: Threshold for considering variations identical (0.0-1.0)
                1.0 = exact match, 0.9 = very similar, 0.5 = somewhat similar
        """
        self.similarity_threshold = similarity_threshold
        self.variation_hashes: Dict[str, Dict[str, Any]] = {}

    def compute_hash(self, config: Dict[str, Any]) -> str:
        """
        Compute hash of variation's key distinguishing features.

        Args:
            config: Configuration dict

        Returns:
            Hash string
        """
        # Extract metadata that defines the variation
        metadata = config.get("metadata", {})

        # Create canonical representation
        canonical = {
            "variation_strategy": metadata.get("variation_strategy"),
            "variation_index": metadata.get("variation_index"),
            # Include key variation parameters
            "personality_variations": metadata.get("personality_variations", []),
            "knowledge_distributions": metadata.get("knowledge_distributions", []),
            "initial_relationships": metadata.get("initial_relationships", []),
            "decision_parameters": metadata.get("decision_parameters", []),
            "starting_states": metadata.get("starting_states", [])
        }

        # Hash the canonical representation
        canonical_str = json.dumps(canonical, sort_keys=True)
        return hashlib.sha256(canonical_str.encode()).hexdigest()

    def is_duplicate(self, config: Dict[str, Any]) -> bool:
        """
        Check if configuration is too similar to existing variations.

        Args:
            config: Configuration to check

        Returns:
            True if duplicate, False otherwise
        """
        config_hash = self.compute_hash(config)

        # Exact match check
        if config_hash in self.variation_hashes:
            return True

        # For now, use hash-based exact matching
        # Future: implement fuzzy similarity comparison
        return False

    def register_variation(self, config: Dict[str, Any]):
        """Register a variation as seen"""
        config_hash = self.compute_hash(config)
        self.variation_hashes[config_hash] = {
            "timestamp": datetime.utcnow().isoformat(),
            "variation_index": config.get("metadata", {}).get("variation_index")
        }

    def get_duplicate_count(self) -> int:
        """Get count of registered variations"""
        return len(self.variation_hashes)

    def reset(self):
        """Clear all registered variations"""
        self.variation_hashes.clear()


class HorizontalGenerator:
    """
    Generate variations of a base scenario configuration.

    Example:
        generator = HorizontalGenerator()

        # Generate 100 variations
        variations = generator.generate_variations(
            base_config=SimulationConfig.example_board_meeting(),
            count=100,
            strategies=["vary_personalities", "vary_outcomes"],
            parallel=True
        )

        # Check quality
        stats = generator.get_generation_stats()
        print(f"Generated {stats['variations_created']} unique variations")
    """

    def __init__(self, deduplication_threshold: float = 0.9):
        """
        Args:
            deduplication_threshold: Similarity threshold for deduplication
        """
        self.deduplicator = VariationDeduplicator(deduplication_threshold)
        self.generation_stats = {
            "variations_requested": 0,
            "variations_created": 0,
            "duplicates_rejected": 0,
            "strategies_used": [],
            "generation_time_seconds": 0.0
        }

    def generate_variations(
        self,
        base_config: SimulationConfig,
        count: int,
        strategies: List[str],
        parallel: bool = False,
        max_workers: Optional[int] = None,
        random_seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[SimulationConfig]:
        """
        Generate variations of base configuration.

        Args:
            base_config: Base simulation configuration
            count: Number of variations to generate
            strategies: List of variation strategy names to apply
            parallel: Whether to generate in parallel
            max_workers: Max threads for parallel generation
            random_seed: Random seed for reproducibility
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of SimulationConfig variations

        Raises:
            ValueError: If no strategies provided or count < 1
        """
        if not strategies:
            raise ValueError("Must provide at least one variation strategy")
        if count < 1:
            raise ValueError("Count must be at least 1")

        start_time = datetime.utcnow()

        # Reset stats
        self.generation_stats = {
            "variations_requested": count,
            "variations_created": 0,
            "duplicates_rejected": 0,
            "strategies_used": strategies,
            "generation_time_seconds": 0.0
        }

        # Create strategy instances
        strategy_instances = [
            VariationStrategyFactory.create(strategy_name)
            for strategy_name in strategies
        ]

        variations = []

        if parallel:
            variations = self._generate_parallel(
                base_config, count, strategy_instances, max_workers, random_seed, progress_callback
            )
        else:
            variations = self._generate_sequential(
                base_config, count, strategy_instances, random_seed, progress_callback
            )

        # Update stats
        end_time = datetime.utcnow()
        self.generation_stats["generation_time_seconds"] = (end_time - start_time).total_seconds()
        self.generation_stats["variations_created"] = len(variations)

        return variations

    def _generate_sequential(
        self,
        base_config: SimulationConfig,
        count: int,
        strategies: List[VariationStrategy],
        random_seed: Optional[int],
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> List[SimulationConfig]:
        """Generate variations sequentially"""
        variations = []

        for i in range(count):
            # Apply strategies in sequence to create variation
            config_dict = base_config.to_dict()

            for strategy in strategies:
                config_dict = strategy.apply(config_dict, i, random_seed)

            # Check for duplicates
            if self.deduplicator.is_duplicate(config_dict):
                self.generation_stats["duplicates_rejected"] += 1
                continue

            # Register and add variation
            self.deduplicator.register_variation(config_dict)

            # Update world_id to be unique
            config_dict["world_id"] = f"{base_config.world_id}_var_{i}"

            # Create SimulationConfig from dict
            variation = SimulationConfig.from_dict(config_dict)
            variations.append(variation)

            # Progress callback
            if progress_callback:
                progress_callback(len(variations), count)

        return variations

    def _generate_parallel(
        self,
        base_config: SimulationConfig,
        count: int,
        strategies: List[VariationStrategy],
        max_workers: Optional[int],
        random_seed: Optional[int],
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> List[SimulationConfig]:
        """Generate variations in parallel"""
        variations = []

        def generate_single(index: int) -> Optional[SimulationConfig]:
            """Generate a single variation"""
            config_dict = base_config.to_dict()

            for strategy in strategies:
                config_dict = strategy.apply(config_dict, index, random_seed)

            # Check for duplicates
            if self.deduplicator.is_duplicate(config_dict):
                return None

            # Register variation
            self.deduplicator.register_variation(config_dict)

            # Update world_id
            config_dict["world_id"] = f"{base_config.world_id}_var_{index}"

            return SimulationConfig.from_dict(config_dict)

        # Use ThreadPoolExecutor for parallel generation
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(generate_single, i): i
                for i in range(count)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    variations.append(result)
                else:
                    self.generation_stats["duplicates_rejected"] += 1

                # Progress callback
                if progress_callback:
                    progress_callback(len(variations), count)

        return variations

    def generate_with_retry(
        self,
        base_config: SimulationConfig,
        count: int,
        strategies: List[str],
        max_retries: int = 3,
        **kwargs
    ) -> List[SimulationConfig]:
        """
        Generate variations with retry on insufficient unique variations.

        Args:
            base_config: Base configuration
            count: Desired number of variations
            strategies: Variation strategies
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for generate_variations

        Returns:
            List of unique variations (may be < count if unable to generate enough)
        """
        variations = []
        attempts = 0

        while len(variations) < count and attempts < max_retries:
            # Generate additional variations
            remaining = count - len(variations)
            new_variations = self.generate_variations(
                base_config, remaining, strategies, **kwargs
            )

            variations.extend(new_variations)
            attempts += 1

        return variations[:count]  # Return exactly count variations

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics from last generation run"""
        return dict(self.generation_stats)

    def estimate_variation_quality(
        self,
        variations: List[SimulationConfig]
    ) -> Dict[str, Any]:
        """
        Estimate quality metrics for generated variations.

        Args:
            variations: List of generated variations

        Returns:
            Dictionary with quality metrics:
                - unique_count: Number of unique variations
                - diversity_score: Estimated diversity (0.0-1.0)
                - strategy_distribution: Distribution of strategies used
        """
        if not variations:
            return {
                "unique_count": 0,
                "diversity_score": 0.0,
                "strategy_distribution": {}
            }

        # Count unique variations
        unique_count = len(variations)

        # Estimate diversity based on metadata variance
        strategy_counts = {}
        for var in variations:
            strategy = var.metadata.get("variation_strategy", "unknown")
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        # Simple diversity score: entropy of strategy distribution
        total = len(variations)
        diversity_score = 0.0
        if total > 0:
            for count in strategy_counts.values():
                p = count / total
                if p > 0:
                    # Shannon entropy normalized to 0-1 range
                    import math
                    diversity_score -= p * math.log2(p)

            # Normalize by max possible entropy (log2 of number of strategies)
            max_entropy = math.log2(len(strategy_counts)) if len(strategy_counts) > 1 else 1.0
            diversity_score = diversity_score / max_entropy if max_entropy > 0 else 0.0

        return {
            "unique_count": unique_count,
            "diversity_score": max(0.0, min(1.0, diversity_score)),
            "strategy_distribution": strategy_counts
        }

    def batch_generate(
        self,
        base_configs: List[SimulationConfig],
        count_per_config: int,
        strategies: List[str],
        **kwargs
    ) -> Dict[str, List[SimulationConfig]]:
        """
        Generate variations for multiple base configurations.

        Args:
            base_configs: List of base configurations
            count_per_config: Variations to generate per config
            strategies: Variation strategies to use
            **kwargs: Additional arguments for generate_variations

        Returns:
            Dictionary mapping world_id to list of variations
        """
        results = {}

        for base_config in base_configs:
            variations = self.generate_variations(
                base_config, count_per_config, strategies, **kwargs
            )
            results[base_config.world_id] = variations

        return results

    def export_variations(
        self,
        variations: List[SimulationConfig],
        output_path: str,
        format: str = "json"
    ):
        """
        Export variations to file.

        Args:
            variations: List of variations to export
            output_path: Output file path
            format: Export format (json, jsonl)

        Raises:
            ValueError: If format not supported
        """
        import json

        if format == "json":
            # Export as JSON array
            with open(output_path, 'w') as f:
                json.dump(
                    [v.to_dict() for v in variations],
                    f,
                    indent=2
                )
        elif format == "jsonl":
            # Export as JSON lines (one per line)
            with open(output_path, 'w') as f:
                for variation in variations:
                    f.write(json.dumps(variation.to_dict()) + '\n')
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_to_oxen(
        self,
        variations: List[SimulationConfig],
        oxen_client: "OxenClient",
        commit_message: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> "UploadResult":
        """
        Export variations to Oxen.ai for storage and fine-tuning.

        Args:
            variations: List of variations to export
            oxen_client: OxenClient instance
            commit_message: Optional commit message. Auto-generated if None.
            dataset_name: Optional dataset filename. Auto-generated if None.

        Returns:
            UploadResult with URLs for viewing and fine-tuning

        Example:
            >>> from oxen_integration import OxenClient
            >>> client = OxenClient(namespace="user", repo_name="variations")
            >>> result = generator.export_to_oxen(variations, client)
            >>> print(f"Fine-tune at: {result.finetune_url}")
        """
        import tempfile
        import os

        # Import here to avoid circular dependency
        try:
            from oxen_integration import UploadResult
        except ImportError:
            raise ImportError(
                "oxen_integration module required. Ensure it's installed."
            )

        if not variations:
            raise ValueError("No variations to export")

        # Generate filename if not provided
        if dataset_name is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"variations_{timestamp}.jsonl"

        # Generate commit message if not provided
        if commit_message is None:
            stats = self.get_generation_stats()
            commit_message = (
                f"Add {len(variations)} variations "
                f"(strategies: {', '.join(stats['strategies_used'])})"
            )

        # Export to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jsonl', delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            for variation in variations:
                tmp_file.write(json.dumps(variation.to_dict()) + '\n')

        try:
            # Upload to Oxen
            result = oxen_client.upload_dataset(
                file_path=tmp_path,
                commit_message=commit_message,
                dst_path=f"datasets/{dataset_name}"
            )
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
