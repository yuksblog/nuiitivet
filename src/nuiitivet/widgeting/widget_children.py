"""Child management helpers for widgets."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from nuiitivet.common.logging_once import exception_once

from .children_store import ChildrenStore


logger = logging.getLogger(__name__)


class ChildContainerMixin:
    """Provides ChildrenStore-backed ownership helpers."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        max_children = kwargs.pop("max_children", None)
        overflow_policy = kwargs.pop("overflow_policy", "none")
        super().__init__(*args, **kwargs)
        policy = self._normalize_children_policy(max_children, overflow_policy)
        store = getattr(self, "_children_store", None)
        if not isinstance(store, ChildrenStore):
            self._children_store = ChildrenStore(
                self,
                max_children=policy[0],
                overflow_policy=policy[1],
            )
        else:
            try:
                store._configure(max_children=policy[0], overflow_policy=policy[1])
            except Exception:
                exception_once(logger, "children_store_configure_exc", "ChildrenStore._configure failed")
                self._children_store = ChildrenStore(
                    self,
                    max_children=policy[0],
                    overflow_policy=policy[1],
                )

    # --- Read helpers ------------------------------------------------------
    @property
    def children(self) -> Tuple:
        try:
            return tuple(self._children_store.view())
        except Exception:
            exception_once(logger, "children_store_view_exc", "ChildrenStore.view failed")
            return tuple()

    def children_snapshot(self) -> List:
        try:
            return self._children_store.snapshot()
        except Exception:
            exception_once(logger, "children_store_snapshot_exc", "ChildrenStore.snapshot failed")
            return []

    def clear_children(self) -> None:
        try:
            self._children_store.clear()
            return
        except Exception:
            exception_once(logger, "children_store_clear_exc", "ChildrenStore.clear failed")
        try:
            self._children_store._items = __import__("collections").deque()
        except Exception:
            exception_once(logger, "children_store_clear_fallback_exc", "Failed to reset ChildrenStore internal deque")

    # --- Mutation helpers --------------------------------------------------
    def add_child(self, widget) -> None:
        try:
            self._children_store.add(widget)
            return
        except Exception:
            exception_once(logger, "children_store_add_exc", "ChildrenStore.add failed")
        try:
            widget._parent = self
        except Exception:
            exception_once(logger, "children_store_set_parent_exc", "Failed to set widget._parent")
        app = getattr(self, "_app", None)
        if app is not None:
            try:
                widget.mount(app)
            except Exception:
                exception_once(logger, "children_store_mount_child_exc", "widget.mount failed in fallback add_child")

    def remove_child(self, widget_or_index) -> None:
        try:
            self._children_store.remove(widget_or_index)
            return
        except Exception:
            exception_once(logger, "children_store_remove_exc", "ChildrenStore.remove failed")
        try:
            items = list(self._children_store._items)
            items.remove(widget_or_index)
            self._children_store._items = __import__("collections").deque(items)
        except Exception:
            exception_once(logger, "children_store_remove_fallback_exc", "Fallback remove_child failed")
            return

    # --- Policy helpers ---------------------------------------------------
    @staticmethod
    def _normalize_children_policy(
        max_children: Optional[int],
        overflow_policy: Optional[str],
    ) -> Tuple[Optional[int], str]:
        normalized_max: Optional[int]
        if max_children is None:
            normalized_max = None
        else:
            try:
                normalized = int(max_children)
                normalized_max = max(1, normalized)
            except Exception:
                exception_once(
                    logger,
                    "children_policy_max_children_int_exc",
                    "Failed to normalize max_children (type=%s)",
                    type(max_children).__name__,
                )
                normalized_max = None
        normalized_policy = str(overflow_policy or "none")
        return (normalized_max, normalized_policy)
