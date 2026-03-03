"""
Oxen.ai integration for Timepoint-Pro.

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

from .auth import AuthManager
from .client import OxenClient
from .config import ConfigManager, OxenConfig
from .evaluation import (
    EvaluationExample,
    EvaluationResults,
    ModelEvaluator,
    TimepointEvaluator,
)
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    OxenError,
    RepositoryError,
    UploadError,
)
from .finetune import (
    DataFormatter,
    FineTuneConfig,
    FineTuneJob,
    FineTuneLauncher,
)
from .models import GenerationPipelineResult, RepositoryInfo, UploadResult

# Phase 4: Tensor versioning (optional - requires pyarrow)
try:
    from .parquet_schemas import (
        get_instance_schema,
        get_template_schema,
        parquet_row_to_tensor_record,
        read_instances_parquet,
        read_templates_parquet,
        tensor_record_to_parquet_row,
        write_instances_parquet,
        write_templates_parquet,
    )
    from .sync import (
        SyncState,
        TensorSyncManager,
    )
    from .tensor_versioning import (
        FetchResult,
        SyncResult,
        TensorVersionController,
    )

    TENSOR_VERSIONING_AVAILABLE = True
except ImportError:
    TENSOR_VERSIONING_AVAILABLE = False

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
    # Tensor versioning (Phase 4)
    "TENSOR_VERSIONING_AVAILABLE",
    "TensorVersionController",
    "TensorSyncManager",
    "SyncResult",
    "FetchResult",
    "SyncState",
]

__version__ = "0.1.0"
