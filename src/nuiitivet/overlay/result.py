"""Overlay result semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Optional, TypeVar


class OverlayDismissReason(str, Enum):
    """Reason why an overlay entry completed."""

    CLOSED = "closed"
    OUTSIDE_TAP = "outside_tap"
    TIMEOUT = "timeout"
    DISPOSED = "disposed"


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class OverlayResult(Generic[T]):
    """Structured completion result for an overlay entry."""

    value: Optional[T]
    reason: OverlayDismissReason
