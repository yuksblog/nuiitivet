"""Functions the worker spike sends to a second Pyodide, as a process pool would send them to a child."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float


def add(a: int, b: int) -> int:
    return a + b


def norm(point: Point) -> float:
    return (point.x**2 + point.y**2) ** 0.5


def burn(seconds: float) -> int:
    """Keep the CPU busy for ``seconds``; the count shows it really ran."""
    end = time.perf_counter() + seconds
    count = 0
    while time.perf_counter() < end:
        count += 1
    return count


def fail() -> None:
    raise ValueError("bad input")


def framework() -> int:
    import nuiitivet.material as nv

    return len(dir(nv))
