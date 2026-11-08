"""What the frame loop tells widgets about the frame: whether one is under way, when it began, how long it has."""

from __future__ import annotations

from typing import Optional

# The frame interval before a loop reports one: a 60 Hz display.
DEFAULT_FRAME_INTERVAL = 1.0 / 60.0

_interval = DEFAULT_FRAME_INTERVAL
_started_at: Optional[float] = None


def set_frame_interval(seconds: float) -> None:
    """Record the time one frame has.

    Args:
        seconds: The display's refresh period, or the loop's cadence when
            that is longer.
    """
    global _interval
    _interval = max(0.001, float(seconds))


def frame_interval() -> float:
    """The time one frame has, in seconds."""
    return _interval


def begin_frame(now: float) -> None:
    """Record that a frame began at ``now``; the loop calls it before it draws.

    Args:
        now: A ``perf_counter()`` value.
    """
    global _started_at
    _started_at = float(now)


def end_frame() -> None:
    """Record that the frame is over; the loop calls it after it drew."""
    global _started_at
    _started_at = None


def frame_started_at() -> Optional[float]:
    """When the frame under way began; ``None`` between frames."""
    return _started_at


def frame_deadline(share: float) -> Optional[float]:
    """The moment ``share`` of the frame under way has passed, as a ``perf_counter()`` value.

    ``None`` between frames, and wherever no loop runs: a test, a headless
    render.
    """
    if _started_at is None:
        return None
    return _started_at + _interval * max(0.0, float(share))


__all__ = [
    "DEFAULT_FRAME_INTERVAL",
    "begin_frame",
    "end_frame",
    "frame_deadline",
    "frame_interval",
    "frame_started_at",
    "set_frame_interval",
]
