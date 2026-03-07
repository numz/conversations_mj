"""Unit tests for source title passthrough in AIAgentService."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from chat.ai_sdk_types import LanguageModelV1Source, SourceUIPart
from chat.clients.pydantic_ai import AIAgentService
from chat.factories import ChatConversationFactory
from chat.vercel_ai_sdk.core import events_v4

pytestmark = pytest.mark.django_db()


@pytest.fixture(autouse=True)
def base_settings(settings):
    """Set up base settings for the tests."""
    settings.AI_BASE_URL = "https://api.llm.com/v1/"
    settings.AI_API_KEY = "test-key"
    settings.AI_MODEL = "model-123"
    settings.AI_AGENT_INSTRUCTIONS = "You are a helpful assistant"
    settings.AI_AGENT_TOOLS = []


class TestSourceTitlePassthrough:
    """Tests that source titles from tools are correctly passed through to LanguageModelV1Source."""

    def test_source_dict_with_titles(self):
        """When sources is a dict {url: title}, titles should be passed to LanguageModelV1Source."""
        sources = {
            "https://www.legifrance.gouv.fr/codes/article/123": "Article 1240 du Code civil [Modifie]",
            "https://www.legifrance.gouv.fr/codes/article/456": "Article 1241 du Code civil",
        }

        # Simulate what pydantic_ai.py does with dict sources
        if isinstance(sources, dict):
            source_items = sources.items()
        else:
            source_items = ((url, None) for url in sources)

        results = []
        for source_url, source_title in source_items:
            url_source = LanguageModelV1Source(
                sourceType="url",
                id=str(uuid.uuid4()),
                url=source_url,
                title=source_title or None,
                providerMetadata={},
            )
            results.append(url_source)

        assert len(results) == 2
        assert results[0].url == "https://www.legifrance.gouv.fr/codes/article/123"
        assert results[0].title == "Article 1240 du Code civil [Modifie]"
        assert results[1].url == "https://www.legifrance.gouv.fr/codes/article/456"
        assert results[1].title == "Article 1241 du Code civil"

    def test_source_set_without_titles(self):
        """When sources is a set of URLs, titles should be None."""
        sources = {
            "https://www.legifrance.gouv.fr/codes/article/123",
            "https://www.example.com/page",
        }

        if isinstance(sources, dict):
            source_items = sources.items()
        else:
            source_items = ((url, None) for url in sources)

        results = []
        for source_url, source_title in source_items:
            url_source = LanguageModelV1Source(
                sourceType="url",
                id=str(uuid.uuid4()),
                url=source_url,
                title=source_title or None,
                providerMetadata={},
            )
            results.append(url_source)

        assert len(results) == 2
        for result in results:
            assert result.title is None

    def test_source_list_without_titles(self):
        """When sources is a list of URLs, titles should be None."""
        sources = [
            "https://www.legifrance.gouv.fr/codes/article/123",
            "https://www.example.com/page",
        ]

        if isinstance(sources, dict):
            source_items = sources.items()
        else:
            source_items = ((url, None) for url in sources)

        results = []
        for source_url, source_title in source_items:
            url_source = LanguageModelV1Source(
                sourceType="url",
                id=str(uuid.uuid4()),
                url=source_url,
                title=source_title or None,
                providerMetadata={},
            )
            results.append(url_source)

        assert len(results) == 2
        assert results[0].title is None
        assert results[1].title is None

    def test_source_dict_with_empty_title_becomes_none(self):
        """When a source dict has an empty string title, it should become None."""
        sources = {
            "https://www.legifrance.gouv.fr/codes/article/123": "",
        }

        if isinstance(sources, dict):
            source_items = sources.items()
        else:
            source_items = ((url, None) for url in sources)

        results = []
        for source_url, source_title in source_items:
            url_source = LanguageModelV1Source(
                sourceType="url",
                id=str(uuid.uuid4()),
                url=source_url,
                title=source_title or None,
                providerMetadata={},
            )
            results.append(url_source)

        assert len(results) == 1
        assert results[0].title is None

    def test_source_ui_part_preserves_title(self):
        """SourceUIPart should preserve the title from LanguageModelV1Source."""
        url_source = LanguageModelV1Source(
            sourceType="url",
            id="test-id",
            url="https://www.legifrance.gouv.fr/codes/article/123",
            title="Article 1240 du Code civil",
            providerMetadata={},
        )
        source_part = SourceUIPart(type="source", source=url_source)

        assert source_part.source.title == "Article 1240 du Code civil"
        dumped = source_part.model_dump()
        assert dumped["source"]["title"] == "Article 1240 du Code civil"

    def test_source_ui_part_title_none_when_absent(self):
        """SourceUIPart should have None title when not provided."""
        url_source = LanguageModelV1Source(
            sourceType="url",
            id="test-id",
            url="https://www.example.com",
            providerMetadata={},
        )
        source_part = SourceUIPart(type="source", source=url_source)

        assert source_part.source.title is None
