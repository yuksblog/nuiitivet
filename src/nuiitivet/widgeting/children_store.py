from collections import deque
import logging
from typing import Deque, Iterable, List, Optional, Sequence, Union

from nuiitivet.common.logging_once import debug_once, exception_once
from nuiitivet.common.call import safe_call  # centralized error-handling helper


_logger = logging.getLogger(__name__)


class ChildrenStore:
    """Ownership container for Widget children.

    Responsibilities:
    - Store children in a deque for efficient head/tail ops.
    - Manage parent pointers and mount/unmount lifecycle relative to owner.
    - Provide snapshot() (list) and view() (immutable sequence) helpers.
    - Optional capacity with eviction policies.
    """

    def __init__(
        self,
        owner,
        max_children: Optional[int] = None,
        overflow_policy: str = "none",
    ) -> None:
        self.owner = owner
        self._items: Deque = deque()
        self.max_children: Optional[int] = None
        self.overflow_policy: str = "none"
        self._configure(max_children=max_children, overflow_policy=overflow_policy)
        self._dirty_snapshot = True
        self._snapshot_cache: Optional[List] = None

    # NOTE: use module-level safe_call imported above to keep lifecycle calls
    # concise and consistent. Avoid assigning to instance attributes at module
    # scope (that caused a scoping bug previously).

    # --- basic inspection ---------------------------------
    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, idx: int):
        return list(self._items)[idx]

    def snapshot(self) -> List:
        """Return a stable list snapshot of children. Cached until mutation."""
        if self._dirty_snapshot or self._snapshot_cache is None:
            self._snapshot_cache = list(self._items)
            self._dirty_snapshot = False
        return list(self._snapshot_cache)

    def view(self) -> Sequence:
        """Immutable view of current children (tuple)."""
        return tuple(self.snapshot())

    def _configure(self, *, max_children: Optional[int] = None, overflow_policy: Optional[str] = None) -> None:
        if max_children is not None:
            self.max_children = None if max_children is None else max(1, int(max_children))
        if overflow_policy is not None:
            self.overflow_policy = str(overflow_policy)

    # --- mutation -----------------------------------------
    def _mark_dirty(self) -> None:
        self._dirty_snapshot = True
        mark_layout = getattr(self.owner, "mark_needs_layout", None)
        if callable(mark_layout):
            try:
                mark_layout()
            except Exception:
                exception_once(
                    _logger,
                    f"children_store_mark_needs_layout_exc:{type(self.owner).__name__}",
                    "Exception in owner.mark_needs_layout() for owner=%s",
                    type(self.owner).__name__,
                )

    def add(self, w) -> None:
        """Append a child, enforcing capacity and lifecycle semantics."""
        owner = self.owner

        # Enforce capacity
        if self.max_children is not None and len(self._items) >= self.max_children:
            if self.overflow_policy == "evict_oldest":
                try:
                    old = self._items.popleft()
                    # unmount old child if mounted
                    try:
                        if getattr(old, "_app", None) is not None:
                            safe_call(
                                getattr(old, "unmount"),
                                default=None,
                                exc_msg="children_store: unmount failed for evicted child",
                            )
                    except Exception:
                        # keep best-effort semantics
                        exception_once(
                            _logger,
                            f"children_store_evict_unmount_exc:{type(owner).__name__}",
                            "Exception while unmounting evicted child (owner=%s)",
                            type(owner).__name__,
                        )
                    try:
                        old._parent = None
                    except Exception:
                        exception_once(
                            _logger,
                            f"children_store_evict_clear_parent_exc:{type(owner).__name__}",
                            "Failed to clear _parent on evicted child (owner=%s)",
                            type(owner).__name__,
                        )
                except Exception:
                    # fallback: convert to list replacement
                    try:
                        items = list(self._items)
                        old = items.pop(0)
                        try:
                            if getattr(old, "_app", None) is not None:
                                safe_call(
                                    getattr(old, "unmount"),
                                    default=None,
                                    exc_msg="children_store: unmount failed for evicted child (fallback)",
                                )
                        except Exception:
                            exception_once(
                                _logger,
                                f"children_store_evict_unmount_fallback_exc:{type(owner).__name__}",
                                "Exception while unmounting evicted child in fallback path (owner=%s)",
                                type(owner).__name__,
                            )
                        try:
                            old._parent = None
                        except Exception:
                            exception_once(
                                _logger,
                                f"children_store_evict_clear_parent_fallback_exc:{type(owner).__name__}",
                                "Failed to clear _parent on evicted child (fallback owner=%s)",
                                type(owner).__name__,
                            )
                        self._items = deque(items)
                    except Exception:
                        # last-resort: clear
                        self._items = deque()
            elif self.overflow_policy == "replace_last":
                try:
                    old = self._items.pop()
                    try:
                        if getattr(old, "_app", None) is not None:
                            safe_call(
                                getattr(old, "unmount"),
                                default=None,
                                exc_msg="children_store: unmount failed for evicted child (replace_last)",
                            )
                    except Exception:
                        exception_once(
                            _logger,
                            f"children_store_replace_last_unmount_exc:{type(owner).__name__}",
                            "Exception while unmounting replaced child (owner=%s)",
                            type(owner).__name__,
                        )
                    try:
                        old._parent = None
                    except Exception:
                        exception_once(
                            _logger,
                            f"children_store_replace_last_clear_parent_exc:{type(owner).__name__}",
                            "Failed to clear _parent on replaced child (owner=%s)",
                            type(owner).__name__,
                        )
                except Exception:
                    try:
                        self._items.clear()
                    except Exception:
                        self._items = deque()
            elif self.overflow_policy == "error":
                raise RuntimeError("capacity exceeded")
            else:
                # 'none' means unbounded
                pass

        # append new child
        try:
            self._items.append(w)
        except Exception:
            # fall back to reassigning deque
            try:
                self._items = deque(list(self._items) + [w])
            except Exception:
                self._items = deque([w])

        # lifecycle: parent pointer and mount
        try:
            w._parent = owner
        except Exception:
            exception_once(
                _logger,
                f"children_store_set_parent_exc:{type(owner).__name__}",
                "Failed to set _parent on child (owner=%s child=%s)",
                type(owner).__name__,
                type(w).__name__,
            )
        try:
            if getattr(owner, "_app", None) is not None:
                # mount in safe way
                safe_call(
                    getattr(w, "mount"),
                    owner._app,
                    default=None,
                    exc_msg="children_store: mount failed for added child",
                )
        except Exception:
            exception_once(
                _logger,
                f"children_store_mount_added_child_exc:{type(owner).__name__}",
                "Exception while mounting added child (owner=%s child=%s)",
                type(owner).__name__,
                type(w).__name__,
            )

        self._mark_dirty()

    def remove(self, w_or_idx: Union[object, int]) -> None:
        """Remove a child by object or index; unmount and clear parent."""
        try:
            if isinstance(w_or_idx, int):
                # index-based
                items = list(self._items)
                target = items.pop(w_or_idx)
                self._items = deque(items)
            else:
                # object-based
                try:
                    self._items.remove(w_or_idx)
                    target = w_or_idx
                except ValueError:
                    debug_once(
                        _logger,
                        f"children_store_remove_missing:{type(self.owner).__name__}",
                        "Child not found while removing by object (owner=%s child=%s)",
                        type(self.owner).__name__,
                        type(w_or_idx).__name__,
                    )
                    return
        except Exception:
            exception_once(
                _logger,
                f"children_store_remove_exc:{type(self.owner).__name__}",
                "Unexpected error while removing child (owner=%s)",
                type(self.owner).__name__,
            )
            return

        try:
            if getattr(target, "_app", None) is not None:
                safe_call(
                    getattr(target, "unmount"), default=None, exc_msg="children_store: unmount failed for removed child"
                )
        except Exception:
            try:
                safe_call(
                    getattr(target, "unmount"),
                    default=None,
                    exc_msg="children_store: unmount failed for removed child (fallback)",
                )
            except Exception:
                exception_once(
                    _logger,
                    f"children_store_remove_unmount_fallback_exc:{type(self.owner).__name__}",
                    "Exception while unmounting removed child in fallback path (owner=%s)",
                    type(self.owner).__name__,
                )
        try:
            target._parent = None
        except Exception:
            exception_once(
                _logger,
                f"children_store_remove_clear_parent_exc:{type(self.owner).__name__}",
                "Failed to clear _parent on removed child (owner=%s)",
                type(self.owner).__name__,
            )

        self._mark_dirty()

    def clear(self) -> None:
        # unmount all
        try:
            for c in list(self._items):
                try:
                    if getattr(c, "_app", None) is not None:
                        safe_call(
                            getattr(c, "unmount"), default=None, exc_msg="children_store: unmount_all failed for child"
                        )
                except Exception:
                    try:
                        safe_call(
                            getattr(c, "unmount"),
                            default=None,
                            exc_msg="children_store: unmount_all failed for child (fallback)",
                        )
                    except Exception:
                        exception_once(
                            _logger,
                            f"children_store_clear_unmount_fallback_exc:{type(self.owner).__name__}",
                            "Exception while unmounting child in clear fallback (owner=%s)",
                            type(self.owner).__name__,
                        )
                try:
                    c._parent = None
                except Exception:
                    exception_once(
                        _logger,
                        f"children_store_clear_clear_parent_exc:{type(self.owner).__name__}",
                        "Failed to clear _parent during clear (owner=%s)",
                        type(self.owner).__name__,
                    )
        except Exception:
            exception_once(
                _logger,
                f"children_store_clear_iter_exc:{type(self.owner).__name__}",
                "Exception while iterating children during clear (owner=%s)",
                type(self.owner).__name__,
            )
        try:
            self._items.clear()
        except Exception:
            self._items = deque()
        self._mark_dirty()

    def unmount_all(self) -> None:
        """Unmount all children but keep them attached (do not remove from store).

        This preserves the collection while clearing their mounted state. Useful
        when the owner itself is being unmounted and we want to keep the child
        objects for later rebuild without losing the objects.
        """
        try:
            for c in list(self._items):
                try:
                    if getattr(c, "_app", None) is not None:
                        safe_call(
                            getattr(c, "unmount"), default=None, exc_msg="children_store: unmount_all failed for child"
                        )
                except Exception:
                    try:
                        safe_call(
                            getattr(c, "unmount"),
                            default=None,
                            exc_msg="children_store: unmount_all failed for child (fallback)",
                        )
                    except Exception:
                        exception_once(
                            _logger,
                            f"children_store_unmount_all_fallback_exc:{type(self.owner).__name__}",
                            "Exception while unmounting child in unmount_all fallback (owner=%s)",
                            type(self.owner).__name__,
                        )
        except Exception:
            exception_once(
                _logger,
                f"children_store_unmount_all_iter_exc:{type(self.owner).__name__}",
                "Exception while iterating children during unmount_all (owner=%s)",
                type(self.owner).__name__,
            )

    def extend(self, items: Iterable) -> None:
        for it in items:
            self.add(it)
