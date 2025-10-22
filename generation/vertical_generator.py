"""
Vertical Data Generation - Temporal Depth

Generate deep temporal context around critical moments:
- Progressive resolution training (start low-res, peak at critical moment)
- Causal chain enforcement
- Exposure event propagation
- Narrative arc shaping
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from copy import deepcopy

from .config_schema import SimulationConfig
from .temporal_expansion import TemporalExpander


class VerticalGenerator:
    """
    Generate temporal depth (vertical expansion) for simulations.

    Adds timepoints before and/or after a critical moment with:
    - Progressive resolution training
    - Causal chain validation
    - Narrative arc structure

    Example:
        generator = VerticalGenerator()

        # Expand around "Jefferson Dinner" critical moment
        config = generator.generate_temporal_depth(
            base_config=SimulationConfig.example_jefferson_dinner(),
            before_count=5,
            after_count=5,
            strategy="progressive_training"
        )

        # Results in: 5 lead-up + 1 critical + 5 consequence = 11 total timepoints
    """

    def __init__(self):
        self.expander = TemporalExpander()
        self.generation_stats = {
            "timepoints_added_before": 0,
            "timepoints_added_after": 0,
            "total_timepoints": 0,
            "strategy_used": None,
            "cost_savings_estimated": 0.0
        }

    def generate_temporal_depth(
        self,
        base_config: SimulationConfig,
        before_count: int = 0,
        after_count: int = 0,
        strategy: str = "progressive_training"
    ) -> SimulationConfig:
        """
        Generate temporal depth around base configuration.

        Args:
            base_config: Base simulation configuration
            before_count: Number of timepoints to add before critical moment
            after_count: Number of timepoints to add after critical moment
            strategy: Expansion strategy ("progressive_training", "narrative_arc", "causal_chain")

        Returns:
            SimulationConfig with expanded temporal structure

        Raises:
            ValueError: If counts are negative or strategy invalid
        """
        if before_count < 0 or after_count < 0:
            raise ValueError("Timepoint counts must be non-negative")

        # Reset stats
        self.generation_stats = {
            "timepoints_added_before": before_count,
            "timepoints_added_after": after_count,
            "total_timepoints": base_config.timepoints.count + before_count + after_count,
            "strategy_used": strategy,
            "cost_savings_estimated": 0.0
        }

        # Use temporal expander
        expanded_config = self.expander.expand_temporal_depth(
            base_config,
            strategy=strategy,
            before_count=before_count,
            after_count=after_count
        )

        # Estimate cost savings from progressive training
        if strategy == "progressive_training":
            self.generation_stats["cost_savings_estimated"] = self._estimate_cost_savings(
                expanded_config, before_count, after_count
            )

        return expanded_config

    def _estimate_cost_savings(
        self,
        config: SimulationConfig,
        before_count: int,
        after_count: int
    ) -> float:
        """
        Estimate cost savings from progressive training vs uniform high-res.

        Returns:
            Estimated savings as percentage (0.0-1.0)
        """
        # Naive approach: all timepoints at full resolution
        entity_count = config.entities.count
        total_timepoints = config.timepoints.count + before_count + after_count

        naive_tokens = entity_count * total_timepoints * 50000  # Full detail

        # Progressive approach: resolution varies
        resolution_tokens = {
            "tensor_only": 200,
            "scene": 2000,
            "graph": 5000,
            "dialog": 10000,
            "full_detail": 50000
        }

        # Estimate average token usage with progressive training
        # Assume: 40% tensor_only, 20% scene, 20% graph, 10% dialog, 10% full_detail
        avg_tokens = (
            0.4 * resolution_tokens["tensor_only"] +
            0.2 * resolution_tokens["scene"] +
            0.2 * resolution_tokens["graph"] +
            0.1 * resolution_tokens["dialog"] +
            0.1 * resolution_tokens["full_detail"]
        )

        progressive_tokens = entity_count * total_timepoints * avg_tokens

        # Calculate savings
        if naive_tokens > 0:
            savings = 1.0 - (progressive_tokens / naive_tokens)
            return max(0.0, min(1.0, savings))
        return 0.0

    def generate_before(
        self,
        base_config: SimulationConfig,
        count: int,
        strategy: str = "progressive_training"
    ) -> SimulationConfig:
        """Generate timepoints before critical moment"""
        return self.generate_temporal_depth(
            base_config,
            before_count=count,
            after_count=0,
            strategy=strategy
        )

    def generate_after(
        self,
        base_config: SimulationConfig,
        count: int,
        strategy: str = "progressive_training"
    ) -> SimulationConfig:
        """Generate timepoints after critical moment"""
        return self.generate_temporal_depth(
            base_config,
            before_count=0,
            after_count=count,
            strategy=strategy
        )

    def generate_around(
        self,
        base_config: SimulationConfig,
        before_count: int,
        after_count: int,
        strategy: str = "progressive_training"
    ) -> SimulationConfig:
        """Generate timepoints in both directions"""
        return self.generate_temporal_depth(
            base_config,
            before_count=before_count,
            after_count=after_count,
            strategy=strategy
        )

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics from last generation"""
        return dict(self.generation_stats)

    def validate_causal_chain(
        self,
        config: SimulationConfig
    ) -> Dict[str, Any]:
        """
        Validate that temporal expansion maintains causal integrity.

        Args:
            config: Configuration to validate

        Returns:
            Dictionary with validation results:
                - is_valid: bool
                - violations: List[str]
                - timepoint_count: int
        """
        violations = []

        # Check that we have timepoint configuration
        if not hasattr(config.timepoints, 'count'):
            violations.append("No timepoint configuration found")

        # Check that temporal expansion metadata exists if expansion was done
        if config.timepoints.before_count > 0 or config.timepoints.after_count > 0:
            if "temporal_expansion" not in config.metadata:
                violations.append("Temporal expansion metadata missing")

        # Check for causal chain metadata if required
        if config.metadata.get("require_causal_validation", False):
            if "causal_chain_before" not in config.metadata and config.timepoints.before_count > 0:
                violations.append("Causal chain metadata missing for 'before' timepoints")
            if "causal_chain_after" not in config.metadata and config.timepoints.after_count > 0:
                violations.append("Causal chain metadata missing for 'after' timepoints")

        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "timepoint_count": (
                config.timepoints.count +
                config.timepoints.before_count +
                config.timepoints.after_count
            )
        }

    def analyze_resolution_schedule(
        self,
        config: SimulationConfig
    ) -> Dict[str, Any]:
        """
        Analyze the resolution schedule from progressive training.

        Args:
            config: Configuration with resolution schedule

        Returns:
            Dictionary with analysis:
                - has_schedule: bool
                - schedule_before: List[str]
                - schedule_after: List[str]
                - peak_resolution: str
                - avg_resolution_cost: float
        """
        analysis = {
            "has_schedule": False,
            "schedule_before": [],
            "schedule_after": [],
            "peak_resolution": None,
            "avg_resolution_cost": 0.0
        }

        # Check for resolution schedules in metadata
        if "resolution_schedule_before" in config.metadata:
            analysis["has_schedule"] = True
            analysis["schedule_before"] = config.metadata["resolution_schedule_before"]

        if "resolution_schedule_after" in config.metadata:
            analysis["has_schedule"] = True
            analysis["schedule_after"] = config.metadata["resolution_schedule_after"]

        # Determine peak resolution
        all_resolutions = analysis["schedule_before"] + analysis["schedule_after"]
        if all_resolutions:
            resolution_ranks = {
                "tensor_only": 1,
                "scene": 2,
                "graph": 3,
                "dialog": 4,
                "full_detail": 5
            }
            peak = max(all_resolutions, key=lambda r: resolution_ranks.get(r, 0))
            analysis["peak_resolution"] = peak

            # Calculate average cost
            resolution_costs = {
                "tensor_only": 0.2,
                "scene": 2.0,
                "graph": 5.0,
                "dialog": 10.0,
                "full_detail": 50.0
            }
            total_cost = sum(resolution_costs.get(r, 0) for r in all_resolutions)
            analysis["avg_resolution_cost"] = total_cost / len(all_resolutions) if all_resolutions else 0.0

        return analysis

    def compare_strategies(
        self,
        base_config: SimulationConfig,
        before_count: int,
        after_count: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare different expansion strategies for same config.

        Args:
            base_config: Base configuration
            before_count: Timepoints before
            after_count: Timepoints after

        Returns:
            Dictionary mapping strategy name to comparison metrics
        """
        strategies = self.expander.get_available_strategies()
        comparison = {}

        for strategy in strategies:
            expanded = self.generate_temporal_depth(
                base_config, before_count, after_count, strategy
            )

            stats = self.get_generation_stats()

            comparison[strategy] = {
                "total_timepoints": stats["total_timepoints"],
                "cost_savings_estimated": stats.get("cost_savings_estimated", 0.0),
                "metadata_keys": list(expanded.metadata.keys())
            }

        return comparison

    def export_temporal_structure(
        self,
        config: SimulationConfig,
        output_path: str,
        format: str = "json"
    ):
        """
        Export temporal structure to file.

        Args:
            config: Configuration with temporal expansion
            output_path: Output file path
            format: Export format ("json", "yaml")
        """
        import json

        structure = {
            "base_timepoints": config.timepoints.count,
            "before_timepoints": config.timepoints.before_count,
            "after_timepoints": config.timepoints.after_count,
            "total_timepoints": (
                config.timepoints.count +
                config.timepoints.before_count +
                config.timepoints.after_count
            ),
            "temporal_expansion": config.metadata.get("temporal_expansion", {}),
            "resolution_schedule_before": config.metadata.get("resolution_schedule_before", []),
            "resolution_schedule_after": config.metadata.get("resolution_schedule_after", []),
            "narrative_structure": config.metadata.get("narrative_structure", None)
        }

        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(structure, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_to_oxen(
        self,
        config: SimulationConfig,
        oxen_client: "OxenClient",
        commit_message: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> "UploadResult":
        """
        Export temporally-expanded configuration to Oxen.ai.

        Args:
            config: Configuration with temporal expansion
            oxen_client: OxenClient instance
            commit_message: Optional commit message. Auto-generated if None.
            dataset_name: Optional dataset filename. Auto-generated if None.

        Returns:
            UploadResult with URLs for viewing and fine-tuning

        Example:
            >>> from oxen_integration import OxenClient
            >>> client = OxenClient(namespace="user", repo_name="temporal")
            >>> expanded = generator.generate_temporal_depth(base, 5, 5)
            >>> result = generator.export_to_oxen(expanded, client)
            >>> print(f"Fine-tune at: {result.finetune_url}")
        """
        import tempfile
        import os
        import json
        from datetime import datetime

        # Import here to avoid circular dependency
        try:
            from oxen_integration import UploadResult
        except ImportError:
            raise ImportError(
                "oxen_integration module required. Ensure it's installed."
            )

        # Generate filename if not provided
        if dataset_name is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"temporal_expansion_{timestamp}.json"

        # Generate commit message if not provided
        if commit_message is None:
            stats = self.get_generation_stats()
            total_tp = stats["total_timepoints"]
            savings = stats.get("cost_savings_estimated", 0.0)
            commit_message = (
                f"Add temporal expansion ({total_tp} timepoints, "
                f"{savings:.1%} cost savings)"
            )

        # Export configuration to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            json.dump(config.to_dict(), tmp_file, indent=2)

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
