"""Tests for legifrance_get_document tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.exceptions import (
    LegifranceAuthError,
    LegifranceDocumentNotFoundError,
    LegifranceParseError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from chat.tools.legifrance.tools.get_document import legifrance_get_document


class TestLegifranceGetDocument:
    """Test legifrance_get_document tool."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, mocked_context, sample_document_response):
        """Test successful document retrieval."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value=sample_document_response)

            result = await legifrance_get_document(
                mocked_context, article_id="LEGIARTI000032041571"
            )

            assert isinstance(result, ToolReturn)
            assert "1240" in result.return_value
            assert result.metadata["found"] is True
            assert result.metadata["article_id"] == "LEGIARTI000032041571"

    @pytest.mark.asyncio
    async def test_get_document_not_found_none_response(self, mocked_context):
        """Test document not found when API returns None."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value=None)

            result = await legifrance_get_document(mocked_context, article_id="LEGIARTI999999")

            assert isinstance(result, ToolReturn)
            assert "non trouvé" in result.return_value
            assert result.metadata["found"] is False

    @pytest.mark.asyncio
    async def test_get_document_not_found_exception(self, mocked_context):
        """Test document not found exception handling."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value={"article": None})

            result = await legifrance_get_document(mocked_context, article_id="LEGIARTI999999")

            assert "non trouvé" in result.return_value
            assert result.metadata["found"] is False

    @pytest.mark.asyncio
    async def test_get_document_parse_error(self, mocked_context):
        """Test parse error handling."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value={"article": "invalid"})

            result = await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

            assert "format invalide" in result.return_value
            assert result.metadata["error"] == "parse_error"

    @pytest.mark.asyncio
    async def test_get_document_rate_limit(self, mocked_context):
        """Test rate limit error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(side_effect=LegifranceRateLimitError("Rate limited"))

            with pytest.raises(ModelRetry):
                await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

    @pytest.mark.asyncio
    async def test_get_document_timeout(self, mocked_context):
        """Test timeout error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(side_effect=LegifranceTimeoutError("Timeout"))

            with pytest.raises(ModelRetry):
                await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

    @pytest.mark.asyncio
    async def test_get_document_server_error(self, mocked_context):
        """Test server error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(side_effect=LegifranceServerError("Server error"))

            with pytest.raises(ModelRetry):
                await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

    @pytest.mark.asyncio
    async def test_get_document_auth_error(self, mocked_context):
        """Test auth error returns error message (via decorator soft fail)."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(side_effect=LegifranceAuthError("Auth failed"))

            result = await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "Auth" in result or "authentification" in result.lower()

    @pytest.mark.asyncio
    async def test_get_document_unexpected_error(self, mocked_context):
        """Test unexpected error returns error message (via decorator soft fail)."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(side_effect=RuntimeError("Unexpected"))

            result = await legifrance_get_document(mocked_context, article_id="LEGIARTI000001")

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "RuntimeError" in result

    @pytest.mark.asyncio
    async def test_get_document_metadata_includes_sources(
        self, mocked_context, sample_document_response
    ):
        """Test metadata includes document URL as source."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value=sample_document_response)

            result = await legifrance_get_document(
                mocked_context, article_id="LEGIARTI000032041571"
            )

            # Sources should contain full Legifrance URL
            sources = result.metadata["sources"]
            assert len(sources) > 0
            source_url = next(iter(sources))
            assert "legifrance.gouv.fr" in source_url
            assert "LEGIARTI000032041571" in source_url

    @pytest.mark.asyncio
    async def test_get_document_includes_url(self, mocked_context, sample_document_response):
        """Test returned document includes URL."""
        with patch("chat.tools.legifrance.tools.get_document.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_document = AsyncMock(return_value=sample_document_response)

            result = await legifrance_get_document(
                mocked_context, article_id="LEGIARTI000032041571"
            )

            assert "Lien:" in result.return_value
            assert result.metadata["url"] is not None
