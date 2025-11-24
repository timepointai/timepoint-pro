"""
Unit tests for Oxen.ai integration module.
"""
import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from oxen_integration import (
    OxenClient,
    AuthManager,
    ConfigManager,
    OxenConfig,
    UploadResult,
    RepositoryInfo,
    AuthenticationError,
    UploadError,
    RepositoryError,
    ConfigurationError,
)


class TestOxenConfig:
    """Test OxenConfig data class."""

    def test_oxen_config_creation(self):
        """Test creating OxenConfig."""
        config = OxenConfig(
            api_token="test_token",
            default_namespace="test_user",
            default_repo="test_repo",
        )

        assert config.api_token == "test_token"
        assert config.default_namespace == "test_user"
        assert config.default_repo == "test_repo"
        assert config.hub_url == "https://www.oxen.ai"

    def test_oxen_config_to_dict(self):
        """Test converting config to dict."""
        config = OxenConfig(api_token="test_token", default_namespace="user")
        config_dict = config.to_dict()

        assert "api_token" in config_dict
        assert "default_namespace" in config_dict
        assert config_dict["api_token"] == "test_token"

    def test_oxen_config_from_dict(self):
        """Test creating config from dict."""
        data = {"api_token": "test_token", "default_namespace": "user"}
        config = OxenConfig.from_dict(data)

        assert config.api_token == "test_token"
        assert config.default_namespace == "user"


class TestConfigManager:
    """Test ConfigManager."""

    def test_config_manager_init_default(self):
        """Test ConfigManager with default path."""
        manager = ConfigManager()
        assert manager.config_path == Path.home() / ".oxen" / "config.json"

    def test_config_manager_init_custom(self):
        """Test ConfigManager with custom path."""
        custom_path = Path("/tmp/custom_oxen.json")
        manager = ConfigManager(custom_path)
        assert manager.config_path == custom_path

    def test_config_manager_load_env_var(self, monkeypatch):
        """Test loading config from environment variable."""
        monkeypatch.setenv("OXEN_API_TOKEN", "env_token")

        manager = ConfigManager()
        config = manager.load()

        assert config.api_token == "env_token"

    def test_config_manager_load_from_file(self):
        """Test loading config from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "api_token": "file_token",
                "default_namespace": "test_user",
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(Path(temp_path))
            config = manager.load()

            assert config.api_token == "file_token"
            assert config.default_namespace == "test_user"
        finally:
            os.unlink(temp_path)

    def test_config_manager_save(self):
        """Test saving config to file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "oxen_config.json"
            manager = ConfigManager(config_path)

            config = OxenConfig(
                api_token="save_token", default_namespace="save_user"
            )
            manager.save(config)

            assert config_path.exists()

            # Load and verify
            with open(config_path, "r") as f:
                saved_data = json.load(f)

            assert saved_data["api_token"] == "save_token"
            assert saved_data["default_namespace"] == "save_user"

    def test_config_manager_env_overrides_file(self, monkeypatch):
        """Test that environment variable takes precedence over file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"api_token": "file_token"}
            json.dump(config_data, f)
            temp_path = f.name

        try:
            monkeypatch.setenv("OXEN_API_TOKEN", "env_token")

            manager = ConfigManager(Path(temp_path))
            config = manager.load()

            # Environment should override file
            assert config.api_token == "env_token"
        finally:
            os.unlink(temp_path)


class TestAuthManager:
    """Test AuthManager."""

    def test_auth_manager_get_token_from_env(self, monkeypatch):
        """Test getting token from environment."""
        monkeypatch.setenv("OXEN_API_TOKEN", "env_token")

        auth_manager = AuthManager()
        token, config = auth_manager.get_token(interactive=False)

        assert token == "env_token"
        assert config.api_token == "env_token"

    def test_auth_manager_no_token_non_interactive(self, monkeypatch):
        """Test error when no token and non-interactive."""
        monkeypatch.delenv("OXEN_API_TOKEN", raising=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_manager = ConfigManager(config_path)
            auth_manager = AuthManager(config_manager)

            with pytest.raises(AuthenticationError):
                auth_manager.get_token(interactive=False)

    @patch("oxen_integration.auth.config_auth")
    @patch("oxen_integration.auth.config_user")
    def test_configure_oxen_sdk(self, mock_config_user, mock_config_auth):
        """Test configuring Oxen SDK."""
        auth_manager = AuthManager()
        auth_manager.configure_oxen_sdk("test_token", "Test User", "test@example.com")

        mock_config_auth.assert_called_once_with("test_token")
        mock_config_user.assert_called_once_with("Test User", "test@example.com")


class TestOxenClient:
    """Test OxenClient."""

    def test_oxen_client_init_with_config(self, monkeypatch):
        """Test OxenClient initialization with config."""
        monkeypatch.setenv("OXEN_API_TOKEN", "test_token")

        config = OxenConfig(
            api_token="test_token",
            default_namespace="test_user",
            default_repo="test_repo",
        )

        with patch("oxen_integration.client.AuthManager.configure_oxen_sdk"):
            client = OxenClient(config=config, interactive_auth=False)

            assert client.config.api_token == "test_token"
            assert client.namespace == "test_user"
            assert client.repo_name == "test_repo"

    def test_oxen_client_no_token_raises(self):
        """Test that OxenClient raises error without token."""
        config = OxenConfig()  # No token

        with pytest.raises(AuthenticationError):
            OxenClient(config=config, interactive_auth=False)

    def test_oxen_client_get_hub_url(self, monkeypatch):
        """Test getting Hub URL."""
        monkeypatch.setenv("OXEN_API_TOKEN", "test_token")

        config = OxenConfig(api_token="test_token")

        with patch("oxen_integration.client.AuthManager.configure_oxen_sdk"):
            client = OxenClient(
                namespace="user", repo_name="repo", config=config, interactive_auth=False
            )

            url = client.get_hub_url()
            assert url == "https://www.oxen.ai/user/repo"

            file_url = client.get_hub_url("datasets/data.jsonl")
            assert file_url == "https://www.oxen.ai/user/repo/file/main/datasets/data.jsonl"

    def test_oxen_client_get_finetune_url(self, monkeypatch):
        """Test getting fine-tune URL."""
        monkeypatch.setenv("OXEN_API_TOKEN", "test_token")

        config = OxenConfig(api_token="test_token")

        with patch("oxen_integration.client.AuthManager.configure_oxen_sdk"):
            client = OxenClient(
                namespace="user", repo_name="repo", config=config, interactive_auth=False
            )

            url = client.get_finetune_url()
            assert url == "https://www.oxen.ai/fine-tune?repo=user/repo"

            file_url = client.get_finetune_url("datasets/data.jsonl")
            assert (
                file_url
                == "https://www.oxen.ai/fine-tune?repo=user/repo&file=datasets/data.jsonl"
            )


class TestUploadResult:
    """Test UploadResult model."""

    def test_upload_result_success(self):
        """Test successful upload result."""
        result = UploadResult(
            success=True,
            repo_url="https://www.oxen.ai/user/repo",
            dataset_url="https://www.oxen.ai/user/repo/file/main/data.jsonl",
            finetune_url="https://www.oxen.ai/fine-tune?repo=user/repo",
            file_size_bytes=1024,
            commit_id="abc123",
        )

        assert result.success
        assert result.file_size_bytes == 1024
        assert "✅" in str(result)

    def test_upload_result_failure(self):
        """Test failed upload result."""
        result = UploadResult(
            success=False,
            repo_url="",
            dataset_url="",
            finetune_url="",
            file_size_bytes=0,
            error_message="Upload failed: network error",
        )

        assert not result.success
        assert "❌" in str(result)
        assert "network error" in str(result)


class TestRepositoryInfo:
    """Test RepositoryInfo model."""

    def test_repository_info(self):
        """Test repository info creation."""
        info = RepositoryInfo(
            namespace="user",
            name="repo",
            full_name="user/repo",
            url="https://www.oxen.ai/user/repo",
            exists=True,
            description="Test repository",
        )

        assert info.namespace == "user"
        assert info.name == "repo"
        assert info.repo_id == "user/repo"
        assert info.exists


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
