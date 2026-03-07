"""Tests for legifrance_search_admin tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.tools.search_admin import legifrance_search_admin


class TestLegifranceSearchAdmin:
    """Test legifrance_search_admin tool."""

    @pytest.mark.asyncio
    async def test_search_admin_jorf_success(self, mocked_context):
        """Test successful JORF search."""
        sample_results = [
            {
                "id": "JORFTEXT000001",
                "titles": [{"id": "JORFTEXT000001", "title": "Décret"}],
                "nature": "DECRET",
                "datePublication": "2020-01-15T00:00:00",
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = sample_results

            result = await legifrance_search_admin(mocked_context, query="protection données")

            assert isinstance(result, ToolReturn)
            assert result.metadata["fond"] == "JORF"

    @pytest.mark.asyncio
    async def test_search_admin_circ_source(self, mocked_context):
        """Test CIRC source uses correct fond."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(mocked_context, query="test", source="CIRC")

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "CIRC"

    @pytest.mark.asyncio
    async def test_search_admin_cnil_source(self, mocked_context):
        """Test CNIL source uses correct fond."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(mocked_context, query="test", source="CNIL")

            call_args = mock_search.call_args
            assert call_args[1]["fond"] == "CNIL"

    @pytest.mark.asyncio
    async def test_search_admin_empty_results(self, mocked_context):
        """Test empty results handling."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await legifrance_search_admin(mocked_context, query="inexistant")

            assert "Aucun résultat" in result.return_value

    @pytest.mark.asyncio
    async def test_search_admin_query_cleanup(self, mocked_context):
        """Test source name is removed from query."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(
                mocked_context, query="JORF protection données", source="JORF"
            )

            call_args = mock_search.call_args
            assert call_args[1]["query"] == "protection données"

    @pytest.mark.asyncio
    async def test_search_admin_cnil_with_nature_delib(self, mocked_context):
        """Test CNIL nature_delib filter."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(
                mocked_context, query="test", source="CNIL", nature_delib="DECISION"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            nature_filter = next((f for f in filtres if f.facette == "NATURE_DELIB"), None)
            assert nature_filter is not None
            assert "DECISION" in nature_filter.valeurs

    @pytest.mark.asyncio
    async def test_search_admin_cnil_with_nor(self, mocked_context):
        """Test CNIL NOR filter."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(
                mocked_context, query="test", source="CNIL", nor="PRMD2000001A"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            nor_filter = next((f for f in filtres if f.facette == "NOR"), None)
            assert nor_filter is not None

    @pytest.mark.asyncio
    async def test_search_admin_cnil_with_date(self, mocked_context):
        """Test CNIL date filter uses DATE_DELIB."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(
                mocked_context, query="test", source="CNIL", date="2020-01-15"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_DELIB"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_admin_jorf_with_date(self, mocked_context):
        """Test JORF date filter uses DATE_VERSION."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(
                mocked_context, query="test", source="JORF", date="2020-01-15"
            )

            call_args = mock_search.call_args
            filtres = call_args[1]["filtres"]
            date_filter = next((f for f in filtres if f.facette == "DATE_VERSION"), None)
            assert date_filter is not None

    @pytest.mark.asyncio
    async def test_search_admin_jorf_sort(self, mocked_context):
        """Test JORF uses publication date sort."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(mocked_context, query="test", source="JORF")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "PUBLICATION_DATE_DESC"

    @pytest.mark.asyncio
    async def test_search_admin_circ_sort(self, mocked_context):
        """Test CIRC uses signature date sort."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(mocked_context, query="test", source="CIRC")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "SIGNATURE_DATE_DESC"

    @pytest.mark.asyncio
    async def test_search_admin_cnil_sort(self, mocked_context):
        """Test CNIL uses decision date sort."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            await legifrance_search_admin(mocked_context, query="test", source="CNIL")

            call_args = mock_search.call_args
            assert call_args[1]["sort"] == "DATE_DECISION_DESC"

    @pytest.mark.asyncio
    async def test_search_admin_unexpected_error(self, mocked_context):
        """Test unexpected errors return error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_admin.legifrance_search_core",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = AttributeError("Unexpected")

            result = await legifrance_search_admin(mocked_context, query="test")

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "AttributeError" in result
