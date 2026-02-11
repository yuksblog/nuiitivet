from __future__ import annotations
from typing import Union

from nuiitivet.observable.protocols import ReadOnlyObservableProtocol


def normalize_gap(value: Union[int, float, str, ReadOnlyObservableProtocol, None]) -> int:
    """Normalize a gap value to a non-negative integer.

    Args:
        value: The gap value to normalize (int, str, None, or Observable).

    Returns:
        A non-negative integer.
    """
    if value is None:
        return 0
    # If it is observable, we cannot resolve it to int here.
    # The caller must check for instance before calling this if they support observability.
    # Currently existing code assumes int return.
    if isinstance(value, ReadOnlyObservableProtocol):
        return 0
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return 0
