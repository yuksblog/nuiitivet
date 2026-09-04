"""Capture surfaces that feed the runtime journal (dev-only).

The runtime journal (:mod:`nuiitivet.dev.runtime_journal`) is only as useful as
what reaches it. This module installs the three taps that route the running
app's output and failures into it, covering every thread a dev session touches:

* a **``logging.Handler``** on the root logger (WARNING and above) -- captures
  framework and app log records from *any* thread. This is the primary net: the
  framework swallows callback exceptions and re-emits them through ``logging``
  (see :func:`nuiitivet.widgeting.callbacks.invoke_event_handler`), and asyncio
  reports an unretrieved task exception by *logging* it at ERROR on the
  ``asyncio`` logger -- so both land here without any asyncio-specific hook;
* **``threading.excepthook``** -- a background thread that dies on an uncaught
  exception is reported here (Python does not route those through ``logging``);
* **``sys.excepthook``** -- the same, for an uncaught exception on the main
  thread.

All three chain to the previous hook, so the human's console output is
unchanged; capture is purely additive.

**Verbose mode.** De-duplication of repeated failures lives at the emit sites
(``logging_once``): a record suppressed there never reaches the handler, so by
default the journal shows each distinct failure once rather than a flood of the
same one. :meth:`RuntimeLogCapture.set_verbose` flips that global switch off so a
debugging session can see *every* occurrence -- the dev bridge exposes it as the
``set_runtime_log_verbose`` control.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from typing import Any, Optional

from nuiitivet.common.logging_once import is_log_once_enabled, set_log_once_enabled

from .runtime_journal import RuntimeJournal

logger = logging.getLogger(__name__)

# Exceptions that signal an intentional shutdown, not an app fault. Recording
# them as errors would be misleading noise, so both excepthook taps skip them.
_IGNORED_EXC_TYPES = (KeyboardInterrupt, SystemExit)


class _JournalHandler(logging.Handler):
    """A ``logging.Handler`` that mirrors each record into a :class:`RuntimeJournal`."""

    def __init__(self, journal: RuntimeJournal, level: int) -> None:
        super().__init__(level)
        self._journal = journal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            exc_type: Optional[str] = None
            tb_text: Optional[str] = None
            if record.exc_info and record.exc_info[0] is not None:
                exc_type = record.exc_info[0].__name__
                tb_text = "".join(traceback.format_exception(*record.exc_info))
            self._journal.record(
                level=record.levelname,
                source="logging",
                thread=record.threadName or "?",
                message=record.getMessage(),
                logger=record.name,
                exc_type=exc_type,
                traceback=tb_text,
            )
        except Exception:
            # Never let capture break the logging call that triggered it.
            self.handleError(record)


class RuntimeLogCapture:
    """Installs and removes the runtime-log capture taps for one dev session.

    Lifecycle mirrors the other dev components: :meth:`install` before the event
    loop runs, :meth:`shutdown` after it exits. Not reentrant -- one per process.
    """

    def __init__(self, journal: RuntimeJournal, *, level: int = logging.WARNING) -> None:
        self._journal = journal
        self._level = level
        self._handler: Optional[_JournalHandler] = None
        self._prev_threading_hook: Any = None
        self._prev_sys_hook: Any = None
        # The bound hooks we install, kept so :meth:`shutdown` can identity-check
        # "am I still the live hook?" -- accessing ``self._on_*`` again would
        # create a *fresh* bound method that no ``is`` comparison would match.
        self._threading_hook: Any = None
        self._sys_hook: Any = None
        self._installed = False

    def install(self) -> None:
        """Attach the logging handler and the thread/main excepthooks."""
        if self._installed:
            return
        self._installed = True

        self._handler = _JournalHandler(self._journal, self._level)
        logging.getLogger().addHandler(self._handler)

        self._prev_threading_hook = threading.excepthook
        self._threading_hook = self._on_thread_exception
        threading.excepthook = self._threading_hook

        self._prev_sys_hook = sys.excepthook
        self._sys_hook = self._on_sys_exception
        sys.excepthook = self._sys_hook

    def shutdown(self) -> None:
        """Detach the handler, restore the excepthooks, and re-enable de-dup."""
        if not self._installed:
            return
        self._installed = False

        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None

        # Only restore if we are still the installed hook, so we do not clobber a
        # hook another component set after us.
        if self._prev_threading_hook is not None and threading.excepthook is self._threading_hook:
            threading.excepthook = self._prev_threading_hook
        self._prev_threading_hook = None
        self._threading_hook = None

        if self._prev_sys_hook is not None and sys.excepthook is self._sys_hook:
            sys.excepthook = self._prev_sys_hook
        self._prev_sys_hook = None
        self._sys_hook = None

        # Leave the global de-dup switch on when the session ends, in case a
        # verbose run forgot to reset it.
        set_log_once_enabled(True)

    def set_verbose(self, enabled: bool) -> bool:
        """Turn verbose capture on/off and return the resulting verbose state.

        Verbose disables once-per-process de-dup process-wide, so every repeated
        failure reaches the journal rather than only its first occurrence.
        """
        set_log_once_enabled(not enabled)
        return self.is_verbose()

    def is_verbose(self) -> bool:
        """Return whether verbose capture (de-dup disabled) is currently active."""
        return not is_log_once_enabled()

    def _on_thread_exception(self, args: Any) -> None:
        """``threading.excepthook``: record a background thread's uncaught exception."""
        thread = getattr(args, "thread", None)
        thread_name = thread.name if thread is not None else "?"
        self._record_exception(
            "thread", thread_name, args.exc_type, args.exc_value, args.exc_traceback
        )
        if self._prev_threading_hook is not None:
            self._prev_threading_hook(args)

    def _on_sys_exception(self, exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        """``sys.excepthook``: record the main thread's uncaught exception."""
        self._record_exception(
            "excepthook", threading.current_thread().name, exc_type, exc_value, exc_tb
        )
        hook = self._prev_sys_hook or sys.__excepthook__
        hook(exc_type, exc_value, exc_tb)

    def _record_exception(
        self, source: str, thread: str, exc_type: Any, exc_value: Any, exc_tb: Any
    ) -> None:
        """Record an uncaught exception, skipping intentional-shutdown signals."""
        if exc_type is None or issubclass(exc_type, _IGNORED_EXC_TYPES):
            return
        try:
            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            self._journal.record(
                level="ERROR",
                source=source,
                thread=thread,
                message=f"{exc_type.__name__}: {exc_value}",
                exc_type=exc_type.__name__,
                traceback=tb_text,
            )
        except Exception:
            # Capture must never itself raise out of an excepthook.
            logger.debug("runtime capture: failed to record uncaught exception", exc_info=True)


__all__ = [
    "RuntimeLogCapture",
]
