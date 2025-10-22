"""
Custom exceptions for Oxen.ai integration.
"""


class OxenError(Exception):
    """Base exception for all Oxen integration errors."""
    pass


class AuthenticationError(OxenError):
    """Raised when authentication with Oxen.ai fails."""
    pass


class UploadError(OxenError):
    """Raised when dataset upload fails."""
    pass


class RepositoryError(OxenError):
    """Raised when repository operations fail."""
    pass


class ConfigurationError(OxenError):
    """Raised when configuration is invalid or missing."""
    pass
