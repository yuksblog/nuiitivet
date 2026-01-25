from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import detach_batch

logger = logging.getLogger(__name__)


def invoke_event_handler(
    cb: Callable[..., Any],
    *args: Any,
    error_key: str,
    error_msg: str,
    owner_name: str = "<unknown>",
) -> None:
    """Invoke an event handler, scheduling it as a task if it is async.

    This helper handles:
    1. Synchronous execution.
    2. Asynchronous execution (scheduling as task).
    3. Detaching from the current batch context for async tasks.
    4. Error logging.
    """
    try:
        result = cb(*args)
        if inspect.isawaitable(result):

            async def _wrapper():
                # Async tasks should not inherit the synchronous batch context
                # because the batch will likely exit before the task completes.
                detach_batch()
                try:
                    await result
                except Exception:
                    exception_once(
                        logger,
                        f"async_{error_key}_exc:{owner_name}",
                        f"Async {error_msg} (owner=%s)",
                        owner_name,
                    )

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_wrapper())
            except RuntimeError:
                # Event loop might not be running (e.g. during tests or shutdown)
                pass
    except Exception:
        exception_once(
            logger,
            f"{error_key}_exc:{owner_name}",
            f"{error_msg} (owner=%s)",
            owner_name,
        )
