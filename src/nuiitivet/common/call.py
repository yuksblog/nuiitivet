from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def safe_call(
    fn: Callable[..., T] | Any,
    *args,
    default: Optional[T] = None,
    exc_msg: Optional[str] = None,
) -> Optional[T]:
    """Call fn(*args) and on exception log a consistent message and return default.

    If fn is not callable, it will be returned as-is (useful for passing
    attribute values). exc_msg may be provided to give context in logs.
    """
    try:
        return fn(*args) if callable(fn) else fn
    except Exception:
        logger.exception(exc_msg or "error in safe_call")
    return default
