"""Tests for Legifrance exceptions hierarchy."""

import pytest

from chat.tools.legifrance.exceptions import (
    LegifranceAPIError,
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceDocumentNotFoundError,
    LegifranceError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_legifrance_error_is_base(self):
        """Test LegifranceError is the base exception."""
        exc = LegifranceError("test error")
        assert isinstance(exc, Exception)
        assert str(exc) == "test error"

    def test_api_error_inherits_from_base(self):
        """Test LegifranceAPIError inherits from LegifranceError."""
        exc = LegifranceAPIError("api error", status_code=500)
        assert isinstance(exc, LegifranceError)
        assert exc.status_code == 500

    def test_auth_error_inherits_from_api_error(self):
        """Test LegifranceAuthError inherits from LegifranceAPIError."""
        exc = LegifranceAuthError("auth failed", status_code=401)
        assert isinstance(exc, LegifranceAPIError)
        assert isinstance(exc, LegifranceError)
        assert exc.status_code == 401

    def test_rate_limit_error_inherits_from_api_error(self):
        """Test LegifranceRateLimitError inherits from LegifranceAPIError."""
        exc = LegifranceRateLimitError("rate limited", status_code=429)
        assert isinstance(exc, LegifranceAPIError)
        assert exc.status_code == 429

    def test_server_error_inherits_from_api_error(self):
        """Test LegifranceServerError inherits from LegifranceAPIError."""
        exc = LegifranceServerError("server error", status_code=500)
        assert isinstance(exc, LegifranceAPIError)
        assert exc.status_code == 500

    def test_client_error_inherits_from_api_error(self):
        """Test LegifranceClientError inherits from LegifranceAPIError."""
        exc = LegifranceClientError("bad request", status_code=400)
        assert isinstance(exc, LegifranceAPIError)
        assert exc.status_code == 400

    def test_timeout_error_inherits_from_api_error(self):
        """Test LegifranceTimeoutError inherits from LegifranceAPIError."""
        exc = LegifranceTimeoutError("timeout")
        assert isinstance(exc, LegifranceAPIError)

    def test_connection_error_inherits_from_api_error(self):
        """Test LegifranceConnectionError inherits from LegifranceAPIError."""
        exc = LegifranceConnectionError("connection failed")
        assert isinstance(exc, LegifranceAPIError)


class TestDocumentNotFoundError:
    """Test LegifranceDocumentNotFoundError."""

    def test_document_not_found_basic(self):
        """Test basic document not found error."""
        exc = LegifranceDocumentNotFoundError("LEGIARTI000001")
        assert isinstance(exc, LegifranceError)
        assert exc.document_id == "LEGIARTI000001"
        assert "LEGIARTI000001" in str(exc)

    def test_document_not_found_with_custom_message(self):
        """Test document not found with custom message."""
        exc = LegifranceDocumentNotFoundError("JURITEXT000001", "Custom not found message")
        assert exc.document_id == "JURITEXT000001"
        assert str(exc) == "Custom not found message"


class TestParseError:
    """Test LegifranceParseError."""

    def test_parse_error_basic(self):
        """Test basic parse error."""
        exc = LegifranceParseError("Invalid response format")
        assert isinstance(exc, LegifranceError)
        assert exc.raw_data is None
        assert str(exc) == "Invalid response format"

    def test_parse_error_with_raw_data(self):
        """Test parse error with raw data for debugging."""
        raw = {"invalid": "data"}
        exc = LegifranceParseError("Parse failed", raw_data=raw)
        assert exc.raw_data == raw


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_all_legifrance_errors(self):
        """Test catching all Legifrance errors with base class."""
        errors = [
            LegifranceError("base"),
            LegifranceAPIError("api"),
            LegifranceAuthError("auth"),
            LegifranceRateLimitError("rate"),
            LegifranceServerError("server"),
            LegifranceClientError("client"),
            LegifranceTimeoutError("timeout"),
            LegifranceConnectionError("connection"),
            LegifranceDocumentNotFoundError("doc123"),
            LegifranceParseError("parse"),
        ]

        for error in errors:
            try:
                raise error
            except LegifranceError:
                pass  # All should be caught
            else:
                pytest.fail(f"Exception {type(error).__name__} was not caught")

    def test_catch_api_errors_only(self):
        """Test catching only API errors."""
        api_errors = [
            LegifranceAPIError("api"),
            LegifranceAuthError("auth"),
            LegifranceRateLimitError("rate"),
            LegifranceServerError("server"),
            LegifranceClientError("client"),
            LegifranceTimeoutError("timeout"),
            LegifranceConnectionError("connection"),
        ]

        non_api_errors = [
            LegifranceDocumentNotFoundError("doc123"),
            LegifranceParseError("parse"),
        ]

        for error in api_errors:
            try:
                raise error
            except LegifranceAPIError:
                pass
            else:
                pytest.fail(f"Exception {type(error).__name__} was not caught as APIError")

        for error in non_api_errors:
            with pytest.raises(LegifranceError):
                try:
                    raise error
                except LegifranceAPIError:
                    pytest.fail(
                        f"Exception {type(error).__name__} was incorrectly caught as APIError"
                    )
                except LegifranceError:
                    raise
