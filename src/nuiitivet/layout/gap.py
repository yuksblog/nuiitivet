from __future__ import annotations
from typing import Union

from nuiitivet.observable.protocols import StateBase


def normalize_gap(value: Union[int, float, str, StateBase, None]) -> int:
    """Normalize a gap value to a non-negative integer.

    Args:
        value: The gap value to normalize (int, str, None, or State).

    Returns:
        A non-negative integer.
    """
    if value is None:
        return 0
    # If it is a State, we cannot resolve it to int here.
    # The caller must check for instance before calling this if they support observability.
    # Currently existing code assumes int return.
    if isinstance(value, StateBase):
        return 0
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return 0
