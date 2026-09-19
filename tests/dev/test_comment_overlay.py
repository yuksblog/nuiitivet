"""Tests for the comment-mode and source-jump overlay.

The load-bearing property is negative: the human's marks are drawn for
the human only, and must never reach the assistant's perception. If they did,
the assistant would read its own human's annotations back as app content.
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


def test_the_badge_names_the_mode_its_exit_and_the_switch(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first line is the one that never goes away, so the way out and the
    way across live there."""
    app, mode = marking
    seen: dict[str, Any] = {}
    monkeypatch.setattr(so, "paint_hud", lambda *args, **kwargs: seen.update(kwargs))

    so.paint_comments(app, _Canvas(), app.width, app.height)

    assert seen["mode_line"] == SEPARATOR.join(
        ("COMMENT", "for the assistant", "1 widget", "Esc discard", "Ctrl+Shift+E edit")
    )
    assert seen["hints"] == mode.hints
    assert seen["placement"] is mode.placement


def test_the_jump_notice_rides_in_the_badge_while_the_mode_is_on(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two boxes at the same corner would cover each other."""
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

    assert len(calls) == 1, "one badge, not a badge and a loose notice"
    assert calls[0]["notices"] == [jump.notice]


def test_the_hover_caption_shows_where_the_widget_was_built() -> None:
    """What makes the jump discoverable without anything pressable.

    The overlay is a paint-only registry outside the widget tree; a button would
    need its own hit testing. Seeing the location is what tells the human it can
    be reached, and the HUD says how.
    """
    from nuiitivet.dev import source

    source.install()
    try:
        leaf = Text("AAA")
        with mount(Column(children=[leaf])) as host:
            host.layout(300, 200)
            host.settle()

            caption = so.describe_node(leaf)
    finally:
        source.uninstall()

    assert "test_comment_overlay.py:" in caption


def test_the_caption_omits_the_location_when_none_was_recorded() -> None:
    """A production-shaped run reads exactly as it did before source capture."""
    leaf = Text("AAA")

    assert SEPARATOR not in so.describe_node(leaf)


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
    comments.toggle(main_content, root=main_win.root)
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
    """``Enter`` out of the session, declining the field the fresh mark offers."""
    mode.on_key_press(app, "enter", 0)
    mode.on_key_press(app, "escape", 0)
    mode.on_key_press(app, "enter", 0)


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


def test_an_instruction_is_captioned_beside_its_badge(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    captions = _captions(monkeypatch)
    mode.comments.set_instruction(1, "make this wider")
    _leave(app, mode)

    so.paint_comments(app, _Canvas(), 300, 200)

    assert "make this wider" in captions


def test_a_long_instruction_is_cut_short_on_the_badge(
    marking: tuple[_App, CommentMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, mode = marking
    captions = _captions(monkeypatch)
    mode.comments.set_instruction(1, "x" * 80)
    _leave(app, mode)

    so.paint_comments(app, _Canvas(), 300, 200)

    (caption,) = [text for text in captions if text.startswith("x")]
    assert len(caption) < 40 and caption.endswith("…")


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

    ((_skia, _canvas, _app, rect, value, accent, _font, _typeface),) = painted
    assert rect[0] > so.BADGE_RADIUS and value is mode.writing.field.value
    assert accent == so._ACCENT


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
