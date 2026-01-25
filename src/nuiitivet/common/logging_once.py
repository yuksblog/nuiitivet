"""Log helpers that emit at most once per process.

These helpers are intended for backend and integration code paths where
fallbacks may happen repeatedly and log spam should be avoided.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from typing import OrderedDict as OrderedDictType


_MAX_LOG_ONCE_KEYS = 1024
_LOG_ONCE_KEYS: OrderedDictType[str, None] = OrderedDict()
_LOCK = threading.Lock()


def _should_log_once(key: str) -> bool:
    with _LOCK:
        if key in _LOG_ONCE_KEYS:
            return False
        _LOG_ONCE_KEYS[key] = None
        if len(_LOG_ONCE_KEYS) > _MAX_LOG_ONCE_KEYS:
            try:
                _LOG_ONCE_KEYS.popitem(last=False)
            except Exception:
                _LOG_ONCE_KEYS.clear()
        return True


def debug_once(logger: logging.Logger, key: str, msg: str, *args: object) -> None:
    """Log a DEBUG message once per process for the given key."""

    if not _should_log_once(key):
        return
    try:
        logger.debug(msg, *args)
    except Exception:
        # Logging must never raise.
        return


def exception_once(logger: logging.Logger, key: str, msg: str, *args: object) -> None:
    """Log an exception once per process for the given key."""

    if not _should_log_once(key):
        return
    try:
        logger.exception(msg, *args)
    except Exception:
        return


def _clear_log_once_keys_for_tests() -> None:
    """Clear internal log-once keys (tests only)."""

    with _LOCK:
        try:
            _LOG_ONCE_KEYS.clear()
        except Exception:
            return
