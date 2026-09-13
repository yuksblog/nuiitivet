"""Tests for layout mode -- the drags that rewrite a size or an order in the source.

The widgets under test are built from a real file so their construction sites
point at it, and the assertions read the file back: the mode's whole job is what
ends up written there.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

from nuiitivet.dev import landing, source
from nuiitivet.dev.layout_mode import LayoutMode
from nuiitivet.dev.select_mode import SelectMode
from nuiitivet.dev.selection import Selection
from nuiitivet.dev.source_edit import EditLog
from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text

_CHORD = MOD_CTRL | MOD_SHIFT

_APP = '''
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.modifiers.border import border
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.text import TextBase as Text

from layout_side import side

w = 100


class Square(Widget):
    def __init__(self, size=24):
        super().__init__(width=size, height=size)


def tile(label):
    return Text(label, width=100, height=40)


def build():
    return Column(children=[Text("AAA", width=100, height=40)], gap=0)


def build_bound():
    return Column(children=[Text("AAA", width=w, height=40)], gap=0)


def build_square():
    return Column(children=[Square(size=24)], gap=0)


def build_shared():
    return Column(children=[tile("a"), tile("b")], gap=0)


class Labeled(Column):
    def __init__(self, width=100, height=40):
        super().__init__(children=[Text("inner", width=50, height=20)], width=width, height=height, gap=0)


def build_labeled():
    return Column(children=[Labeled(width=100, height=40)], gap=0)


def build_list():
    return Column(children=[Text("AAA", width=100, height=40), Text("BBB", width=100, height=40), Text("CCC", width=100, height=40)], gap=0)  # noqa: E501


def build_row():
    return Row(children=[Text("AAA", width=100, height=40), Text("BBB", width=100, height=40), Text("CCC", width=100, height=40)], gap=0)  # noqa: E501


def build_flow():
    return Flow(children=[Text("AAA", width=100, height=40), Text("BBB", width=100, height=40), Text("CCC", width=100, height=40), Text("DDD", width=100, height=40)])  # noqa: E501


def build_for_each():
    return Column.builder(["a", "b", "c"], lambda item, index: Text(item, width=100, height=40), gap=0)


def build_comprehension():
    return Column(children=[Text(item, width=100, height=40) for item in ("a", "b")], gap=0)


def build_local_literal():
    tags = ["a", "b", "c"]
    return Column(children=[Text(tag, width=100, height=40) for tag in tags], gap=0)


def load():
    return ["a", "b", "c"]


def build_data_driven():
    return Column.builder(load(), lambda item, index: Text(item, width=100, height=40), gap=0)


def card(label):
    return Column(children=[Text(label, width=100, height=40), Text("x", width=100, height=40)], gap=0)


def build_cards():
    return Column(children=[card("a"), card("b")], gap=0)


def t(label):
    return Text(label, width=100, height=40)


def build_rows():
    return Column(children=[Row(children=[t("AAA"), t("BBB")], gap=0), Row(children=[t("CCC")], gap=0)], gap=0)


def build_empty_row():
    return Column(children=[Row(children=[t("AAA")], gap=0), Row(children=[], gap=0, width=100, height=40)], gap=0)


def build_from_stack():
    return Row(children=[Stack(children=[t("AAA"), t("BBB")], width=100, height=40), Column(children=[t("CCC")], gap=0)], gap=0)  # noqa: E501


def build_from_builder():
    return Column(children=[Row.builder(["a", "b"], lambda item, index: t(item), gap=0), Row(children=[t("CCC")], gap=0)], gap=0)  # noqa: E501


def build_into_comprehension():
    tags = ["a"]
    return Column(children=[Row(children=[t("AAA")], gap=0), Row(children=[t(tag) for tag in tags], gap=0)], gap=0)


def build_two_files():
    return Column(children=[Row(children=[t("AAA")], gap=0), side()], gap=0)


def build_wrapped():
    return Row(children=[Column(children=[t("AAA")], padding=10).modifier(border("#000", width=1)), Column(children=[t("BBB")], padding=10)], gap=0)  # noqa: E501
'''

_SIDE = '''
from nuiitivet.layout.row import Row
from nuiitivet.widgets.text import TextBase as Text


def side():
    return Row(children=[Text("SSS", width=100, height=40)], gap=0)
'''


class _App:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.invalidated = 0
        self._select_mode: Any = None
        self._layout_mode: Any = None

    def invalidate(self) -> None:
        self.invalidated += 1


@pytest.fixture
def app_file(tmp_path: Path) -> Iterator[Path]:
    """A user module on disk, imported with site capture on."""
    path = tmp_path / "layout_app.py"
    path.write_text(_APP, encoding="utf-8")
    (tmp_path / "layout_side.py").write_text(_SIDE, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    source.install()
    try:
        yield path
    finally:
        source.uninstall()
        sys.path.remove(str(tmp_path))
        sys.modules.pop("layout_app", None)
        sys.modules.pop("layout_side", None)


def _load(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("layout_app", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["layout_app"] = module
    spec.loader.exec_module(module)
    return module


class _Session:
    """A mode latched over a tree built from ``app_file``."""

    def __init__(self, path: Path, factory: str = "build", width: int = 300) -> None:
        self.path = path
        self.reloads: list[str] = []
        self.edits = EditLog()
        self.mode = LayoutMode(self.edits, request_reload=self.reloads.append)
        self.column = getattr(_load(path), factory)()
        self.host = mount(self.column)
        self.root = self.host.__enter__().root
        self.host.layout(width, 200)
        self.app = _App(self.root)
        self.app._layout_mode = self.mode
        self.mode.on_key_press(self.app, "e", _CHORD)

    def close(self) -> None:
        self.host.__exit__(None, None, None)

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def leaf(self) -> Any:
        return self.column.children[0]

    def hover(self, x: float, y: float) -> None:
        self.mode.on_mouse_motion(self.app, x, y)

    def drag_corner(self, start: tuple[float, float], end: tuple[float, float], mods: int = 0) -> None:
        self.mode.on_mouse_press(self.app, *start, mods)
        self.mode.on_mouse_motion(self.app, *end, mods)
        self.mode.on_mouse_release(self.app, *end, mods)

    drag_body = drag_corner


@pytest.fixture
def session(app_file: Path) -> Iterator[_Session]:
    s = _Session(app_file)
    try:
        yield s
    finally:
        s.close()


# --- latching -----------------------------------------------------------------


def test_the_chord_latches_the_mode_on() -> None:
    mode, app = LayoutMode(EditLog()), _App()

    assert mode.on_key_press(app, "e", _CHORD) is True
    assert mode.active is True


def test_the_meta_accelerator_also_enters() -> None:
    mode, app = LayoutMode(EditLog()), _App()

    mode.on_key_press(app, "e", MOD_META | MOD_SHIFT)

    assert mode.active is True


def test_a_bare_e_does_not_enter() -> None:
    mode, app = LayoutMode(EditLog()), _App()

    assert mode.on_key_press(app, "e", 0) is False
    assert mode.active is False


def test_escape_leaves() -> None:
    mode, app = LayoutMode(EditLog()), _App()
    mode.on_key_press(app, "e", _CHORD)

    assert mode.on_key_press(app, "escape", 0) is True
    assert mode.active is False


def test_every_key_is_consumed_while_latched_and_none_before() -> None:
    mode, app = LayoutMode(EditLog()), _App()
    assert mode.on_key_press(app, "a", 0) is False
    assert mode.on_key_release(app, "a", 0) is False
    mode.on_key_press(app, "e", _CHORD)

    assert mode.on_key_press(app, "a", 0) is True
    assert mode.on_key_release(app, "a", 0) is True


# --- switching with select mode -----------------------------------------------


def _through_layers(app: _App, key: str) -> None:
    """Offer a key the way the runner does: to each layer until one takes it."""
    for layer in (app._select_mode, app._layout_mode):
        if layer.on_key_press(app, key, _CHORD):
            return


def test_the_layout_chord_switches_out_of_select_mode_keeping_its_marks() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        selection = Selection()
        app._select_mode = SelectMode(selection)
        app._layout_mode = LayoutMode(EditLog())
        app._select_mode.on_key_press(app, "c", _CHORD)
        app._select_mode.on_mouse_press(app, 2, 2)
        app._select_mode.on_mouse_release(app, 2, 2)
        assert selection.members()

        _through_layers(app, "e")

        assert app._select_mode.active is False
        assert app._layout_mode.active is True
        assert selection.members(), "switching keeps the marks, as Enter does"


def test_the_select_chord_switches_out_of_layout_mode() -> None:
    app = _App()
    app._select_mode = SelectMode(Selection())
    app._layout_mode = LayoutMode(EditLog())
    app._layout_mode.on_key_press(app, "e", _CHORD)

    _through_layers(app, "c")

    assert app._layout_mode.active is False
    assert app._select_mode.active is True


def test_without_a_layout_mode_select_mode_keeps_consuming_the_chord() -> None:
    app = _App()
    app._select_mode = SelectMode(Selection())
    app._select_mode.on_key_press(app, "c", _CHORD)

    assert app._select_mode.on_key_press(app, "e", _CHORD) is True
    assert app._select_mode.active is True


# --- candidate and selection ----------------------------------------------------


def test_hovering_names_the_widget_under_the_cursor(session: _Session) -> None:
    session.hover(50, 20)

    assert session.mode.hovered is session.leaf()
    assert session.mode.candidate is session.leaf()


def test_a_click_selects_and_the_arrows_walk_the_tree(session: _Session) -> None:
    session.hover(50, 20)
    session.mode.on_mouse_press(session.app, 50, 20)
    session.mode.on_mouse_release(session.app, 50, 20)
    assert session.mode.selected is session.leaf()

    session.mode.on_key_press(session.app, "up", 0)
    assert session.mode.selected is session.column
    assert session.mode.candidate is session.column, "the selection outranks the hover"

    session.mode.on_key_press(session.app, "down", 0)
    assert session.mode.selected is session.leaf()


def test_moving_off_the_selection_releases_it_and_hover_takes_over(session: _Session) -> None:
    """A selection exists to reach a container through its children; leaving
    it is how it ends, so hover never gets stuck behind a click."""
    session.hover(50, 20)
    session.mode.on_mouse_press(session.app, 50, 20)
    session.mode.on_mouse_release(session.app, 50, 20)
    assert session.mode.candidate is session.leaf()

    session.hover(200, 150)

    assert session.mode.selected is None
    assert session.mode.candidate is session.column, "hover drives the candidate again"


def test_the_selection_survives_the_pointer_crossing_its_children(session: _Session) -> None:
    """Walking up to the column and heading for its corner passes over the leaf."""
    session.hover(50, 20)
    session.mode.on_mouse_press(session.app, 50, 20)
    session.mode.on_mouse_release(session.app, 50, 20)
    session.mode.on_key_press(session.app, "up", 0)
    assert session.mode.selected is session.column

    session.hover(80, 30)
    assert session.mode.candidate is session.column
    session.hover(305, 205)
    assert session.mode.candidate is session.column, "the corner grab zone counts as on it"

    session.hover(50, 260)
    assert session.mode.selected is None


# --- the corner drag ------------------------------------------------------------


def test_a_corner_drag_writes_the_new_width_and_asks_for_a_reload(session: _Session) -> None:
    session.hover(50, 20)

    session.drag_corner((100, 40), (160, 40))

    assert 'Text("AAA", width=160, height=40)' in session.text()
    assert session.reloads == [str(session.path)]
    assert session.edits.pending is not None
    assert session.mode.ghosts, "the ghost stays until the reload lands"


def test_an_axis_left_where_it_was_is_not_rewritten(session: _Session) -> None:
    session.hover(50, 20)

    session.drag_corner((100, 40), (100, 90))

    assert 'Text("AAA", width=100, height=90)' in session.text()


def test_dragging_to_the_intrinsic_width_lands_on_auto(session: _Session) -> None:
    natural = landing.intrinsic_size(session.leaf())[0]
    session.hover(50, 20)

    session.drag_corner((100, 40), (natural + 2, 40))

    assert 'width="auto"' in session.text()


def test_dragging_to_the_weight_width_lands_on_wt(session: _Session) -> None:
    session.hover(50, 20)

    session.drag_corner((100, 40), (298, 40))

    assert 'width="wt"' in session.text()


def test_alt_lands_on_the_integer_under_the_pointer(session: _Session) -> None:
    natural = landing.intrinsic_size(session.leaf())[0]
    session.hover(50, 20)

    session.drag_corner((100, 40), (natural + 2, 40), MOD_ALT)

    assert f"width={natural + 2}," in session.text()


def test_the_top_left_corner_resizes_too(session: _Session) -> None:
    session.hover(50, 20)

    session.drag_corner((0, 0), (20, 0))

    assert "width=80," in session.text()


def test_a_press_on_a_corner_that_does_not_travel_selects(session: _Session) -> None:
    session.hover(50, 20)
    before = session.text()

    session.drag_corner((100, 40), (101, 41))

    assert session.text() == before
    assert session.mode.selected is session.leaf()


def test_escape_cancels_the_drag_in_flight(session: _Session) -> None:
    session.hover(50, 20)
    before = session.text()
    session.mode.on_mouse_press(session.app, 100, 40)
    session.mode.on_mouse_motion(session.app, 160, 40)
    assert session.mode.dragging

    session.mode.on_key_press(session.app, "escape", 0)

    assert session.mode.dragging is False
    assert session.mode.active is True
    session.mode.on_mouse_release(session.app, 160, 40)
    assert session.text() == before


def test_the_ghost_follows_the_drag(session: _Session) -> None:
    session.hover(50, 20)
    session.mode.on_mouse_press(session.app, 100, 40)
    session.mode.on_mouse_motion(session.app, 160, 40)

    [ghost] = session.mode.ghosts

    assert ghost.rect == (0.0, 0.0, 160.0, 40.0)
    assert ghost.caption.startswith("w 160")
    session.mode.on_key_press(session.app, "escape", 0)


# --- the size keyword -----------------------------------------------------------


def test_a_size_widget_takes_the_larger_delta_and_stays_square(app_file: Path) -> None:
    s = _Session(app_file, "build_square")
    try:
        s.hover(12, 12)

        s.drag_corner((24, 24), (44, 29))

        assert "Square(size=44)" in s.text()
        [ghost] = s.mode.ghosts
        assert ghost.rect[2:] == (44.0, 44.0)
    finally:
        s.close()


# --- refusals -------------------------------------------------------------------


def test_a_bound_value_is_refused_with_its_name(app_file: Path) -> None:
    s = _Session(app_file, "build_bound")
    try:
        before = s.text()
        s.hover(50, 20)

        s.drag_corner((100, 40), (160, 40))

        assert s.text() == before
        assert s.mode.notice == "width is bound to w"
        assert s.reloads == []
    finally:
        s.close()


def test_a_notice_clears_on_the_next_press(app_file: Path) -> None:
    s = _Session(app_file, "build_bound")
    try:
        s.hover(50, 20)
        s.drag_corner((100, 40), (160, 40))
        assert s.mode.notice

        s.mode.on_mouse_press(s.app, 50, 20)

        assert s.mode.notice is None
    finally:
        s.close()


def test_a_widget_without_a_site_is_refused() -> None:
    leaf = Text("AAA", width=100, height=40)
    with mount(Column(children=[leaf], gap=0)) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = LayoutMode(EditLog())
        mode.on_key_press(app, "e", _CHORD)
        mode.on_mouse_motion(app, 50, 20)

        mode.on_mouse_press(app, 100, 40)
        mode.on_mouse_motion(app, 160, 40)
        mode.on_mouse_release(app, 160, 40)

        assert mode.notice == "no source recorded for this widget"


# --- shared sites ---------------------------------------------------------------


def test_a_shared_site_ghosts_every_instance_and_counts_them(app_file: Path) -> None:
    s = _Session(app_file, "build_shared")
    try:
        s.hover(50, 20)
        s.mode.on_mouse_press(s.app, 100, 40)
        s.mode.on_mouse_motion(s.app, 160, 40)

        ghosts = s.mode.ghosts

        assert len(ghosts) == 2
        assert "2 widgets" in ghosts[0].caption
        assert ghosts[1].rect == (0.0, 40.0, 160.0, 40.0)

        s.mode.on_mouse_release(s.app, 160, 40)
        assert "Text(label, width=160, height=40)" in s.text()
        assert s.edits.pending is not None and s.edits.pending.instances == 2
    finally:
        s.close()


def test_a_pointer_on_a_child_the_widget_built_for_itself_means_the_widget(app_file: Path) -> None:
    """A button's label carries the button's site. Dragging the label's corner
    must resize the button by the button's size, not write the label's few
    pixels into the button's ``width``."""
    s = _Session(app_file, "build_labeled")
    try:
        s.hover(25, 10)
        assert type(s.mode.hovered).__name__ == "Labeled", "the owner, not the inner Text"

        s.drag_corner((100, 40), (160, 40))

        assert "Labeled(width=160, height=40)" in s.text()
        assert "inner" in s.text() and 'width=50, height=20' in s.text(), "the label call is untouched"

        s.mode.on_mouse_press(s.app, 25, 10)
        s.mode.on_mouse_release(s.app, 25, 10)
        assert type(s.mode.selected).__name__ == "Labeled", "a click on the label selects the owner"
        s.mode.on_key_press(s.app, "down", 0)
        assert type(s.mode.selected).__name__ == "Labeled", "there is nothing below it with a call of its own"
    finally:
        s.close()


def test_the_children_a_widget_builds_for_itself_get_no_ghost(app_file: Path) -> None:
    """A button's label carries the button's site; resizing the button must
    not ghost the label at the button's size."""
    s = _Session(app_file, "build_labeled")
    try:
        s.hover(80, 35)
        assert type(s.mode.hovered).__name__ == "Labeled"
        s.mode.on_mouse_press(s.app, 100, 40)
        s.mode.on_mouse_motion(s.app, 160, 40)

        ghosts = s.mode.ghosts

        assert len(ghosts) == 1
        assert "widgets" not in ghosts[0].caption
        s.mode.on_mouse_release(s.app, 160, 40)
        assert "Labeled(width=160, height=40)" in s.text()
        assert s.edits.pending is not None and s.edits.pending.instances == 1
    finally:
        s.close()


# --- the body drag ---------------------------------------------------------------


def _list(path: Path, factory: str, width: int = 300) -> _Session:
    s = _Session(path, factory, width)
    s.hover(50, 20)
    return s


def _written(s: _Session, factory: str) -> str:
    """The children list of ``factory`` as written, whitespace collapsed."""
    text = s.text()
    start = text.index("[", text.index(f"def {factory}"))
    return " ".join(text[start : text.index("]", start) + 1].split())


def _lines(ghosts: list[Any]) -> list[Any]:
    """The insertion lines among the ghosts, the wash over the landing list left out."""
    return [g for g in ghosts if g.shape == "line"]


def test_a_body_drag_down_a_column_moves_the_child_past_the_siblings_it_crossed(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    try:
        s.drag_body((50, 20), (50, 100))

        assert _written(s, "build_list").startswith('[Text("BBB", width=100, height=40), Text("AAA"')
        assert s.reloads == [str(s.path)]
        assert s.edits.pending is not None and s.edits.pending.kind == "move"
        assert s.mode.selected is None, "the moved widget's path changes with the reload"
        assert _lines(s.mode.ghosts), "the ghost stays until the reload lands"
    finally:
        s.close()


def test_the_ghost_is_an_insertion_line_before_the_next_sibling(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 100)

        assert [g.shape for g in s.mode.ghosts] == ["wash", "line"], "the column washed, one line in it"
        ghosts = _lines(s.mode.ghosts)
        x, y, w, h = ghosts[0].rect
        assert (x, w, h) == (0.0, 300.0, 0.0), "across the column, no thickness"
        assert 77.0 <= y <= 80.0, "in the gap above CCC"
        assert ghosts[0].caption == "before TextBase CCC"
        s.mode.on_key_press(s.app, "escape", 0)
    finally:
        s.close()


def test_the_last_slot_is_captioned_to_the_end(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 119)

        assert _lines(s.mode.ghosts)[0].caption == "to the end"
        s.mode.on_mouse_release(s.app, 50, 119)
        assert _written(s, "build_list").endswith('Text("AAA", width=100, height=40)]')
    finally:
        s.close()


def test_cross_axis_travel_in_a_column_has_no_reading(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    before = s.text()
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 200, 30)
        assert s.mode.dragging and [g.shape for g in s.mode.ghosts] == ["wash"], "the column washed, no line"

        s.mode.on_mouse_release(s.app, 200, 30)

        assert s.text() == before
        assert s.mode.notice is None
        assert s.reloads == []
    finally:
        s.close()


def test_the_childs_own_slot_shows_no_line_and_release_there_is_silent(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    before = s.text()
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 30)
        assert s.mode.dragging and [g.shape for g in s.mode.ghosts] == ["wash"], "the column washed, no line"

        s.mode.on_mouse_release(s.app, 50, 30)

        assert s.text() == before
        assert s.mode.notice is None
    finally:
        s.close()


def test_a_body_drag_along_a_row_reorders_too(app_file: Path) -> None:
    s = _list(app_file, "build_row")
    try:
        s.drag_body((50, 20), (250, 20))

        assert _written(s, "build_row").startswith('[Text("BBB", width=100, height=40), Text("AAA"')
    finally:
        s.close()


def test_a_container_wrapped_by_a_modifier_moves_as_its_wrapped_element(app_file: Path) -> None:
    """Pressing a Column's own padding grabs the Column; the ``.modifier()`` box around it is
    the list element, so the whole expression moves. The pointer lands past the
    other Column, over the Row, since inside it the drag would read as a move
    into it."""
    s = _Session(app_file, "build_wrapped")
    try:
        s.hover(60, 5)
        s.drag_body((60, 5), (250, 5))

        text = s.text()
        line = text[text.index("return Row", text.index("def build_wrapped")) :].splitlines()[0]
        assert line.startswith(
            'return Row(children=[Column(children=[t("BBB")], padding=10), '
            'Column(children=[t("AAA")], padding=10).modifier(border("#000", width=1))], gap=0)'
        )
    finally:
        s.close()


def test_a_body_drag_in_a_flow_reads_by_row_then_by_column(app_file: Path) -> None:
    """At 250 wide the flow wraps CCC and DDD onto a second row; dragging CCC up
    and to the left of AAA puts it first."""
    s = _list(app_file, "build_flow", width=250)
    try:
        s.hover(50, 60)
        s.drag_body((50, 60), (40, 10))

        assert _written(s, "build_flow").startswith('[Text("CCC", width=100, height=40), Text("AAA"')
    finally:
        s.close()


def test_the_line_at_a_flows_line_break_follows_the_pointers_row(app_file: Path) -> None:
    """The slot after BBB and before CCC is one slot; the line sits at the end
    of the first row or the start of the second, whichever row the pointer is on."""
    s = _list(app_file, "build_flow", width=250)
    try:
        s.hover(150, 60)
        s.mode.on_mouse_press(s.app, 150, 60)

        s.mode.on_mouse_motion(s.app, 230, 20)
        end_of_row = _lines(s.mode.ghosts)[0].rect
        s.mode.on_mouse_motion(s.app, 5, 45)
        start_of_row = _lines(s.mode.ghosts)[0].rect

        assert end_of_row == (203.0, 0.0, 0.0, 40.0), "after BBB, on the first row"
        assert start_of_row == (-3.0, 40.0, 0.0, 40.0), "before CCC, on the second"
        assert _lines(s.mode.ghosts)[0].caption == "before TextBase CCC"
        s.mode.on_key_press(s.app, "escape", 0)
    finally:
        s.close()


def test_children_built_by_a_builder_over_a_literal_are_reordered_in_the_literal(app_file: Path) -> None:
    s = _list(app_file, "build_for_each")
    try:
        s.drag_body((50, 20), (50, 100))

        assert 'Column.builder(["b", "a", "c"], lambda' in s.text()
        assert s.edits.pending is not None and s.edits.pending.child == "TextBase"
    finally:
        s.close()


def test_a_comprehension_over_a_literal_bound_in_the_function_is_reordered_there(app_file: Path) -> None:
    s = _list(app_file, "build_local_literal")
    try:
        s.drag_body((50, 20), (50, 100))

        assert 'tags = ["b", "a", "c"]' in s.text()
    finally:
        s.close()


def test_a_comprehension_over_an_inline_tuple_is_reordered_in_the_tuple(app_file: Path) -> None:
    s = _list(app_file, "build_comprehension")
    try:
        s.drag_body((50, 20), (50, 70))

        assert 'for item in ("b", "a")]' in s.text()
    finally:
        s.close()


def test_children_whose_order_is_not_in_a_literal_are_refused_on_release(app_file: Path) -> None:
    s = _list(app_file, "build_data_driven")
    before = s.text()
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 100)
        assert s.mode.ghosts, "the source decides, so the ghost shows until release"

        s.mode.on_mouse_release(s.app, 50, 100)

        assert s.text() == before
        assert s.mode.notice == "items are the result of load(...), not one list"
    finally:
        s.close()


def test_a_shared_container_site_ghosts_every_instance_and_moves_them_all(app_file: Path) -> None:
    s = _list(app_file, "build_cards")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 70)

        assert [g.shape for g in s.mode.ghosts] == ["wash", "wash", "line", "line"], "both cards washed and lined"
        ghosts = _lines(s.mode.ghosts)
        assert ghosts[0].caption == "to the end  ·  2 widgets"
        assert ghosts[1].rect[1] > 80.0, "the second card's line"

        s.mode.on_mouse_release(s.app, 50, 70)
        assert _written(s, "card") == '[Text("x", width=100, height=40), Text(label, width=100, height=40)]'
        assert s.edits.pending is not None and s.edits.pending.instances == 2
    finally:
        s.close()


def test_ctrl_z_reverts_a_move(app_file: Path) -> None:
    s = _list(app_file, "build_list")
    before = s.text()
    try:
        s.drag_body((50, 20), (50, 100))
        assert s.text() != before

        s.mode.on_key_press(s.app, "z", MOD_CTRL)

        assert s.text() == before
        assert s.mode.notice == "undoing TextBase → position 2"
    finally:
        s.close()


# --- the move into another container ----------------------------------------------


def _rows(s: _Session) -> str:
    """The two rows of ``build_rows`` as written, whitespace collapsed."""
    text = s.text()
    start = text.index("Column(children=[Row(", text.index("def build_rows"))
    return " ".join(text[start : text.index("\n", start)].split())


def test_a_body_drag_over_another_row_moves_the_child_into_it(app_file: Path) -> None:
    """AAA leaves the first row for the second, after CCC; the second row is
    the deepest container under the pointer, so the drag is a move."""
    s = _list(app_file, "build_rows")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 90, 60)
        shapes = [g.shape for g in s.mode.ghosts]
        assert shapes == ["wash", "line"], "the destination is washed and the slot marked"
        assert s.mode.ghosts[1].caption == "into Row, to the end"

        s.mode.on_mouse_release(s.app, 90, 60)

        assert _rows(s) == (
            'Column(children=[Row(children=[t("BBB")], gap=0), Row(children=[t("CCC"), t("AAA")], gap=0)], gap=0)'
        )
        assert s.edits.pending is not None and s.edits.pending.destination is not None
        assert s.mode.selected is None
    finally:
        s.close()


def test_returning_to_the_own_row_restores_the_reorder_reading(app_file: Path) -> None:
    s = _list(app_file, "build_rows")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 60)
        washes = [g.rect for g in s.mode.ghosts if g.shape == "wash"]
        assert washes and washes[0][1] == 40.0, "the wash is over the other row"

        s.mode.on_mouse_motion(s.app, 190, 20)

        assert [g.shape for g in s.mode.ghosts] == ["wash", "line"]
        assert s.mode.ghosts[0].rect[1] == 0.0, "the wash is back over the own row"
        assert s.mode.ghosts[1].caption == "to the end"
        s.mode.on_key_press(s.app, "escape", 0)
    finally:
        s.close()


def test_an_empty_container_takes_the_child_at_its_one_slot(app_file: Path) -> None:
    s = _list(app_file, "build_empty_row")
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 60)
        line = next(g for g in s.mode.ghosts if g.shape == "line")
        assert line.rect == (3.0, 40.0, 0.0, 40.0), "at the start of the empty row's content box"

        s.mode.on_mouse_release(s.app, 50, 60)

        assert 'Row(children=[], gap=0), Row(children=[t("AAA")], gap=0, width=100, height=40)' in s.text()
    finally:
        s.close()


def test_a_stack_child_cannot_be_reordered_but_can_leave(app_file: Path) -> None:
    s = _Session(app_file, "build_from_stack")
    try:
        s.hover(50, 20)
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 30)
        assert s.mode.ghosts == [], "no in-place reading inside a Stack"
        assert s.mode.notice == "Stack children have no order to drag; drop it in a Column, Row, Flow or UniformFlow"

        s.mode.on_mouse_motion(s.app, 150, 30)
        assert s.mode.notice is None and any(g.shape == "wash" for g in s.mode.ghosts), "over the Column, a move"
        s.mode.on_mouse_release(s.app, 150, 30)

        text = s.text()
        assert "Stack(children=[t(" in text and text.count('t("CCC"), t("') == 1
        assert 'Column(children=[t("CCC"), t("' in text
    finally:
        s.close()


def test_a_child_built_from_data_is_blocked_from_leaving_while_the_pointer_is_elsewhere(app_file: Path) -> None:
    s = _list(app_file, "build_from_builder")
    before = s.text()
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 50, 60)

        assert s.mode.ghosts == []
        assert s.mode.notice == "the children come from Row.builder(); the child has no expression of its own to move"

        s.mode.on_mouse_release(s.app, 50, 60)
        assert s.text() == before
    finally:
        s.close()


def test_a_destination_built_from_data_is_blocked_while_the_pointer_is_over_it(app_file: Path) -> None:
    """The reverse: dragging CCC into the builder-built row."""
    s = _Session(app_file, "build_from_builder")
    try:
        s.hover(50, 60)
        s.mode.on_mouse_press(s.app, 50, 60)
        s.mode.on_mouse_motion(s.app, 150, 20)

        assert s.mode.ghosts == []
        assert s.mode.notice == "the destination's children come from Row.builder(); it cannot take a widget"
        s.mode.on_key_press(s.app, "escape", 0)
    finally:
        s.close()


def test_a_comprehension_destination_is_blocked_while_the_pointer_is_over_it(app_file: Path) -> None:
    """The tree sees a plain row; the source, read as the pointer enters, says otherwise."""
    s = _list(app_file, "build_into_comprehension")
    before = s.text()
    try:
        s.mode.on_mouse_press(s.app, 50, 20)
        s.mode.on_mouse_motion(s.app, 90, 60)

        assert s.mode.ghosts == []
        assert s.mode.notice == "the destination's children come from a comprehension; it cannot take a widget"

        s.mode.on_mouse_release(s.app, 90, 60)
        assert s.text() == before
    finally:
        s.close()


def test_a_move_into_a_container_built_in_another_file_writes_both_and_undoes_both(app_file: Path) -> None:
    s = _list(app_file, "build_two_files")
    side_path = app_file.parent / "layout_side.py"
    before_app, before_side = s.text(), side_path.read_text(encoding="utf-8")
    try:
        s.drag_body((50, 20), (90, 60))

        assert 'Row(children=[], gap=0), side()' in s.text()
        side_after = side_path.read_text(encoding="utf-8")
        assert 'Row(children=[Text("SSS", width=100, height=40), t("AAA")], gap=0)' in side_after
        assert s.reloads == [str(s.path)]

        s.mode.on_key_press(s.app, "z", MOD_CTRL)

        assert s.text() == before_app
        assert side_path.read_text(encoding="utf-8") == before_side
        assert s.mode.notice == "undoing TextBase → Row"
    finally:
        s.close()


def test_an_undo_across_two_files_is_refused_when_either_moved(app_file: Path) -> None:
    s = _list(app_file, "build_two_files")
    side_path = app_file.parent / "layout_side.py"
    try:
        s.drag_body((50, 20), (90, 60))
        side_path.write_text("# a hand edit\n" + side_path.read_text(encoding="utf-8"), encoding="utf-8")
        app_after = s.text()

        s.mode.on_key_press(s.app, "z", MOD_CTRL)

        assert s.text() == app_after, "neither file is touched"
        assert s.mode.notice == "cannot undo: layout_side.py changed under the edit"
    finally:
        s.close()


# --- undo -----------------------------------------------------------------------


def test_ctrl_z_reverts_the_last_edit(session: _Session) -> None:
    session.hover(50, 20)
    session.drag_corner((100, 40), (160, 40))
    assert "width=160" in session.text()

    session.mode.on_key_press(session.app, "z", MOD_CTRL)

    assert 'Text("AAA", width=100, height=40)' in session.text()
    assert len(session.reloads) == 2
    assert session.mode.notice is not None and "undoing" in session.mode.notice


def test_ghosts_clear_once_the_reload_lands(session: _Session) -> None:
    session.hover(50, 20)
    session.drag_corner((100, 40), (160, 40))
    assert session.mode.ghosts

    session.edits.after_reload([session.root])

    assert session.mode.ghosts == []


def test_hover_and_selection_move_to_the_rebuilt_tree_when_the_reload_lands(session: _Session) -> None:
    """The old widgets outlive the reload for a while and still report their old
    rects; left as they were, the brackets would show the size from before."""
    session.hover(50, 20)
    session.drag_corner((100, 40), (160, 40))
    old_leaf = session.leaf()
    assert session.mode.candidate is old_leaf, "the resized widget stays the candidate"
    new_column = _load(session.path).build()
    with mount(new_column) as host:
        host.layout(300, 200)
        session.app.root = host.root

        session.edits.after_reload([host.root])

        assert session.mode.candidate is new_column.children[0]
        assert session.mode.hovered is not old_leaf
        assert session.mode.hovered in (new_column, new_column.children[0])


def test_a_reload_outcome_shows_as_the_notice(session: _Session) -> None:
    session.hover(50, 20)
    session.drag_corner((100, 40), (160, 40))

    session.edits.after_reload([session.root])

    assert session.mode.notice == "width landed at 100, expected 160"
