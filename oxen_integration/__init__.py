"""
Oxen.ai integration for Timepoint-Daedalus.

This module provides optional integration with Oxen.ai for:
- Dataset storage and versioning
- Easy access to web-based fine-tuning
- Model evaluation and comparison
- Data collaboration and sharing

Basic usage:
    >>> from oxen_integration import OxenClient
    >>> client = OxenClient(namespace="your-username", repo_name="my-dataset")
    >>> result = client.upload_dataset("data.jsonl", "Initial dataset")
    >>> print(result.finetune_url)  # Open in browser to fine-tune

Fine-tuning workflow:
    >>> from oxen_integration import FineTuneConfig, FineTuneLauncher, DataFormatter
    >>> config = FineTuneConfig(dataset_path="datasets/training.jsonl")
    >>> launcher = FineTuneLauncher(client)
    >>> job = launcher.prepare_and_approve(config, "local_data.jsonl")
    >>> instructions = launcher.launch_via_notebook(job)
"""

from .client import OxenClient
from .auth import AuthManager
from .config import OxenConfig, ConfigManager
from .models import UploadResult, RepositoryInfo, GenerationPipelineResult
from .exceptions import (
    OxenError,
    AuthenticationError,
    UploadError,
    RepositoryError,
    ConfigurationError,
)
from .finetune import (
    FineTuneConfig,
    FineTuneJob,
    FineTuneLauncher,
    DataFormatter,
)
from .evaluation import (
    ModelEvaluator,
    TimepointEvaluator,
    EvaluationResults,
    EvaluationExample,
)

__all__ = [
    # Main client
    "OxenClient",
    # Auth & config
    "AuthManager",
    "OxenConfig",
    "ConfigManager",
    # Models
    "UploadResult",
    "RepositoryInfo",
    "GenerationPipelineResult",
    # Exceptions
    "OxenError",
    "AuthenticationError",
    "UploadError",
    "RepositoryError",
    "ConfigurationError",
    # Fine-tuning
    "FineTuneConfig",
    "FineTuneJob",
    "FineTuneLauncher",
    "DataFormatter",
    # Evaluation
    "ModelEvaluator",
    "TimepointEvaluator",
    "EvaluationResults",
    "EvaluationExample",
]

__version__ = "0.1.0"
