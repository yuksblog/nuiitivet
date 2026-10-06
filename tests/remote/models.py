"""Types the server function tests exchange; a module the page would get too."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Order:
    id: int
    items: list[str]
