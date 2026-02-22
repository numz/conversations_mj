"""Tests for _clean_tool_name() — Feature 3: Tool Name Sanitize."""

from unittest.mock import patch

import pytest

from chat.clients.pydantic_ai import AIAgentService


@pytest.fixture()
def service():
    """Return an AIAgentService with __init__ bypassed."""
    with patch.object(AIAgentService, "__init__", return_value=None):
        return AIAgentService()


# ------------------------------------------------------------------ #
# Feature flag OFF (default) — should be a no-op
# ------------------------------------------------------------------ #
class TestCleanToolNameDisabled:
    """When TOOL_NAME_SANITIZE_ENABLED is False the name must pass through unchanged."""

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", False)
    def test_plain_name_unchanged(self, service):
        assert service._clean_tool_name("get_weather") == "get_weather"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", False)
    def test_dirty_name_unchanged_when_disabled(self, service):
        dirty = "get_weather<|channel|>extra"
        assert service._clean_tool_name(dirty) == dirty

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", False)
    def test_empty_string_unchanged(self, service):
        assert service._clean_tool_name("") == ""


# ------------------------------------------------------------------ #
# Feature flag ON — invalid tokens must be stripped
# ------------------------------------------------------------------ #
class TestCleanToolNameEnabled:
    """When TOOL_NAME_SANITIZE_ENABLED is True, vLLM artefacts are removed."""

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_plain_name_unchanged(self, service):
        assert service._clean_tool_name("get_weather") == "get_weather"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_strip_channel_token(self, service):
        assert service._clean_tool_name("get_weather<|channel|>junk") == "get_weather"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_strip_start_token(self, service):
        assert service._clean_tool_name("search<|start|>") == "search"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_strip_end_token(self, service):
        assert service._clean_tool_name("lookup<|end|>rest") == "lookup"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_multiple_tokens(self, service):
        name = "tool<|channel|>a<|start|>b"
        assert service._clean_tool_name(name) == "tool"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_trailing_whitespace_stripped(self, service):
        assert service._clean_tool_name("tool  <|channel|>x") == "tool"

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_empty_string_returns_empty(self, service):
        assert service._clean_tool_name("") == ""

    @patch("chat.clients.pydantic_ai.settings.TOOL_NAME_SANITIZE_ENABLED", True)
    def test_only_token_returns_empty(self, service):
        assert service._clean_tool_name("<|channel|>") == ""
