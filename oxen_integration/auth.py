"""
Authentication management for Oxen.ai integration.
"""
import getpass
from typing import Optional, Tuple
from .config import OxenConfig, ConfigManager
from .exceptions import AuthenticationError


class AuthManager:
    """Manages Oxen.ai authentication."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize auth manager.

        Args:
            config_manager: Config manager instance. Creates default if None.
        """
        self.config_manager = config_manager or ConfigManager()

    def get_token(self, interactive: bool = True) -> Tuple[str, OxenConfig]:
        """
        Get API token with interactive fallback.

        Priority:
        1. Environment variable OXEN_API_TOKEN
        2. Config file
        3. Interactive prompt (if interactive=True)

        Args:
            interactive: Whether to prompt user if token not found

        Returns:
            Tuple of (token, config)

        Raises:
            AuthenticationError: If token not found and interactive=False
        """
        # Load existing config
        config = self.config_manager.load()

        # If we have a token, return it
        if config.api_token:
            return config.api_token, config

        # No token found
        if not interactive:
            raise AuthenticationError(
                "No Oxen API token found. Set OXEN_API_TOKEN or OXEN_API_KEY environment variable "
                "or run with interactive=True to enter token."
            )

        # Interactive prompt
        print("=" * 70)
        print("Oxen.ai Authentication")
        print("=" * 70)
        print()
        print("No API token found. You can get one from:")
        print("  https://www.oxen.ai → Settings → API Tokens")
        print()

        token = getpass.getpass("Enter your Oxen API token: ").strip()

        if not token:
            raise AuthenticationError("No token provided")

        # Update config
        config.api_token = token

        # Ask if user wants to save
        save_response = input("Save token to ~/.oxen/config.json? [Y/n]: ").strip().lower()

        if save_response in ("", "y", "yes"):
            # Ask for optional namespace
            namespace = input("Default namespace (username) [optional]: ").strip()
            if namespace:
                config.default_namespace = namespace

            # Save config
            self.config_manager.save(config)
            print(f"✅ Configuration saved to {self.config_manager.config_path}")
        else:
            print("⚠️  Token will only be used for this session")

        print()
        return token, config

    def configure_oxen_sdk(self, token: str, user_name: Optional[str] = None, user_email: Optional[str] = None) -> None:
        """
        Configure Oxen SDK with authentication.

        Args:
            token: API token
            user_name: Optional user name for commits
            user_email: Optional user email for commits
        """
        try:
            from oxen import auth, user

            # Set auth token
            auth.config_auth(token)

            # Set user info if provided
            if user_name or user_email:
                user.config_user(
                    user_name or "Timepoint User",
                    user_email or "noreply@timepoint.ai"
                )

        except ImportError:
            raise AuthenticationError(
                "oxenai package not installed. Install with: pip install oxenai"
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to configure Oxen SDK: {e}")

    def verify_authentication(self) -> bool:
        """
        Verify that authentication is working.

        Returns:
            True if authenticated successfully

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Simply verify we have a token configured
            config = self.config_manager.load()
            if config.api_token:
                return True
            else:
                raise AuthenticationError("No API token configured")

        except Exception as e:
            raise AuthenticationError(f"Authentication verification failed: {e}")
