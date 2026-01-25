"""Binding helpers for widgets."""

from __future__ import annotations

import logging
import weakref
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from nuiitivet.common.logging_once import exception_once
from .widget_builder import flush_scope_recompositions


_logger = logging.getLogger(__name__)


_DEPENDENCY_ALL = object()
_PendingEntry = Tuple[weakref.ReferenceType[Any], Set[object], Set[str]]
_pending_invalidation: Dict[int, _PendingEntry] = {}


def _make_finalizer(key: int):
    def _cleanup(_ref: Optional[Any]) -> None:
        _pending_invalidation.pop(key, None)

    return _cleanup


def _queue_binding_invalidation(widget: Any, dependency: Optional[str], scope_id: Optional[str]) -> bool:
    key = id(widget)
    entry = _pending_invalidation.get(key)
    if entry is None:
        ref = weakref.ref(widget, _make_finalizer(key))
        deps: Set[object] = set()
        scopes: Set[str] = set()
        entry = (ref, deps, scopes)
        _pending_invalidation[key] = entry
        first_insert = True
    else:
        deps = entry[1]
        scopes = entry[2]
        first_insert = False

    if dependency is None:
        deps.clear()
        deps.add(_DEPENDENCY_ALL)
    else:
        if _DEPENDENCY_ALL in deps:
            return first_insert
        deps.add(dependency)

    if scope_id is not None:
        scopes.add(scope_id)
    return first_insert


def flush_binding_invalidations() -> None:
    if not _pending_invalidation:
        return
    pending = list(_pending_invalidation.items())
    _pending_invalidation.clear()
    for _, (ref, deps, scopes) in pending:
        widget = ref()
        if widget is None:
            continue
        handler = getattr(widget, "_handle_dependency_invalidation", None)
        if callable(handler):
            handled_scope = False
            for scope_id in list(scopes):
                try:
                    result = handler(scope_id)
                except Exception:
                    exception_once(
                        _logger,
                        f"widget_binding_handle_dependency_invalidation_scope_exc:{type(widget).__name__}",
                        "Exception in _handle_dependency_invalidation(scope_id=%s) for widget=%s",
                        scope_id,
                        type(widget).__name__,
                    )
                    continue
                if result:
                    handled_scope = True
            if handled_scope:
                continue
            if not deps or _DEPENDENCY_ALL in deps:
                try:
                    handler(None)
                except Exception:
                    exception_once(
                        _logger,
                        f"widget_binding_handle_dependency_invalidation_all_exc:{type(widget).__name__}",
                        "Exception in _handle_dependency_invalidation(None) for widget=%s",
                        type(widget).__name__,
                    )
            else:
                for dep in list(deps):
                    if isinstance(dep, str):
                        try:
                            handler(dep)
                        except Exception:
                            exception_once(
                                _logger,
                                f"widget_binding_handle_dependency_invalidation_dep_exc:{type(widget).__name__}",
                                "Exception in _handle_dependency_invalidation(dep=%s) for widget=%s",
                                dep,
                                type(widget).__name__,
                            )
            continue
        invalidate = getattr(widget, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_invalidate_exc:{type(widget).__name__}",
                    "Exception in widget.invalidate() during binding flush for widget=%s",
                    type(widget).__name__,
                )
    try:
        flush_scope_recompositions()
    except Exception:
        exception_once(
            _logger,
            "widget_binding_flush_scope_recompositions_exc",
            "Exception in flush_scope_recompositions()",
        )


class BindingHostMixin:
    """Stores disposables tied to widget lifetime."""

    _bindings: List

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)
        self._bindings = []

    def bind(self, disposable) -> None:
        try:
            self._bindings.append(disposable)
        except Exception:
            exception_once(
                _logger,
                f"widget_binding_bind_append_exc:{type(self).__name__}",
                "Failed to append binding disposable for widget=%s",
                type(self).__name__,
            )

    def bind_many(self, disposables: Iterable) -> None:
        for disposable in disposables:
            try:
                self.bind(disposable)
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_bind_many_exc:{type(self).__name__}",
                    "Failed to bind disposable for widget=%s",
                    type(self).__name__,
                )

    def bind_to(
        self,
        observable,
        setter,
        *,
        dependency: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> None:
        if not hasattr(observable, "subscribe"):
            return

        def _on_value(value) -> None:
            try:
                setter(value)
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_setter_exc:{type(self).__name__}",
                    "Exception in binding setter for widget=%s dependency=%s scope_id=%s",
                    type(self).__name__,
                    dependency,
                    scope_id,
                )
            self._invalidate_binding_dependency(dependency, scope_id)

        try:
            disposable = observable.subscribe(_on_value)
        except Exception:
            exception_once(
                _logger,
                f"widget_binding_subscribe_exc:{type(self).__name__}",
                "Failed to subscribe observable for widget=%s dependency=%s scope_id=%s",
                type(self).__name__,
                dependency,
                scope_id,
            )
            return
        if hasattr(disposable, "dispose"):
            self.bind(disposable)
        elif callable(disposable):
            try:
                disposable()
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_callable_disposable_exc:{type(self).__name__}",
                    "Exception while calling disposable callback for widget=%s",
                    type(self).__name__,
                )

    def _invalidate_binding_dependency(self, dependency: Optional[str], scope_id: Optional[str]) -> None:
        should_request_frame = _queue_binding_invalidation(self, dependency, scope_id)
        invalidate = getattr(self, "invalidate", None)
        if should_request_frame and callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_request_frame_invalidate_exc:{type(self).__name__}",
                    "Exception in invalidate() after binding change for widget=%s",
                    type(self).__name__,
                )
        if getattr(self, "_app", None) is None:
            flush_binding_invalidations()

    def _dispose_bindings(self) -> None:
        for disposable in list(self._bindings):
            try:
                disposable.dispose()
            except Exception:
                exception_once(
                    _logger,
                    f"widget_binding_dispose_exc:{type(self).__name__}",
                    "Exception while disposing binding for widget=%s",
                    type(self).__name__,
                )
        self._bindings.clear()

    def on_unmount(self) -> None:
        self._dispose_bindings()
        super().on_unmount()  # type: ignore


__all__ = ["BindingHostMixin", "flush_binding_invalidations"]
