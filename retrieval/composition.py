"""
Tensor composition strategies for combining multiple tensors.

Provides methods to blend, merge, or pool multiple tensors
into a single result tensor.

Phase 3: Retrieval System
"""

import numpy as np
from typing import List, Optional

from schemas import TTMTensor


class TensorComposer:
    """
    Composes multiple tensors using various strategies.

    Strategies:
    - weighted_blend: Weighted average of tensor values
    - max_pool: Take maximum value per dimension
    - hierarchical: Later tensors override earlier ones (non-zero values)
    """

    def weighted_blend(
        self,
        tensors: List[np.ndarray],
        weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """
        Blend tensors using weighted average.

        Args:
            tensors: List of tensor value arrays
            weights: Optional weights (defaults to equal weights)

        Returns:
            Blended tensor values
        """
        if not tensors:
            raise ValueError("Cannot blend empty tensor list")

        if len(tensors) == 1:
            return tensors[0].copy()

        # Default to equal weights
        if weights is None:
            weights = [1.0 / len(tensors)] * len(tensors)

        # Normalize weights
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        # Compute weighted sum
        result = np.zeros_like(tensors[0], dtype=np.float32)
        for tensor, weight in zip(tensors, weights):
            result += tensor.astype(np.float32) * weight

        return result

    def max_pool(self, tensors: List[np.ndarray]) -> np.ndarray:
        """
        Pool tensors by taking maximum value per dimension.

        Args:
            tensors: List of tensor value arrays

        Returns:
            Max-pooled tensor values
        """
        if not tensors:
            raise ValueError("Cannot pool empty tensor list")

        if len(tensors) == 1:
            return tensors[0].copy()

        stacked = np.stack([t.astype(np.float32) for t in tensors])
        return np.max(stacked, axis=0)

    def hierarchical(self, tensors: List[np.ndarray]) -> np.ndarray:
        """
        Compose tensors hierarchically.

        Later tensors override earlier ones where they have non-zero values.
        Useful for applying specific overrides to a base tensor.

        Args:
            tensors: List of tensor value arrays (first is base)

        Returns:
            Hierarchically composed tensor values
        """
        if not tensors:
            raise ValueError("Cannot compose empty tensor list")

        if len(tensors) == 1:
            return tensors[0].copy()

        # Start with base tensor
        result = tensors[0].astype(np.float32).copy()

        # Apply overrides
        for tensor in tensors[1:]:
            tensor_f = tensor.astype(np.float32)
            mask = tensor_f != 0
            result[mask] = tensor_f[mask]

        return result

    def compose_tensors(
        self,
        tensors: List[TTMTensor],
        method: str = "weighted_blend",
        weights: Optional[List[float]] = None
    ) -> TTMTensor:
        """
        Compose full TTMTensor objects.

        Args:
            tensors: List of TTMTensor objects
            method: Composition method ("weighted_blend", "max_pool", "hierarchical")
            weights: Optional weights for weighted_blend

        Returns:
            Composed TTMTensor
        """
        if not tensors:
            raise ValueError("Cannot compose empty tensor list")

        if len(tensors) == 1:
            # Return a copy of the single tensor
            return TTMTensor(
                context_vector=tensors[0].context_vector,
                biology_vector=tensors[0].biology_vector,
                behavior_vector=tensors[0].behavior_vector,
            )

        # Extract arrays from each tensor using to_arrays()
        context_arrays = []
        biology_arrays = []
        behavior_arrays = []

        for t in tensors:
            context, biology, behavior = t.to_arrays()
            context_arrays.append(np.asarray(context, dtype=np.float32))
            biology_arrays.append(np.asarray(biology, dtype=np.float32))
            behavior_arrays.append(np.asarray(behavior, dtype=np.float32))

        # Apply composition method
        if method == "weighted_blend":
            context = self.weighted_blend(context_arrays, weights)
            biology = self.weighted_blend(biology_arrays, weights)
            behavior = self.weighted_blend(behavior_arrays, weights)
        elif method == "max_pool":
            context = self.max_pool(context_arrays)
            biology = self.max_pool(biology_arrays)
            behavior = self.max_pool(behavior_arrays)
        elif method == "hierarchical":
            context = self.hierarchical(context_arrays)
            biology = self.hierarchical(biology_arrays)
            behavior = self.hierarchical(behavior_arrays)
        else:
            raise ValueError(f"Unknown composition method: {method}")

        # Create new TTMTensor using from_arrays
        return TTMTensor.from_arrays(
            context=context,
            biology=biology,
            behavior=behavior,
        )

    def blend_with_scores(
        self,
        tensors: List[TTMTensor],
        scores: List[float]
    ) -> TTMTensor:
        """
        Blend tensors using their similarity scores as weights.

        Higher scoring tensors contribute more to the blend.

        Args:
            tensors: List of TTMTensor objects
            scores: Similarity scores (will be normalized)

        Returns:
            Blended TTMTensor
        """
        return self.compose_tensors(tensors, method="weighted_blend", weights=scores)
