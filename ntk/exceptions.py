class NTKError(Exception):
    """Base class for ntk errors surfaced to the CLI entry point."""


class NTKAuthError(NTKError):
    """Raised on a 401 response (invalid or missing API key)."""


class NTKNotFoundError(NTKError):
    """Raised on a 404 response (store, theme, or template not found)."""


class NTKConnectionError(NTKError):
    """Raised when a request cannot reach the store after retries."""
