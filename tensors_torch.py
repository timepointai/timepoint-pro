"""
PyTorch implementations of tensor compression algorithms.

Drop-in replacements for the numpy/scipy versions in tensors.py.
Supports CUDA, MPS (Apple Silicon), and CPU backends.

These produce numerically equivalent results to the numpy versions
(within floating-point tolerance) so either backend can be swapped freely.
"""

from __future__ import annotations

import numpy as np

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from tensor_backend import get_device


def pca_compress_torch(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    """PCA compression using torch.pca_lowrank."""
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for torch tensor backend")

    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)

    if np.any(np.isnan(tensor)):
        raise ValueError("PCA compression failed: tensor contains NaN values")
    if np.any(np.isinf(tensor)):
        raise ValueError("PCA compression failed: tensor contains inf values")

    n_samples, n_features = tensor.shape
    if n_samples < 2:
        return tensor.flatten()

    n_components = min(n_components, n_features, n_samples)
    n_components = max(1, n_components)

    device = get_device()
    t = torch.tensor(tensor, dtype=torch.float32, device=device)

    # Center the data (PCA requires centered input)
    mean = t.mean(dim=0)
    t_centered = t - mean

    # torch.pca_lowrank returns (U, S, V)
    U, S, V = torch.pca_lowrank(t_centered, q=n_components)

    # Project data onto principal components
    compressed = t_centered @ V[:, :n_components]
    return compressed.cpu().numpy().flatten()


def svd_compress_torch(tensor: np.ndarray, n_components: int = 8) -> np.ndarray:
    """SVD compression using torch.linalg.svd."""
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for torch tensor backend")

    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)

    device = get_device()
    t = torch.tensor(tensor, dtype=torch.float32, device=device)

    U, S, Vh = torch.linalg.svd(t, full_matrices=False)
    k = min(n_components, len(S), t.shape[0], t.shape[1])
    k = max(1, k)

    result = U[:, :k] @ torch.diag(S[:k]) @ Vh[:k, :]
    return result.cpu().numpy().flatten()


def nmf_compress_torch(tensor: np.ndarray, n_components: int = 8, max_iter: int = 200) -> np.ndarray:
    """
    NMF compression using multiplicative update rules in PyTorch.

    Since PyTorch doesn't have a built-in NMF, we implement the standard
    multiplicative update algorithm (Lee & Seung, 2001).
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for torch tensor backend")

    if len(tensor.shape) == 1:
        tensor = tensor.reshape(1, -1)

    tensor = np.abs(tensor)  # NMF requires non-negative
    n_components = min(n_components, tensor.shape[0], tensor.shape[1])
    n_components = max(1, n_components)

    device = get_device()
    V = torch.tensor(tensor, dtype=torch.float32, device=device)

    # Initialize W and H with random non-negative values
    torch.manual_seed(42)
    m, n = V.shape
    W = torch.rand(m, n_components, device=device)
    H = torch.rand(n_components, n, device=device)

    eps = 1e-10  # Avoid division by zero

    for _ in range(max_iter):
        # Update H: H *= (W^T V) / (W^T W H + eps)
        numerator_h = W.T @ V
        denominator_h = W.T @ W @ H + eps
        H = H * (numerator_h / denominator_h)

        # Update W: W *= (V H^T) / (W H H^T + eps)
        numerator_w = V @ H.T
        denominator_w = W @ H @ H.T + eps
        W = W * (numerator_w / denominator_w)

    return W.cpu().numpy().flatten()


# Registry of torch compression methods (mirrors tensors.py registry)
TORCH_COMPRESSORS = {
    "pca": pca_compress_torch,
    "svd": svd_compress_torch,
    "nmf": nmf_compress_torch,
}


def compress_torch(tensor: np.ndarray, method: str, **kwargs) -> np.ndarray:
    """Compress tensor using the specified PyTorch method."""
    if method not in TORCH_COMPRESSORS:
        raise ValueError(f"Unknown torch compression method: {method}")
    return TORCH_COMPRESSORS[method](tensor, **kwargs)
