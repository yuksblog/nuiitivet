"""Reports app code that runs long on the UI thread (dev-only)."""

from __future__ import annotations

import functools
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

from nuiitivet.common.call_probe import CallKind, call_probe, set_call_probe
from nuiitivet.common.logging_once import is_log_once_enabled
from nuiitivet.observable.runtime import probe_clock, unprobe_clock
from nuiitivet.runtime.threading import is_ui_thread
from nuiitivet.widgeting.frame_clock import frame_interval

logger = logging.getLogger(__name__)

# The share of a frame one call may take: past it, layout and paint have less than the rest.
_LIMIT_SHARE = 0.5

# How many functions a slow frame start names.
_NAMED_CALLS = 5

# How many wrappers a function is looked for under before its name is taken as it is.
_MAX_UNWRAP = 8


@dataclass
class _FrameStart:
    """The calls one frame start made.

    Attributes:
        depth: How many calls were under way when it began.
        calls: Each call made at that depth, with its time in seconds.
        has_slow_call: Whether one of them, or a call inside one, was slow alone.
    """

    depth: int
    calls: list[tuple[Callable[..., Any], float]] = field(default_factory=list)
    has_slow_call: bool = False


class SlowCallReporter:
    """Times the app code the framework calls on the UI thread and logs a warning for a slow call.

    A call is slow when it takes longer than half a frame. The time of a slow
    call is not counted again in the call around it. A frame start whose
    calls are each under the limit is reported when their total is over it.
    A function is reported once, until :meth:`reset`; with the verbose runtime
    log, every time. Nothing is timed before the first frame starts, nor
    inside :meth:`paused`.
    """

    def __init__(self, *, limit: Optional[float] = None, timer: Callable[[], float] = time.perf_counter) -> None:
        """Initialize a SlowCallReporter.

        Args:
            limit: The longest a call may take, in seconds; ``None`` is half a frame.
            timer: The clock the calls are timed with, in seconds.
        """
        self._fixed_limit = limit
        self._timer = timer
        self._reported: set[str] = set()
        # Off until the first frame starts: the builds that mount the app hold no frame up.
        self._started = False
        self._timing = False
        # One slot per call under way: the time its slow nested calls took.
        self._nested_slow: list[float] = []
        self._frames: list[_FrameStart] = []

    def install(self) -> None:
        """Route the framework's calls of app code through this reporter."""
        set_call_probe(self)
        probe_clock()

    def shutdown(self) -> None:
        """Stop timing; a probe installed since is left in place."""
        if call_probe() is self:
            set_call_probe(None)
            unprobe_clock()

    def reset(self) -> None:
        """Forget what was reported, so a function still slow is reported again."""
        self._reported.clear()

    def call(self, kind: CallKind, fn: Callable[..., Any], *args: Any) -> Any:
        """Call ``fn(*args)``, timed on the UI thread; return its result. An exception passes through.

        Args:
            kind: What the framework is calling.
            fn: The app's function.
            *args: Its arguments.
        """
        if not self._timing or not is_ui_thread():
            return fn(*args)
        self._nested_slow.append(0.0)
        started = self._timer()
        try:
            return fn(*args)
        finally:
            elapsed = self._timer() - started
            self._record(kind, fn, elapsed, self._nested_slow.pop())

    @contextmanager
    def paused(self) -> Iterator[None]:
        """Time nothing inside the block."""
        timing, self._timing = self._timing, False
        try:
            yield
        finally:
            self._timing = timing

    def begin_frame_start(self) -> None:
        """Start adding up the calls a frame makes before it lays out."""
        if not self._started:
            self._started = self._timing = True
        self._frames.append(_FrameStart(depth=len(self._nested_slow)))

    def end_frame_start(self) -> None:
        """Report the frame start when its calls together took too long and none did alone."""
        if not self._frames:
            return
        frame = self._frames.pop()
        calls = frame.calls
        if not calls or frame.has_slow_call:
            return
        try:
            total = sum(elapsed for _fn, elapsed in calls)
            limit = self._limit()
            if total <= limit:
                return
            slowest = sorted(calls, key=lambda entry: entry[1], reverse=True)[:_NAMED_CALLS]
            named = ", ".join(f"{_site(fn)} {elapsed * 1000.0:.1f} ms" for fn, elapsed in slowest)
            self._warn(
                f"frame start:{_site(slowest[0][0])}",
                "Slow frame start on the UI thread: %d calls took %.1f ms in total; the limit is %.1f ms. Slowest: %s.",
                len(calls),
                total * 1000.0,
                limit * 1000.0,
                named,
            )
        except Exception:
            logger.debug("slow call report: frame start failed", exc_info=True)

    def _limit(self) -> float:
        return self._fixed_limit if self._fixed_limit is not None else frame_interval() * _LIMIT_SHARE

    def _record(self, kind: CallKind, fn: Callable[..., Any], elapsed: float, nested_slow: float) -> None:
        # Never raises: it runs in the ``finally`` of the app's own call.
        try:
            limit = self._limit()
            # What is left once the slow calls inside it, each reported under its own name, are taken out.
            own = elapsed - nested_slow
            slow = own > limit
            if self._nested_slow:
                self._nested_slow[-1] += elapsed if slow else nested_slow
            frame = self._frames[-1] if self._frames else None
            # A call made inside another is already in the outer call's time.
            if frame is not None and len(self._nested_slow) == frame.depth:
                frame.calls.append((fn, elapsed))
                frame.has_slow_call = frame.has_slow_call or slow or nested_slow > 0.0
            if not slow:
                return
            site = _site(fn)
            self._warn(
                f"{kind}:{site}",
                "Slow %s on the UI thread: %s took %.1f ms; the limit is %.1f ms.",
                kind,
                site,
                own * 1000.0,
                limit * 1000.0,
            )
        except Exception:
            logger.debug("slow call report: record failed", exc_info=True)

    def _warn(self, key: str, message: str, *args: object) -> None:
        if is_log_once_enabled():
            if key in self._reported:
                return
            self._reported.add(key)
        logger.warning(message, *args)


def _site(fn: Callable[..., Any]) -> str:
    """``fn`` as ``name (file:line)``, the function under a ``partial`` or a wrapper."""
    target: Any = fn
    for _ in range(_MAX_UNWRAP):
        if isinstance(target, functools.partial):
            target = target.func
        elif getattr(target, "__wrapped__", None) is not None:
            target = target.__wrapped__
        else:
            break
    code = getattr(target, "__code__", None)
    name = getattr(target, "__qualname__", None)
    if code is None:
        # An object called through ``__call__``.
        code = getattr(getattr(type(target), "__call__", None), "__code__", None)
        name = type(target).__qualname__
    if code is None:
        return str(name)
    return f"{name} ({_short_path(code.co_filename)}:{code.co_firstlineno})"


def _short_path(path: str) -> str:
    """``path`` relative to the working directory when it is under it."""
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return path
    outside = relative == os.pardir or relative.startswith(os.pardir + os.sep)
    return path if outside else relative


__all__ = ["SlowCallReporter"]
