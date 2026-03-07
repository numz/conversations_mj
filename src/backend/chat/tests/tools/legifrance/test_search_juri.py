"""Tests for legifrance_search_jurisprudence tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.tools.search_jurisprudence import legifrance_search_jurisprudence


class TestLegifranceSearchJurisprudence:
    """Test legifrance_search_jurisprudence tool."""

    @pytest.mark.asyncio
    async def test_search_juri_success(self, mocked_context, sample_juri_results):
        """Test successful jurisprudence search."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = sample_juri_results

            result = await legifrance_search_jurisprudence(mocked_context, query="responsabilité")

            assert isinstance(result, ToolReturn)
            assert result.metadata["fond"] == "JURI"

    @pytest.mark.asyncio
    async def test_search_juri_empty_results(self, mocked_context):
        """Test empty jurisprudence results."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await legifrance_search_jurisprudence(mocked_context, query="inexistant")

            assert "Aucun résultat" in result.return_value

    @pytest.mark.asyncio
    async def test_search_juri_administratif(self, mocked_context):
        """Test administrative jurisdiction uses CETAT fond."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(
                mocked_context, query="test", juridiction="ADMINISTRATIF"
            )

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "CETAT"

    @pytest.mark.asyncio
    async def test_search_juri_constitutionnel(self, mocked_context):
        """Test constitutional jurisdiction uses CONSTIT fond."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(
                mocked_context, query="test", juridiction="CONSTITUTIONNEL"
            )

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "CONSTIT"

    @pytest.mark.asyncio
    async def test_search_juri_financier(self, mocked_context):
        """Test financial jurisdiction uses JUFI fond."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(
                mocked_context, query="test", juridiction="FINANCIER"
            )

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "JUFI"

    @pytest.mark.asyncio
    async def test_search_juri_with_date(self, mocked_context):
        """Test date filter is applied."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(mocked_context, query="test", date="2020-01-15")

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_DECISION"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_juri_with_numero_decision(self, mocked_context):
        """Test decision number filter is applied."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(
                mocked_context, query="test", numero_decision="20-12.345"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            num_filter = next((f for f in filtres if f.facette == "NUMERO_DECISION"), None)
            assert num_filter is not None
            assert "20-12.345" in num_filter.valeurs

    @pytest.mark.asyncio
    async def test_search_juri_sort_date_desc(self, mocked_context):
        """Test DATE_DESC sort is converted correctly."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(mocked_context, query="test", sort="DATE_DESC")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "DATE_DECISION_DESC"

    @pytest.mark.asyncio
    async def test_search_juri_sort_date_asc(self, mocked_context):
        """Test DATE_ASC sort is converted correctly."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_jurisprudence(mocked_context, query="test", sort="DATE_ASC")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "DATE_DECISION_ASC"

    @pytest.mark.asyncio
    async def test_search_juri_model_retry_propagates(self, mocked_context):
        """Test ModelRetry propagates correctly."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = ModelRetry("Rate limited")

            with pytest.raises(ModelRetry):
                await legifrance_search_jurisprudence(mocked_context, query="test")

    @pytest.mark.asyncio
    async def test_search_juri_unexpected_error(self, mocked_context):
        """Test unexpected errors return error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_jurisprudence.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = RuntimeError("Unexpected")

            result = await legifrance_search_jurisprudence(mocked_context, query="test")

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "RuntimeError" in result
