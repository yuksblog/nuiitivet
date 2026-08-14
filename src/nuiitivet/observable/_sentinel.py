"""Shared "no value" sentinel for the observable package.

Several observables need to distinguish "nothing is pending" from "the pending
value happens to be ``None``". ``None`` cannot carry both meanings, so they hold
:data:`UNSET` instead and test against it with ``is``.

The sentinel is an enum member rather than a bare ``object()`` so that type
checkers narrow it: a field declared ``T | _Unset`` becomes ``T`` inside an
``is not UNSET`` branch, which a plain ``object()`` sentinel cannot express
without falling back to ``Any``.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class _Unset(Enum):
    """Type of :data:`UNSET`. Never instantiate or subclass this."""

    TOKEN = 0

    def __repr__(self) -> str:
        return "UNSET"


UNSET: Final = _Unset.TOKEN
"""Marker meaning "no value here", distinct from a legitimate ``None``."""
