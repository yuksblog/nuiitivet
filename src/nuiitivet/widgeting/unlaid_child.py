"""The warning for a widget that is painted and was never laid out."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from nuiitivet.common.logging_once import exception_once, warning_once

if TYPE_CHECKING:  # pragma: no cover
    from .widget_kernel import WidgetKernel

_logger = logging.getLogger(__name__)


def warn_child_without_rect(child: "WidgetKernel") -> None:
    """Warn that ``child`` has no layout rect at paint, and name the parent that never laid it out.

    The widget named is the highest one without a rect, with its parent. A
    pair of classes is named once. A parent whose layout is still to come is
    not named: that layout gives the child a rect. With no parent the widget
    is named alone.

    Args:
        child: The child a paint skipped for its missing rect.
    """
    try:
        unlaid = child
        parent = unlaid.parent
        while parent is not None and parent.layout_rect is None:
            unlaid, parent = parent, parent.parent
        name = type(unlaid).__name__
        if parent is None:
            warning_once(
                _logger,
                f"unlaid_child_root:{name}",
                "%s has no layout rect when it is painted, and a widget with no rect is not painted. "
                "Call layout(width, height) before paint().",
                name,
            )
            return
        if _layout_is_coming(parent):
            return
        parent_name = type(parent).__name__
        warning_once(
            _logger,
            f"unlaid_child:{parent_name}:{name}",
            "%s has no layout rect when it is painted: its parent %s never laid it out. "
            "A widget with no rect is not painted. %s.layout() must call super().layout(width, height) "
            "and lay out each child: child.layout(width, height), then child.set_layout_rect(x, y, width, height).",
            name,
            parent_name,
            parent_name,
        )
    except Exception:
        exception_once(_logger, "unlaid_child_warning_exc", "The warning for a child without a rect failed")


def _layout_is_coming(widget: "WidgetKernel") -> bool:
    """Whether a layout will reach ``widget``: one is pending above it, or it is marked up to the root."""
    node: Optional["WidgetKernel"] = widget
    while node is not None and node.needs_layout:
        if node._layout_pending:
            return True
        node = node.parent
    return node is None
