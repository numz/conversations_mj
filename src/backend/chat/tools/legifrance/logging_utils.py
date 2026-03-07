"""Structured logging utilities for Legifrance API.

This module provides structured logging with:
- Request duration tracking
- Request ID for distributed tracing
- Contextual information (fond, query, article_id)
- Performance metrics collection
- Langfuse integration for unified observability (when enabled)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Generator, TypeVar

from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Langfuse Integration
# =============================================================================


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled in settings."""
    return getattr(settings, "LANGFUSE_ENABLED", False)


def _get_langfuse_client():
    """Get Langfuse client if available."""
    if not is_langfuse_enabled():
        return None
    try:
        from langfuse import get_client

        return get_client()
    except ImportError:
        logger.debug("Langfuse not installed, skipping integration")
        return None
    except Exception as e:
        logger.warning("Failed to get Langfuse client: %s", e)
        return None


# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Request Context
# =============================================================================


@dataclass
class RequestContext:
    """Context information for a Legifrance API request."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operation: str = ""
    fond: str = ""
    query: str = ""
    article_id: str = ""
    cache_hit: bool = False
    start_time: float = field(default_factory=time.perf_counter)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        return (time.perf_counter() - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        data: dict[str, Any] = {
            "request_id": self.request_id,
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 2),
        }

        if self.fond:
            data["fond"] = self.fond
        if self.query:
            data["query"] = self.query[:100]  # Truncate long queries
        if self.article_id:
            data["article_id"] = self.article_id
        if self.cache_hit:
            data["cache_hit"] = self.cache_hit
        if self.extra:
            data.update(self.extra)

        return data


# =============================================================================
# Structured Logger
# =============================================================================


class StructuredLogger:
    """Logger with structured context support."""

    def __init__(self, name: str = "legifrance"):
        """Initialize structured logger."""
        self.logger = logging.getLogger(f"chat.tools.legifrance.{name}")
        self._context: RequestContext | None = None

    def set_context(self, context: RequestContext) -> None:
        """Set the current request context."""
        self._context = context

    def clear_context(self) -> None:
        """Clear the current request context."""
        self._context = None

    def _format_message(self, message: str, **kwargs: Any) -> str:
        """Format message with context."""
        if self._context:
            ctx_dict = self._context.to_dict()
            ctx_dict.update(kwargs)
            ctx_str = " ".join(f"{k}={v}" for k, v in ctx_dict.items())
            return f"[{ctx_str}] {message}"
        elif kwargs:
            ctx_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"[{ctx_str}] {message}"
        return message

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self.logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self.logger.error(self._format_message(message, **kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with context."""
        self.logger.exception(self._format_message(message, **kwargs))


# Global structured logger instance
slog = StructuredLogger()


# =============================================================================
# Context Manager for Request Tracking
# =============================================================================


@contextmanager
def track_request(
    operation: str,
    fond: str = "",
    query: str = "",
    article_id: str = "",
    **extra: Any,
) -> Generator[RequestContext, None, None]:
    """Context manager for tracking API request duration and context.

    Integrates with Langfuse when enabled, creating spans for distributed tracing.

    Args:
        operation: Name of the operation (e.g., "search", "get_document").
        fond: The document source being queried.
        query: The search query (if applicable).
        article_id: The article ID (if applicable).
        **extra: Additional context to include.

    Yields:
        RequestContext with timing and context information.

    Example:
        with track_request("search", fond="CODE_DATE", query="article 1240") as ctx:
            results = await api.search(...)
            ctx.extra["result_count"] = len(results)
    """
    ctx = RequestContext(
        operation=operation,
        fond=fond,
        query=query,
        article_id=article_id,
        extra=extra,
    )
    slog.set_context(ctx)

    # Langfuse span (if available)
    langfuse = _get_langfuse_client()
    span = None
    span_context = None

    if langfuse:
        try:
            # Build input metadata for Langfuse
            span_input = {"operation": operation}
            if fond:
                span_input["fond"] = fond
            if query:
                span_input["query"] = query[:200]  # Truncate for Langfuse
            if article_id:
                span_input["article_id"] = article_id
            span_input.update(extra)

            span_context = langfuse.start_as_current_span(
                name=f"legifrance.{operation}",
                input=span_input,
            )
            span = span_context.__enter__()
        except Exception as e:
            logger.debug("Failed to create Langfuse span: %s", e)

    try:
        slog.debug(f"Starting {operation}")
        yield ctx

        # Update Langfuse span with success
        if span:
            try:
                output = {"status": "success", "duration_ms": round(ctx.duration_ms, 2)}
                if ctx.cache_hit:
                    output["cache_hit"] = True
                output.update(ctx.extra)
                span.update(output=output, level="DEFAULT")
            except Exception as e:
                logger.debug("Failed to update Langfuse span: %s", e)

        slog.info(f"Completed {operation}", status="success")

    except Exception as e:
        # Update Langfuse span with error
        if span:
            try:
                span.update(
                    output={
                        "status": "error",
                        "error": type(e).__name__,
                        "duration_ms": round(ctx.duration_ms, 2),
                    },
                    level="ERROR",
                )
            except Exception as le:
                logger.debug("Failed to update Langfuse span with error: %s", le)

        slog.error(f"Failed {operation}", status="error", error=type(e).__name__)
        raise

    finally:
        # Close Langfuse span
        if span_context:
            try:
                span_context.__exit__(None, None, None)
            except Exception as e:
                logger.debug("Failed to close Langfuse span: %s", e)

        slog.clear_context()


# =============================================================================
# Performance Metrics
# =============================================================================


@dataclass
class PerformanceMetrics:
    """Collect performance metrics for API calls."""

    _call_counts: dict[str, int] = field(default_factory=dict)
    _total_duration_ms: dict[str, float] = field(default_factory=dict)
    _error_counts: dict[str, int] = field(default_factory=dict)
    _cache_hits: dict[str, int] = field(default_factory=dict)
    _cache_misses: dict[str, int] = field(default_factory=dict)

    def record_call(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        cache_hit: bool = False,
    ) -> None:
        """Record a call with its metrics."""
        self._call_counts[operation] = self._call_counts.get(operation, 0) + 1
        self._total_duration_ms[operation] = self._total_duration_ms.get(operation, 0) + duration_ms

        if not success:
            self._error_counts[operation] = self._error_counts.get(operation, 0) + 1

        if cache_hit:
            self._cache_hits[operation] = self._cache_hits.get(operation, 0) + 1
        else:
            self._cache_misses[operation] = self._cache_misses.get(operation, 0) + 1

    def get_stats(self, operation: str | None = None) -> dict[str, Any]:
        """Get statistics for an operation or all operations."""
        if operation:
            calls = self._call_counts.get(operation, 0)
            total_ms = self._total_duration_ms.get(operation, 0)
            errors = self._error_counts.get(operation, 0)
            hits = self._cache_hits.get(operation, 0)
            misses = self._cache_misses.get(operation, 0)

            return {
                "operation": operation,
                "total_calls": calls,
                "avg_duration_ms": round(total_ms / calls, 2) if calls > 0 else 0,
                "error_count": errors,
                "error_rate_percent": round(errors / calls * 100, 2) if calls > 0 else 0,
                "cache_hit_rate_percent": (
                    round(hits / (hits + misses) * 100, 2) if (hits + misses) > 0 else 0
                ),
            }

        # Return stats for all operations
        return {op: self.get_stats(op) for op in self._call_counts.keys()}

    def reset(self) -> None:
        """Reset all metrics."""
        self._call_counts.clear()
        self._total_duration_ms.clear()
        self._error_counts.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()


# Global metrics instance
metrics = PerformanceMetrics()


# =============================================================================
# Decorator for Automatic Tracking
# =============================================================================


def track_api_call(operation: str) -> Callable[[F], F]:
    """Decorator to automatically track API call duration and metrics.

    Args:
        operation: Name of the operation being tracked.

    Returns:
        Decorated function with automatic tracking.

    Example:
        @track_api_call("search")
        async def search(self, query: str) -> list:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = RequestContext(operation=operation)
            slog.set_context(ctx)

            try:
                slog.debug(f"Starting {operation}")
                result = await func(*args, **kwargs)
                slog.info(f"Completed {operation}", status="success")
                metrics.record_call(
                    operation,
                    ctx.duration_ms,
                    success=True,
                    cache_hit=ctx.cache_hit,
                )
                return result
            except Exception as e:
                slog.error(
                    f"Failed {operation}",
                    status="error",
                    error=type(e).__name__,
                )
                metrics.record_call(operation, ctx.duration_ms, success=False)
                raise
            finally:
                slog.clear_context()

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = RequestContext(operation=operation)
            slog.set_context(ctx)

            try:
                slog.debug(f"Starting {operation}")
                result = func(*args, **kwargs)
                slog.info(f"Completed {operation}", status="success")
                metrics.record_call(
                    operation,
                    ctx.duration_ms,
                    success=True,
                    cache_hit=ctx.cache_hit,
                )
                return result
            except Exception as e:
                slog.error(
                    f"Failed {operation}",
                    status="error",
                    error=type(e).__name__,
                )
                metrics.record_call(operation, ctx.duration_ms, success=False)
                raise
            finally:
                slog.clear_context()

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# =============================================================================
# Utility Functions
# =============================================================================


def log_api_response(
    operation: str,
    duration_ms: float,
    success: bool,
    result_count: int = 0,
    cache_hit: bool = False,
    **extra: Any,
) -> None:
    """Log an API response with structured context.

    Also records a Langfuse event if within an active span.

    Args:
        operation: Name of the operation.
        duration_ms: Duration in milliseconds.
        success: Whether the operation succeeded.
        result_count: Number of results returned.
        cache_hit: Whether result was from cache.
        **extra: Additional context.
    """
    status = "success" if success else "error"
    level = logging.INFO if success else logging.ERROR

    context = {
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "cache_hit": cache_hit,
    }

    if result_count > 0:
        context["result_count"] = result_count

    context.update(extra)

    ctx_str = " ".join(f"{k}={v}" for k, v in context.items())
    message = f"[{ctx_str}] API {operation} {status}"

    logger.log(level, message)

    # Record metrics
    metrics.record_call(operation, duration_ms, success, cache_hit)

    # Record Langfuse event (if within an active span)
    langfuse = _get_langfuse_client()
    if langfuse:
        try:
            langfuse.event(
                name=f"legifrance.{operation}.response",
                metadata=context,
                level="DEFAULT" if success else "ERROR",
            )
        except Exception as e:
            logger.debug("Failed to record Langfuse event: %s", e)
