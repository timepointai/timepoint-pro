"""
Data models for Oxen.ai integration.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UploadResult:
    """Result of uploading a dataset to Oxen.ai."""

    success: bool
    repo_url: str
    dataset_url: str
    finetune_url: str
    file_size_bytes: int
    commit_id: Optional[str] = None
    branch: str = "main"
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return (
                f"✅ Upload successful\n"
                f"   Repository: {self.repo_url}\n"
                f"   Dataset: {self.dataset_url}\n"
                f"   Size: {self.file_size_bytes:,} bytes\n"
                f"   Commit: {self.commit_id}\n"
                f"\n"
                f"   Next steps to create a fine-tune:\n"
                f"   1. Visit: {self.finetune_url}\n"
                f"   2. Navigate to the dataset file\n"
                f"   3. Click 'Fine-tune' to create a fine-tuning job\n"
                f"   \n"
                f"   Note: Oxen.ai does not support programmatic fine-tune creation.\n"
                f"         Fine-tunes must be created manually through the web UI."
            )
        else:
            return f"❌ Upload failed: {self.error_message}"


@dataclass
class RepositoryInfo:
    """Information about an Oxen repository."""

    namespace: str
    name: str
    full_name: str  # namespace/name
    url: str
    exists: bool
    branch: str = "main"
    description: Optional[str] = None

    @property
    def repo_id(self) -> str:
        """Get repository identifier."""
        return self.full_name


@dataclass
class GenerationPipelineResult:
    """Result of generation + upload pipeline."""

    generation_success: bool
    upload_result: Optional[UploadResult] = None
    variations_generated: int = 0
    generation_time_seconds: float = 0.0
    upload_time_seconds: float = 0.0
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        """Overall success status."""
        return self.generation_success and (
            self.upload_result.success if self.upload_result else False
        )

    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return (
                f"✅ Pipeline successful\n"
                f"   Variations: {self.variations_generated}\n"
                f"   Generation time: {self.generation_time_seconds:.2f}s\n"
                f"   Upload time: {self.upload_time_seconds:.2f}s\n"
                f"   {self.upload_result}"
            )
        else:
            return f"❌ Pipeline failed: {self.error_message}"
