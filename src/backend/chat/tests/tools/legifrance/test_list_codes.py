"""Tests for legifrance_list_codes tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.exceptions import (
    LegifranceAuthError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from chat.tools.legifrance.tools.list_codes import legifrance_list_codes


class TestLegifranceListCodes:
    """Test legifrance_list_codes tool."""

    @pytest.mark.asyncio
    async def test_list_codes_success(self, mocked_context, sample_code_list_results):
        """Test successful code listing."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=sample_code_list_results)

            result = await legifrance_list_codes(mocked_context)

            assert isinstance(result, ToolReturn)
            assert "Code civil" in result.return_value
            assert "Code pénal" in result.return_value
            assert result.metadata["found"] is True
            assert result.metadata["count"] == 2

    @pytest.mark.asyncio
    async def test_list_codes_with_filter(self, mocked_context, sample_code_list_results):
        """Test code listing with name filter."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=[sample_code_list_results[0]])

            result = await legifrance_list_codes(mocked_context, code_name="civil")

            assert "Code civil" in result.return_value
            assert result.metadata["code_name_filter"] == "civil"
            assert result.metadata["count"] == 1

    @pytest.mark.asyncio
    async def test_list_codes_empty_results(self, mocked_context):
        """Test empty code list."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=[])

            result = await legifrance_list_codes(mocked_context, code_name="inexistant")

            assert "Aucun code trouvé" in result.return_value
            assert result.metadata["found"] is False
            assert result.metadata["count"] == 0

    @pytest.mark.asyncio
    async def test_list_codes_includes_urls(self, mocked_context, sample_code_list_results):
        """Test code listing includes URLs for LEGITEXT codes."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=sample_code_list_results)

            result = await legifrance_list_codes(mocked_context)

            assert "Lien:" in result.return_value
            assert "legifrance.gouv.fr" in result.return_value

    @pytest.mark.asyncio
    async def test_list_codes_rate_limit(self, mocked_context):
        """Test rate limit error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(side_effect=LegifranceRateLimitError("Rate limited"))

            with pytest.raises(ModelRetry):
                await legifrance_list_codes(mocked_context)

    @pytest.mark.asyncio
    async def test_list_codes_timeout(self, mocked_context):
        """Test timeout error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(side_effect=LegifranceTimeoutError("Timeout"))

            with pytest.raises(ModelRetry):
                await legifrance_list_codes(mocked_context)

    @pytest.mark.asyncio
    async def test_list_codes_server_error(self, mocked_context):
        """Test server error raises ModelRetry."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(side_effect=LegifranceServerError("Server error"))

            with pytest.raises(ModelRetry):
                await legifrance_list_codes(mocked_context)

    @pytest.mark.asyncio
    async def test_list_codes_auth_error(self, mocked_context):
        """Test auth error returns error message (via decorator soft fail)."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(side_effect=LegifranceAuthError("Auth failed"))

            result = await legifrance_list_codes(mocked_context)

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "Auth" in result or "authentification" in result.lower()

    @pytest.mark.asyncio
    async def test_list_codes_unexpected_error(self, mocked_context):
        """Test unexpected error returns error message (via decorator soft fail)."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(side_effect=TypeError("Unexpected"))

            result = await legifrance_list_codes(mocked_context)

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "TypeError" in result

    @pytest.mark.asyncio
    async def test_list_codes_metadata_includes_sources(
        self, mocked_context, sample_code_list_results
    ):
        """Test metadata includes code URLs as sources."""
        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=sample_code_list_results)

            result = await legifrance_list_codes(mocked_context)

            sources = result.metadata["sources"]
            assert len(sources) >= 2
            assert any("LEGITEXT000006070721" in url for url in sources)
            assert any("LEGITEXT000006070719" in url for url in sources)
            assert all("legifrance.gouv.fr" in url for url in sources)

    @pytest.mark.asyncio
    async def test_list_codes_handles_missing_cid(self, mocked_context):
        """Test handling of codes without CID (no URL generated)."""
        results = [{"id": "123", "title": "Code sans CID", "etat": "VIGUEUR"}]

        with patch("chat.tools.legifrance.tools.list_codes.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.list_codes = AsyncMock(return_value=results)

            result = await legifrance_list_codes(mocked_context)

            assert "Code sans CID" in result.return_value
            # No URL generated because CID is missing/invalid
            assert result.metadata["sources"] == set()
