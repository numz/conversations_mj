"""
Helpers to manage async objects in a synchronous context.

This is not optimal, but we would prefer to stay in a synchronous context
for now.
"""

import asyncio
import logging
import queue
import threading

from django.db import close_old_connections

from chat.clients.exceptions import StreamCancelException

logger = logging.getLogger(__name__)


def convert_async_generator_to_sync(async_gen, cancel_event: threading.Event = None):
    """Convert an async generator to a sync generator.

    Args:
        async_gen: The async generator to convert.
        cancel_event: Optional threading.Event that, when set, will cancel the async task
                      and close the HTTP connection to the LLM.
    """
    q = queue.Queue()
    sentinel = object()
    exc_sentinel = object()

    if cancel_event is None:
        # Original behavior: simple asyncio.run without cancellation support
        async def run_async_gen():
            try:
                async for async_item in async_gen:
                    q.put(async_item)
            except StreamCancelException:
                q.put(sentinel)
            except Exception as exc:  # pylint: disable=broad-except #noqa: BLE001
                q.put((exc_sentinel, exc))
            finally:
                q.put(sentinel)

        def start_async_loop():
            asyncio.run(run_async_gen())

        thread = threading.Thread(target=start_async_loop, daemon=True)
        thread.start()

        try:
            while True:
                item = q.get()
                if item is sentinel:
                    break
                if isinstance(item, tuple) and item[0] is exc_sentinel:
                    raise item[1]
                yield item
        finally:
            thread.join()

    else:
        # Cancel event mode: supports asyncio task cancellation to close
        # the HTTP connection to the LLM immediately on stop.
        loop_holder = {"loop": None, "task": None}

        async def run_async_gen_cancellable():
            try:
                async for async_item in async_gen:
                    q.put(async_item)
            except asyncio.CancelledError:
                logger.info("Async task cancelled - HTTP connection closed")
                q.put(sentinel)
            except StreamCancelException:
                q.put(sentinel)
            except Exception as exc:  # pylint: disable=broad-except #noqa: BLE001
                q.put((exc_sentinel, exc))
            finally:
                q.put(sentinel)

        def start_async_loop_cancellable():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_holder["loop"] = loop

            task = loop.create_task(run_async_gen_cancellable())
            loop_holder["task"] = task

            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                logger.info("Event loop task cancelled")
            finally:
                loop.close()
                close_old_connections()

        def cancel_checker():
            """Monitor cancel_event and cancel the async task when triggered."""
            while not cancel_event.wait(timeout=0.5):
                if loop_holder["task"] is not None and loop_holder["task"].done():
                    return
            # Cancel event was set
            if loop_holder["loop"] and loop_holder["task"] and not loop_holder["task"].done():
                logger.info("Cancel event triggered - cancelling async task")
                loop_holder["loop"].call_soon_threadsafe(loop_holder["task"].cancel)

        thread = threading.Thread(target=start_async_loop_cancellable, daemon=True)
        thread.start()

        cancel_thread = threading.Thread(target=cancel_checker, daemon=True)
        cancel_thread.start()

        try:
            while True:
                item = q.get()
                if item is sentinel:
                    break
                if isinstance(item, tuple) and item[0] is exc_sentinel:
                    raise item[1]
                yield item
        finally:
            cancel_event.set()
            thread.join(timeout=5.0)
            cancel_thread.join(timeout=1.0)
