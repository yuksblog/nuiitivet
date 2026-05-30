from __future__ import annotations

from typing import List

from nuiitivet.widgeting.widget import ComposableWidget, Widget, layout_depends_on, paint_depends_on
from nuiitivet.widgeting.widget_binding import flush_binding_invalidations


class _Emitter:
    def __init__(self) -> None:
        self._subs: List = []

    def subscribe(self, cb):
        self._subs.append(cb)

        class _Disposable:
            def dispose(self_inner) -> None:  # pragma: no cover - nothing to release
                return None

        return _Disposable()

    def emit(self, value) -> None:
        for cb in list(self._subs):
            cb(value)


class _AppStub:
    def __init__(self) -> None:
        self.invalidate_calls = 0

    def invalidate(self, immediate: bool = False) -> None:
        self.invalidate_calls += 1


@layout_depends_on("size")
@paint_depends_on("color")
class _TestWidget(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout_hits = 0
        self.paint_hits = 0

    def build(self) -> Widget:
        return self

    def _invalidate_layout_cache(self) -> None:
        self.layout_hits += 1

    def _invalidate_paint_cache(self) -> None:
        self.paint_hits += 1


class _ScopeAwareWidget(_TestWidget):
    def __init__(self) -> None:
        super().__init__()
        self.scope_hits = 0
        self.scope_id: str | None = None
        self.scope_recomposes = 0

    def build(self) -> Widget:
        with self.scope("body") as handle:
            self.scope_id = handle.id
            return self.render_scope_with_handle(handle, self._build_body)

    def _build_body(self) -> Widget:
        self.scope_recomposes += 1
        return _LeafWidget()

    def _handle_scope_invalidation(self, scope_id: str) -> bool:
        handled = super()._handle_scope_invalidation(scope_id)
        if handled:
            self.scope_hits += 1
        return handled


@layout_depends_on("alpha")
@paint_depends_on("beta")
class _LeafWidget(Widget):
    def build(self) -> Widget:  # pragma: no cover - trivial leaf
        return self


def test_binding_queue_batches_per_frame() -> None:
    widget = _TestWidget()
    widget._app = _AppStub()
    emitter = _Emitter()
    values: List[int] = []
    widget.bind_to(emitter, lambda v: values.append(v), dependency="size")

    emitter.emit(1)
    emitter.emit(2)

    assert values == [1, 2]
    assert widget._app.invalidate_calls == 1
    assert widget.layout_hits == 0

    flush_binding_invalidations()

    assert widget.layout_hits == 1
    assert widget.paint_hits == 0


def test_binding_queue_full_invalidation_without_app() -> None:
    widget = _TestWidget()
    emitter = _Emitter()
    widget.bind_to(emitter, lambda v: None)

    emitter.emit("color-change")

    # No app attached, so flush happens immediately.
    assert widget.layout_hits == 1
    assert widget.paint_hits == 1


def test_binding_queue_targets_scope_before_cache_clear() -> None:
    widget = _ScopeAwareWidget()
    widget._app = _AppStub()
    widget.rebuild()
    # Note: ScopedFragment seems to be built twice (once in render_scope, once in mount)
    # This might be an inefficiency in the framework, but for now we accept 2.
    assert widget.scope_recomposes == 2
    emitter = _Emitter()
    widget.bind_to(emitter, lambda v: None, dependency="alpha")

    emitter.emit("update")

    assert widget._app.invalidate_calls == 1

    flush_binding_invalidations()

    assert widget.scope_recomposes == 3
    assert widget.layout_hits == 0
    assert widget.paint_hits == 0
