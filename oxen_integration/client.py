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
        RemoteRepo = None
        import_error = None

        # Try multiple import paths for oxenai package
        try:
            from oxen import RemoteRepo
        except ImportError as e1:
            import_error = e1
            try:
                from oxen.remote_repo import RemoteRepo
            except ImportError as e2:
                import_error = e2
                try:
                    from oxenai import RemoteRepo
                except ImportError as e3:
                    import_error = e3

        if RemoteRepo is None:
            raise ConfigurationError(
                f"oxenai package import failed: {import_error}. "
                "Install with: pip install oxenai"
            )

        try:
            self.remote_repo = RemoteRepo(f"{self.namespace}/{self.repo_name}")
        except AttributeError as e:
            raise ConfigurationError(
                f"oxenai package API mismatch: {e}. "
                "Try: pip install --upgrade oxenai"
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
        # Try multiple import paths for oxenai package
        RemoteRepo = None
        import_error = None
        try:
            from oxen import RemoteRepo
        except ImportError as e1:
            import_error = e1
            try:
                from oxen.remote_repo import RemoteRepo
            except ImportError as e2:
                import_error = e2
                try:
                    from oxenai import RemoteRepo
                except ImportError as e3:
                    import_error = e3

        if RemoteRepo is None:
            raise ConfigurationError(
                f"oxenai package import failed: {import_error}. "
                "Install with: pip install oxenai"
            )

        try:
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

        except (ConfigurationError, RepositoryError):
            raise
        except AttributeError as e:
            raise ConfigurationError(
                f"oxenai package API mismatch: {e}. "
                "Try: pip install --upgrade oxenai"
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
        # Try multiple import paths for oxenai package
        RemoteRepo = None
        import_error = None
        try:
            from oxen import RemoteRepo
        except ImportError as e1:
            import_error = e1
            try:
                from oxen.remote_repo import RemoteRepo
            except ImportError as e2:
                import_error = e2
                try:
                    from oxenai import RemoteRepo
                except ImportError as e3:
                    import_error = e3

        if RemoteRepo is None:
            raise ConfigurationError(
                f"oxenai package import failed: {import_error}. "
                "Install with: pip install oxenai"
            )

        try:
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
            # For file URLs, need to append filename at the end
            dataset_url = f"{repo_url}/file/main/{dst_path}/{file_path_obj.name}"
            # Oxen.ai does not support programmatic fine-tune creation
            # Users must create fine-tunes manually through the web UI
            finetune_url = repo_url  # Direct users to repo where they can create fine-tune

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

        except (ConfigurationError, UploadError, RepositoryError):
            raise
        except AttributeError as e:
            raise ConfigurationError(
                f"oxenai package API mismatch: {e}. "
                "Try: pip install --upgrade oxenai"
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

    # Branch Management Methods

    def create_branch(
        self, branch_name: str, from_branch: str = "main"
    ) -> str:
        """
        Create a new branch from an existing branch.

        Args:
            branch_name: Name of the new branch
            from_branch: Branch to create from (default: "main")

        Returns:
            Branch name

        Raises:
            RepositoryError: If branch creation fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            self.remote_repo.create_branch(branch_name, from_branch)
            return branch_name
        except Exception as e:
            raise RepositoryError(f"Failed to create branch '{branch_name}': {e}")

    def list_branches(self) -> list:
        """
        List all branches in the repository.

        Returns:
            List of branch names

        Raises:
            RepositoryError: If listing branches fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            branches = self.remote_repo.branches()
            # Extract branch names from branch objects
            return [b.name if hasattr(b, 'name') else str(b) for b in branches]
        except Exception as e:
            raise RepositoryError(f"Failed to list branches: {e}")

    def get_current_branch(self) -> str:
        """
        Get the current branch name.

        Returns:
            Current branch name

        Raises:
            RepositoryError: If getting current branch fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            branch = self.remote_repo.branch()
            return branch.name if hasattr(branch, 'name') else str(branch)
        except Exception as e:
            raise RepositoryError(f"Failed to get current branch: {e}")

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a branch exists.

        Args:
            branch_name: Name of the branch to check

        Returns:
            True if branch exists

        Raises:
            RepositoryError: If checking branch existence fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            return self.remote_repo.branch_exists(branch_name)
        except Exception as e:
            raise RepositoryError(f"Failed to check if branch exists: {e}")

    def switch_branch(self, branch_name: str) -> None:
        """
        Switch to a different branch (checkout).

        Args:
            branch_name: Name of the branch to switch to

        Raises:
            RepositoryError: If checkout fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            self.remote_repo.checkout(branch_name)
        except Exception as e:
            raise RepositoryError(f"Failed to checkout branch '{branch_name}': {e}")

    def delete_branch(self, branch_name: str) -> None:
        """
        Delete a branch.

        Args:
            branch_name: Name of the branch to delete

        Raises:
            RepositoryError: If branch deletion fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            self.remote_repo.delete_branch(branch_name)
        except Exception as e:
            raise RepositoryError(f"Failed to delete branch '{branch_name}': {e}")

    def merge_branch(
        self, source_branch: str, target_branch: str, message: Optional[str] = None
    ) -> str:
        """
        Merge source branch into target branch.

        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into
            message: Optional merge commit message

        Returns:
            Merge commit ID

        Raises:
            RepositoryError: If merge fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            # First checkout target branch
            self.remote_repo.checkout(target_branch)

            # Check if merge is possible
            is_mergeable = self.remote_repo.mergeable(source_branch, target_branch)
            if not is_mergeable:
                raise RepositoryError(
                    f"Cannot merge '{source_branch}' into '{target_branch}' - conflicts detected"
                )

            # Perform merge
            merge_result = self.remote_repo.merge(source_branch, message or f"Merge {source_branch} into {target_branch}")
            return getattr(merge_result, "id", "unknown")
        except Exception as e:
            raise RepositoryError(f"Failed to merge '{source_branch}' into '{target_branch}': {e}")

    def create_feature_branch(self, feature_name: str, from_branch: str = "main") -> str:
        """
        Convenience method to create a feature branch with standard naming.

        Args:
            feature_name: Name of the feature (will be prefixed with "feature/")
            from_branch: Branch to create from (default: "main")

        Returns:
            Full branch name (e.g., "feature/my-feature")

        Raises:
            RepositoryError: If branch creation fails
        """
        branch_name = f"feature/{feature_name}"
        return self.create_branch(branch_name, from_branch)

    def create_experiment_branch(self, experiment_name: str, from_branch: str = "main") -> str:
        """
        Convenience method to create an experiment branch for model training.

        Args:
            experiment_name: Name of the experiment (will be prefixed with "experiments/")
            from_branch: Branch to create from (default: "main")

        Returns:
            Full branch name (e.g., "experiments/my-experiment")

        Raises:
            RepositoryError: If branch creation fails
        """
        branch_name = f"experiments/{experiment_name}"
        return self.create_branch(branch_name, from_branch)

    # Workspace Management Methods

    def create_workspace(self, workspace_id: Optional[str] = None, branch: str = "main"):
        """
        Create a workspace for making changes.

        Args:
            workspace_id: Optional workspace ID (auto-generated if None)
            branch: Branch to create workspace from (default: "main")

        Returns:
            Workspace object

        Raises:
            RepositoryError: If workspace creation fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            if workspace_id:
                workspace = self.remote_repo.create_workspace(workspace_id, branch)
            else:
                workspace = self.remote_repo.create_workspace(branch)
            return workspace
        except Exception as e:
            raise RepositoryError(f"Failed to create workspace: {e}")

    def list_workspaces(self) -> list:
        """
        List all workspaces in the repository.

        Returns:
            List of workspace objects

        Raises:
            RepositoryError: If listing workspaces fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            return self.remote_repo.list_workspaces()
        except Exception as e:
            raise RepositoryError(f"Failed to list workspaces: {e}")

    def delete_workspace(self, workspace_id: str) -> None:
        """
        Delete a workspace.

        Args:
            workspace_id: ID of the workspace to delete

        Raises:
            RepositoryError: If workspace deletion fails
        """
        if not self.remote_repo:
            raise RepositoryError("No repository initialized")

        try:
            self.remote_repo.delete_workspace(workspace_id)
        except Exception as e:
            raise RepositoryError(f"Failed to delete workspace '{workspace_id}': {e}")
