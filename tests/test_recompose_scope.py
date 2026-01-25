from __future__ import annotations

from nuiitivet.widgeting.widget import ComposableWidget, Widget, layout_depends_on, paint_depends_on
from nuiitivet.widgeting.widget_builder import ScopeHandle, flush_scope_recompositions
from nuiitivet.layout.column import Column
from nuiitivet.widgets.text import TextBase as Text


class ScopeHostWidget(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.header_value = "H0"
        self.body_value = "B0"
        self.header_builds = 0
        self.body_builds = 0
        self._header_scope: str | None = None
        self._body_scope: str | None = None
        self._header_handle: ScopeHandle | None = None
        self._body_handle: ScopeHandle | None = None

    def build(self) -> Widget:
        with self.scope("header") as header_handle:
            self._header_scope = header_handle.id
            self._header_handle = header_handle
            header = self.render_scope_with_handle(header_handle, self._build_header)
        with self.scope("body") as body_handle:
            self._body_scope = body_handle.id
            self._body_handle = body_handle
            body = self.render_scope_with_handle(body_handle, self._build_body)
        return Column([header, body], gap=0)

    def _build_header(self) -> Widget:
        self.header_builds += 1
        return Text(f"header:{self.header_value}")

    def _build_body(self) -> Widget:
        self.body_builds += 1
        return Text(f"body:{self.body_value}")

    def invalidate_header(self) -> None:
        if self._header_scope:
            self.invalidate_scope_id(self._header_scope)

    def invalidate_body(self) -> None:
        if self._body_scope:
            self.invalidate_scope_id(self._body_scope)

    def invalidate_header_handle(self) -> None:
        if self._header_handle is not None:
            self._header_handle.invalidate()


@layout_depends_on("alpha")
@paint_depends_on("beta")
class DependencyLeaf(Widget):
    def __init__(self) -> None:
        super().__init__()

    def build(self) -> Widget:
        return Text("dep")


class DependencyScopeWidget(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.scope_id: str | None = None
        self.body_builds = 0

    def build(self) -> Widget:
        with self.scope("dep") as handle:
            self.scope_id = handle.id
            return self.render_scope_with_handle(handle, self._build_dep)

    def _build_dep(self) -> Widget:
        self.body_builds += 1
        return DependencyLeaf()


class _AppStub:
    def __init__(self) -> None:
        self.invalidate_calls = 0

    def invalidate(self, immediate: bool = False) -> None:
        self.invalidate_calls += 1


def test_scope_rebuild_targets_single_fragment() -> None:
    widget = ScopeHostWidget()
    widget.rebuild()
    assert widget.header_builds == 1
    assert widget.body_builds == 1

    widget.header_value = "H1"
    widget.invalidate_header()
    assert widget.header_builds == 2
    assert widget.body_builds == 1

    widget.body_value = "B1"
    widget.invalidate_body()
    assert widget.header_builds == 2
    assert widget.body_builds == 2


def test_scope_handle_fallback_invalid_id_is_safe() -> None:
    widget = ScopeHostWidget()
    widget.rebuild()
    assert widget._handle_scope_invalidation("scope:missing") is False


def test_scope_metadata_tracks_child_and_factory() -> None:
    widget = ScopeHostWidget()
    widget.rebuild()
    assert widget._header_scope is not None
    meta = widget.get_scope_metadata(widget._header_scope)
    assert meta is not None
    meta_func = getattr(meta.factory, "__func__", meta.factory)
    widget_func = getattr(widget._build_header, "__func__", widget._build_header)
    assert meta_func is widget_func
    child = meta.child
    assert isinstance(child, Text)
    assert child.label == "header:H0"

    widget.header_value = "H1"
    widget.invalidate_header()
    meta_after = widget.get_scope_metadata(widget._header_scope)
    assert meta_after is not None
    updated_child = meta_after.child
    assert isinstance(updated_child, Text)
    assert updated_child.label == "header:H1"


def test_scope_metadata_indexes_dependencies() -> None:
    widget = DependencyScopeWidget()
    widget.rebuild()
    assert widget.scope_id is not None
    assert widget.body_builds == 1
    meta = widget.get_scope_metadata(widget.scope_id)
    assert meta is not None
    assert meta.layout_dependencies == ("alpha",)
    assert meta.paint_dependencies == ("beta",)
    scopes = widget._lookup_scope_ids_for_dependency("alpha")
    assert widget.scope_id in scopes
    scopes_beta = widget._lookup_scope_ids_for_dependency("beta")
    assert widget.scope_id in scopes_beta


def test_scope_invalidation_defers_until_flush_when_mounted() -> None:
    widget = ScopeHostWidget()
    widget.rebuild()
    app = _AppStub()
    widget._app = app
    assert widget._header_scope is not None

    widget.header_value = "H1"
    widget.invalidate_header()

    assert widget.header_builds == 1
    assert app.invalidate_calls == 1

    flush_scope_recompositions()

    assert widget.header_builds == 2


def test_dependency_name_routes_scope_rebuild() -> None:
    widget = DependencyScopeWidget()
    widget.rebuild()
    assert widget.body_builds == 1

    widget._handle_dependency_invalidation("alpha")

    assert widget.body_builds == 2


class HandleScopeWidget(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.builds = 0
        self.scope_handle: ScopeHandle | None = None

    def build(self) -> Widget:
        with self.scope("content") as handle:
            self.scope_handle = handle
            return self.render_scope_with_handle(handle, self._build_content)

    def _build_content(self) -> Widget:
        self.builds += 1
        return Text(f"content:{self.builds}")


def test_scope_handle_invalidate_triggers_targeted_rebuild() -> None:
    widget = HandleScopeWidget()
    widget.rebuild()
    assert widget.builds == 1
    assert widget.scope_handle is not None

    widget.scope_handle.invalidate()

    assert widget.builds == 2
