"""Initial-value contract for BindingHostMixin.observe / bind_to."""

from __future__ import annotations

from typing import Any, List

from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget, layout_depends_on, paint_depends_on
from nuiitivet.widgeting.widget_binding import flush_binding_invalidations


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


class _ValuelessEmitter:
    """A subscribe-only source: no `.value` to seed from."""

    def __init__(self) -> None:
        self._subs: List = []

    def subscribe(self, cb):
        self._subs.append(cb)

        class _Disposable:
            def dispose(self_inner) -> None:
                return None

        return _Disposable()

    def emit(self, value) -> None:
        for cb in list(self._subs):
            cb(value)


def test_bind_to_applies_current_value_immediately() -> None:
    widget = _TestWidget()
    widget._app = _AppStub()
    source = Observable("hello")
    seen: List[Any] = []

    widget.bind_to(source, seen.append, dependency="size")

    assert seen == ["hello"]


def test_bind_to_initial_apply_does_not_invalidate() -> None:
    """The seed runs before anything is cached, so it must not queue a frame."""
    widget = _TestWidget()
    widget._app = _AppStub()
    source = Observable("hello")

    widget.bind_to(source, lambda _v: None, dependency="size")

    assert widget._app.invalidate_calls == 0
    flush_binding_invalidations()
    assert widget.layout_hits == 0
    assert widget.paint_hits == 0


def test_bind_to_still_invalidates_on_change() -> None:
    widget = _TestWidget()
    widget._app = _AppStub()
    source = Observable("hello")
    seen: List[Any] = []

    widget.bind_to(source, seen.append, dependency="size")
    source.value = "world"

    assert seen == ["hello", "world"]
    assert widget._app.invalidate_calls == 1

    flush_binding_invalidations()

    assert widget.layout_hits == 1
    assert widget.paint_hits == 0


def test_bind_to_tolerates_source_without_value() -> None:
    widget = _TestWidget()
    widget._app = _AppStub()
    emitter = _ValuelessEmitter()
    seen: List[Any] = []

    widget.bind_to(emitter, seen.append, dependency="size")

    assert seen == []

    emitter.emit(1)

    assert seen == [1]


def test_observe_applies_current_value_and_disposes_on_unmount() -> None:
    widget = _TestWidget()
    source = Observable(1)
    seen: List[int] = []

    widget.observe(source, seen.append)
    assert seen == [1]

    source.value = 2
    assert seen == [1, 2]

    widget.on_unmount()
    source.value = 3
    assert seen == [1, 2]
