"""Exceptions for Legifrance API and tools."""

from __future__ import annotations


class LegifranceError(Exception):
    """Base exception for all Legifrance-related errors."""


class LegifranceAPIError(LegifranceError):
    """Base exception for Legifrance API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize with message and optional HTTP status code."""
        self.status_code = status_code
        super().__init__(message)


class LegifranceAuthError(LegifranceAPIError):
    """Authentication error (HTTP 401)."""


class LegifranceRateLimitError(LegifranceAPIError):
    """Rate limit exceeded (HTTP 429)."""


class LegifranceServerError(LegifranceAPIError):
    """Server-side error (HTTP 5xx, 421)."""


class LegifranceClientError(LegifranceAPIError):
    """Client-side error (HTTP 4xx except 401, 429)."""


class LegifranceTimeoutError(LegifranceAPIError):
    """Request timeout error."""


class LegifranceConnectionError(LegifranceAPIError):
    """Connection error (network issues)."""


class LegifranceDocumentNotFoundError(LegifranceError):
    """Document not found in Legifrance."""

    def __init__(self, document_id: str, message: str | None = None):
        """Initialize with document ID and optional message."""
        self.document_id = document_id
        super().__init__(message or f"Document non trouvé: {document_id}")


class LegifranceParseError(LegifranceError):
    """Error parsing Legifrance API response."""

    def __init__(self, message: str, raw_data: dict[str, object] | None = None):
        """Initialize with message and optional raw data for debugging."""
        self.raw_data = raw_data
        super().__init__(message)
