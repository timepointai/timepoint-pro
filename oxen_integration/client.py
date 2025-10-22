"""
Main client for Oxen.ai integration.
"""
import os
from pathlib import Path
from typing import Optional
from .auth import AuthManager
from .config import OxenConfig, ConfigManager
from .models import UploadResult, RepositoryInfo
from .exceptions import (
    AuthenticationError,
    UploadError,
    RepositoryError,
    ConfigurationError,
)


class OxenClient:
    """Client for interacting with Oxen.ai."""

    def __init__(
        self,
        repo_name: Optional[str] = None,
        namespace: Optional[str] = None,
        config: Optional[OxenConfig] = None,
        interactive_auth: bool = True,
    ):
        """
        Initialize Oxen client.

        Args:
            repo_name: Repository name (e.g., "negotiation-variations")
            namespace: Username/organization (e.g., "your-username")
            config: Optional pre-configured OxenConfig
            interactive_auth: Whether to prompt for credentials if missing

        Raises:
            AuthenticationError: If authentication fails
        """
        self.config_manager = ConfigManager()
        self.auth_manager = AuthManager(self.config_manager)

        # Get or create config
        if config is None:
            token, config = self.auth_manager.get_token(interactive=interactive_auth)
        else:
            token = config.api_token
            if not token:
                if interactive_auth:
                    token, config = self.auth_manager.get_token(interactive=True)
                else:
                    raise AuthenticationError("No API token in provided config")

        self.config = config
        self.token = token

        # Set namespace and repo
        self.namespace = namespace or config.default_namespace
        self.repo_name = repo_name or config.default_repo

        # Configure Oxen SDK
        self.auth_manager.configure_oxen_sdk(self.token)

        # Initialize remote repo if namespace and repo_name provided
        self.remote_repo = None
        if self.namespace and self.repo_name:
            self._init_remote_repo()

    def _init_remote_repo(self):
        """Initialize RemoteRepo instance."""
        try:
            from oxen.remote_repo import RemoteRepo

            self.remote_repo = RemoteRepo(f"{self.namespace}/{self.repo_name}")
        except ImportError:
            raise ConfigurationError(
                "oxenai package not installed. Install with: pip install oxenai"
            )
        except Exception as e:
            # Remote repo initialization failure is not critical
            # User might want to create the repo first
            pass

    def authenticate(self) -> bool:
        """
        Verify authentication is working.

        Returns:
            True if authenticated

        Raises:
            AuthenticationError: If authentication fails
        """
        return self.auth_manager.verify_authentication()

    def create_repo(
        self, name: Optional[str] = None, description: str = "", empty: bool = False
    ) -> RepositoryInfo:
        """
        Create a new Oxen repository.

        Args:
            name: Repository name. Uses self.repo_name if None.
            description: Repository description
            empty: Whether to create empty repo (no initial commit)

        Returns:
            RepositoryInfo object

        Raises:
            RepositoryError: If repository creation fails
        """
        try:
            from oxen.remote_repo import RemoteRepo

            repo_name = name or self.repo_name
            if not repo_name:
                raise RepositoryError("Repository name required")

            if not self.namespace:
                raise RepositoryError(
                    "Namespace required. Set namespace in constructor or config."
                )

            full_name = f"{self.namespace}/{repo_name}"

            # Create repository - RemoteRepo() initializes, then .create() creates it
            remote_repo = RemoteRepo(full_name)
            remote_repo.create(empty=empty, is_public=False)

            # Update instance variables
            if name:
                self.repo_name = name
            self.remote_repo = remote_repo

            # Build repository info
            repo_url = f"{self.config.hub_url}/{full_name}"

            return RepositoryInfo(
                namespace=self.namespace,
                name=repo_name,
                full_name=full_name,
                url=repo_url,
                exists=True,
                description=description,
            )

        except ImportError:
            raise ConfigurationError(
                "oxenai package not installed. Install with: pip install oxenai"
            )
        except Exception as e:
            raise RepositoryError(f"Failed to create repository: {e}")

    def upload_dataset(
        self,
        file_path: str,
        commit_message: str,
        dst_path: Optional[str] = None,
        create_repo_if_missing: bool = True,
    ) -> UploadResult:
        """
        Upload a dataset file to Oxen.ai.

        Args:
            file_path: Path to local file
            commit_message: Commit message
            dst_path: Destination path in repo. Defaults to filename in "datasets/"
            create_repo_if_missing: Whether to create repo if it doesn't exist

        Returns:
            UploadResult object

        Raises:
            UploadError: If upload fails
        """
        try:
            from oxen.remote_repo import RemoteRepo

            # Validate file exists
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise UploadError(f"File not found: {file_path}")

            # Ensure we have a repository
            if not self.namespace or not self.repo_name:
                raise UploadError(
                    "Repository not specified. Set namespace and repo_name."
                )

            # Check if repo exists - try to access it
            if not self.remote_repo or not self.repo_exists():
                full_name = f"{self.namespace}/{self.repo_name}"

                # Repo doesn't exist - create it if allowed
                if create_repo_if_missing:
                    repo_info = self.create_repo()
                    # remote_repo is now set by create_repo()
                else:
                    raise UploadError(
                        f"Repository {full_name} does not exist. "
                        "Set create_repo_if_missing=True to create it."
                    )

            # Determine destination path
            if dst_path is None:
                dst_path = f"datasets/{file_path_obj.name}"

            # Upload file
            self.remote_repo.add(file_path, dst=dst_path)
            commit_result = self.remote_repo.commit(commit_message)

            # Get file size
            file_size = file_path_obj.stat().st_size

            # Build URLs
            full_name = f"{self.namespace}/{self.repo_name}"
            repo_url = f"{self.config.hub_url}/{full_name}"
            dataset_url = f"{repo_url}/file/main/{dst_path}"
            finetune_url = f"{self.config.hub_url}/fine-tune?repo={full_name}&file={dst_path}"

            # Extract commit ID if available
            commit_id = getattr(commit_result, "id", None) or "unknown"

            return UploadResult(
                success=True,
                repo_url=repo_url,
                dataset_url=dataset_url,
                finetune_url=finetune_url,
                file_size_bytes=file_size,
                commit_id=commit_id,
            )

        except ImportError:
            raise ConfigurationError(
                "oxenai package not installed. Install with: pip install oxenai"
            )
        except (UploadError, RepositoryError):
            raise
        except Exception as e:
            raise UploadError(f"Upload failed: {e}")

    def get_hub_url(self, file_path: Optional[str] = None) -> str:
        """
        Get Oxen Hub URL for repository or file.

        Args:
            file_path: Optional file path within repo

        Returns:
            URL string
        """
        if not self.namespace or not self.repo_name:
            raise ConfigurationError("Namespace and repo_name required")

        base_url = f"{self.config.hub_url}/{self.namespace}/{self.repo_name}"

        if file_path:
            return f"{base_url}/file/main/{file_path}"
        else:
            return base_url

    def get_finetune_url(self, file_path: Optional[str] = None) -> str:
        """
        Get fine-tuning URL for dataset.

        Args:
            file_path: Optional specific file to fine-tune on

        Returns:
            URL string to fine-tuning interface
        """
        if not self.namespace or not self.repo_name:
            raise ConfigurationError("Namespace and repo_name required")

        full_name = f"{self.namespace}/{self.repo_name}"

        if file_path:
            return f"{self.config.hub_url}/fine-tune?repo={full_name}&file={file_path}"
        else:
            return f"{self.config.hub_url}/fine-tune?repo={full_name}"

    def repo_exists(self) -> bool:
        """
        Check if repository exists.

        Returns:
            True if repository exists
        """
        if not self.remote_repo:
            return False

        try:
            # Try to list files - if this works, repo exists
            self.remote_repo.ls()
            return True
        except Exception:
            return False
