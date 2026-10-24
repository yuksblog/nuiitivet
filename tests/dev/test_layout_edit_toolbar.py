"""Tests for the toolbar: the selection's presets in select boxes over the selection.

Same load-bearing property as the mode's other tests: the boxes write into
the file the widgets were built from, and the assertions read it back.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from nuiitivet.dev import toolbar
from nuiitivet.dev.inline_field import measure
from nuiitivet.dev.toolbar import Box, Toolbar
from nuiitivet.input.codes import MOD_CTRL
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount

from .test_layout_edit_mode import _Session, _load, _select

# ButtonStyle's presets, in the order the class defines them.
_BUTTON_NAMES = ("filled", "outlined", "text", "elevated", "tonal")
_SIZES = ("xs", "s", "m", "l", "xl")


def _bar(s: _Session) -> Toolbar:
    bar = s.mode.toolbar
    assert bar is not None, "no toolbar for the selection"
    return bar


def _window(s: _Session) -> tuple[float, float]:
    return (float(s.app.width), float(s.app.height))


def _box_centre(s: _Session, index: int) -> tuple[float, float]:
    x, y, w, h = toolbar.box_rects(_bar(s), measure, _window(s))[index]
    return (x + w / 2.0, y + h / 2.0)


def _row_centre(s: _Session, index: int) -> tuple[float, float]:
    x, y, w, h = toolbar.row_rects(_bar(s), measure, _window(s))[index]
    return (x + w / 2.0, y + h / 2.0)


def _click(s: _Session, at: tuple[float, float]) -> None:
    s.mode.on_mouse_motion(s.app, *at)
    s.mode.on_mouse_press(s.app, *at)
    s.mode.on_mouse_release(s.app, *at)


@pytest.fixture
def button(app_file: Path) -> Iterator[_Session]:
    """``build_button``: a ``Button("Go", style=ButtonStyle.filled("s"))``, selected."""
    s = _Session(app_file, "build_button")
    try:
        _select(s, 50, 20)
        assert s.mode.selected is s.leaf(), "the button, not the label it builds"
        yield s
    finally:
        s.close()


_BOXES = (Box("style", "filled", _BUTTON_NAMES, 0), Box("size", "s", _SIZES, 1))


def test_the_bar_hangs_over_the_anchor_with_the_name_leading_and_the_boxes_after() -> None:
    bar = Toolbar("Button Go", _BOXES, (100.0, 120.0, 80.0, 40.0))

    panel = toolbar.backdrop(bar, measure, (900.0, 600.0))
    name = toolbar.name_rect(bar, measure, (900.0, 600.0))
    rects = toolbar.box_rects(bar, measure, (900.0, 600.0))

    assert panel[0] == 100.0, "left-aligned with the anchor"
    assert panel[1] + panel[3] == 120.0 - toolbar.STANDOFF, "just over it"
    assert name[0] == panel[0] + toolbar.BOX_PAD
    assert rects[0][0] == name[0] + name[2] + toolbar.GAP
    assert rects[1][0] == rects[0][0] + rects[0][2] + toolbar.GAP
    assert rects[1][0] + rects[1][2] + toolbar.BOX_PAD == panel[0] + panel[2], "the panel ends with the last box"


def test_the_bar_drops_under_an_anchor_at_the_top_and_is_pushed_inside_the_window() -> None:
    at_top = Toolbar("Button Go", _BOXES, (0.0, 0.0, 80.0, 40.0))
    at_right = Toolbar("Button Go", _BOXES, (280.0, 100.0, 80.0, 40.0))

    under = toolbar.backdrop(at_top, measure, (900.0, 600.0))
    pushed = toolbar.backdrop(at_right, measure, (300.0, 200.0))

    assert under[1] == 40.0 + toolbar.STANDOFF, "no room above, so below"
    assert pushed[0] + pushed[2] <= 300.0 - 12.0, "inside the window's right margin"
    assert toolbar.backdrop(at_right, measure, (0.0, 0.0))[0] == 280.0, "an unknown window pushes nothing"


def test_the_open_list_hangs_under_its_box_and_stays_inside_the_window() -> None:
    box = Box("type scale", "BODY_MEDIUM", ("DISPLAY_LARGE", "BODY_MEDIUM"), 1)
    bar = Toolbar("Text", (box,), (0.0, 100.0, 80.0, 40.0), open=0)

    panel = toolbar.backdrop(bar, measure, (300.0, 200.0))
    boxes = toolbar.box_rects(bar, measure, (300.0, 200.0))
    rows = toolbar.row_rects(bar, measure, (300.0, 200.0))

    assert rows[0][1] == panel[1] + panel[3] and rows[1][1] == rows[0][1] + toolbar.ROW_H
    assert rows[0][2] >= boxes[0][2], "as wide as the box at least"
    assert rows[0][0] + rows[0][2] <= 300.0 - 12.0
    assert toolbar.hit(bar, measure, (300.0, 200.0), panel[0] + 1.0, panel[1] + 1.0) == ("bar", 0)


def test_selecting_a_button_shows_its_style_and_size_and_the_selection_outlives_the_pointer(button: _Session) -> None:
    bar = _bar(button)

    assert [(b.label, b.value, b.options, b.current) for b in bar.boxes] == [
        ("style", "filled", _BUTTON_NAMES, 0),
        ("size", "s", _SIZES, 1),
    ]
    assert bar.open is None

    button.hover(200, 150)
    assert button.mode.selected is button.leaf() and button.mode.candidate is button.column
    assert button.mode.toolbar is not None, "the bar stays while the pointer travels to it"


def test_a_box_opens_its_list_on_the_written_row_and_a_row_writes_the_preset(button: _Session) -> None:
    _click(button, _box_centre(button, 0))
    bar = _bar(button)
    assert (bar.open, bar.highlighted) == (0, 0)
    assert button.mode.hovered is None, "nothing beneath the bar is hovered"

    button.mode.on_mouse_motion(button.app, *_row_centre(button, 1))
    assert _bar(button).highlighted == 1
    _click(button, _row_centre(button, 1))

    assert _bar(button).open is None
    assert 'Button("Go", style=ButtonStyle.outlined("s"))' in button.text()
    assert button.reloads == [str(button.path)]
    pending = button.edits.pending
    assert pending is not None and pending.kind == "preset"
    assert (pending.before, pending.after) == ({"style": "filled s"}, {"style": "outlined s"})
    assert [g.caption for g in button.mode.ghosts] == ["style outlined s"]
    assert button.mode.selected is button.leaf(), "the button keeps its path through the reload"


def test_the_size_box_writes_the_size_and_keeps_the_name(button: _Session) -> None:
    _click(button, _box_centre(button, 1))
    assert (_bar(button).open, _bar(button).highlighted) == (1, 1)

    _click(button, _row_centre(button, 2))

    assert 'Button("Go", style=ButtonStyle.filled("m"))' in button.text()


def test_the_keys_step_an_open_list_and_escape_closes_it_without_writing(button: _Session) -> None:
    before = button.text()
    _click(button, _box_centre(button, 0))
    button.mode.on_key_press(button.app, "s", 0)
    button.mode.on_key_press(button.app, "s", 0)
    button.mode.on_key_press(button.app, "w", 0)
    assert _bar(button).highlighted == 1
    for _ in range(9):
        button.mode.on_key_press(button.app, "s", 0)
    assert _bar(button).highlighted == 4, "the list stops at its end"

    button.mode.on_key_press(button.app, "escape", 0)

    assert _bar(button).open is None and button.mode.active
    assert button.text() == before and button.reloads == []

    _click(button, _box_centre(button, 0))
    button.mode.on_key_press(button.app, "s", 0)
    button.mode.on_key_press(button.app, "enter", 0)
    assert 'Button("Go", style=ButtonStyle.outlined("s"))' in button.text()


def test_a_second_click_on_the_box_and_a_click_elsewhere_close_the_list(button: _Session) -> None:
    _click(button, _box_centre(button, 0))
    _click(button, _box_centre(button, 0))
    assert _bar(button).open is None

    _click(button, _box_centre(button, 0))
    _click(button, (50, 150))

    assert button.mode.toolbar is None, "the click selected the column beneath, which has no presets"
    assert button.mode.selected is button.column


def test_picking_the_written_preset_again_writes_nothing(button: _Session) -> None:
    before = button.text()
    _click(button, _box_centre(button, 0))

    _click(button, _row_centre(button, 0))

    assert button.text() == before and button.reloads == []
    assert button.mode.notice == "unchanged"


def test_a_button_without_a_style_shows_the_default_and_a_pick_inserts_the_keyword(app_file: Path) -> None:
    s = _Session(app_file, "build_bare_button")
    try:
        _select(s, 50, 20)
        bar = _bar(s)
        assert [(b.value, b.current) for b in bar.boxes] == [("filled (default)", None), ("s (default)", None)]
        _click(s, _box_centre(s, 0))
        assert _bar(s).highlighted == 0, "nothing written, so the list opens on its first row"

        _click(s, _row_centre(s, 1))

        assert 'Button("Go", style=ButtonStyle.outlined())' in s.text(), "no size, as none was asked for"
        pending = s.edits.pending
        assert pending is not None and pending.before == {"style": ""}
    finally:
        s.close()


def test_a_style_that_is_not_a_preset_shows_custom_and_a_pick_overwrites_it(app_file: Path) -> None:
    s = _Session(app_file, "build_custom_button")
    try:
        _select(s, 50, 20)
        assert [(b.value, b.current) for b in _bar(s).boxes] == [("custom", None), ("custom", None)]
        _click(s, _box_centre(s, 0))

        _click(s, _row_centre(s, 1))

        assert 'Button("Go", style=ButtonStyle.outlined())' in s.text(), "the whole expression is replaced"
        assert s.mode.notice is None
        pending = s.edits.pending
        assert pending is not None and pending.before == {"style": ""}
        s.mode.on_key_press(s.app, "z", MOD_CTRL)
        assert "copy_with(elevation=2)" in s.text(), "and Ctrl+Z brings it back"
    finally:
        s.close()


def test_escape_drops_the_selection_and_its_bar_before_it_leaves_the_mode(button: _Session) -> None:
    assert button.mode.toolbar is not None

    button.mode.on_key_press(button.app, "escape", 0)

    assert button.mode.selected is None and button.mode.toolbar is None
    assert button.mode.active, "the first press only cleared the selection"

    button.mode.on_key_press(button.app, "escape", 0)

    assert not button.mode.active


def test_a_widget_without_presets_has_no_bar(app_file: Path) -> None:
    s = _Session(app_file, "build_spaced")
    try:
        _select(s, 50, 20)
        s.mode.on_key_press(s.app, "w", 0)
        assert s.mode.selected is s.column

        assert s.mode.toolbar is None
    finally:
        s.close()


def test_text_shows_its_type_scale_and_writes_a_role_as_an_attribute(app_file: Path) -> None:
    s = _Session(app_file, "build_text_role")
    try:
        _select(s, 50, 20)
        bar = _bar(s)
        assert len(bar.boxes) == 1 and bar.boxes[0].label == "type scale"
        assert (bar.boxes[0].value, bar.boxes[0].current, len(bar.boxes[0].options)) == ("BODY_MEDIUM", 10, 15)
        _click(s, _box_centre(s, 0))
        assert _bar(s).highlighted == 10

        _click(s, _row_centre(s, 9))

        assert "type_scale=TypeScale.BODY_LARGE)" in s.text()
        assert [g.caption for g in s.mode.ghosts] == ["type_scale BODY_LARGE"]
    finally:
        s.close()


def test_the_reload_check_passes_on_the_rebuilt_preset(button: _Session) -> None:
    _click(button, _box_centre(button, 0))
    _click(button, _row_centre(button, 1))
    rebuilt = _load(button.path).build_button()

    with mount(rebuilt) as host:
        host.layout(300, 200)
        assert button.edits.after_reload([host.root]) is None


def test_the_bar_goes_with_the_selection_when_a_reload_lands(button: _Session) -> None:
    """The old widget is gone with the reload; the bar follows the selection's path to the new one."""
    rebuilt = _load(button.path).build_button()
    with mount(rebuilt) as host:
        host.layout(300, 200)
        button.app.root = host.root

        button.edits.after_reload([host.root])

        assert button.mode.selected is rebuilt.children[0]
        assert button.mode.toolbar is not None and _bar(button).boxes[0].value == "filled"


def test_the_bar_over_a_widget_at_the_top_drops_below_it_and_names_it(button: _Session) -> None:
    bar = _bar(button)
    panel = toolbar.backdrop(bar, measure, _window(button))

    assert bar.name == "Button" and bar.anchor[1] == 0.0, "the type alone; the label is on screen already"
    assert button.mode.caption == "Button"
    assert panel[1] == bar.anchor[3] + toolbar.STANDOFF, "no room above the button, so the bar sits under it"
    _click(button, (panel[0] + 1.0, panel[1] + 1.0))
    assert button.mode.selected is button.leaf(), "a press on the panel itself changes nothing"


def test_a_chip_shows_one_box_as_its_presets_take_no_argument(app_file: Path) -> None:
    s = _Session(app_file, "build_chip")
    try:
        _select(s, 20, 16)
        bar = _bar(s)
        assert [(b.label, b.value, b.options) for b in bar.boxes] == [
            ("style", "assist (default)", ("assist", "filter", "input", "suggestion"))
        ]

        _click(s, _box_centre(s, 0))
        _click(s, _row_centre(s, 1))

        assert 'AssistChip(label="Go", style=ChipStyle.filter())' in s.text()
    finally:
        s.close()


def test_a_fab_shows_its_own_sizes_and_a_size_pick_on_a_bare_call_writes_the_default_preset(app_file: Path) -> None:
    s = _Session(app_file, "build_fab")
    try:
        _select(s, 20, 16)
        bar = _bar(s)
        assert [(b.label, b.value) for b in bar.boxes] == [("style", "primary (default)"), ("size", "s (default)")]
        assert bar.boxes[1].options == ("s", "m", "l")

        _click(s, _box_centre(s, 1))
        _click(s, _row_centre(s, 1))

        assert 'Fab("add", style=FabStyle.primary("m"))' in s.text()
    finally:
        s.close()


def test_a_toggle_button_is_checked_by_the_preset_it_was_given_not_the_style_it_shows(app_file: Path) -> None:
    s = _Session(app_file, "build_toggle")
    try:
        _select(s, 50, 20)
        assert [(b.value, b.current) for b in _bar(s).boxes] == [("outlined", 1), ("m", 2)]

        _click(s, _box_centre(s, 0))
        _click(s, _row_centre(s, 0))

        assert 'ToggleButton("Go", style=ToggleButtonStyle.filled("m"))' in s.text()
        rebuilt = _load(s.path).build_toggle()
        with mount(rebuilt) as host:
            host.layout(300, 200)
            assert s.edits.after_reload([host.root]) is None, "the toggle's style property is a ButtonStyle"
    finally:
        s.close()


def test_a_bar_is_none_for_a_mount_without_a_window_size() -> None:
    from nuiitivet.dev.layout_edit_mode import LayoutEditMode
    from nuiitivet.dev.source_edit import EditLog
    from nuiitivet.widgets.text import TextBase as Text

    with mount(Column(children=[Text("AAA", width=100, height=40)])) as host:
        host.layout(300, 200)
        mode = LayoutEditMode(EditLog())

        assert mode.toolbar is None, "no selection, no bar"
