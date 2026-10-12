"""Tests for the comment-mode and source-jump overlay.

The load-bearing property is negative: the human's marks are drawn for
the human only, and must never reach the agent's perception. If they did,
the agent would read its own human's annotations back as app content.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet._interaction.perception import describe_tree
from nuiitivet.dev import comment_overlay as so
from nuiitivet.dev.hud import SEPARATOR
from nuiitivet.dev.comment_mode import CommentMode
from nuiitivet.dev.comments import Comments
from nuiitivet.input.codes import MOD_CTRL, MOD_SHIFT
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text

_ENTER = MOD_CTRL | MOD_SHIFT


class _Canvas:
    """Records the draw calls made against it, in place of a real skia canvas."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def _record(*_args: Any, **_kwargs: Any) -> None:
            self.calls.append(name)

        return _record


class _App:
    def __init__(self, root: Any, mode: Any = None, jump: Any = None) -> None:
        self.root = root
        self.width = 300
        self.height = 200
        self.modifier_keys = 0
        self._comment_mode = mode
        self._source_jump = jump

    def invalidate(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NUIITIVET_DEV_ACTION_OVERLAY", raising=False)


@pytest.fixture
def marking() -> Iterator[tuple[_App, CommentMode]]:
    """An app with comment mode latched on and one widget already marked."""
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        mode = CommentMode(Comments())
        app = _App(host.root, mode)
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_press(app, 2, 2)
        mode.on_mouse_release(app, 2, 2)
        yield (app, mode)


def test_the_overlay_never_enters_the_widget_tree(
    marking: tuple[_App, CommentMode]
) -> None:
    """The invariant: it holds no widgets, so ``describe_tree`` cannot see it."""
    app, _mode = marking
    before = describe_tree(app.root)

    so.paint_comments(app, _Canvas(), app.width, app.height)

    assert describe_tree(app.root) == before


def test_paints_something_while_marking(marking: tuple[_App, CommentMode]) -> None:
    app, _mode = marking
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert canvas.calls, "a marked widget must be marked on screen"


def test_paints_nothing_without_a_select_mode() -> None:
    """Production, and any run without the dev runner."""
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        so.paint_comments(_App(host.root), canvas, 300, 200)

        assert canvas.calls == []


def test_paints_nothing_when_idle_with_nothing_marked() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        so.paint_comments(_App(host.root, CommentMode(Comments())), canvas, 300, 200)

        assert canvas.calls == []


def test_the_env_kill_switch_disables_it(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _mode = marking
    monkeypatch.setenv("NUIITIVET_DEV_ACTION_OVERLAY", "0")
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert canvas.calls == []


def test_a_committed_mark_still_marks_the_screen(
    marking: tuple[_App, CommentMode]
) -> None:
    """Leaving commits, so the badges survive the mode being switched off."""
    app, mode = marking
    mode.on_key_press(app, "enter", 0)
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert canvas.calls, "committed marks keep their numbered badges"


def test_painting_never_raises_on_a_broken_canvas(
    marking: tuple[_App, CommentMode]
) -> None:
    """A decoration must never break the frame."""

    class _Broken:
        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("boom")

    app, _mode = marking

    so.paint_comments(app, _Broken(), app.width, app.height)


def test_a_region_is_marked_on_screen(marking: tuple[_App, CommentMode]) -> None:
    app, mode = marking
    mode.comments.add_region((10.0, 10.0, 40.0, 30.0))
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert "drawRect" in canvas.calls, "a marked area needs its own wash"


def test_a_region_only_buffer_still_paints(marking: tuple[_App, CommentMode]) -> None:
    """Regions and nodes are independent, so either alone must be drawable."""
    app, mode = marking
    mode.comments.clear()
    mode.comments.add_region((10.0, 10.0, 40.0, 30.0))
    mode.on_key_press(app, "enter", 0)
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert canvas.calls


def test_the_rubber_band_is_drawn_while_dragging(
    marking: tuple[_App, CommentMode]
) -> None:
    app, mode = marking
    mode.on_mouse_press(app, 10, 10)
    mode.on_mouse_motion(app, 60, 40)
    canvas = _Canvas()

    so.paint_comments(app, canvas, app.width, app.height)

    assert mode.band is not None
    assert "drawRect" in canvas.calls


def _later(monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    import time

    from nuiitivet.dev import hud

    monkeypatch.setattr(hud, "_now", lambda: time.monotonic() + seconds)


def test_the_splash_names_the_mode_and_the_help_key_for_a_moment(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev.hud import SPLASH

    app, _mode = marking
    splashes: list[str] = []
    monkeypatch.setattr(so, "paint_splash", lambda _s, _c, text, *a: splashes.append(text))

    so.paint_comments(app, _Canvas(), app.width, app.height)
    assert splashes == ["COMMENT MODE" + SEPARATOR + "H help"]

    _later(monkeypatch, SPLASH)
    so.paint_comments(app, _Canvas(), app.width, app.height)
    assert len(splashes) == 1, "gone after a tooltip's time"


def test_the_leaving_line_paints_after_the_mode_is_off(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev.hud import SPLASH

    app, mode = marking
    splashes: list[str] = []
    monkeypatch.setattr(so, "paint_splash", lambda _s, _c, text, *a: splashes.append(text))
    _later(monkeypatch, SPLASH)
    _leave(app, mode)
    monkeypatch.undo()
    monkeypatch.setattr(so, "paint_splash", lambda _s, _c, text, *a: splashes.append(text))

    so.paint_comments(app, _Canvas(), app.width, app.height)

    assert splashes == ["COMMENT MODE off" + SEPARATOR + "comments kept"]


def test_the_help_sheet_paints_while_h_is_held(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    sheets: list[tuple[Any, ...]] = []
    monkeypatch.setattr(so, "paint_sheet", lambda *args, **kwargs: sheets.append(args))
    _close_field(app, mode)

    so.paint_comments(app, _Canvas(), app.width, app.height)
    assert sheets == []

    mode.on_key_press(app, "h", 0)
    so.paint_comments(app, _Canvas(), app.width, app.height)
    assert len(sheets) == 1 and sheets[0][2] == "COMMENT MODE" and sheets[0][3] is so.HELP

    mode.on_key_release(app, "h", 0)
    so.paint_comments(app, _Canvas(), app.width, app.height)
    assert len(sheets) == 1


def test_the_jump_notice_paints_in_the_box_at_the_bottom_left_while_the_mode_is_on(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev.source_jump import SourceJump

    app, _mode = marking
    jump = SourceJump()
    app._source_jump = jump
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", lambda path, line: "no editor")
    jump.on_mouse_press(app, 2, 2, _ENTER)
    jump.on_mouse_release(app, 2, 2, _ENTER)
    assert jump.notice
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(so, "paint_hud", lambda *args, **kwargs: calls.append(kwargs))

    so.paint_comments(app, _Canvas(), app.width, app.height)

    assert len(calls) == 1, "one box, not a box and a loose notice"
    assert calls[0]["notices"] == [jump.notice]


def test_the_jump_caption_shows_where_the_widget_was_built_and_the_hover_caption_does_not() -> None:
    """Under the chord the location is the aim; on an ordinary hover it is noise."""
    from nuiitivet.dev import source

    source.install()
    try:
        leaf = Text("AAA")
        with mount(Column(children=[leaf])) as host:
            host.layout(300, 200)
            host.settle()

            jump_caption = so.describe_node(leaf, site=True)
            hover_caption = so.describe_node(leaf)
    finally:
        source.uninstall()

    assert "test_comment_overlay.py:" in jump_caption
    assert SEPARATOR not in hover_caption


def test_the_caption_omits_the_location_when_none_was_recorded() -> None:
    """A production-shaped run reads exactly as it did before source capture."""
    leaf = Text("AAA")

    assert SEPARATOR not in so.describe_node(leaf, site=True)


def test_a_node_mark_paints_only_in_its_own_window() -> None:
    """The comment buffer is shared across windows; the rect must not ghost into
    windows that do not contain the node."""
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    main_content = Container(width=50, height=40)
    app = App(Window(content=main_content, width=300, height=200))
    second = Window(content=Container(), width=300, height=200).open()
    main_win = app.main_window
    main_win.root.layout(300, 200)

    comments = Comments()
    comments.add(main_content, root=main_win.root)
    main_win._comment_mode = CommentMode(comments)
    second._comment_mode = CommentMode(comments)

    own_canvas, foreign_canvas = _Canvas(), _Canvas()
    so.paint_comments(main_win, own_canvas, 300, 200)
    so.paint_comments(second, foreign_canvas, 300, 200)

    assert own_canvas.calls
    assert foreign_canvas.calls == []


# --- the source jump ---------------------------------------------------------


def test_the_jump_affordance_paints_with_no_mode_on() -> None:
    """The chord works outside any mode, so its feedback cannot depend on one."""
    from nuiitivet.dev.source_jump import SourceJump

    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        jump = SourceJump()
        app = _App(host.root, jump=jump)
        app.modifier_keys = _ENTER
        jump.on_mouse_motion(app, 2, 2)
        canvas = _Canvas()

        so.paint_comments(app, canvas, 300, 200)

        assert "drawLine" in canvas.calls, "the widget a click would open gets brackets"


def test_an_idle_jump_paints_nothing() -> None:
    from nuiitivet.dev.source_jump import SourceJump

    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        so.paint_comments(_App(host.root, jump=SourceJump()), canvas, 300, 200)

        assert canvas.calls == []


def test_the_notice_paints_after_the_chord_is_released(monkeypatch: pytest.MonkeyPatch) -> None:
    """What the jump did has to be readable even with nothing left to hang it on."""
    from nuiitivet.dev.source_jump import SourceJump

    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", lambda path, line: "no editor")
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        jump = SourceJump()
        app = _App(host.root, jump=jump)
        jump.on_mouse_press(app, 2, 2, _ENTER)
        jump.on_mouse_release(app, 2, 2, _ENTER)
        assert jump.hovered is None and jump.notice
        canvas = _Canvas()

        so.paint_comments(app, canvas, 300, 200)

        assert "drawRoundRect" in canvas.calls, "the caption box is drawn"


# --- instructions, the field, and the prompt --------------------------------


def _leave(app: _App, mode: CommentMode) -> None:
    """``Enter`` out of the session, first closing the field the new mark opened."""
    if mode.writing is not None:
        mode.on_key_press(app, "escape", 0)
    mode.on_key_press(app, "enter", 0)


def _close_field(app: _App, mode: CommentMode) -> None:
    if mode.writing is not None:
        mode.on_key_press(app, "escape", 0)


def _captions(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def fake(_skia: Any, _canvas: Any, text: str, *_args: Any, **_kwargs: Any) -> None:
        seen.append(text)

    monkeypatch.setattr(so, "paint_caption", fake)
    return seen


def _notices(monkeypatch: pytest.MonkeyPatch) -> list[list[Any]]:
    seen: list[list[Any]] = []

    def fake(*_args: Any, **kwargs: Any) -> None:
        seen.append(list(kwargs["notices"]))

    monkeypatch.setattr(so, "paint_hud", fake)
    return seen


def test_nothing_but_the_badge_is_painted_beside_a_mark(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    captions = _captions(monkeypatch)
    mode.comments.set_instruction(1, "make this wider")
    _leave(app, mode)

    so.paint_comments(app, _Canvas(), 300, 200)

    assert not any("make this wider" in text for text in captions)


def test_a_marked_widget_hovers_like_any_other(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The badge says it is marked; the brackets still say what a click would unmark."""
    app, mode = marking
    captions = _captions(monkeypatch)
    _close_field(app, mode)
    rect = so.visible_rect(mode.comments.members()[0])
    assert rect is not None
    x, y, w, h = rect
    mode.on_mouse_motion(app, x + w - 1.0, y + h - 1.0)
    assert mode.hovered is mode.comments.members()[0]
    assert mode.hovered_badge is None
    canvas = _Canvas()

    so.paint_comments(app, canvas, 300, 200)

    assert "drawLine" in canvas.calls, "the brackets"
    assert any("AAA" in text for text in captions), "the caption"
    assert canvas.calls.index("drawLine") < canvas.calls.index("drawCircle"), "the badge paints over the hover"


def test_the_hover_steps_aside_while_the_pointer_rests_on_a_badge(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    """There a click reopens the field, so the brackets would promise the wrong thing."""
    app, mode = marking
    captions = _captions(monkeypatch)
    _close_field(app, mode)
    mode.comments.set_instruction(1, "make this wider")
    mode.on_mouse_motion(app, 150, 150)
    mode.on_mouse_motion(app, 2, 2)
    assert mode.hovered_badge == 1
    canvas = _Canvas()

    so.paint_comments(app, canvas, 300, 200)

    assert captions == ["make this wider"]
    assert "drawLine" not in canvas.calls


def test_the_open_field_paints_beside_the_badge_in_amber(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    painted: list[tuple[Any, ...]] = []
    monkeypatch.setattr(so, "paint_field", lambda *args, **kwargs: painted.append(args))
    mode.on_mouse_press(app, 2, 2)
    mode.on_mouse_release(app, 2, 2)
    assert mode.writing is not None

    so.paint_comments(app, _Canvas(), 300, 200)

    ((_skia, _canvas, _app, slot, value, accent, _font, _typeface, window),) = painted
    assert slot.side == "right" and slot.gap > so.BADGE_RADIUS and value is mode.writing.field.value
    assert accent == so._ACCENT and window == (300.0, 200.0)


# --- the field stays inside the window ----------------------------------------


def _field_rects(monkeypatch: pytest.MonkeyPatch) -> list[tuple[float, float, float, float]]:
    """Run the real ``paint_field`` and keep the rect it took, frame by frame."""
    rects: list[tuple[float, float, float, float]] = []
    real = so.paint_field

    def spy(*args: Any, **kwargs: Any) -> Any:
        rect = real(*args, **kwargs)
        rects.append(rect)
        return rect

    monkeypatch.setattr(so, "paint_field", spy)
    return rects


def _inside(rect: tuple[float, float, float, float], window: tuple[float, float]) -> bool:
    x, y, w, h = rect
    return x >= 0 and y >= 0 and x + w <= window[0] and y + h <= window[1]


def _open_field_on_a_region(
    app: _App, mode: CommentMode, press: tuple[float, float], release: tuple[float, float]
) -> None:
    mode.on_mouse_press(app, *press)
    mode.on_mouse_release(app, *release)
    assert mode.writing is not None, "the new region opened its field"


def test_a_field_on_a_mark_at_the_right_edge_opens_on_the_badges_left(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    rects = _field_rects(monkeypatch)
    _open_field_on_a_region(app, mode, (280.0, 20.0), (295.0, 60.0))

    so.paint_comments(app, _Canvas(), 300, 200)

    assert mode.writing is not None and mode.writing.slot.side == "left"
    (rect,) = rects
    assert _inside(rect, (300.0, 200.0)) and rect[0] + rect[2] < 280.0


def test_typing_past_the_room_wraps_and_keeps_the_side(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    rects = _field_rects(monkeypatch)
    _open_field_on_a_region(app, mode, (40.0, 20.0), (60.0, 60.0))
    assert mode.writing is not None and mode.writing.slot.side == "right"

    for _ in range(12):
        assert mode.on_text(app, "wider than the room ") is True
        so.paint_comments(app, _Canvas(), 300, 200)

    assert all(_inside(rect, (300.0, 200.0)) for rect in rects)
    assert rects[-1][3] > rects[0][3], "the box grew downward, not sideways"
    assert mode.writing.slot.side == "right"


def test_a_field_at_the_bottom_edge_moves_up_as_its_lines_grow(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    rects = _field_rects(monkeypatch)
    _open_field_on_a_region(app, mode, (100.0, 185.0), (120.0, 198.0))

    for _ in range(6):
        mode.on_key_press(app, "enter", MOD_SHIFT)
        so.paint_comments(app, _Canvas(), 300, 200)

    assert all(_inside(rect, (300.0, 200.0)) for rect in rects)
    assert rects[-1][1] < rects[0][1], "the box moved up to stay inside"


def test_the_caption_beside_a_mark_at_the_right_edge_stays_inside(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev.hud import caption_size, hud_font
    from nuiitivet.rendering.skia.skia_module import get_skia

    app, mode = marking
    placed: list[tuple[str, float, float]] = []

    def fake(_skia: Any, _canvas: Any, text: str, _font: Any, _typeface: Any, x: float, y: float, *_a: Any) -> None:
        placed.append((text, x, y))

    monkeypatch.setattr(so, "paint_caption", fake)
    mode.on_mouse_press(app, 280.0, 20.0)
    mode.on_mouse_release(app, 295.0, 60.0)
    _close_field(app, mode)
    mode.comments.set_instruction(2, "move this to the left")
    mode.on_mouse_motion(app, 282.0, 22.0)
    assert mode.hovered_badge == 2

    so.paint_comments(app, _Canvas(), 300, 200)

    _font, typeface = hud_font(get_skia())
    ((text, x, _y),) = [entry for entry in placed if entry[0].startswith("move")]
    assert x + caption_size(text, typeface)[0] <= 300.0 - so.BADGE_RADIUS, "flipped to the badge's left"


def test_the_prompt_shows_after_a_commit_until_the_comments_are_served(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    notices = _notices(monkeypatch)
    so.paint_comments(app, _Canvas(), 300, 200)
    assert so.PROMPT not in notices[-1], "no prompt while still marking"

    _leave(app, mode)
    so.paint_comments(app, _Canvas(), 300, 200)
    assert notices[-1] == [so.PROMPT, None]

    mode.comments.served()
    notices.clear()
    so.paint_comments(app, _Canvas(), 300, 200)
    assert notices == [], "read: the prompt is gone, and nothing else needs the badge"


def test_the_prompt_names_the_skill_first_and_the_tool_second() -> None:
    assert so.PROMPT == "in chat: /nuiitivet-see-comments  |  see_comments"


# --- hovering a badge reads the whole instruction ------------------------------


def _placed_captions(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, float]]:
    seen: list[tuple[str, float, float]] = []

    def fake(_skia: Any, _canvas: Any, text: str, _font: Any, _typeface: Any, x: float, y: float, *_a: Any) -> None:
        seen.append((text, x, y))

    monkeypatch.setattr(so, "paint_caption", fake)
    return seen


def test_hovering_a_badge_shows_the_whole_instruction(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    captions = _placed_captions(monkeypatch)
    _close_field(app, mode)
    mode.comments.set_instruction(1, "x" * 80)
    mode.on_mouse_motion(app, 2, 2)
    assert mode.hovered_badge == 1

    so.paint_comments(app, _Canvas(), 300, 200)

    ((text, _x, _y),) = [entry for entry in captions if entry[0].startswith("x")]
    assert text.replace("\n", "") == "x" * 80 and "…" not in text
    assert "\n" in text, "wrapped at the field's room, not drawn as one long line"


def test_moving_off_the_badge_leaves_only_the_number(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    captions = _placed_captions(monkeypatch)
    _close_field(app, mode)
    mode.comments.set_instruction(1, "x" * 80)
    mode.on_mouse_motion(app, 2, 2)
    mode.on_mouse_motion(app, 150, 150)
    assert mode.hovered_badge is None

    so.paint_comments(app, _Canvas(), 300, 200)

    assert not [entry for entry in captions if entry[0].startswith("x")]


def test_a_hovered_multi_line_instruction_keeps_its_lines_inside_the_window(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev.hud import MARGIN, caption_size, hud_font
    from nuiitivet.rendering.skia.skia_module import get_skia

    app, mode = marking
    captions = _placed_captions(monkeypatch)
    _close_field(app, mode)
    mode.comments.set_instruction(1, "first line\nsecond line")
    mode.on_mouse_motion(app, 2, 2)

    so.paint_comments(app, _Canvas(), 300, 200)

    _font, typeface = hud_font(get_skia())
    ((text, x, y),) = [entry for entry in captions if entry[0].startswith("first")]
    assert text == "first line\nsecond line"
    w, h = caption_size(text, typeface)
    assert x >= MARGIN and y >= MARGIN and x + w <= 300.0 - MARGIN and y + h <= 200.0 - MARGIN
