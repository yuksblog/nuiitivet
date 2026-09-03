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
                # An empty provider misses this branch and is laid out as an ordinary
                # child, so drop the zero-area rect it was stamped with back then.
                try:
                    child.clear_layout_rect()
                except Exception:
                    exception_once(_logger, "layout_utils_clear_layout_rect_exc", "clear_layout_rect failed")
                continue
        materialized.append(child)
    return materialized


def layout_child_if_needed(child: "Widget", width: int, height: int) -> None:
    """Run ``child.layout`` unless it would recompute an unchanged result.

    A clean child — nothing in its subtree called ``mark_needs_layout`` since
    its last pass — laid out again at the same size produces the same subtree
    geometry, because ``layout()`` is a pure function of the widget's state and
    its allocated size (see RENDERING_PIPELINE.md). Skipping the recursion
    makes re-arranging an unchanged sibling O(1). The caller still positions
    the child with ``set_layout_rect``; position is not an input to ``layout``.
    """

    rect = getattr(child, "layout_rect", None)
    if (
        rect is not None
        and not getattr(child, "needs_layout", True)
        and rect[2] == int(width)
        and rect[3] == int(height)
    ):
        return
    child.layout(width, height)
