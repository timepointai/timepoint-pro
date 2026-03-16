"""
Tensor backend selector for Timepoint Pro.

Auto-detects the best available compute backend:
  CUDA (NVIDIA GPU) > MPS (Apple Silicon) > CPU (numpy)

Set TENSOR_BACKEND env var to override:
  TENSOR_BACKEND=torch   — use PyTorch (auto-detects device)
  TENSOR_BACKEND=numpy   — use numpy/scipy (default)

Usage:
  from tensor_backend import get_backend, get_device

  backend = get_backend()   # "torch" or "numpy"
  device = get_device()     # "cuda", "mps", or "cpu"
"""

from __future__ import annotations

import os
import warnings


def get_backend() -> str:
    """Return the active tensor backend name."""
    env = os.environ.get("TENSOR_BACKEND", "numpy").lower()
    if env == "torch":
        if _torch_available():
            return "torch"
        warnings.warn(
            "TENSOR_BACKEND=torch but PyTorch is not installed. Falling back to numpy.",
            stacklevel=2,
        )
        return "numpy"
    return "numpy"


def get_device() -> str:
    """Return the best available PyTorch device string."""
    if get_backend() != "torch":
        return "cpu"

    import torch

    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _torch_available() -> bool:
    """Check if PyTorch is importable."""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def describe() -> str:
    """Human-readable backend description."""
    backend = get_backend()
    device = get_device()

    if backend == "torch":
        import torch
        return f"PyTorch {torch.__version__} on {device}"
    return "NumPy/SciPy (CPU)"
