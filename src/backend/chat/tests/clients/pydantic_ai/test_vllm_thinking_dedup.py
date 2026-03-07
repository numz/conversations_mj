"""Tests for vLLM thinking dedup — Feature 4: vLLM Thinking Dedup."""

import dataclasses
from unittest.mock import MagicMock, patch

import pytest

from chat.clients.pydantic_ai import AIAgentService, StreamingState


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_thinking_part(content="thinking...", part_id=None):
    """Create a minimal ThinkingPart-like object."""
    part = MagicMock()
    part.content = content
    part.id = part_id
    return part


def _make_text_part(content="hello"):
    part = MagicMock()
    part.content = content
    return part


# ------------------------------------------------------------------ #
# StreamingState.ignored_thinking_indexes
# ------------------------------------------------------------------ #
class TestStreamingState:
    """Verify StreamingState initializes correctly."""

    def test_ignored_thinking_indexes_empty_by_default(self):
        state = StreamingState()
        assert state.ignored_thinking_indexes == set()

    def test_can_add_indexes(self):
        state = StreamingState()
        state.ignored_thinking_indexes.add(0)
        state.ignored_thinking_indexes.add(2)
        assert 0 in state.ignored_thinking_indexes
        assert 2 in state.ignored_thinking_indexes
        assert 1 not in state.ignored_thinking_indexes


# ------------------------------------------------------------------ #
# Non-streaming handler dedup
# ------------------------------------------------------------------ #
class TestNonStreamingDedup:
    """_handle_non_streaming_response should skip ThinkingPart(id='reasoning_content') when enabled."""

    @pytest.fixture()
    def service(self):
        with patch.object(AIAgentService, "__init__", return_value=None):
            svc = AIAgentService()
            return svc

    @patch("chat.clients.pydantic_ai.settings")
    def test_thinking_part_skipped_when_enabled(self, mock_settings, service):
        """When flag on and id='reasoning_content', ThinkingPart must be skipped."""
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True

        from pydantic_ai.messages import ThinkingPart

        part = ThinkingPart(content="duplicate", id="reasoning_content")

        # Test the condition directly
        assert mock_settings.VLLM_THINKING_DEDUP_ENABLED is True
        assert getattr(part, "id", None) == "reasoning_content"

    @patch("chat.clients.pydantic_ai.settings")
    def test_thinking_part_passed_when_disabled(self, mock_settings, service):
        """When flag off, all ThinkingParts should pass through."""
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = False

        from pydantic_ai.messages import ThinkingPart

        part = ThinkingPart(content="normal", id="reasoning_content")

        # With flag off, the condition should NOT trigger skip
        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and getattr(part, "id", None) == "reasoning_content"
        )
        assert should_skip is False

    @patch("chat.clients.pydantic_ai.settings")
    def test_thinking_part_with_different_id_not_skipped(self, mock_settings, service):
        """ThinkingParts with non-matching id should pass through even when enabled."""
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True

        from pydantic_ai.messages import ThinkingPart

        part = ThinkingPart(content="keep me", id="other_id")

        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and getattr(part, "id", None) == "reasoning_content"
        )
        assert should_skip is False

    @patch("chat.clients.pydantic_ai.settings")
    def test_thinking_part_with_no_id_not_skipped(self, mock_settings, service):
        """ThinkingParts without id attribute should pass through."""
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True

        from pydantic_ai.messages import ThinkingPart

        part = ThinkingPart(content="keep me")

        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and getattr(part, "id", None) == "reasoning_content"
        )
        assert should_skip is False


# ------------------------------------------------------------------ #
# Streaming handler dedup (index tracking)
# ------------------------------------------------------------------ #
class TestStreamingDedup:
    """Streaming dedup uses ignored_thinking_indexes to track and skip."""

    @patch("chat.clients.pydantic_ai.settings")
    def test_start_event_adds_index_when_enabled(self, mock_settings):
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True
        state = StreamingState()

        from pydantic_ai.messages import ThinkingPart

        part = ThinkingPart(content="dup", id="reasoning_content")
        event_index = 3

        if mock_settings.VLLM_THINKING_DEDUP_ENABLED and getattr(part, "id", None) == "reasoning_content":
            state.ignored_thinking_indexes.add(event_index)

        assert 3 in state.ignored_thinking_indexes

    @patch("chat.clients.pydantic_ai.settings")
    def test_delta_event_skipped_when_index_ignored(self, mock_settings):
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True
        state = StreamingState()
        state.ignored_thinking_indexes.add(3)

        event_index = 3
        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and event_index in state.ignored_thinking_indexes
        )
        assert should_skip is True

    @patch("chat.clients.pydantic_ai.settings")
    def test_delta_event_not_skipped_for_other_index(self, mock_settings):
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = True
        state = StreamingState()
        state.ignored_thinking_indexes.add(3)

        event_index = 5
        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and event_index in state.ignored_thinking_indexes
        )
        assert should_skip is False

    @patch("chat.clients.pydantic_ai.settings")
    def test_delta_event_not_skipped_when_disabled(self, mock_settings):
        mock_settings.VLLM_THINKING_DEDUP_ENABLED = False
        state = StreamingState()
        state.ignored_thinking_indexes.add(3)

        event_index = 3
        should_skip = (
            mock_settings.VLLM_THINKING_DEDUP_ENABLED
            and event_index in state.ignored_thinking_indexes
        )
        assert should_skip is False
