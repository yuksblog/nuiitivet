"""Standard dialog intent types.

These intents are used by the default dialog registry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AlertDialogIntent:
    title: str
    message: str


@dataclass(frozen=True, slots=True)
class LoadingDialogIntent:
    message: str = "Loading..."


__all__ = ["AlertDialogIntent", "LoadingDialogIntent"]
