"""Tests for the source jump -- the modeless chorded click that opens the code."""

from __future__ import annotations

from typing import Any

from nuiitivet.dev import source
from nuiitivet.dev.select_mode import SelectMode
from nuiitivet.dev.selection import Selection
from nuiitivet.dev.source_jump import SourceJump
from nuiitivet.input.codes import MOD_CTRL, MOD_META, MOD_SHIFT
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text

_CHORD = MOD_CTRL | MOD_SHIFT


class _App:
    """Stand-in window: the jump reads ``root`` and ``modifier_keys`` and repaints."""

    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.modifier_keys = 0
        self.invalidated = 0

    def invalidate(self) -> None:
        self.invalidated += 1


def _records_into(sink: list[tuple[str, int]]) -> Any:
    """A stand-in for ``open_at`` that records the jump instead of launching."""

    def _open(path: str, line: int) -> None:
        sink.append((path, line))
        return None

    return _open


def _chord_click(jump: SourceJump, app: _App, x: float, y: float, mods: int = _CHORD) -> tuple[bool, bool]:
    return (jump.on_mouse_press(app, x, y, mods), jump.on_mouse_release(app, x, y, mods))


# --- the chord --------------------------------------------------------------


def test_a_chorded_click_opens_the_source_outside_any_mode(monkeypatch: Any) -> None:
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            jump = SourceJump()

            consumed = _chord_click(jump, _App(host.root), 2, 2)
    finally:
        source.uninstall()

    assert consumed == (True, True)
    assert len(opened) == 1
    assert opened[0][0].endswith("test_source_jump.py")


def test_the_meta_accelerator_also_jumps(monkeypatch: Any) -> None:
    """macOS spells the prefix Cmd+Shift."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()

            _chord_click(SourceJump(), _App(host.root), 2, 2, MOD_META | MOD_SHIFT)
    finally:
        source.uninstall()

    assert len(opened) == 1


def test_a_plain_click_passes_through(monkeypatch: Any) -> None:
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        jump = SourceJump()

        assert _chord_click(jump, _App(host.root), 2, 2, 0) == (False, False)

    assert opened == []


def test_half_the_chord_is_not_the_chord(monkeypatch: Any) -> None:
    """``Ctrl+Click`` and ``Shift+Click`` are the app's; only the prefix jumps."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)

        assert _chord_click(SourceJump(), app, 2, 2, MOD_CTRL) == (False, False)
        assert _chord_click(SourceJump(), app, 2, 2, MOD_SHIFT) == (False, False)

    assert opened == []


def test_a_chorded_drag_opens_nothing_but_is_still_consumed(monkeypatch: Any) -> None:
    """The app never saw the press, so it must not see the release either."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            jump = SourceJump()
            app = _App(host.root)

            assert jump.on_mouse_press(app, 2, 2, _CHORD) is True
            assert jump.on_mouse_motion(app, 40, 30, _CHORD) is True
            assert jump.on_mouse_release(app, 80, 60, _CHORD) is True
    finally:
        source.uninstall()

    assert opened == []


def test_the_release_of_an_unseen_press_passes_through() -> None:
    jump = SourceJump()

    assert jump.on_mouse_release(_App(), 2, 2, _CHORD) is False


def test_keys_are_never_consumed() -> None:
    jump = SourceJump()
    app = _App()

    assert jump.on_key_press(app, "lctrl", MOD_CTRL) is False
    assert jump.on_key_press(app, "c", _CHORD) is False
    assert jump.on_key_release(app, "c", _CHORD) is False


# --- inside select mode ------------------------------------------------------


def test_inside_select_mode_the_chord_jumps_instead_of_designating(monkeypatch: Any) -> None:
    """The runner offers the press to the jump first; a consumed press never
    reaches the mode, so browsing code leaves no marks behind."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            selection = Selection()
            mode = SelectMode(selection)
            jump = SourceJump()
            app = _App(host.root)
            mode.on_key_press(app, "c", _CHORD)

            if not jump.on_mouse_press(app, 2, 2, _CHORD):
                mode.on_mouse_press(app, 2, 2, _CHORD)
            if not jump.on_mouse_release(app, 2, 2, _CHORD):
                mode.on_mouse_release(app, 2, 2, _CHORD)
    finally:
        source.uninstall()

    assert len(opened) == 1
    assert selection.members() == []
    assert mode.active is True


def test_select_mode_no_longer_jumps_on_ctrl_click(monkeypatch: Any) -> None:
    """One chord for the jump everywhere; ``Ctrl+Click`` in the mode designates."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    source.install()
    try:
        leaf = Text("AAA")
        with mount(Column(children=[leaf])) as host:
            host.layout(300, 200)
            host.settle()
            selection = Selection()
            mode = SelectMode(selection)
            app = _App(host.root)
            mode.on_key_press(app, "c", _CHORD)

            mode.on_mouse_press(app, 2, 2, MOD_CTRL)
            mode.on_mouse_release(app, 2, 2, MOD_CTRL)

            assert selection.members() == [leaf]
    finally:
        source.uninstall()

    assert opened == []


# --- the notice ---------------------------------------------------------------


def test_a_widget_with_no_recorded_source_says_so(monkeypatch: Any) -> None:
    """Silence would be indistinguishable from a broken feature."""
    opened: list[tuple[str, int]] = []
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", _records_into(opened))

    # Capture never installed, so nothing carries a site.
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        host.settle()
        jump = SourceJump()

        _chord_click(jump, _App(host.root), 2, 2)

    assert opened == []
    assert jump.notice is not None
    assert "no source" in jump.notice


def test_a_failed_launch_reaches_the_human(monkeypatch: Any) -> None:
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", lambda path, line: "code is not on PATH")

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            jump = SourceJump()

            _chord_click(jump, _App(host.root), 2, 2)
    finally:
        source.uninstall()

    assert jump.notice == "code is not on PATH"


def test_a_successful_jump_names_the_file(monkeypatch: Any) -> None:
    """The URL is fire-and-forget, so naming the file is the only evidence the
    click was received."""
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", lambda path, line: None)

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            jump = SourceJump()

            _chord_click(jump, _App(host.root), 2, 2)
    finally:
        source.uninstall()

    assert jump.notice is not None
    assert jump.notice.startswith("opening test_source_jump.py:")


def test_the_notice_clears_on_the_next_move(monkeypatch: Any) -> None:
    """It replaces the hover caption, so it must not outlive the moment."""
    monkeypatch.setattr("nuiitivet.dev.source_jump.open_at", lambda path, line: None)

    source.install()
    try:
        with mount(Column(children=[Text("AAA")])) as host:
            host.layout(300, 200)
            host.settle()
            jump = SourceJump()
            app = _App(host.root)
            _chord_click(jump, app, 2, 2)
            assert jump.notice is not None

            assert jump.on_mouse_motion(app, 40, 40) is False

            assert jump.notice is None
    finally:
        source.uninstall()


# --- the affordance ---------------------------------------------------------


def test_the_chord_lights_up_the_widget_under_the_pointer() -> None:
    """Pressed while the pointer is stationary, so the last known position
    stands in for a move."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        jump = SourceJump()
        app = _App(host.root)

        jump.on_mouse_motion(app, 2, 2)
        assert jump.hovered is None

        jump.on_key_press(app, "lshift", _CHORD)
        assert jump.hovered is leaf

        jump.on_key_release(app, "lshift", MOD_CTRL)
        assert jump.hovered is None


def test_a_move_with_the_chord_held_follows_the_pointer() -> None:
    """A plain move carries no modifiers, so the window's mask stands in."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        jump = SourceJump()
        app = _App(host.root)
        app.modifier_keys = _CHORD

        assert jump.on_mouse_motion(app, 2, 2) is False

        assert jump.hovered is leaf
        assert app.invalidated == 1


def test_hovering_the_same_candidate_does_not_repaint() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        jump = SourceJump()
        app = _App(host.root)
        app.modifier_keys = _CHORD
        jump.on_mouse_motion(app, 2, 2)
        painted = app.invalidated

        jump.on_mouse_motion(app, 3, 3)

        assert app.invalidated == painted
