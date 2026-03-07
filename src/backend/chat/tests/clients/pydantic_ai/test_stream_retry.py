"""Tests for stream retry logic — Feature 2: Stream Retry."""

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat.clients.pydantic_ai import AIAgentService


@pytest.fixture()
def service():
    """Return an AIAgentService with __init__ bypassed."""
    with patch.object(AIAgentService, "__init__", return_value=None):
        svc = AIAgentService()
        svc._langfuse_available = False
        svc._clean = AsyncMock()
        return svc


def _identity_encoder(event):
    """Pass-through encoder for testing."""
    return event


# ------------------------------------------------------------------ #
# max_retries <= 0  →  no retry (original behaviour)
# ------------------------------------------------------------------ #
class TestStreamContentNoRetry:
    """When STREAM_RETRY_MAX_ATTEMPTS <= 0, _stream_content runs once with no retry."""

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.settings")
    async def test_single_pass_when_retries_zero(self, mock_settings, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 0

        events = ["chunk1", "chunk2"]

        async def fake_run_agent(*_a, **_kw):
            for e in events:
                yield e

        service._run_agent = fake_run_agent

        result = []
        async for chunk in service._stream_content([], encoder_fn=_identity_encoder):
            result.append(chunk)

        assert result == events

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.settings")
    async def test_error_propagates_when_retries_zero(self, mock_settings, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 0

        async def failing_agent(*_a, **_kw):
            raise RuntimeError("boom")
            yield  # noqa: E501 – make it an async generator

        service._run_agent = failing_agent

        with pytest.raises(RuntimeError, match="boom"):
            async for _ in service._stream_content([], encoder_fn=_identity_encoder):
                pass


# ------------------------------------------------------------------ #
# max_retries > 0  →  retry on transient errors
# ------------------------------------------------------------------ #
class TestStreamContentRetry:
    """When STREAM_RETRY_MAX_ATTEMPTS > 0, transient errors trigger retries."""

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.asyncio.sleep", new_callable=AsyncMock)
    @patch("chat.clients.pydantic_ai.settings")
    async def test_succeeds_on_second_attempt(self, mock_settings, mock_sleep, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 3
        call_count = 0

        async def flaky_agent(*_a, **_kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient")
            yield "ok"

        service._run_agent = flaky_agent

        result = []
        async for chunk in service._stream_content([], encoder_fn=_identity_encoder):
            result.append(chunk)

        assert "ok" in result
        assert call_count == 2

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.asyncio.sleep", new_callable=AsyncMock)
    @patch("chat.clients.pydantic_ai.settings")
    async def test_all_retries_exhausted_yields_error(self, mock_settings, mock_sleep, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 2

        async def always_fail(*_a, **_kw):
            raise RuntimeError("persistent")
            yield  # noqa: E501

        service._run_agent = always_fail

        result = []
        async for chunk in service._stream_content([], encoder_fn=_identity_encoder):
            result.append(chunk)

        # Should contain the technical error message
        assert any("Technical error" in str(c) for c in result if c)

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.asyncio.sleep", new_callable=AsyncMock)
    @patch("chat.clients.pydantic_ai.settings")
    async def test_clean_called_between_retries(self, mock_settings, mock_sleep, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 3
        call_count = 0

        async def flaky_agent(*_a, **_kw):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("retry me")
            yield "done"

        service._run_agent = flaky_agent

        async for _ in service._stream_content([], encoder_fn=_identity_encoder):
            pass

        # _clean is called once at start + once per retry
        assert service._clean.call_count >= 3

    @pytest.mark.asyncio
    @patch("chat.clients.pydantic_ai.asyncio.sleep", new_callable=AsyncMock)
    @patch("chat.clients.pydantic_ai.settings")
    async def test_sleep_called_with_backoff(self, mock_settings, mock_sleep, service):
        mock_settings.STREAM_RETRY_MAX_ATTEMPTS = 3

        async def always_fail(*_a, **_kw):
            raise RuntimeError("fail")
            yield  # noqa: E501

        service._run_agent = always_fail

        async for _ in service._stream_content([], encoder_fn=_identity_encoder):
            pass

        # Should have slept between attempts
        assert mock_sleep.call_count >= 1
