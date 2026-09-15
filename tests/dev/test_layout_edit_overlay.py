"""Tests for the layout-mode overlay.

Same load-bearing property as the selection overlay: nothing here enters the
widget tree, so the assistant's perception never sees a ghost.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet._interaction.perception import describe_tree
from nuiitivet.dev import layout_edit_overlay as lo
from nuiitivet.dev.layout_edit_mode import LayoutEditMode
from nuiitivet.dev.source_edit import EditLog
from nuiitivet.input.codes import MOD_CTRL, MOD_SHIFT
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text

_ENTER = MOD_CTRL | MOD_SHIFT


class _Canvas:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def _record(*_args: Any, **_kwargs: Any) -> None:
            self.calls.append(name)

        return _record


class _IME:
    def __init__(self) -> None:
        self.rects: list[tuple[float, float, float, float]] = []

    def update_cursor_rect(self, x: float, y: float, width: float, height: float) -> None:
        self.rects.append((x, y, width, height))


class _App:
    def __init__(self, root: Any, mode: Any = None, jump: Any = None) -> None:
        self.root = root
        self.width = 300
        self.height = 200
        self.modifier_keys = 0
        self._layout_edit_mode = mode
        self._source_jump = jump
        self.ime = _IME()

    def invalidate(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NUIITIVET_DEV_ACTION_OVERLAY", raising=False)


@pytest.fixture
def latched() -> Iterator[tuple[_App, LayoutEditMode]]:
    with mount(Column(children=[Text("AAA", width=100, height=40)])) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())
        app = _App(host.root, mode)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_mouse_motion(app, 50, 20)
        yield (app, mode)


def test_the_overlay_never_enters_the_widget_tree(latched: tuple[_App, LayoutEditMode]) -> None:
    app, _mode = latched
    before = describe_tree(app.root)

    lo.paint_layout_edit(app, _Canvas(), app.width, app.height)

    assert describe_tree(app.root) == before


def test_paints_nothing_without_a_mode() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        lo.paint_layout_edit(_App(host.root), canvas, 300, 200)

        assert canvas.calls == []


def test_paints_nothing_while_off() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        lo.paint_layout_edit(_App(host.root, LayoutEditMode(EditLog())), canvas, 300, 200)

        assert canvas.calls == []


def test_the_badge_and_the_candidate_paint_while_latched(latched: tuple[_App, LayoutEditMode]) -> None:
    app, _mode = latched
    canvas = _Canvas()

    lo.paint_layout_edit(app, canvas, app.width, app.height)

    assert "drawRoundRect" in canvas.calls, "the badge"
    assert "drawLine" in canvas.calls, "the candidate's brackets"


def test_the_ghost_paints_as_a_dashed_rect_while_dragging(latched: tuple[_App, LayoutEditMode]) -> None:
    app, mode = latched
    mode.on_mouse_press(app, 100, 40)
    mode.on_mouse_motion(app, 160, 40)
    canvas = _Canvas()

    lo.paint_layout_edit(app, canvas, app.width, app.height)

    assert "drawRect" in canvas.calls
    assert "drawLine" not in canvas.calls, "the brackets yield to the ghost mid-drag"
    mode.on_key_press(app, "escape", 0)


def test_a_reorder_ghost_paints_as_a_line() -> None:
    with mount(Column(children=[Text("AAA", width=100, height=40), Text("BBB", width=100, height=40)])) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())
        app = _App(host.root, mode)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_mouse_motion(app, 50, 20)
        mode.on_mouse_press(app, 50, 20)
        mode.on_mouse_motion(app, 50, 70)
        canvas = _Canvas()

        lo.paint_layout_edit(app, canvas, app.width, app.height)

        assert "drawLine" in canvas.calls, "the insertion line"
        assert canvas.calls.count("drawRect") == 2, "the wash's fill and edge over the own container; no size outline"
        mode.on_key_press(app, "escape", 0)


def test_a_move_into_another_container_washes_it_and_marks_the_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.dev import layout_edit_mode
    from nuiitivet.layout.row import Row

    # No source is recorded here; the gate that reads it is the mode's test.
    monkeypatch.setattr(layout_edit_mode, "_list_refusal", lambda container, role: None)
    rows = [Row(children=[Text("AAA", width=100, height=40)]), Row(children=[Text("BBB", width=100, height=40)])]
    with mount(Column(children=rows)) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())
        app = _App(host.root, mode)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_mouse_motion(app, 50, 20)
        mode.on_mouse_press(app, 50, 20)
        mode.on_mouse_motion(app, 90, 60)
        canvas = _Canvas()

        lo.paint_layout_edit(app, canvas, app.width, app.height)

        assert "drawRect" in canvas.calls, "the wash over the destination"
        assert "drawLine" in canvas.calls, "the insertion line"
        mode.on_key_press(app, "escape", 0)


def test_a_move_to_another_grid_cell_paints_the_cell_inside_the_wash(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.dev import layout_edit_mode
    from nuiitivet.layout.grid import Grid, GridItem

    # No source is recorded here; the gate that reads it is the mode's test.
    monkeypatch.setattr(layout_edit_mode, "_item_refusal", lambda item: None)
    monkeypatch.setattr(layout_edit_mode, "_list_refusal", lambda container, role: None)
    grid = Grid(children=[GridItem(Text("AAA", width=100, height=40), row=0, column=0)], rows=[40, 40], columns=[100])
    with mount(grid) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())
        app = _App(host.root, mode)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_mouse_motion(app, 50, 20)
        mode.on_mouse_press(app, 50, 20)
        mode.on_mouse_motion(app, 50, 60)
        canvas = _Canvas()

        lo.paint_layout_edit(app, canvas, app.width, app.height)

        assert canvas.calls.count("drawRect") == 4, "the grid's wash and the cell's tint, each a fill and an edge"
        assert "drawLine" not in canvas.calls, "a cell, not a slot"
        mode.on_key_press(app, "escape", 0)


def test_the_candidate_yields_to_the_source_jump_while_its_chord_is_held() -> None:
    """The jump's rose brackets are painted underneath; a teal wash over them
    reads as grey, and the click is a jump anyway."""
    from nuiitivet.dev.source_jump import SourceJump

    with mount(Column(children=[Text("AAA", width=100, height=40)])) as host:
        host.layout(300, 200)
        mode, jump = LayoutEditMode(EditLog()), SourceJump()
        app = _App(host.root, mode, jump)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_mouse_motion(app, 50, 20)
        app.modifier_keys = _ENTER
        jump.on_mouse_motion(app, 50, 20)
        assert jump.hovered is not None
        canvas = _Canvas()

        lo.paint_layout_edit(app, canvas, app.width, app.height)

        assert "drawLine" not in canvas.calls and "drawRect" not in canvas.calls
        assert "drawRoundRect" in canvas.calls, "the badge stays"


def test_the_env_kill_switch_disables_it(latched: tuple[_App, LayoutEditMode], monkeypatch: pytest.MonkeyPatch) -> None:
    app, _mode = latched
    monkeypatch.setenv("NUIITIVET_DEV_ACTION_OVERLAY", "0")
    canvas = _Canvas()

    lo.paint_layout_edit(app, canvas, app.width, app.height)

    assert canvas.calls == []


def test_painting_never_raises_on_a_broken_canvas(latched: tuple[_App, LayoutEditMode]) -> None:
    class _Broken:
        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("boom")

    app, _mode = latched

    lo.paint_layout_edit(app, _Broken(), app.width, app.height)


def test_the_badge_names_the_mode_its_exit_and_the_switch(
    latched: tuple[_App, LayoutEditMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first line is the one that never goes away, so the way out and the
    way across live there."""
    from nuiitivet.dev.hud import SEPARATOR

    app, mode = latched
    seen: dict[str, Any] = {}
    monkeypatch.setattr(lo, "paint_hud", lambda *args, **kwargs: seen.update(kwargs))

    lo.paint_layout_edit(app, _Canvas(), app.width, app.height)

    assert seen["mode_line"] == SEPARATOR.join(
        ("LAYOUT EDIT", "release writes the source", "Esc leave", "Ctrl+Shift+D designate")
    )
    assert seen["hints"] == mode.hints
    assert seen["placement"] is mode.placement


def test_a_notice_outliving_the_mode_still_paints(monkeypatch: pytest.MonkeyPatch) -> None:
    """An edit written just before leaving reports through the same box."""
    with mount(Column(children=[Text("AAA", width=100, height=40)])) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())
        app = _App(host.root, mode)
        mode.on_key_press(app, "e", _ENTER)
        mode.on_key_press(app, "escape", 0)
        monkeypatch.setattr(type(mode), "notice", property(lambda self: "width landed at 100, expected 160"))
        seen: dict[str, Any] = {}
        monkeypatch.setattr(lo, "paint_hud", lambda *args, **kwargs: seen.update(kwargs))

        lo.paint_layout_edit(app, _Canvas(), app.width, app.height)

        assert seen["mode_line"] is None and seen["notices"] == ["width landed at 100, expected 160"]


def test_the_open_field_paints_over_the_widget() -> None:
    """The field needs the widget's site, so the tree is built with capture on."""
    from nuiitivet.dev import source

    source.install()
    try:
        with mount(Column(children=[Text("AAA", width=100, height=40)])) as host:
            host.layout(300, 200)
            mode = LayoutEditMode(EditLog())
            app = _App(host.root, mode)
            mode.on_key_press(app, "e", _ENTER)
            mode.on_mouse_motion(app, 50, 20)
            mode.on_mouse_press(app, 50, 20)
            mode.on_mouse_release(app, 50, 20)
            mode.on_key_press(app, "enter", 0)
            assert mode.editor is not None, mode.notice
            canvas = _Canvas()

            lo.paint_layout_edit(app, canvas, app.width, app.height)

            assert canvas.calls.count("drawRoundRect") >= 3, "the field's box and edge, plus the badge"
            assert "drawTextBlob" in canvas.calls and "drawLine" in canvas.calls, "the text and the caret"
            assert app.ime.rects, "the caret's rect reaches the IME, so the candidate window opens beside it"
            assert app.ime.rects[-1][0] > 0.0 and app.ime.rects[-1][3] > 0.0

            lines_with_caret = canvas.calls.count("drawLine")
            mode.on_key_press(app, "a", MOD_CTRL)
            canvas = _Canvas()
            lo.paint_layout_edit(app, canvas, app.width, app.height)

            assert canvas.calls.count("drawRect") == 2, "the candidate's wash, and the selection's highlight"
            assert canvas.calls.count("drawLine") == lines_with_caret - 1, "no caret while text is selected"
    finally:
        source.uninstall()


def test_the_layer_list_ends_with_the_keys_that_pick_one() -> None:
    """The keys act on the list, so they are taught beside it and nowhere else."""
    from nuiitivet.dev.hud import hud_font
    from nuiitivet.dev.layout_edit_mode import LayerList
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        pytest.skip("skia is not available")
    font, typeface = hud_font(skia)
    canvas = _Canvas()

    lo._paint_layers(skia, canvas, LayerList((0.0, 0.0, 50.0, 50.0), ["AAA", "BBB"], 1, None), font, typeface, 900)

    assert canvas.calls.count("drawTextBlob") == 4, "on top, two layers, and the hint"
