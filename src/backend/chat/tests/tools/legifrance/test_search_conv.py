"""Tests for legifrance_search_conventions tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.tools.search_conventions import legifrance_search_conventions


class TestLegifranceSearchConventions:
    """Test legifrance_search_conventions tool."""

    @pytest.mark.asyncio
    async def test_search_conventions_kali_success(self, mocked_context):
        """Test successful KALI (collective agreements) search."""
        sample_results = [
            {
                "id": "KALITEXT000001",
                "titles": [{"id": "KALITEXT000001", "title": "Convention collective"}],
                "dateSignature": "2020-01-15T00:00:00",
                "etat": "VIGUEUR",
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = sample_results

            result = await legifrance_search_conventions(mocked_context, query="congés payés")

            assert isinstance(result, ToolReturn)
            assert result.metadata["fond"] == "KALI"

    @pytest.mark.asyncio
    async def test_search_conventions_acco_source(self, mocked_context):
        """Test ACCO (company agreements) uses correct fond."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(mocked_context, query="test", type_source="ACCO")

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "ACCO"

    @pytest.mark.asyncio
    async def test_search_conventions_empty_results(self, mocked_context):
        """Test empty results handling."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await legifrance_search_conventions(mocked_context, query="inexistant")

            assert "Aucun résultat" in result.return_value

    @pytest.mark.asyncio
    async def test_search_conventions_with_idcc(self, mocked_context):
        """Test IDCC filter is applied."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(mocked_context, query="test", idcc="1234")

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            idcc_filter = next((f for f in filtres if f.facette == "IDCC"), None)
            assert idcc_filter is not None
            assert "1234" in idcc_filter.valeurs

    @pytest.mark.asyncio
    async def test_search_conventions_kali_with_date(self, mocked_context):
        """Test date filter for KALI."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(
                mocked_context, query="test", type_source="KALI", date="2020-01-15"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_SIGNATURE"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_conventions_acco_with_date(self, mocked_context):
        """Test date filter for ACCO."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(
                mocked_context, query="test", type_source="ACCO", date="2020-01-15"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_SIGNATURE"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_conventions_kali_with_etat_texte(self, mocked_context):
        """Test legal status filter for KALI."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(mocked_context, query="test", etat_texte="VIGUEUR")

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            status_filter = next((f for f in filtres if f.facette == "LEGAL_STATUS"), None)
            assert status_filter is not None
            assert "VIGUEUR" in status_filter.valeurs

    @pytest.mark.asyncio
    async def test_search_conventions_kali_sort(self, mocked_context):
        """Test KALI uses signature date sort."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_conventions(mocked_context, query="test", type_source="KALI")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "SIGNATURE_DATE_DESC"

    @pytest.mark.asyncio
    async def test_search_conventions_metadata_includes_idcc(self, mocked_context):
        """Test metadata includes IDCC when provided."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await legifrance_search_conventions(mocked_context, query="test", idcc="5678")

            assert result.metadata["idcc"] == "5678"

    @pytest.mark.asyncio
    async def test_search_conventions_unexpected_error(self, mocked_context):
        """Test unexpected errors return error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_conventions.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = KeyError("Unexpected")

            result = await legifrance_search_conventions(mocked_context, query="test")

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "KeyError" in result
