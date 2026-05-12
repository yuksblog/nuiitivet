from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable
from typing import Any, Callable, Optional, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import detach_batch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared type aliases for user-facing event handler parameters.
# Each alias accepts both a synchronous and an async callable so that
# users can write either ``def on_click(): ...`` or
# ``async def on_click(): ...`` without mypy errors.
# ---------------------------------------------------------------------------

#: No-arg, fire-and-forget callback (e.g. on_click).
VoidCallback = Union[Callable[[], None], Callable[[], Awaitable[None]]]
#: Single ``bool`` argument callback (e.g. on_hover, on_focus_change).
BoolCallback = Union[Callable[[bool], None], Callable[[bool], Awaitable[None]]]
#: Optional ``bool`` argument callback (e.g. on_change for tristate toggles).
OptionalBoolCallback = Union[
    Callable[[Optional[bool]], None],
    Callable[[Optional[bool]], Awaitable[None]],
]
#: Single ``str`` argument callback (e.g. on_change for text inputs).
StrCallback = Union[Callable[[str], None], Callable[[str], Awaitable[None]]]


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
