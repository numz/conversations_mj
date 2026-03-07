"""Tests for Legifrance search core functionality."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.core import (
    SearchField,
    SearchFilter,
    legifrance_search_core,
)
from chat.tools.legifrance.exceptions import (
    LegifranceAuthError,
    LegifranceClientError,
    LegifranceConnectionError,
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)


class TestLegifranceSearchCore:
    """Test legifrance_search_core function."""

    @pytest.mark.asyncio
    async def test_search_core_success(self, mocked_context, sample_search_results):
        """Test successful search returns results."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(return_value=sample_search_results)

            results = await legifrance_search_core(
                ctx=mocked_context, query="test query", fond="CODE_DATE", criteres=[], filtres=[]
            )

            assert len(results) == 1
            assert results[0]["id"] == "LEGIARTI000006417749"

    @pytest.mark.asyncio
    async def test_search_core_empty_results(self, mocked_context):
        """Test search returns empty list when no results."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(return_value=[])

            results = await legifrance_search_core(
                ctx=mocked_context, query="nonexistent", fond="CODE_DATE", criteres=[], filtres=[]
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_search_core_rate_limit_raises_model_retry(self, mocked_context):
        """Test rate limit error is converted to ModelRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(side_effect=LegifranceRateLimitError("Rate limited"))

            with pytest.raises(ModelRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "surchargée" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_core_timeout_raises_model_retry(self, mocked_context):
        """Test timeout error is converted to ModelRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(side_effect=LegifranceTimeoutError("Request timed out"))

            with pytest.raises(ModelRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "expiré" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_core_connection_error_raises_model_retry(self, mocked_context):
        """Test connection error is converted to ModelRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(side_effect=LegifranceConnectionError("Connection failed"))

            with pytest.raises(ModelRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "connexion" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_core_server_error_raises_model_retry(self, mocked_context):
        """Test server error is converted to ModelRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(
                side_effect=LegifranceServerError("Server error", status_code=500)
            )

            with pytest.raises(ModelRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "difficultés" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_core_auth_error_raises_model_cannot_retry(self, mocked_context):
        """Test auth error is converted to ModelCannotRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(side_effect=LegifranceAuthError("Auth failed"))

            with pytest.raises(ModelCannotRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "authentification" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_core_client_error_raises_model_cannot_retry(self, mocked_context):
        """Test client error is converted to ModelCannotRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(
                side_effect=LegifranceClientError("Bad request", status_code=400)
            )

            with pytest.raises(ModelCannotRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_core_unexpected_error_raises_model_cannot_retry(self, mocked_context):
        """Test unexpected error is converted to ModelCannotRetry."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(side_effect=ValueError("Unexpected"))

            with pytest.raises(ModelCannotRetry) as exc_info:
                await legifrance_search_core(
                    ctx=mocked_context, query="test", fond="CODE_DATE", criteres=[], filtres=[]
                )

            assert "ValueError" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_core_passes_criteria_correctly(self, mocked_context):
        """Test search core passes criteria to API correctly."""
        with patch("chat.tools.legifrance.api.LegifranceAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search = AsyncMock(return_value=[])

            from chat.tools.legifrance.core import (
                SearchCriterion,
                SearchField,
                SearchFilter,
            )

            criteres = [
                SearchField(
                    typeChamp="ALL",
                    criteres=[SearchCriterion(typeRecherche="UN_DES_MOTS", valeur="test")],
                )
            ]
            filtres = [SearchFilter(facette="NOM_CODE", valeurs=["Code civil"])]

            await legifrance_search_core(
                ctx=mocked_context,
                query="test",
                fond="CODE_DATE",
                criteres=criteres,
                filtres=filtres,
                sort="PERTINENCE",
            )

            mock_api.search.assert_called_once()
            call_kwargs = mock_api.search.call_args[1]
            assert call_kwargs["fond"] == "CODE_DATE"
            assert call_kwargs["sort"] == "PERTINENCE"
            assert len(call_kwargs["criteres"]) == 1
            assert len(call_kwargs["filtres"]) == 1
