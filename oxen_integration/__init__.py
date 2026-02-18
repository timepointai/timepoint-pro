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

# Phase 4: Tensor versioning (optional - requires pyarrow)
try:
    from .parquet_schemas import (
        get_template_schema,
        get_instance_schema,
        tensor_record_to_parquet_row,
        parquet_row_to_tensor_record,
        write_templates_parquet,
        write_instances_parquet,
        read_templates_parquet,
        read_instances_parquet,
    )
    from .tensor_versioning import (
        TensorVersionController,
        SyncResult,
        FetchResult,
    )
    from .sync import (
        TensorSyncManager,
        SyncState,
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
