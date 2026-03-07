"""Tests for streaming cancel event lifecycle — Feature 5: Streaming Cancel Event."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from chat.clients import pydantic_ai as pai_module
from chat.clients.pydantic_ai import AIAgentService


@pytest.fixture()
def service():
    """AIAgentService with mocked __init__ and a fake conversation."""
    with patch.object(AIAgentService, "__init__", return_value=None):
        svc = AIAgentService()
        svc.conversation = MagicMock()
        svc.conversation.pk = "conv-123"
        svc.conversation.id = "conv-123"
        return svc


@pytest.fixture(autouse=True)
def _clear_cancel_events():
    """Ensure the global dict is clean between tests."""
    pai_module._cancel_events.clear()
    yield
    pai_module._cancel_events.clear()


# ------------------------------------------------------------------ #
# _stop_cache_key
# ------------------------------------------------------------------ #
class TestStopCacheKey:
    def test_key_format(self, service):
        assert service._stop_cache_key == "streaming:stop:conv-123"


# ------------------------------------------------------------------ #
# _get_or_create_cancel_event
# ------------------------------------------------------------------ #
class TestGetOrCreateCancelEvent:
    def test_creates_event_when_missing(self, service):
        event = service._get_or_create_cancel_event()
        assert isinstance(event, threading.Event)
        assert "conv-123" in pai_module._cancel_events

    def test_returns_same_event_on_second_call(self, service):
        e1 = service._get_or_create_cancel_event()
        e2 = service._get_or_create_cancel_event()
        assert e1 is e2

    def test_different_conversations_get_different_events(self, service):
        e1 = service._get_or_create_cancel_event()

        service.conversation.pk = "conv-456"
        e2 = service._get_or_create_cancel_event()

        assert e1 is not e2


# ------------------------------------------------------------------ #
# _cleanup_cancel_event
# ------------------------------------------------------------------ #
class TestCleanupCancelEvent:
    def test_removes_event(self, service):
        service._get_or_create_cancel_event()
        assert "conv-123" in pai_module._cancel_events

        service._cleanup_cancel_event()
        assert "conv-123" not in pai_module._cancel_events

    def test_cleanup_when_not_present_is_noop(self, service):
        service._cleanup_cancel_event()  # should not raise


# ------------------------------------------------------------------ #
# stop_streaming
# ------------------------------------------------------------------ #
class TestStopStreaming:
    @patch("chat.clients.pydantic_ai.cache")
    @patch("chat.clients.pydantic_ai.settings")
    def test_sets_cache_key(self, mock_settings, mock_cache, service):
        mock_settings.STREAMING_CANCEL_EVENT_ENABLED = False
        service.stop_streaming()
        mock_cache.set.assert_called_once()

    @patch("chat.clients.pydantic_ai.cache")
    @patch("chat.clients.pydantic_ai.settings")
    def test_triggers_cancel_event_when_enabled(self, mock_settings, mock_cache, service):
        mock_settings.STREAMING_CANCEL_EVENT_ENABLED = True

        event = service._get_or_create_cancel_event()
        assert not event.is_set()

        service.stop_streaming()
        assert event.is_set()

    @patch("chat.clients.pydantic_ai.cache")
    @patch("chat.clients.pydantic_ai.settings")
    def test_no_error_if_no_event_when_enabled(self, mock_settings, mock_cache, service):
        mock_settings.STREAMING_CANCEL_EVENT_ENABLED = True
        # No event created, stop_streaming should not raise
        service.stop_streaming()


# ------------------------------------------------------------------ #
# Thread safety
# ------------------------------------------------------------------ #
class TestThreadSafety:
    def test_concurrent_get_or_create(self, service):
        """Multiple threads calling _get_or_create_cancel_event should all get the same Event."""
        results = []

        def worker():
            results.append(service._get_or_create_cancel_event())

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is results[0] for r in results)
