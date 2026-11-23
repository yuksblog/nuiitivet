"""The slot a dev session fills to time the app code the framework calls on the UI thread."""

from __future__ import annotations

import functools
import types
from typing import Any, Awaitable, Callable, Generator, Literal, Optional, Protocol, TypeVar, cast

T = TypeVar("T")

CallKind = Literal["event handler", "size-change callback", "clock callback", "draw function", "build"]


class CallProbe(Protocol):
    """What a dev session installs to time app code."""

    def call(self, kind: CallKind, fn: Callable[..., Any], *args: Any) -> Any:
        """Call ``fn(*args)`` and return its result; an exception passes through.

        Args:
            kind: What the framework is calling.
            fn: The app's function.
            *args: Its arguments.
        """
        ...

    def begin_frame_start(self) -> None:
        """Note that a frame starts to run its queued app code."""
        ...

    def end_frame_start(self) -> None:
        """Note that the frame has run its queued app code."""
        ...


# ``None`` in a plain run: a call site then calls the app's function directly.
_probe: Optional[CallProbe] = None


def set_call_probe(probe: Optional[CallProbe]) -> None:
    """Install the probe, or clear it with ``None``.

    Args:
        probe: The probe every call site routes app code through from now on.
    """
    global _probe
    _probe = probe


def call_probe() -> Optional[CallProbe]:
    """The installed probe; ``None`` outside a dev session."""
    return _probe


def run_frame_start(run: Callable[[], None]) -> None:
    """Run the app code queued for the start of a frame, told to the probe as one frame start.

    Args:
        run: Runs the queues.
    """
    probe = _probe
    if probe is None:
        run()
        return
    probe.begin_frame_start()
    try:
        run()
    finally:
        probe.end_frame_start()


def probed_steps(kind: CallKind, fn: Callable[..., Any], awaitable: Awaitable[T]) -> Awaitable[T]:
    """Return an awaitable whose every step runs through the probe as a call of ``fn``.

    With no probe installed it is ``awaitable`` itself.

    Args:
        kind: What the framework is awaiting.
        fn: The app's function that returned ``awaitable``.
        awaitable: What that function returned.
    """
    if _probe is None:
        return awaitable
    return cast("Awaitable[T]", _probed_steps(kind, fn, awaitable))


@types.coroutine
def _probed_steps(kind: CallKind, fn: Callable[..., Any], awaitable: Awaitable[T]) -> Generator[Any, Any, T]:
    steps = awaitable.__await__()

    # Named after ``fn``, so a slow step is reported under the app's function.
    @functools.wraps(fn)
    def step(resume: Callable[[Any], Any], value: Any) -> Any:
        return resume(value)

    resume: Callable[[Any], Any] = steps.send
    value: Any = None
    while True:
        probe = _probe
        try:
            yielded = resume(value) if probe is None else probe.call(kind, step, resume, value)
        except StopIteration as stop:
            return stop.value
        try:
            value = yield yielded
            resume = steps.send
        except GeneratorExit:
            steps.close()
            raise
        except BaseException as exc:
            resume, value = steps.throw, exc


__all__ = ["CallKind", "CallProbe", "call_probe", "probed_steps", "run_frame_start", "set_call_probe"]
