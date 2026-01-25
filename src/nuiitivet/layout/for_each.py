"""ForEach: build children from iterables or observable state.

ForEach acts as a layout provider that materializes its children inside
scoped fragments so individual items can be invalidated without forcing
the parent layout to rebuild entirely. The widget can be embedded inside
Row/Column/Flow (or any other layout) and can also materialize
convenience wrappers via ``row()``, ``column()`` and ``flow()`` helper
methods.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, cast

from ..widgeting.widget import ComposableWidget, Widget
from nuiitivet.observable import ObservableProtocol
from ..rendering.sizing import SizingLike
from nuiitivet.common.logging_once import exception_once
from .spacer import Spacer

logger = logging.getLogger(__name__)


ItemsLike = Union[Iterable[Any], ObservableProtocol, Any]
BuilderFn = Callable[[Any, int], Optional[Widget]]


@dataclass
class _TokenInfo:
    token: str
    index: int
    value: Any


@dataclass
class _ItemsHandle:
    source: ItemsLike
    owner: Optional[Any] = None
    attr_name: Optional[str] = None

    def resolve(self) -> ItemsLike:
        if self.owner is None or not self.attr_name:
            return self.source
        try:
            resolved = getattr(self.owner, self.attr_name)
        except Exception:
            exception_once(
                logger,
                "for_each_items_handle_resolve_exc",
                "Failed to resolve items handle attribute (owner=%s attr=%s)",
                type(self.owner).__name__,
                self.attr_name,
            )
            return self.source
        if resolved is None:
            return self.source
        self.source = resolved
        return resolved


@dataclass
class _ForEachEntry:
    token: str
    scope_name: str
    index: int
    value: Any
    fragment: Optional[Widget] = None
    scope_id: Optional[str] = None


class ForEach(ComposableWidget):
    def __init__(
        self,
        items: ItemsLike,
        builder: BuilderFn,
        *,
        key: Optional[Callable[[Any, int], Any]] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ):
        super().__init__(width=width, height=height)
        self.items = items
        self._items_handle = self._capture_items_handle(items)
        self.builder = builder
        self.key_fn = key
        self._items_unsub: Optional[Callable[[], None]] = None
        self._entries_by_token: Dict[str, _ForEachEntry] = {}
        self._ordered_entries: List[_ForEachEntry] = []
        self._provider_children: List[Widget] = []
        self._pending_tokens: Optional[List[_TokenInfo]] = None

    def build(self) -> Widget:
        self._rebuild_children()
        return self

    # ---- Public helpers ----------------------------------------------
    def provide_layout_children(self) -> List[Widget]:
        """Expose built children so parent layouts can measure/paint them."""

        if not self._provider_children:
            self._rebuild_children()
        if self._provider_children:
            return list(self._provider_children)
        return list(self.children_snapshot())

    # ---- Passive widget surface --------------------------------------
    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        from .measure import preferred_size as measure_preferred_size

        children = self.provide_layout_children()
        child_max_w: Optional[int] = None
        child_max_h: Optional[int] = None
        if max_width is not None:
            child_max_w = int(max_width)
        elif self.width_sizing.kind == "fixed":
            child_max_w = int(self.width_sizing.value)
        if max_height is not None:
            child_max_h = int(max_height)
        elif self.height_sizing.kind == "fixed":
            child_max_h = int(self.height_sizing.value)
        if not children:
            default_w, default_h = 0, 0
        else:
            widths: List[int] = []
            heights: List[int] = []
            for child in children:
                w, h = measure_preferred_size(child, max_width=child_max_w, max_height=child_max_h)
                widths.append(max(0, int(w)))
                heights.append(max(0, int(h)))
            default_w = max(widths, default=0)
            default_h = max(heights, default=0)

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = default_w
            if max_width is not None:
                width = min(width, int(max_width))

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = default_h
            if max_height is not None:
                height = min(height, int(max_height))

        return (width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        # ForEach is a provider; actual painting happens in parent layouts.
        return None

    # ---- Data helpers -------------------------------------------------
    def _materialize_items(self) -> List[Any]:
        items_obj = self._resolve_items_object()
        if hasattr(items_obj, "value"):
            try:
                value = getattr(items_obj, "value")
                return list(value) if value is not None else []
            except Exception:
                logger.exception("error accessing .value on items")
                return []
        try:
            return list(items_obj) if items_obj is not None else []
        except Exception:
            logger.exception("error converting items to list")
            return []

    def _consume_pending_tokens(self) -> Optional[List[_TokenInfo]]:
        if self._pending_tokens is None:
            return None
        tokens = self._pending_tokens
        self._pending_tokens = None
        return tokens

    def _enumerate_tokens(self, items: List[Any]) -> List[_TokenInfo]:
        counts: Dict[str, int] = {}
        tokens: List[_TokenInfo] = []
        for idx, value in enumerate(items):
            label = self._key_label(value, idx)
            counter = counts.get(label, 0)
            counts[label] = counter + 1
            token = label if counter == 0 else f"{label}#{counter}"
            tokens.append(_TokenInfo(token=token, index=idx, value=value))
        return tokens

    def _key_label(self, value: Any, idx: int) -> str:
        if self.key_fn is None:
            base = f"idx{idx}"
        else:
            try:
                resolved = self.key_fn(value, idx)
            except Exception:
                logger.exception("key function failed for ForEach item")
                resolved = None
            if resolved is None:
                base = "none"
            else:
                base = str(resolved)
        return self._sanitize_scope_component(base) or f"idx{idx}"

    @staticmethod
    def _sanitize_scope_component(text: str) -> str:
        if not text:
            return ""
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:"
        return "".join(ch if ch in allowed else "_" for ch in text)

    def _sync_entries_from_tokens(self, tokens: List[_TokenInfo]) -> None:
        next_entries: List[_ForEachEntry] = []
        next_children: List[Widget] = []
        seen_tokens = set()
        for info in tokens:
            entry = self._entries_by_token.get(info.token)
            if entry is None:
                entry = _ForEachEntry(
                    token=info.token,
                    scope_name=f"item:{info.token}",
                    index=info.index,
                    value=info.value,
                )
                self._entries_by_token[info.token] = entry
            else:
                entry.index = info.index
                entry.value = info.value
            fragment = self._ensure_fragment(entry)
            if fragment is not None:
                next_children.append(fragment)
            next_entries.append(entry)
            seen_tokens.add(info.token)

        stale_tokens = [token for token in list(self._entries_by_token.keys()) if token not in seen_tokens]
        for token in stale_tokens:
            entry = self._entries_by_token.pop(token)
            self._dispose_entry(entry)

        self._ordered_entries = next_entries
        self._replace_children(next_children)

    def _ensure_fragment(self, entry: _ForEachEntry) -> Optional[Widget]:
        def factory(entry_ref: _ForEachEntry = entry) -> Widget:
            return self._build_entry_widget(entry_ref)

        try:
            with self.scope(entry.scope_name) as handle:
                fragment = self.render_scope_with_handle(handle, factory)
                entry.scope_id = handle.id
        except RuntimeError:
            # render_scope fallback outside build context
            fragment = self.render_scope(entry.scope_name, factory)
            entry.scope_id = getattr(fragment, "scope_id", None)
        entry.fragment = fragment
        return fragment

    def _build_entry_widget(self, entry: _ForEachEntry) -> Widget:
        try:
            built = self.builder(entry.value, entry.index)
        except Exception:
            logger.exception("ForEach builder failed for item index %s", entry.index)
            return Spacer(0, 0)
        if not isinstance(built, Widget):
            logger.error(
                "ForEach builder must return a Widget; received %s at index %s",
                type(built).__name__,
                entry.index,
            )
            return Spacer(0, 0)
        return built

    def _replace_children(self, children: List[Widget]) -> None:
        current = self.children_snapshot()
        if len(current) == len(children) and all(a is b for a, b in zip(current, children)):
            self._provider_children = list(children)
            return
        try:
            self.clear_children()
        except Exception:
            logger.exception("failed clearing ForEach children during sync")
        for child in children:
            self.add_child(child)
        self._provider_children = list(children)

    def _dispose_entry(self, entry: _ForEachEntry) -> None:
        fragment = entry.fragment
        if fragment is not None:
            try:
                self.remove_child(fragment)
            except Exception:
                logger.exception("failed removing ForEach fragment during dispose")
        entry.fragment = None
        entry.scope_id = None

    # ---- Data change handling -----------------------------------------
    def _handle_items_changed(self, _value=None) -> None:
        tokens = self._enumerate_tokens(self._materialize_items())
        if not self._ordered_entries:
            self._pending_tokens = tokens
            self._rebuild_children(tokens)
            self.invalidate()
            return
        current_tokens = [entry.token for entry in self._ordered_entries]
        incoming_tokens = [info.token for info in tokens]
        if len(current_tokens) != len(incoming_tokens) or current_tokens != incoming_tokens:
            self._pending_tokens = tokens
            self._rebuild_children(tokens)
            self.invalidate()
            return
        dirty_entries: List[_ForEachEntry] = []
        for info, entry in zip(tokens, self._ordered_entries):
            if not self._values_equal(entry.value, info.value):
                entry.value = info.value
                entry.index = info.index
                dirty_entries.append(entry)
        if not dirty_entries:
            return
        for entry in dirty_entries:
            if entry.scope_id:
                self.invalidate_scope_id(entry.scope_id)
            else:
                self._pending_tokens = tokens
                self._rebuild_children(tokens)
                self.invalidate()
                break

    @staticmethod
    def _values_equal(left: Any, right: Any) -> bool:
        if left is right:
            return True
        try:
            return left == right
        except Exception:
            exception_once(logger, "for_each_values_equal_exc", "ForEach value equality check raised")
            return False

    def on_mount(self) -> None:
        super().on_mount()
        unsub = None
        observable = self._observable_items()
        if observable is not None and hasattr(observable, "subscribe"):
            try:
                disp = observable.subscribe(self._handle_items_changed)
                # Normalize subscribe return: Disposable with dispose() or a callable
                if hasattr(disp, "dispose"):

                    def _unsub():
                        try:
                            disp.dispose()
                        except Exception:
                            exception_once(logger, "for_each_items_dispose_exc", "items dispose failed")

                    unsub = _unsub
                elif callable(disp):
                    unsub = disp
                else:
                    unsub = None
            except Exception:
                logger.exception("items.subscribe failed")
                unsub = None
        self._items_unsub = unsub
        self.invalidate()

    def on_unmount(self) -> None:
        if self._items_unsub:
            try:
                self._items_unsub()
            except Exception:
                logger.exception("items unsubscribe failed")
            self._items_unsub = None
        self._items_unsub = None
        self._pending_tokens = None
        self._ordered_entries.clear()
        self._entries_by_token.clear()
        self._provider_children.clear()
        try:
            super().on_unmount()
        except Exception:
            logger.exception("error during ForEach.on_unmount")

    # ---- Internal rebuild driver --------------------------------------
    def _rebuild_children(self, tokens: Optional[List[_TokenInfo]] = None) -> None:
        managed_ctx = False
        if self._build_ctx is None:
            self.create_build_context()
            managed_ctx = True
        if self._build_ctx is None:
            return
        try:
            token_data = tokens or self._consume_pending_tokens()
            if token_data is None:
                token_data = self._enumerate_tokens(self._materialize_items())
            self._sync_entries_from_tokens(token_data)
        finally:
            if managed_ctx:
                try:
                    self._prune_unused_scopes()
                finally:
                    self._active_scope_ids.clear()
                    self._build_ctx = None

    # ---- Observable canonicalization helpers -------------------------
    def _capture_items_handle(self, items: ItemsLike) -> _ItemsHandle:
        owner = getattr(items, "_owner", None)
        attr_name = getattr(items, "_name", None)
        if owner is not None and attr_name:
            try:
                resolved = getattr(owner, attr_name)
            except Exception:
                exception_once(
                    logger,
                    "for_each_capture_items_getattr_exc",
                    "Failed to read items attribute (owner=%s attr=%s)",
                    type(owner).__name__,
                    attr_name,
                )
                resolved = None
            if resolved is not None:
                return _ItemsHandle(source=resolved, owner=owner, attr_name=str(attr_name))
            return _ItemsHandle(source=items, owner=owner, attr_name=str(attr_name))
        return _ItemsHandle(source=items)

    def _resolve_items_object(self) -> ItemsLike:
        handle = getattr(self, "_items_handle", None)
        if handle is None:
            return self.items
        resolved = handle.resolve()
        self.items = resolved
        return resolved

    def _observable_items(self) -> Optional[ObservableProtocol]:
        candidate = self._resolve_items_object()
        if hasattr(candidate, "subscribe") and callable(getattr(candidate, "subscribe")):
            return cast(ObservableProtocol, candidate)
        return None
