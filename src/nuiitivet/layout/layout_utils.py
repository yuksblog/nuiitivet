"""Layout-related utility helpers.

Moved out from `utils.py` to separate layout concerns.
"""

import logging
from typing import List, Sequence, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from ..widgeting.widget import Widget


_logger = logging.getLogger(__name__)


def expand_layout_children(children: Sequence["Widget"]) -> List["Widget"]:
    """Expand any children that act as layout providers (e.g. ForEach).

    Widgets can implement ``provide_layout_children`` to return a list of
    widgets that should participate directly in the parent's layout. When
    present, the provider's own widget is skipped and the returned children are
    used instead. This enables declarative constructs such as Row.builder(...)
    where the ForEach provider does not paint but supplies multiple children to
    the Row.
    """

    materialized: List["Widget"] = []
    for child in children:
        provider = getattr(child, "provide_layout_children", None)
        if callable(provider):
            try:
                provided = provider()
            except Exception:
                exception_once(_logger, "layout_utils_provide_layout_children_exc", "provide_layout_children failed")
                provided = None
            if provided:
                materialized.extend(list(provided))
                # The provider itself is not laid out, so we must clear its dirty flag
                # to ensure future invalidations propagate correctly.
                try:
                    child.clear_needs_layout()
                except Exception:
                    exception_once(_logger, "layout_utils_clear_needs_layout_exc", "clear_needs_layout failed")
                continue
        materialized.append(child)
    return materialized
