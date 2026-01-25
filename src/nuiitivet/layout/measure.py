from __future__ import annotations

from typing import Optional, Tuple


def preferred_size(
    widget,
    *,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    default: Tuple[int, int] = (0, 0),
) -> Tuple[int, int]:
    """Return widget's preferred size, optionally within constraints.

    This function tolerates legacy implementations that still define
    preferred_size(self) with no constraint parameters.
    """

    fn = getattr(widget, "preferred_size", None)
    if fn is None:
        return default

    try:
        return fn(max_width=max_width, max_height=max_height)
    except TypeError as e:
        msg = str(e)
        if "unexpected keyword argument" in msg:
            try:
                return fn()
            except Exception:
                return default
        return default
    except Exception:
        return default
