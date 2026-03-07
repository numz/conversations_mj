"""Tests for legifrance_search_codes_lois tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.tools.search_codes_lois import legifrance_search_codes_lois


class TestLegifranceSearchCodesLois:
    """Test legifrance_search_codes_lois tool."""

    @pytest.mark.asyncio
    async def test_search_codes_success(self, mocked_context, sample_search_results):
        """Test successful code search returns ToolReturn."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = sample_search_results

            result = await legifrance_search_codes_lois(
                mocked_context, query="responsabilité civile", code_name="Code civil"
            )

            assert isinstance(result, ToolReturn)
            assert "1240" in result.return_value
            assert result.metadata["fond"] == "CODE_DATE"
            assert result.metadata["code_name"] == "Code civil"

    @pytest.mark.asyncio
    async def test_search_codes_empty_results(self, mocked_context):
        """Test empty results returns appropriate message."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await legifrance_search_codes_lois(
                mocked_context, query="inexistant", code_name="Code civil"
            )

            assert isinstance(result, ToolReturn)
            assert "Aucun résultat" in result.return_value
            assert result.metadata["sources"] == {}

    @pytest.mark.asyncio
    async def test_search_codes_article_number_detection(self, mocked_context):
        """Test article number pattern triggers exact search."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_codes_lois(
                mocked_context, query="article 1240", code_name="Code civil"
            )

            # Verify exact search was used (CODE_DATE fond)
            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "CODE_DATE"

    @pytest.mark.asyncio
    async def test_search_codes_loda_source(self, mocked_context):
        """Test LODA source uses correct fond."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_codes_lois(
                mocked_context, query="protection des données", type_source="LODA"
            )

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "LODA_DATE"

    @pytest.mark.asyncio
    async def test_search_codes_with_date_filter(self, mocked_context):
        """Test date filter is applied correctly."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_codes_lois(
                mocked_context, query="test", code_name="Code civil", date="2020-01-15"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_VERSION"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_codes_model_retry_propagates(self, mocked_context):
        """Test ModelRetry from search_core propagates correctly."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = ModelRetry("Rate limited")

            with pytest.raises(ModelRetry):
                await legifrance_search_codes_lois(
                    mocked_context, query="test", code_name="Code civil"
                )

    @pytest.mark.asyncio
    async def test_search_codes_model_cannot_retry_propagates(self, mocked_context):
        """Test ModelCannotRetry returns error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = ModelCannotRetry("Auth error")

            result = await legifrance_search_codes_lois(
                mocked_context, query="test", code_name="Code civil"
            )

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "Auth error" in result

    @pytest.mark.asyncio
    async def test_search_codes_unexpected_error_handled(self, mocked_context):
        """Test unexpected errors return error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = ValueError("Unexpected")

            result = await legifrance_search_codes_lois(
                mocked_context, query="test", code_name="Code civil"
            )

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "ValueError" in result

    @pytest.mark.asyncio
    async def test_search_codes_metadata_includes_sources(
        self, mocked_context, sample_search_results
    ):
        """Test metadata includes document IDs as sources."""
        with patch(
            "chat.tools.legifrance.tools.search_codes_lois.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = sample_search_results

            result = await legifrance_search_codes_lois(
                mocked_context, query="test", code_name="Code civil"
            )

            assert len(result.metadata["sources"]) > 0
