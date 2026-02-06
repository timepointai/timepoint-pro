"""
E2E test for Oxen.ai upload integration.

This test requires:
1. OXEN_INTEGRATION_TEST=true environment variable
2. Valid OXEN_API_TOKEN or ~/.oxen/config.json with credentials
3. OXEN_TEST_NAMESPACE set to your Oxen username

To run:
    export OXEN_INTEGRATION_TEST=true
    export OXEN_API_TOKEN=your_token
    export OXEN_TEST_NAMESPACE=your_username
    pytest tests/test_e2e_oxen_upload.py -v -s
"""
import pytest
import os
import sys
from datetime import datetime

# Skip all tests if integration testing not enabled
pytestmark = pytest.mark.skipif(
    os.getenv("OXEN_INTEGRATION_TEST") != "true",
    reason="Oxen integration test requires OXEN_INTEGRATION_TEST=true"
)


class TestOxenUploadE2E:
    """End-to-end tests for Oxen.ai upload workflow."""

    @pytest.fixture
    def test_namespace(self):
        """Get test namespace from environment."""
        namespace = os.getenv("OXEN_TEST_NAMESPACE")
        if not namespace:
            pytest.skip("OXEN_TEST_NAMESPACE environment variable not set")
        return namespace

    @pytest.fixture
    def test_repo_name(self):
        """Generate unique test repository name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"timepoint_test_{timestamp}"

    def test_horizontal_generator_export_to_oxen(self, test_namespace, test_repo_name):
        """Test exporting horizontal variations to Oxen.ai."""
        print("\n" + "=" * 70)
        print("TEST: Horizontal Generator → Oxen.ai Upload")
        print("=" * 70)

        # Import dependencies
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from generation.config_schema import (
            SimulationConfig, EntityConfig, CompanyConfig,
            TemporalConfig, TemporalMode, OutputConfig, VariationConfig,
        )
        from generation.horizontal_generator import HorizontalGenerator
        from oxen_integration import OxenClient

        # Step 1: Generate variations
        print("\n📊 Step 1: Generating variations...")
        generator = HorizontalGenerator()
        base_config = SimulationConfig(
            scenario_description="Generate variations of a negotiation scenario",
            world_id="negotiation_variations",
            entities=EntityConfig(count=4, types=["human"]),
            timepoints=CompanyConfig(count=2, resolution="hour"),
            temporal=TemporalConfig(mode=TemporalMode.PEARL),
            outputs=OutputConfig(
                formats=["jsonl"],
                export_ml_dataset=True
            ),
            variations=VariationConfig(
                enabled=True,
                count=100,
                strategies=["vary_personalities", "vary_outcomes"]
            )
        )

        variations = generator.generate_variations(
            base_config=base_config,
            count=10,  # Small test dataset
            strategies=["vary_personalities"],
            random_seed=42
        )

        print(f"✅ Generated {len(variations)} variations")

        # Step 2: Initialize Oxen client
        print("\n🔐 Step 2: Initializing Oxen client...")
        client = OxenClient(
            namespace=test_namespace,
            repo_name=test_repo_name,
            interactive_auth=False  # Use env var/config only
        )

        print(f"✅ Client initialized for {test_namespace}/{test_repo_name}")

        # Step 3: Upload to Oxen
        print("\n📤 Step 3: Uploading to Oxen.ai...")
        result = generator.export_to_oxen(
            variations=variations,
            oxen_client=client,
            commit_message="E2E test: 10 negotiation variations"
        )

        print(f"\n{result}")

        # Step 4: Verify upload succeeded
        print("\n✅ Step 4: Verifying upload...")
        assert result.success, f"Upload failed: {result.error_message}"
        assert result.file_size_bytes > 0
        assert result.commit_id is not None

        # Step 5: Print URLs for manual verification
        print("\n🔗 Step 5: Access URLs")
        print("=" * 70)
        print(f"Repository:  {result.repo_url}")
        print(f"Dataset:     {result.dataset_url}")
        print(f"Fine-tune:   {result.finetune_url}")
        print("=" * 70)

        # Step 6: Verify repo exists
        print("\n🔍 Step 6: Verifying repository exists...")
        assert client.repo_exists(), "Repository should exist after upload"
        print("✅ Repository verified!")

        print("\n" + "=" * 70)
        print("TEST COMPLETE ✅")
        print("=" * 70)
        print("\n⚠️  Manual cleanup required:")
        print(f"   Visit {result.repo_url}/settings to delete test repository")
        print("=" * 70)

    def test_vertical_generator_export_to_oxen(self, test_namespace, test_repo_name):
        """Test exporting temporal expansion to Oxen.ai."""
        print("\n" + "=" * 70)
        print("TEST: Vertical Generator → Oxen.ai Upload")
        print("=" * 70)

        # Import dependencies
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from generation.config_schema import SimulationConfig
        from generation.vertical_generator import VerticalGenerator
        from generation.templates.loader import TemplateLoader
        from oxen_integration import OxenClient

        # Use different repo name for vertical test
        vertical_repo_name = f"{test_repo_name}_vertical"

        # Step 1: Generate temporal expansion
        print("\n⏱️  Step 1: Generating temporal expansion...")
        generator = VerticalGenerator()
        base_config = TemplateLoader().load_template("showcase/jefferson_dinner")

        expanded = generator.generate_temporal_depth(
            base_config=base_config,
            before_count=3,
            after_count=3,
            strategy="progressive_training"
        )

        stats = generator.get_generation_stats()
        print(f"✅ Expanded to {stats['total_timepoints']} timepoints")
        print(f"   Cost savings: {stats.get('cost_savings_estimated', 0):.1%}")

        # Step 2: Initialize Oxen client
        print("\n🔐 Step 2: Initializing Oxen client...")
        client = OxenClient(
            namespace=test_namespace,
            repo_name=vertical_repo_name,
            interactive_auth=False
        )

        print(f"✅ Client initialized for {test_namespace}/{vertical_repo_name}")

        # Step 3: Upload to Oxen
        print("\n📤 Step 3: Uploading to Oxen.ai...")
        result = generator.export_to_oxen(
            config=expanded,
            oxen_client=client,
            commit_message="E2E test: Temporal expansion (Jefferson dinner)"
        )

        print(f"\n{result}")

        # Step 4: Verify upload succeeded
        print("\n✅ Step 4: Verifying upload...")
        assert result.success, f"Upload failed: {result.error_message}"
        assert result.file_size_bytes > 0

        # Step 5: Print URLs
        print("\n🔗 Step 5: Access URLs")
        print("=" * 70)
        print(f"Repository:  {result.repo_url}")
        print(f"Dataset:     {result.dataset_url}")
        print(f"Fine-tune:   {result.finetune_url}")
        print("=" * 70)

        print("\n" + "=" * 70)
        print("TEST COMPLETE ✅")
        print("=" * 70)
        print("\n⚠️  Manual cleanup required:")
        print(f"   Visit {result.repo_url}/settings to delete test repository")
        print("=" * 70)

    def test_oxen_client_authentication(self, test_namespace):
        """Test that Oxen client can authenticate."""
        print("\n" + "=" * 70)
        print("TEST: Oxen Client Authentication")
        print("=" * 70)

        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from oxen_integration import OxenClient

        print("\n🔐 Testing authentication...")
        client = OxenClient(
            namespace=test_namespace,
            interactive_auth=False
        )

        # Verify authentication works
        is_authenticated = client.authenticate()

        print(f"✅ Authentication successful: {is_authenticated}")
        assert is_authenticated, "Authentication should succeed with valid token"

        print("\n" + "=" * 70)
        print("TEST COMPLETE ✅")
        print("=" * 70)


if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s"])
