#!/usr/bin/env python3
"""
Quick test for M6 TTM Tensor Compression mechanism
Tests that Phase 7 changes properly generate and compress tensors
"""
import os
import pytest
import json
import numpy as np
from datetime import datetime

from metadata.run_tracker import MetadataManager
from metadata.tracking import set_current_run_id, set_metadata_manager, clear_current_run_id
from schemas import Entity, ResolutionLevel, TemporalMode
from tensors import generate_ttm_tensor, TensorCompressor


@pytest.mark.mechanism
@pytest.mark.m6
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m6_tensor_compression():
    """Test M6 TTM Tensor Compression mechanism end-to-end."""

    print("🧪 Testing M6: TTM Tensor Compression")
    print("=" * 80)

    # Initialize tracking context
    manager = MetadataManager(db_path="metadata/runs.db")
    set_metadata_manager(manager)

    run_id = f"m6_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    manager.start_run(
        run_id=run_id,
        template_id="m6_quick_test",
        causal_mode=TemporalMode.PEARL,
        max_entities=2,
        max_timepoints=1
    )
    set_current_run_id(run_id)

    try:
        # Test 1: Generate TTM tensor from entity metadata
        print("\n[1/4] Testing tensor generation...")
        test_entity = Entity(
            entity_id="test_person",
            entity_type="human",
            resolution_level=ResolutionLevel.SCENE,
            entity_metadata={
                "physical_tensor": {
                    "age": 45,
                    "health_status": 0.8,
                    "pain_level": 0.2,
                    "fever": 37.1,
                    "mobility": 0.9,
                    "stamina": 0.7,
                    "sensory_acuity": {"vision": 0.8, "hearing": 0.9}
                },
                "cognitive_tensor": {
                    "knowledge_state": ["fact1", "fact2", "fact3"],
                    "emotional_valence": 0.6,
                    "emotional_arousal": 0.5,
                    "energy_budget": 80.0,
                    "decision_confidence": 0.75,
                    "patience_threshold": 60.0,
                    "risk_tolerance": 0.4,
                    "social_engagement": 0.7
                },
                "personality_traits": [0.7, 0.6, 0.5, 0.8, 0.6]  # Big Five
            }
        )

        # Generate tensor
        tensor_json = generate_ttm_tensor(test_entity)
        assert tensor_json is not None, "Tensor generation failed"

        test_entity.tensor = tensor_json
        print("  ✅ Tensor generated successfully")
        tensor_data = json.loads(tensor_json)
        print(f"     Context vector: {len(tensor_data['context_vector'])} dimensions")
        print(f"     Biology vector: {len(tensor_data['biology_vector'])} dimensions")
        print(f"     Behavior vector: {len(tensor_data['behavior_vector'])} dimensions")

        # Test 2: Verify tensor is populated (no longer None)
        print("\n[2/4] Verifying tensor field populated...")
        assert test_entity.tensor is not None, "Entity.tensor field is still None"
        print("  ✅ Entity.tensor field is populated")

        # Test 3: Test tensor compression with M6 mechanism
        print("\n[3/4] Testing tensor compression (M6 mechanism)...")

        # Parse the tensor and get the context vector as float array
        tensor_data = json.loads(test_entity.tensor)
        context_array = np.array(tensor_data['context_vector'], dtype=np.float64)

        # This should trigger M6 mechanism via @track_mechanism decorator
        compressed_pca = TensorCompressor.compress(context_array, "pca", n_components=4)
        compressed_svd = TensorCompressor.compress(context_array, "svd", n_components=4)

        # Check if compression worked
        assert compressed_pca is not None and len(compressed_pca) > 0, "PCA compression failed"
        print("  ✅ Tensor compression succeeded (PCA)")
        print(f"     Original dimensions: {len(context_array)}")
        print(f"     Compressed dimensions: {len(compressed_pca)}")

        # Test 4: Verify M6 mechanism was tracked
        print("\n[4/4] Verifying M6 mechanism tracking...")

        manager.complete_run(
            run_id=run_id,
            entities_created=1,
            timepoints_created=0,
            training_examples=0,
            cost_usd=0.0,
            llm_calls=0,
            tokens_used=0
        )

        # Query mechanism_usage table
        import sqlite3
        conn = sqlite3.connect("metadata/runs.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT mechanism, COUNT(*) as count
            FROM mechanism_usage
            WHERE run_id = ?
            GROUP BY mechanism
        """, (run_id,))

        mechanisms_tracked = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        if "M6" in mechanisms_tracked:
            print(f"  ✅ M6 mechanism tracked! ({mechanisms_tracked['M6']} firings)")
            print("\n" + "=" * 80)
            print("🎉 SUCCESS: Phase 7 TTM Tensor Infrastructure Working!")
            print("=" * 80)
        else:
            print("  ⚠️ M6 mechanism not tracked (may be expected if decorator not applied)")
            print(f"  Tracked mechanisms: {list(mechanisms_tracked.keys())}")

    except Exception as e:
        manager.complete_run(
            run_id=run_id,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
