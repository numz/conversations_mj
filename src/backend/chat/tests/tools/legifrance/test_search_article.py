"""Tests for legifrance_search_code_article_by_number tool."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry
from chat.tools.legifrance.exceptions import (
    LegifranceRateLimitError,
    LegifranceServerError,
    LegifranceTimeoutError,
)
from chat.tools.legifrance.tools.search_code_article_by_number import (
    legifrance_search_code_article_by_number,
)


class TestLegifranceSearchCodeArticleByNumber:
    """Test legifrance_search_code_article_by_number tool."""

    @pytest.mark.asyncio
    async def test_search_article_success(self, mocked_context):
        """Test successful article search."""
        sample_results = [
            {
                "titles": [{"cid": "LEGITEXT000006070721", "title": "Code civil"}],
                "sections": [
                    {
                        "title": "Des obligations",
                        "extracts": [
                            {
                                "id": "LEGIARTI000032041571",
                                "title": "Article 1240",
                                "legalStatus": "VIGUEUR",
                                "values": ["Tout fait quelconque..."],
                            }
                        ],
                    }
                ],
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(return_value=sample_results)

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code civil", article_num="1240"
            )

            assert isinstance(result, ToolReturn)
            assert "1240" in result.return_value
            assert result.metadata["found"] is True
            assert result.metadata["code_name"] == "Code civil"
            assert result.metadata["article_num"] == "1240"

    @pytest.mark.asyncio
    async def test_search_article_not_found(self, mocked_context):
        """Test article not found."""
        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(return_value=[])

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code civil", article_num="99999"
            )

            assert isinstance(result, ToolReturn)
            assert "Aucun article trouvé" in result.return_value
            assert result.metadata["found"] is False
            assert result.metadata["sources"] == {}

    @pytest.mark.asyncio
    async def test_search_article_complex_number(self, mocked_context):
        """Test article with complex number format (L123-4-5)."""
        sample_results = [
            {
                "titles": [{"cid": "LEGITEXT000006072050", "title": "Code du travail"}],
                "sections": [
                    {
                        "extracts": [
                            {
                                "id": "LEGIARTI000006900847",
                                "title": "Article L1234-5",
                                "legalStatus": "VIGUEUR",
                                "values": ["Contenu article..."],
                            }
                        ]
                    }
                ],
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(return_value=sample_results)

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code du travail", article_num="L1234-5"
            )

            assert isinstance(result, ToolReturn)
            assert result.metadata["found"] is True

    @pytest.mark.asyncio
    async def test_search_article_rate_limit(self, mocked_context):
        """Test rate limit error raises ModelRetry."""
        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(
                side_effect=LegifranceRateLimitError("Rate limited")
            )

            with pytest.raises(ModelRetry):
                await legifrance_search_code_article_by_number(
                    mocked_context, code_name="Code civil", article_num="1240"
                )

    @pytest.mark.asyncio
    async def test_search_article_timeout(self, mocked_context):
        """Test timeout error raises ModelRetry."""
        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(side_effect=LegifranceTimeoutError("Timeout"))

            with pytest.raises(ModelRetry):
                await legifrance_search_code_article_by_number(
                    mocked_context, code_name="Code civil", article_num="1240"
                )

    @pytest.mark.asyncio
    async def test_search_article_server_error(self, mocked_context):
        """Test server error raises ModelRetry."""
        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(
                side_effect=LegifranceServerError("Server error")
            )

            with pytest.raises(ModelRetry):
                await legifrance_search_code_article_by_number(
                    mocked_context, code_name="Code civil", article_num="1240"
                )

    @pytest.mark.asyncio
    async def test_search_article_unexpected_error(self, mocked_context):
        """Test unexpected error returns error message (via decorator soft fail)."""
        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(side_effect=RuntimeError("Unexpected"))

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code civil", article_num="1240"
            )

            # Decorator converts ModelCannotRetry to string message
            assert isinstance(result, str)
            assert "RuntimeError" in result

    @pytest.mark.asyncio
    async def test_search_article_metadata_includes_sources(self, mocked_context):
        """Test metadata includes article URLs as sources."""
        sample_results = [
            {
                "titles": [{"cid": "LEGITEXT000006070721", "title": "Code civil"}],
                "sections": [
                    {
                        "extracts": [
                            {
                                "id": "LEGIARTI000032041571",
                                "title": "Article 1240",
                                "legalStatus": "VIGUEUR",
                                "values": [],
                            }
                        ]
                    }
                ],
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(return_value=sample_results)

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code civil", article_num="1240"
            )

            sources = result.metadata["sources"]
            assert len(sources) >= 2
            assert any("LEGIARTI000032041571" in url for url in sources)
            assert any("LEGITEXT000006070721" in url for url in sources)
            assert all("legifrance.gouv.fr" in url for url in sources)

    @pytest.mark.asyncio
    async def test_search_article_invalid_code_name(self, mocked_context):
        """Test empty code name returns validation error."""
        result = await legifrance_search_code_article_by_number(
            mocked_context, code_name="", article_num="1240"
        )

        # Decorator converts ModelCannotRetry to string message
        assert isinstance(result, str)
        assert "invalide" in result.lower() or "vide" in result.lower()

    @pytest.mark.asyncio
    async def test_search_article_invalid_article_num(self, mocked_context):
        """Test empty article number returns validation error."""
        result = await legifrance_search_code_article_by_number(
            mocked_context, code_name="Code civil", article_num=""
        )

        # Decorator converts ModelCannotRetry to string message
        assert isinstance(result, str)
        assert "invalide" in result.lower() or "vide" in result.lower()

    @pytest.mark.asyncio
    async def test_search_article_multiple_results(self, mocked_context):
        """Test handling multiple matching articles."""
        sample_results = [
            {
                "titles": [{"cid": "LEGITEXT000006070721", "title": "Code civil"}],
                "sections": [
                    {
                        "extracts": [
                            {"id": "LEGIARTI000001", "title": "Art. 1"},
                            {"id": "LEGIARTI000002", "title": "Art. 1 bis"},
                        ]
                    }
                ],
            }
        ]

        with patch(
            "chat.tools.legifrance.tools.search_code_article_by_number.LegifranceAPI"
        ) as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.search_code_article = AsyncMock(return_value=sample_results)

            result = await legifrance_search_code_article_by_number(
                mocked_context, code_name="Code civil", article_num="1"
            )

            assert isinstance(result, ToolReturn)
            sources = result.metadata["sources"]
            assert any("LEGIARTI000001" in url for url in sources)
            assert any("LEGIARTI000002" in url for url in sources)
            assert all("legifrance.gouv.fr" in url for url in sources)
