"""Log helpers that emit at most once per process.

These helpers are intended for backend and integration code paths where
fallbacks may happen repeatedly and log spam should be avoided.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections import OrderedDict
from typing import OrderedDict as OrderedDictType


_MAX_LOG_ONCE_KEYS = 1024
_LOG_ONCE_KEYS: OrderedDictType[str, None] = OrderedDict()
_LOCK = threading.Lock()

# Global kill-switch for the once-per-process de-duplication. When ``False``,
# every ``*_once`` call emits, regardless of how many times its key was seen.
#
# The dev runner flips this off to run the runtime log in *verbose* mode: the
# dev bridge captures framework log output through a ``logging.Handler``, and a
# suppressed record never reaches any handler, so disabling the de-dup is exactly
# how "show me every occurrence, not just the first" is expressed. Left on by
# default so ordinary runs (and production) keep the anti-spam behaviour. A plain
# module global -- a torn read/write of a bool is harmless for a debug toggle, so
# it is deliberately not lock-guarded on the hot read path.
_LOG_ONCE_ENABLED = True


def set_log_once_enabled(enabled: bool) -> None:
    """Enable or disable once-per-process de-duplication for all ``*_once`` helpers.

    Disabling makes every subsequent ``debug_once`` / ``warning_once`` /
    ``exception_once`` call emit unconditionally (the recorded keys are ignored
    and not extended while disabled). Re-enabling resumes de-duplication from a
    clean slate for keys seen only while disabled.
    """
    global _LOG_ONCE_ENABLED
    _LOG_ONCE_ENABLED = bool(enabled)


def is_log_once_enabled() -> bool:
    """Return whether once-per-process de-duplication is currently active."""
    return _LOG_ONCE_ENABLED


def _should_log_once(key: str) -> bool:
    # When disabled, every call emits and no key is recorded -- so flipping back
    # on later does not spuriously suppress a first, real occurrence.
    if not _LOG_ONCE_ENABLED:
        return True
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


def _current_exc_signature() -> str:
    """Signature of the exception currently being handled: ``Type@file:line``.

    Uses the *innermost* traceback frame so that two failures of the same kind
    from the same place collapse to one key, while a different exception type --
    or the same type raised at a new location after a hot-reload edit -- yields a
    fresh key and is surfaced again. Returns ``"noexc"`` outside an ``except``.
    """
    exc_type, _exc, tb = sys.exc_info()
    if exc_type is None:
        return "noexc"
    filename: str = "?"
    lineno: int = 0
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        lineno = tb.tb_lineno
        tb = tb.tb_next
    return f"{exc_type.__name__}@{filename}:{lineno}"


def debug_once(logger: logging.Logger, key: str, msg: str, *args: object) -> None:
    """Log a DEBUG message once per process for the given key."""

    if not _should_log_once(key):
        return
    try:
        logger.debug(msg, *args)
    except Exception:
        # Logging must never raise.
        return


def warning_once(logger: logging.Logger, key: str, msg: str, *args: object) -> None:
    """Log a WARNING message once per process for the given key."""

    if not _should_log_once(key):
        return
    try:
        logger.warning(msg, *args)
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


def exception_once_per_exc(
    logger: logging.Logger, prefix: str, msg: str, *args: object
) -> None:
    """Log an exception once per *distinct* failure at a call site.

    Like :func:`exception_once`, but the de-dup key is ``prefix`` combined with
    the current exception's signature (type + innermost frame). A callback that
    keeps raising the *same* error stays collapsed to one line, but a *different*
    error from the same site -- e.g. a new failure after the human hot-reloads a
    fix -- is surfaced instead of being hidden under the first one's key. Must be
    called from within an ``except`` block.
    """
    exception_once(logger, f"{prefix}:{_current_exc_signature()}", msg, *args)


def _clear_log_once_keys_for_tests() -> None:
    """Clear internal log-once keys (tests only)."""

    with _LOCK:
        try:
            _LOG_ONCE_KEYS.clear()
        except Exception:
            return
