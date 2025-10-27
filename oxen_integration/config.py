"""
Configuration management for Oxen.ai integration.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class OxenConfig:
    """Configuration for Oxen.ai integration."""

    api_token: Optional[str] = None
    default_namespace: Optional[str] = None
    default_repo: Optional[str] = None
    hub_url: str = "https://www.oxen.ai"
    api_base_url: str = "https://api.oxen.ai"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OxenConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ConfigManager:
    """Manages Oxen configuration loading and saving."""

    DEFAULT_CONFIG_DIR = Path.home() / ".oxen"
    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_path: Path to config file. Defaults to ~/.oxen/config.json
        """
        if config_path is None:
            self.config_path = self.DEFAULT_CONFIG_DIR / self.DEFAULT_CONFIG_FILE
        else:
            self.config_path = Path(config_path)

    def load(self) -> OxenConfig:
        """
        Load configuration from file or environment.

        Priority:
        1. Environment variable OXEN_API_TOKEN
        2. Config file
        3. Empty config (will require interactive input)
        """
        config = OxenConfig()

        # Check environment variable first (check both OXEN_API_TOKEN and OXEN_API_KEY)
        env_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
        if env_token:
            config.api_token = env_token

        # Load from file if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    file_config = OxenConfig.from_dict(data)

                    # Environment variable takes precedence
                    if not config.api_token:
                        config.api_token = file_config.api_token

                    # Load other settings from file
                    if file_config.default_namespace:
                        config.default_namespace = file_config.default_namespace
                    if file_config.default_repo:
                        config.default_repo = file_config.default_repo
                    if file_config.hub_url:
                        config.hub_url = file_config.hub_url
                    if file_config.api_base_url:
                        config.api_base_url = file_config.api_base_url

            except (json.JSONDecodeError, IOError) as e:
                # Config file is corrupted or unreadable, continue with env/empty config
                pass

        return config

    def save(self, config: OxenConfig) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save
        """
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with open(self.config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def config_exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()
