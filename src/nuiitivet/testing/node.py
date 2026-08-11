"""The :class:`Node` facade a query returns.

A thin, deliberately narrow view of one widget. It exists for two reasons that
the widget itself cannot serve: :attr:`Node.is_reachable` is a test-shaped
derived value that does not belong on the framework's public API, and a failed
``assert`` should print something a human can read rather than a widget's
``__repr__``.
"""

from __future__ import annotations

import weakref
from typing import Any, Optional, Tuple

from nuiitivet._interaction.perception import (
    _coerce_display,
    find_obstruction,
    global_visual_rect,
)

from .errors import StaleNodeError


Rect = Tuple[float, float, float, float]


def _display_text(widget: Any) -> Optional[str]:
    """The widget's display string, by the same rule the tree dump uses."""
    for attr in ("label", "text", "title"):
        display = _coerce_display(getattr(widget, attr, None))
        if display is not None:
            return display
    return None


class Node:
    """One widget, as it was when the query ran.

    **A snapshot, not a live view.** ``text``, ``key`` and ``rect`` are captured
    at query time, so a ``Node`` never reports a mix of before and after; re-query
    after an action rather than holding one across it. A ``Node`` whose widget has
    since been unmounted raises :class:`~nuiitivet.testing.errors.StaleNodeError`
    on every attribute, naming the query it came from and the action that
    invalidated it.

    :attr:`is_reachable` is the one exception, and computes on access: it walks
    the ancestor chain and hit-tests, which a ``get_all()`` over a long list
    should not pay for every row it never asks about. That cannot reintroduce a
    mixed reading, because the two ways the tree could have moved underneath it
    are already closed -- an unmounted widget raises first, and every action verb
    settles before it returns.
    """

    __test__ = False

    def __init__(
        self,
        widget: Any,
        *,
        root: Any,
        query: str,
        last_action: Optional["_LastAction"] = None,
    ) -> None:
        self._widget_ref = weakref.ref(widget)
        self._root_ref = weakref.ref(root) if root is not None else None
        self._query = query
        self._last_action = last_action
        self._action_at_query = last_action.description if last_action else None
        # Captured now, while the widget is known good.
        self._text = _display_text(widget)
        self._key = widget.key if isinstance(getattr(widget, "key", None), str) else None
        rect = getattr(widget, "global_layout_rect", None)
        self._rect: Optional[Rect] = None
        if rect is not None:
            x, y, w, h = rect
            self._rect = (float(x), float(y), float(w), float(h))

    # -- staleness ---------------------------------------------------------

    def _live_widget(self) -> Any:
        """The widget, or raise if it is gone from the tree the query ran on."""
        widget = self._widget_ref()
        if widget is None:
            raise StaleNodeError(self._stale_message("it has been garbage collected"))
        if getattr(widget, "_unmounted", False) or not getattr(widget, "_mounted", True):
            raise StaleNodeError(self._stale_message("it has been unmounted"))
        return widget

    def _stale_message(self, what: str) -> str:
        since = None
        if self._last_action is not None:
            since = self._last_action.description
        detail = f"{self._query} is stale: {what}"
        if since is not None and since != self._action_at_query:
            detail += f", by {since}"
        elif since is not None:
            detail += f" (last action: {since})"
        return (
            f"{detail}. A Node describes the tree as it was when the query ran -- "
            "re-query after the action instead of holding one across it."
        )

    # -- the snapshot ------------------------------------------------------

    @property
    def text(self) -> Optional[str]:
        """The display string: ``label`` / ``text`` / ``title``, normalized."""
        self._live_widget()
        return self._text

    @property
    def key(self) -> Optional[str]:
        """The stable identity the widget was given at construction."""
        self._live_widget()
        return self._key

    @property
    def rect(self) -> Optional[Rect]:
        """``global_layout_rect`` at query time. Available, not the front door."""
        self._live_widget()
        return self._rect

    @property
    def widget(self) -> Any:
        """The raw widget. The marked escape hatch -- greppable on purpose."""
        return self._live_widget()

    @property
    def is_reachable(self) -> bool:
        """Whether this node is where a user could actually act on it.

        In the tree, laid out, inside every ancestor's clip and the viewport, and
        not covered by anything on top. **Says nothing about opacity**: it is
        applied at paint time and no cross-widget effective-opacity query exists,
        so a ``visible(False)`` widget -- still laid out at full size, merely
        faded to nothing -- reports ``True``. Assert on the ``Observable`` driving
        ``visible()`` for that.

        Computed on access, not captured at query time; see the class docstring.
        """
        widget = self._live_widget()
        rect = global_visual_rect(widget)
        if rect is None:
            return False
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            return False
        root = self._root_ref() if self._root_ref is not None else None
        if root is None:
            return False
        return find_obstruction(root, widget, x + w / 2, y + h / 2) is None

    def __repr__(self) -> str:
        widget = self._widget_ref()
        if widget is None:
            return f"<Node {self._query} (collected)>"
        parts = [type(widget).__name__]
        if self._key is not None:
            parts.append(f"key={self._key!r}")
        if self._text is not None:
            parts.append(f"text={self._text!r}")
        if self._rect is not None:
            parts.append("rect=({:.0f}, {:.0f}, {:.0f}, {:.0f})".format(*self._rect))
        return f"<Node {' '.join(parts)}>"


class _LastAction:
    """Mutable holder for the harness's most recent verb.

    A ``Node`` keeps a reference to this rather than a copy, so a stale-node
    message can name the action that invalidated it -- which by definition
    happened *after* the ``Node`` was built.
    """

    __slots__ = ("description",)

    def __init__(self) -> None:
        self.description: Optional[str] = None


__all__ = ["Node"]
