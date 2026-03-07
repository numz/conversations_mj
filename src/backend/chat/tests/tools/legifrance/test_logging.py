"""Tests for Legifrance logging utilities."""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from chat.tools.legifrance.logging_utils import (
    PerformanceMetrics,
    RequestContext,
    StructuredLogger,
    _get_langfuse_client,
    is_langfuse_enabled,
    log_api_response,
    metrics,
    slog,
    track_api_call,
    track_request,
)


class TestRequestContext:
    """Test RequestContext dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        ctx = RequestContext()

        assert ctx.request_id  # Should have a generated ID
        assert len(ctx.request_id) == 8
        assert ctx.operation == ""
        assert ctx.fond == ""
        assert ctx.query == ""
        assert ctx.article_id == ""
        assert ctx.cache_hit is False
        assert ctx.start_time > 0

    def test_custom_values(self):
        """Test custom values are set correctly."""
        ctx = RequestContext(
            operation="search",
            fond="CODE_DATE",
            query="article 1240",
            article_id="LEGIARTI000001",
            cache_hit=True,
        )

        assert ctx.operation == "search"
        assert ctx.fond == "CODE_DATE"
        assert ctx.query == "article 1240"
        assert ctx.article_id == "LEGIARTI000001"
        assert ctx.cache_hit is True

    def test_duration_ms(self):
        """Test duration calculation."""
        ctx = RequestContext()
        time.sleep(0.01)  # 10ms

        duration = ctx.duration_ms
        assert duration >= 10  # At least 10ms
        assert duration < 100  # Less than 100ms (reasonable margin)

    def test_to_dict_basic(self):
        """Test to_dict with basic fields."""
        ctx = RequestContext(operation="search")

        data = ctx.to_dict()

        assert "request_id" in data
        assert data["operation"] == "search"
        assert "duration_ms" in data
        assert isinstance(data["duration_ms"], float)

    def test_to_dict_with_optional_fields(self):
        """Test to_dict includes optional fields when set."""
        ctx = RequestContext(
            operation="search",
            fond="CODE_DATE",
            query="test query that is very long" * 5,  # Long query
            article_id="LEGIARTI000001",
            cache_hit=True,
        )

        data = ctx.to_dict()

        assert data["fond"] == "CODE_DATE"
        assert len(data["query"]) <= 100  # Truncated
        assert data["article_id"] == "LEGIARTI000001"
        assert data["cache_hit"] is True

    def test_to_dict_excludes_empty_optional(self):
        """Test to_dict excludes empty optional fields."""
        ctx = RequestContext(operation="search")

        data = ctx.to_dict()

        assert "fond" not in data
        assert "query" not in data
        assert "article_id" not in data
        assert "cache_hit" not in data  # False is excluded

    def test_to_dict_with_extra(self):
        """Test to_dict includes extra fields."""
        ctx = RequestContext(operation="search")
        ctx.extra["result_count"] = 10
        ctx.extra["page"] = 2

        data = ctx.to_dict()

        assert data["result_count"] == 10
        assert data["page"] == 2


class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_init(self):
        """Test logger initialization."""
        logger = StructuredLogger("test")

        assert logger.logger.name == "chat.tools.legifrance.test"
        assert logger._context is None

    def test_set_and_clear_context(self):
        """Test setting and clearing context."""
        logger = StructuredLogger()
        ctx = RequestContext(operation="test")

        logger.set_context(ctx)
        assert logger._context is ctx

        logger.clear_context()
        assert logger._context is None

    def test_format_message_no_context(self):
        """Test message formatting without context."""
        logger = StructuredLogger()

        message = logger._format_message("Test message")
        assert message == "Test message"

    def test_format_message_with_context(self):
        """Test message formatting with context."""
        logger = StructuredLogger()
        ctx = RequestContext(operation="search")
        logger.set_context(ctx)

        message = logger._format_message("Test message")

        assert "request_id=" in message
        assert "operation=search" in message
        assert "Test message" in message

    def test_format_message_with_kwargs(self):
        """Test message formatting with additional kwargs."""
        logger = StructuredLogger()

        message = logger._format_message("Test", key="value")

        assert "[key=value]" in message
        assert "Test" in message

    def test_log_methods(self, caplog):
        """Test all log methods work."""
        logger = StructuredLogger("test_methods")

        with caplog.at_level(logging.DEBUG):
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")

        assert "debug message" in caplog.text
        assert "info message" in caplog.text
        assert "warning message" in caplog.text
        assert "error message" in caplog.text


class TestTrackRequest:
    """Test track_request context manager."""

    def test_basic_usage(self):
        """Test basic context manager usage."""
        with track_request("test_operation") as ctx:
            assert ctx.operation == "test_operation"
            assert ctx.request_id

        # After exit, context should be complete
        assert ctx.duration_ms > 0

    def test_with_parameters(self):
        """Test context manager with parameters."""
        with track_request(
            "search",
            fond="CODE_DATE",
            query="test",
            article_id="LEGIARTI000001",
        ) as ctx:
            assert ctx.operation == "search"
            assert ctx.fond == "CODE_DATE"
            assert ctx.query == "test"
            assert ctx.article_id == "LEGIARTI000001"

    def test_with_extra_kwargs(self):
        """Test context manager with extra kwargs."""
        with track_request("search", page=2, custom_key="value") as ctx:
            assert ctx.extra["page"] == 2
            assert ctx.extra["custom_key"] == "value"

    def test_modify_context(self):
        """Test modifying context during execution."""
        with track_request("search") as ctx:
            ctx.extra["result_count"] = 5
            ctx.cache_hit = True

        assert ctx.extra["result_count"] == 5
        assert ctx.cache_hit is True

    def test_exception_handling(self):
        """Test context manager handles exceptions."""
        with pytest.raises(ValueError):
            with track_request("failing_operation"):
                raise ValueError("Test error")

    def test_sets_and_clears_global_logger(self):
        """Test global logger context is set and cleared."""
        assert slog._context is None

        with track_request("test"):
            assert slog._context is not None
            assert slog._context.operation == "test"

        assert slog._context is None


class TestPerformanceMetrics:
    """Test PerformanceMetrics class."""

    def test_record_call_success(self):
        """Test recording successful calls."""
        metrics = PerformanceMetrics()
        metrics.record_call("search", 100.0, success=True)
        metrics.record_call("search", 150.0, success=True)

        stats = metrics.get_stats("search")

        assert stats["total_calls"] == 2
        assert stats["avg_duration_ms"] == 125.0
        assert stats["error_count"] == 0
        assert stats["error_rate_percent"] == 0

    def test_record_call_failure(self):
        """Test recording failed calls."""
        metrics = PerformanceMetrics()
        metrics.record_call("search", 100.0, success=True)
        metrics.record_call("search", 50.0, success=False)

        stats = metrics.get_stats("search")

        assert stats["total_calls"] == 2
        assert stats["error_count"] == 1
        assert stats["error_rate_percent"] == 50.0

    def test_record_cache_hits(self):
        """Test recording cache hits and misses."""
        metrics = PerformanceMetrics()
        metrics.record_call("get_document", 10.0, cache_hit=True)
        metrics.record_call("get_document", 100.0, cache_hit=False)
        metrics.record_call("get_document", 5.0, cache_hit=True)

        stats = metrics.get_stats("get_document")

        assert stats["cache_hit_rate_percent"] == pytest.approx(66.67, rel=0.1)

    def test_get_stats_unknown_operation(self):
        """Test getting stats for unknown operation."""
        metrics = PerformanceMetrics()

        stats = metrics.get_stats("unknown")

        assert stats["total_calls"] == 0
        assert stats["avg_duration_ms"] == 0
        assert stats["error_rate_percent"] == 0
        assert stats["cache_hit_rate_percent"] == 0

    def test_get_all_stats(self):
        """Test getting stats for all operations."""
        metrics = PerformanceMetrics()
        metrics.record_call("search", 100.0)
        metrics.record_call("get_document", 50.0)

        all_stats = metrics.get_stats()

        assert "search" in all_stats
        assert "get_document" in all_stats

    def test_reset(self):
        """Test resetting metrics."""
        metrics = PerformanceMetrics()
        metrics.record_call("search", 100.0)
        metrics.record_call("search", 50.0, success=False)

        metrics.reset()

        stats = metrics.get_stats("search")
        assert stats["total_calls"] == 0


class TestTrackApiCallDecorator:
    """Test track_api_call decorator."""

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test decorator on async function."""

        @track_api_call("test_async")
        async def async_func():
            return "result"

        result = await async_func()

        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_exception(self):
        """Test decorator handles exceptions in async functions."""

        @track_api_call("test_async_error")
        async def async_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await async_func()

    def test_sync_function(self):
        """Test decorator on sync function."""

        @track_api_call("test_sync")
        def sync_func():
            return "result"

        result = sync_func()

        assert result == "result"

    def test_sync_function_exception(self):
        """Test decorator handles exceptions in sync functions."""

        @track_api_call("test_sync_error")
        def sync_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            sync_func()


class TestLogApiResponse:
    """Test log_api_response utility function."""

    def test_success_logging(self, caplog):
        """Test logging successful response."""
        with caplog.at_level(logging.INFO):
            log_api_response("search", 150.0, True, result_count=10)

        assert "search" in caplog.text
        assert "success" in caplog.text

    def test_error_logging(self, caplog):
        """Test logging error response."""
        with caplog.at_level(logging.ERROR):
            log_api_response("search", 50.0, False)

        assert "error" in caplog.text

    def test_with_cache_hit(self, caplog):
        """Test logging with cache hit."""
        with caplog.at_level(logging.INFO):
            log_api_response("get_document", 5.0, True, cache_hit=True)

        assert "cache_hit=True" in caplog.text

    def test_with_extra_fields(self, caplog):
        """Test logging with extra fields."""
        with caplog.at_level(logging.INFO):
            log_api_response("search", 100.0, True, fond="CODE_DATE", custom_field="value")

        assert "fond=CODE_DATE" in caplog.text
        assert "custom_field=value" in caplog.text

    def test_records_metrics(self):
        """Test that log_api_response records metrics."""
        # Reset global metrics
        metrics.reset()

        log_api_response("test_operation", 100.0, True)

        stats = metrics.get_stats("test_operation")
        assert stats["total_calls"] == 1


class TestGlobalInstances:
    """Test global logger and metrics instances."""

    def test_slog_is_structured_logger(self):
        """Test slog is a StructuredLogger instance."""
        assert isinstance(slog, StructuredLogger)

    def test_metrics_is_performance_metrics(self):
        """Test metrics is a PerformanceMetrics instance."""
        assert isinstance(metrics, PerformanceMetrics)


class TestLangfuseIntegration:
    """Test Langfuse integration."""

    def test_is_langfuse_enabled_default(self, settings):
        """Test Langfuse is disabled by default."""
        if hasattr(settings, "LANGFUSE_ENABLED"):
            delattr(settings, "LANGFUSE_ENABLED")
        assert is_langfuse_enabled() is False

    def test_is_langfuse_enabled_true(self, settings):
        """Test Langfuse enabled setting."""
        settings.LANGFUSE_ENABLED = True
        assert is_langfuse_enabled() is True
        settings.LANGFUSE_ENABLED = False

    def test_get_langfuse_client_disabled(self, settings):
        """Test get client returns None when disabled."""
        settings.LANGFUSE_ENABLED = False
        assert _get_langfuse_client() is None

    def test_get_langfuse_client_import_error(self, settings):
        """Test get client handles import error gracefully."""
        settings.LANGFUSE_ENABLED = True

        with patch.dict("sys.modules", {"langfuse": None}):
            with patch(
                "chat.tools.legifrance.logging_utils.is_langfuse_enabled",
                return_value=True,
            ):
                # Should not raise, just return None
                result = _get_langfuse_client()
                # Result depends on actual langfuse availability

        settings.LANGFUSE_ENABLED = False

    def test_track_request_with_langfuse(self, settings):
        """Test track_request creates Langfuse span when enabled."""
        settings.LANGFUSE_ENABLED = True

        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)

        mock_client = MagicMock()
        mock_client.start_as_current_span.return_value = mock_span_context

        with patch(
            "chat.tools.legifrance.logging_utils._get_langfuse_client",
            return_value=mock_client,
        ):
            with track_request("search", fond="CODE_DATE", query="test") as ctx:
                ctx.extra["result_count"] = 5

        # Verify span was created with correct parameters
        mock_client.start_as_current_span.assert_called_once()
        call_kwargs = mock_client.start_as_current_span.call_args
        assert "legifrance.search" in str(call_kwargs)

        # Verify span was updated with success
        mock_span.update.assert_called()

        # Verify span was closed
        mock_span_context.__exit__.assert_called_once()

        settings.LANGFUSE_ENABLED = False

    def test_track_request_with_langfuse_error(self, settings):
        """Test track_request updates Langfuse span on error."""
        settings.LANGFUSE_ENABLED = True

        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)

        mock_client = MagicMock()
        mock_client.start_as_current_span.return_value = mock_span_context

        with patch(
            "chat.tools.legifrance.logging_utils._get_langfuse_client",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError):
                with track_request("search") as ctx:
                    raise ValueError("Test error")

        # Verify span was updated with error level
        update_calls = mock_span.update.call_args_list
        assert len(update_calls) > 0
        last_call = update_calls[-1]
        assert last_call.kwargs.get("level") == "ERROR"

        settings.LANGFUSE_ENABLED = False

    def test_track_request_without_langfuse(self, settings):
        """Test track_request works normally without Langfuse."""
        settings.LANGFUSE_ENABLED = False

        with track_request("search", fond="CODE_DATE") as ctx:
            ctx.extra["result_count"] = 3

        assert ctx.operation == "search"
        assert ctx.fond == "CODE_DATE"
        assert ctx.extra["result_count"] == 3

    def test_log_api_response_with_langfuse(self, settings):
        """Test log_api_response records Langfuse event."""
        settings.LANGFUSE_ENABLED = True

        mock_client = MagicMock()

        with patch(
            "chat.tools.legifrance.logging_utils._get_langfuse_client",
            return_value=mock_client,
        ):
            log_api_response("search", 150.0, True, result_count=10)

        # Verify event was recorded
        mock_client.event.assert_called_once()
        call_kwargs = mock_client.event.call_args
        assert "legifrance.search.response" in str(call_kwargs)

        settings.LANGFUSE_ENABLED = False

    def test_log_api_response_langfuse_error_level(self, settings):
        """Test log_api_response uses ERROR level for failures."""
        settings.LANGFUSE_ENABLED = True

        mock_client = MagicMock()

        with patch(
            "chat.tools.legifrance.logging_utils._get_langfuse_client",
            return_value=mock_client,
        ):
            log_api_response("search", 50.0, False)

        call_kwargs = mock_client.event.call_args
        assert call_kwargs.kwargs.get("level") == "ERROR"

        settings.LANGFUSE_ENABLED = False

    def test_langfuse_span_includes_cache_hit(self, settings):
        """Test Langfuse span output includes cache_hit."""
        settings.LANGFUSE_ENABLED = True

        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)

        mock_client = MagicMock()
        mock_client.start_as_current_span.return_value = mock_span_context

        with patch(
            "chat.tools.legifrance.logging_utils._get_langfuse_client",
            return_value=mock_client,
        ):
            with track_request("get_document", article_id="LEGIARTI000001") as ctx:
                ctx.cache_hit = True

        # Verify cache_hit is in the output
        update_call = mock_span.update.call_args
        output = update_call.kwargs.get("output", {})
        assert output.get("cache_hit") is True

        settings.LANGFUSE_ENABLED = False
