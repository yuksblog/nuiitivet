"""Tests for comment mode -- the gesture layer over the mark buffer."""

from __future__ import annotations

from typing import Any

import pytest

from nuiitivet.dev.comment_mode import CommentMode
from nuiitivet.dev.interaction import InteractionJournal
from nuiitivet.dev.comments import Comments
from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text

_ENTER = MOD_CTRL | MOD_SHIFT


class _App:
    """Stand-in app: the mode reads ``root`` and asks it to repaint."""

    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.invalidated = 0
        self.tree_repaints = 0

    def invalidate(self, immediate: bool = False, content: bool = True) -> None:
        self.invalidated += 1
        self.tree_repaints += int(content)


def _mode() -> tuple[CommentMode, Comments, _App]:
    """A mode with no tree under it, for the tests that only exercise keys."""
    comments = Comments()
    return (CommentMode(comments), comments, _App())


def _click(mode: CommentMode, app: _App, x: float, y: float) -> None:
    mode.on_mouse_press(app, x, y)
    mode.on_mouse_release(app, x, y)


def _leave(mode: CommentMode, app: _App) -> None:
    """``Enter`` out of the session, first closing the field a new mark opened."""
    if mode.writing is not None:
        mode.on_key_press(app, "escape", 0)
    mode.on_key_press(app, "enter", 0)


def _mark(mode: CommentMode, app: _App, x: float, y: float) -> None:
    """Click, then close the field the new mark opened, for the tests about the mark itself."""
    _click(mode, app, x, y)
    if mode.writing is not None:
        mode.on_key_press(app, "escape", 0)


def _walk(mode: CommentMode, app: _App, key: str, at: tuple[float, float] = (2.0, 2.0)) -> None:
    """``W`` or ``S`` with the pointer at ``at``: the walk moves the hovered candidate."""
    mode.on_mouse_motion(app, *at)
    mode.on_key_press(app, key, 0)


# --- latching ---------------------------------------------------------------


def test_the_shortcut_latches_the_mode_on() -> None:
    mode, comments, app = _mode()

    assert mode.on_key_press(app, "c", _ENTER) is True
    assert comments.active is True


def test_the_meta_accelerator_also_enters() -> None:
    """Ctrl on Windows/Linux, Cmd on macOS -- one shortcut, spelled per platform."""
    mode, comments, app = _mode()

    mode.on_key_press(app, "c", MOD_META | MOD_SHIFT)

    assert comments.active is True


def test_a_bare_c_does_not_enter() -> None:
    mode, comments, app = _mode()

    assert mode.on_key_press(app, "c", 0) is False
    assert comments.active is False


def test_the_wrong_chord_does_not_enter() -> None:
    mode, comments, app = _mode()

    assert mode.on_key_press(app, "c", MOD_CTRL | MOD_ALT) is False
    assert comments.active is False


def test_enter_commits_and_leaves() -> None:
    """Enter keeps the session's work; the mark outlives the mode."""
    root = Column(children=[Text("AAA")])
    with mount(root) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)

        _leave(mode, app)

        assert comments.active is False
        assert len(comments.members()) == 1


def test_keys_pass_through_while_the_mode_is_off() -> None:
    mode, _comments, app = _mode()

    assert mode.on_key_press(app, "enter", 0) is False


def test_every_key_is_consumed_while_latched() -> None:
    """A half-passed-through keyboard would let the app act on picker input."""
    mode, _comments, app = _mode()
    mode.on_key_press(app, "c", _ENTER)

    assert mode.on_key_press(app, "tab", 0) is True
    assert mode.on_key_press(app, "a", 0) is True


# --- mark ------------------------------------------------------------


def test_a_click_designates_the_widget_under_the_cursor() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        _click(mode, app, 2, 2)

        assert comments.members() == [leaf]


def test_clicking_a_marked_widget_opens_its_field_again() -> None:
    """On its body as on its badge: a mark is edited by clicking it, never removed by a click."""
    leaf = Text("AAAAAAAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        rect = leaf.global_layout_rect
        assert rect is not None
        centre = (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
        _mark(mode, app, *centre)

        _click(mode, app, *centre)

        assert comments.members() == [leaf]
        assert mode.writing is not None and mode.writing.index == 1


def test_pointer_events_pass_through_while_the_mode_is_off() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()

        assert mode.on_mouse_press(app, 2, 2) is False
        assert mode.on_mouse_release(app, 2, 2) is False
        assert comments.members() == []


def test_a_drag_does_not_fall_back_to_a_click() -> None:
    """A drag marks a region, so it must not
    quietly mean something else in the meantime."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        mode.on_mouse_press(app, 2, 2)
        mode.on_mouse_release(app, 80, 60)

        assert comments.members() == []


def test_ctrl_z_takes_back_the_newest_mark_and_ctrl_shift_z_returns_it() -> None:
    first, second = Text("AAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        first_rect = first.global_layout_rect
        assert first_rect is not None
        _mark(mode, app, 2, 2)
        _mark(mode, app, 2, first_rect[3] + 2)
        assert len(comments.members()) == 2

        mode.on_key_press(app, "z", MOD_CTRL)
        assert comments.members() == [first]

        mode.on_key_press(app, "z", MOD_CTRL | MOD_SHIFT)
        assert comments.members() == [first, second]


@pytest.mark.parametrize("key", ["delete", "backspace"])
def test_delete_removes_the_mark_on_the_hovered_widget(key: str) -> None:
    """As next door, where it deletes the selected widget; here the mark is what goes."""
    leaf = Text("AAAAAAAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        rect = leaf.global_layout_rect
        assert rect is not None
        centre = (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
        _mark(mode, app, *centre)
        mode.on_mouse_motion(app, *centre)
        assert mode.hovered_badge is None, "on the widget, off its badge"

        assert mode.on_key_press(app, key, 0) is True
        assert comments.members() == []

        mode.on_key_press(app, "z", MOD_CTRL)
        assert comments.members() == [leaf], "one undo step"


def test_delete_removes_the_mark_whose_badge_is_under_the_pointer() -> None:
    """A region has no widget to hover, so its badge is the handle."""
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_press(app, 100, 100)
        mode.on_mouse_release(app, 160, 140)
        mode.on_key_press(app, "escape", 0)
        assert comments.regions() == [(100.0, 100.0, 60.0, 40.0)]
        mode.on_mouse_motion(app, 102, 101)
        assert mode.hovered_badge == 1

        mode.on_key_press(app, "delete", 0)

        assert comments.regions() == []
        assert mode.hovered_badge is None


def test_delete_with_no_mark_under_the_pointer_does_nothing() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        mode.on_mouse_motion(app, 150, 150)
        assert mode.hovered is not leaf

        assert mode.on_key_press(app, "backspace", 0) is True, "still consumed"
        assert comments.members() == [leaf]
        assert not comments.redoable, "no step was recorded"


def test_hover_tracks_the_pick_candidate() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)

        assert mode.on_mouse_motion(app, 2, 2) is True
        assert mode.hovered is leaf


# --- the splash, the help and the notice box --------------------------------


def _latched() -> tuple[CommentMode, _App, Any]:
    leaf = Text("AAA")
    host = mount(Column(children=[leaf]))
    root = host.__enter__().root
    host.layout(300, 200)
    app = _App(root)
    mode = CommentMode(Comments())
    mode.on_key_press(app, "c", _ENTER)
    return (mode, app, host)


def _later(monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    """Move the splash's clock ``seconds`` past real time."""
    import time

    from nuiitivet.dev import hud

    monkeypatch.setattr(hud, "_now", lambda: time.monotonic() + seconds)


def test_entering_shows_the_splash_for_a_moment(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.dev.hud import SPLASH

    mode, app, host = _latched()
    with host:
        assert mode.splash
        mode.on_mouse_motion(app, 150, 150)
        assert mode.splash, "input does not cut it short"

        _later(monkeypatch, SPLASH)

        assert not mode.splash


def test_leaving_shows_how_the_session_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.dev.hud import SEPARATOR, SPLASH

    mode, app, host = _latched()
    with host:
        _later(monkeypatch, SPLASH)
        assert mode.splash is None
        mode.on_key_press(app, "enter", 0)
        assert not mode.active
        assert mode.splash == "COMMENT MODE off" + SEPARATOR + "comments kept"

        mode.on_key_press(app, "c", _ENTER)
        monkeypatch.undo()
        _later(monkeypatch, SPLASH)
        mode.on_key_press(app, "escape", 0)
        assert mode.splash == "COMMENT MODE off" + SEPARATOR + "comments discarded"


def test_switching_to_layout_edit_mode_shows_no_leaving_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other mode's own line takes the centre; two there would overlap."""
    from nuiitivet.dev.hud import SPLASH
    from nuiitivet.dev.layout_edit_mode import LayoutEditMode
    from nuiitivet.dev.source_edit import EditLog

    mode, app, host = _latched()
    with host:
        layout = LayoutEditMode(EditLog())
        setattr(app, "_comment_mode", mode)
        setattr(app, "_layout_edit_mode", layout)
        _later(monkeypatch, SPLASH)
        assert mode.splash is None

        layout.on_key_press(app, "e", _ENTER)

        assert not mode.active and mode.splash is None
        assert layout.splash is not None


def test_h_shows_the_help_while_it_is_held() -> None:
    mode, app, host = _latched()
    with host:
        assert not mode.help

        assert mode.on_key_press(app, "h", 0) is True
        assert mode.help
        mode.on_key_press(app, "h", 0)
        assert mode.help, "the key repeating changes nothing"

        assert mode.on_key_release(app, "h", 0) is True
        assert not mode.help and mode.active


def test_h_types_into_an_open_field_instead() -> None:
    mode, app, host = _latched()
    with host:
        _click(mode, app, 2, 2)
        assert mode.writing is not None

        mode.on_key_press(app, "h", 0)

        assert not mode.help


def test_a_held_h_is_forgotten_on_entry() -> None:
    """``Esc`` under a held ``H`` leaves; the release then lands outside the mode."""
    mode, app, host = _latched()
    with host:
        mode.on_key_press(app, "h", 0)
        mode.on_key_press(app, "escape", 0)
        assert not mode.active
        mode.on_key_release(app, "h", 0)

        mode.on_key_press(app, "c", _ENTER)

        assert not mode.help


def test_the_pointer_nearing_the_badge_asks_for_a_frame_even_over_the_same_candidate() -> None:
    """The badge dodges at paint time, so the frame has to be requested here."""
    mode, app, host = _latched()
    with host:
        mode.on_mouse_motion(app, 150, 20)
        mode.placement.place((200.0, 44.0), (300.0, 200.0), mode.pointer)
        before = app.invalidated

        mode.on_mouse_motion(app, 150, 150)
        assert app.invalidated == before + 1, "one frame for the dodge"

        mode.placement.place((200.0, 44.0), (300.0, 200.0), mode.pointer)
        mode.on_mouse_motion(app, 151, 150)
        assert app.invalidated == before + 1, "not one per motion"


# --- ancestor walk ----------------------------------------------------------


def test_up_moves_the_candidate_to_its_parent_and_enter_marks_it() -> None:
    """A container its children cover cannot be clicked; the walk reaches it before the mark."""
    leaf = Text("AAA")
    column = Column(children=[leaf])
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        _walk(mode, app, "w")

        assert mode.hovered is column and mode.walked
        assert comments.members() == [], "the walk moves the candidate, not a mark"

        mode.on_key_press(app, "enter", 0)

        assert comments.members() == [column]
        assert mode.active and mode.writing is not None and mode.writing.index == 1
        assert not mode.walked


def test_down_retraces_the_way_up_came() -> None:
    """``down`` is only meaningful as the inverse of ``up``: one child of the
    current node lies on the path back to the widget under the cursor."""
    leaf = Text("AAA")
    column = Column(children=[leaf])
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, _comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _walk(mode, app, "w")
        _walk(mode, app, "w")

        _walk(mode, app, "s")
        assert mode.hovered is column
        _walk(mode, app, "s")
        assert mode.hovered is leaf and not mode.walked


def test_down_without_a_walk_does_nothing() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, _comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        _walk(mode, app, "s")

        assert mode.hovered is leaf and not mode.walked


def test_a_click_while_walked_marks_the_walked_widget() -> None:
    leaf = Text("AAA")
    column = Column(children=[leaf])
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _walk(mode, app, "w")

        _click(mode, app, 2, 2)

        assert comments.members() == [column], "not the leaf under the cursor"


def test_the_walk_survives_a_drift_and_ends_once_the_pointer_travels() -> None:
    """A hand resting on the mouse moves a pixel or two on a key press; more than
    the drag threshold is the hand aiming again, wherever the pointer lands."""
    from nuiitivet.dev.gesture import DRAG_THRESHOLD

    leaf = Text("AAAAAAAA")
    inner = Column(children=[leaf])
    with mount(Column(children=[inner])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, _comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _walk(mode, app, "w")
        assert mode.hovered is inner

        mode.on_mouse_motion(app, 2 + DRAG_THRESHOLD, 2 + DRAG_THRESHOLD)
        assert mode.hovered is inner, "a drift keeps the walk"

        mode.on_mouse_motion(app, 2 + DRAG_THRESHOLD + 1, 2)
        assert mode.hovered is leaf and not mode.walked, "still over the same leaf, but the hand moved"


def _centre(node: Any) -> tuple[float, float]:
    rect = node.global_layout_rect
    assert rect is not None
    return (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)


def test_right_moves_the_candidate_to_the_next_sibling_and_left_brings_it_back() -> None:
    """A row of small widgets is walked without the hand leaving the keys."""
    first, second, third = Text("AAAAAAAA"), Text("BBBBBBBB"), Text("CCCCCCCC")
    with mount(Column(children=[first, second, third])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        at = _centre(first)

        _walk(mode, app, "d", at)
        assert mode.hovered is second and mode.walked
        _walk(mode, app, "d", at)
        assert mode.hovered is third
        _walk(mode, app, "a", at)
        _walk(mode, app, "a", at)
        assert mode.hovered is first and not mode.walked, "back on the widget under the cursor"

        _walk(mode, app, "d", at)
        mode.on_key_press(app, "enter", 0)
        assert comments.members() == [second]


def test_the_sideways_walk_stops_at_either_end() -> None:
    first, second = Text("AAAAAAAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, _comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        at = _centre(first)

        _walk(mode, app, "a", at)
        assert mode.hovered is first and not mode.walked

        _walk(mode, app, "d", at)
        _walk(mode, app, "d", at)
        assert mode.hovered is second, "no wrap"


def test_the_sideways_walk_holds_by_the_same_drift() -> None:
    from nuiitivet.dev.gesture import DRAG_THRESHOLD

    first, second = Text("AAAAAAAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, _comments, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        at = _centre(first)
        _walk(mode, app, "d", at)
        assert mode.hovered is second

        mode.on_mouse_motion(app, at[0] + 1, at[1] + 1)
        assert mode.hovered is second, "a drift keeps the walk"

        mode.on_mouse_motion(app, at[0] + DRAG_THRESHOLD + 1, at[1])
        assert mode.hovered is first and not mode.walked


def test_enter_without_a_walk_still_leaves() -> None:
    mode, app, host = _latched()
    with host:
        mode.on_mouse_motion(app, 2, 2)

        mode.on_key_press(app, "enter", 0)

        assert not mode.active


# --- journal ----------------------------------------------------------------


def test_a_designation_leaves_a_content_free_marker() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        journal = InteractionJournal()
        mode = CommentMode(Comments(), journal=journal)
        mode.on_key_press(app, "c", _ENTER)

        _mark(mode, app, 2, 2)

        (event,) = journal.recent()
        assert event.kind == "comment"
        assert event.target is None


# --- repainting -------------------------------------------------------------


def test_latching_the_mode_asks_for_a_frame() -> None:
    """The overlay is a pure function of state read at paint time.

    So a state change that requests no frame is simply invisible: the mode
    latches, clicks stop reaching the app, and the human sees no reason why
    until something else happens to force a redraw.
    """
    mode, _comments, app = _mode()

    mode.on_key_press(app, "c", _ENTER)

    assert app.invalidated > 0


def test_every_designation_change_asks_for_a_frame() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)

        for act in (
            lambda: mode.on_mouse_motion(app, 2, 2),
            lambda: mode.on_key_press(app, "w", 0),
            lambda: mode.on_key_press(app, "s", 0),
            lambda: _mark(mode, app, 2, 2),
            lambda: mode.on_key_press(app, "z", MOD_CTRL),
            lambda: mode.on_key_press(app, "enter", 0),
        ):
            before = app.invalidated
            act()
            assert app.invalidated > before


def test_hovering_the_same_candidate_does_not_repaint() -> None:
    """A repaint per motion event would be a frame storm for no visible change."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_motion(app, 2, 2)

        settled = app.invalidated
        mode.on_mouse_motion(app, 3, 3)

        assert app.invalidated == settled


def test_a_session_never_repaints_the_tree() -> None:
    """Every frame a mode asks for leaves the tree clean: a mark, a hover, a
    band and the badge are all drawn over it, so the renderer reuses the tree
    it last painted instead of walking it again."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf, Text("BBB")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_motion(app, 2, 2)
        mode.on_mouse_motion(app, 2, 60)
        _mark(mode, app, 2, 2)
        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_motion(app, 60, 40)
        mode.on_mouse_release(app, 60, 40)
        _leave(mode, app)

        assert app.invalidated > 0
        assert app.tree_repaints == 0


def test_key_releases_are_swallowed_while_latched() -> None:
    """The press half is consumed, so a lone key-up must not reach the app.

    A widget that acts on key-up would otherwise fire from a keystroke whose
    beginning it never saw.
    """
    mode, _comments, app = _mode()

    assert mode.on_key_release(app, "c", _ENTER) is False
    mode.on_key_press(app, "c", _ENTER)
    assert mode.on_key_release(app, "c", _ENTER) is True


def test_escape_release_passes_through_after_leaving() -> None:
    """Leaving happens on the press, so the release lands with the mode already
    off -- and must not be swallowed, or the app's own escape latch never sees
    the key-up it gates on."""
    mode, _comments, app = _mode()
    mode.on_key_press(app, "c", _ENTER)
    mode.on_key_press(app, "escape", 0)

    assert mode.on_key_release(app, "escape", 0) is False


def test_a_walked_designation_still_survives_a_reload() -> None:
    """The walk must carry the structural path, or the refinement is unresolvable.

    A mark refined with the ancestor walk looks identical to one made by
    clicking, so a missing path here is invisible until a reload silently drops
    the member -- exactly the quiet truncation `lost` exists to prevent.
    """
    leaf = Text("AAA")
    column = Column(children=[leaf])
    comments = Comments()
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(comments)
        mode.on_key_press(app, "c", _ENTER)
        _walk(mode, app, "w")
        mode.on_key_press(app, "enter", 0)
        assert comments.members() == [column]

    rebuilt = Column(children=[Text("AAA")])
    with mount(rebuilt) as host:
        host.layout(300, 200)

        assert comments.restore(host.root) == 1
        assert comments.lost == 0
        assert comments.members() == [rebuilt]


# --- regions ---------------------------------------------------------


def test_a_drag_designates_the_area_it_swept() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)

        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_motion(app, 60, 40)
        mode.on_mouse_release(app, 60, 40)

        assert mode.comments.regions() == [(10.0, 10.0, 50.0, 30.0)]
        assert mode.comments.members() == []


def test_a_drag_normalizes_whichever_way_it_went() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)

        mode.on_mouse_press(app, 60, 40)
        mode.on_mouse_release(app, 10, 10)

        assert mode.comments.regions() == [(10.0, 10.0, 50.0, 30.0)]


def test_the_rubber_band_tracks_the_drag_and_clears_on_release() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)

        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_motion(app, 60, 40)
        assert mode.band == (10.0, 10.0, 50.0, 30.0)

        mode.on_mouse_release(app, 60, 40)
        assert mode.band is None


def test_a_drag_does_not_move_the_hover_candidate() -> None:
    """Mid-drag the pointer is sweeping an area, not aiming at a widget."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_motion(app, 2, 2)
        assert mode.hovered is leaf

        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_motion(app, 200, 180)

        assert mode.hovered is leaf


def test_leaving_clears_an_abandoned_band() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_motion(app, 60, 40)

        mode.on_key_press(app, "enter", 0)

        assert mode.band is None


# --- committing and discarding ---------------------------------------


def test_escape_discards_the_session() -> None:
    """Esc means "undo what I was doing" everywhere; it means that here too."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        comments = mode.comments
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        assert comments.members() == [leaf]

        mode.on_key_press(app, "escape", 0)

        assert comments.active is False
        assert comments.members() == []


def test_escape_rolls_back_only_the_session() -> None:
    """Re-entering to add one more mark and then changing your mind must not
    take the earlier marks with it."""
    first, second = Text("AAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        first_rect = first.global_layout_rect
        assert first_rect is not None

        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        _leave(mode, app)

        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, first_rect[3] + 2)
        assert len(mode.comments.members()) == 2
        mode.on_key_press(app, "escape", 0)

        assert mode.comments.members() == [first]


def test_escape_discards_regions_too() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_press(app, 10, 10)
        mode.on_mouse_release(app, 60, 40)
        assert mode.comments.regions()
        mode.on_key_press(app, "escape", 0)  # closes the field the region opened

        mode.on_key_press(app, "escape", 0)

        assert mode.comments.regions() == []


def test_a_discarded_session_still_moves_seq() -> None:
    """Marks go live as they are made, so a rollback is a state change an
    agent that read mid-session has to be able to notice."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        before = mode.comments.summary()["seq"]

        mode.on_key_press(app, "escape", 0)

        assert mode.comments.summary()["seq"] > before


def test_discarding_outside_a_session_changes_nothing() -> None:
    node = Text("AAA")
    comments = Comments()
    comments.add(node)

    comments.discard()

    assert comments.members() == [node]


def test_a_reload_mid_session_keeps_the_fallback_resolvable() -> None:
    """Cancelling after a reload must not restore members whose referents are
    already gone -- the snapshot holds the old objects too."""
    old = Column(children=[Text("HEADER", key="header")])
    with mount(old) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        mode.comments.add(old.children[0], root=host.root)
        mode.on_key_press(app, "enter", 0)
        mode.on_key_press(app, "c", _ENTER)

    rebuilt = Column(children=[Text("HEADER", key="header")])
    with mount(rebuilt) as host:
        host.layout(300, 200)
        mode.comments.restore(host.root)
        app = _App(host.root)

        mode.on_key_press(app, "escape", 0)

        assert mode.comments.members() == [rebuilt.children[0]]


def test_ctrl_backspace_clears_every_designation() -> None:
    """Removing marks one at a time is the discoverable way and the tedious one."""
    first, second = Text("AAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        rect = first.global_layout_rect
        assert rect is not None
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        _mark(mode, app, 2, rect[3] + 2)
        mode.on_mouse_press(app, 100, 100)
        mode.on_mouse_release(app, 160, 150)
        mode.on_key_press(app, "escape", 0)  # closes the field the region opened
        assert len(mode.comments.marks()) == 3

        mode.on_key_press(app, "backspace", MOD_CTRL)

        assert mode.comments.marks() == []


def test_clearing_is_a_session_operation_so_escape_undoes_it() -> None:
    """Which is what makes a destructive key safe to reach for."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        _leave(mode, app)

        mode.on_key_press(app, "c", _ENTER)
        mode.on_key_press(app, "backspace", MOD_CTRL)
        assert mode.comments.members() == []
        mode.on_key_press(app, "escape", 0)

        assert mode.comments.members() == [leaf]


def test_a_committed_designation_can_still_be_cleared() -> None:
    """The gap that prompted the key: after Enter there was no way back."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        _mark(mode, app, 2, 2)
        _leave(mode, app)

        mode.on_key_press(app, "c", _ENTER)
        mode.on_key_press(app, "backspace", MOD_CTRL)
        mode.on_key_press(app, "enter", 0)

        assert mode.comments.members() == []


def test_text_motions_are_swallowed_while_latched() -> None:
    from nuiitivet.input.codes import TEXT_MOTION_BACKSPACE

    mode, _comments, app = _mode()
    assert mode.on_text_motion(app, TEXT_MOTION_BACKSPACE, False) is False

    mode.on_key_press(app, "c", _ENTER)

    assert mode.on_text_motion(app, TEXT_MOTION_BACKSPACE, False) is True


# --- writing on a mark ------------------------------------------------------


def _marked() -> tuple[CommentMode, _App, Any, Any]:
    """Comment mode latched on with the one leaf marked; its badge sits at (0, 0)."""
    leaf = Text("AAAAAAAA")
    host = mount(Column(children=[leaf]))
    root = host.__enter__().root
    host.layout(300, 200)
    app = _App(root)
    mode = CommentMode(Comments())
    mode.on_key_press(app, "c", _ENTER)
    _click(mode, app, 2, 2)
    return (mode, app, host, leaf)


def test_a_click_on_the_badge_opens_the_field_on_that_mark() -> None:
    mode, app, host, leaf = _marked()
    with host:
        _click(mode, app, 2, 2)

        assert mode.writing is not None and mode.writing.index == 1
        assert mode.comments.members() == [leaf], "the badge click is not an unmark"


def test_typing_then_enter_writes_the_instruction_and_leaves_a_marker() -> None:
    journal = InteractionJournal()
    leaf = Text("AAAAAAAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments(), journal=journal)
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)
        _click(mode, app, 2, 2)
        before = len(journal.recent())

        assert mode.on_text(app, "wider") is True
        mode.on_key_press(app, "enter", 0)

        assert mode.writing is None
        assert mode.active, "writing does not end the session"
        assert mode.comments.instruction(1) == "wider"
        assert [event.kind for event in journal.recent()[before:]] == ["comment"]


def test_escape_closes_the_field_without_writing() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        _click(mode, app, 2, 2)
        mode.on_text(app, "wider")

        mode.on_key_press(app, "escape", 0)

        assert mode.writing is None
        assert mode.active, "Esc closed the field, not the session"
        assert mode.comments.instruction(1) is None


def test_a_click_elsewhere_writes_the_field_and_then_marks_as_usual() -> None:
    first, second = Text("AAAAAAAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        rect = second.global_layout_rect
        assert rect is not None
        _click(mode, app, 2, 2)
        mode.on_text(app, "wider")

        _click(mode, app, rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)

        assert mode.comments.instruction(1) == "wider"
        assert mode.comments.members() == [first, second], "the click went on to mark the second"
        assert mode.writing is not None and mode.writing.index == 2


def test_shift_enter_breaks_the_line_in_the_field_and_enter_writes_both() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        _click(mode, app, 2, 2)
        mode.on_text(app, "wider")

        mode.on_key_press(app, "enter", MOD_SHIFT)

        assert mode.writing is not None
        assert mode.comments.instruction(1) is None
        mode.on_text(app, "and taller")
        mode.on_key_press(app, "enter", 0)

        assert mode.writing is None
        assert mode.comments.instruction(1) == "wider\nand taller"


def test_a_new_mark_opens_its_field_at_once() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        assert mode.writing is not None and mode.writing.index == 1


def test_a_drag_opens_the_field_on_the_region() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_key_press(app, "escape", 0)

        mode.on_mouse_press(app, 100, 100)
        mode.on_mouse_release(app, 160, 150)

        assert mode.writing is not None and mode.writing.index == 2


def test_mark_write_leave_is_click_type_enter_enter() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_text(app, "wider")
        mode.on_key_press(app, "enter", 0)
        assert mode.active and mode.writing is None

        mode.on_key_press(app, "enter", 0)

        assert not mode.active
        assert mode.comments.instruction(1) == "wider"


def test_escape_closes_the_field_and_enter_then_leaves() -> None:
    """The pointer still on the mark does not reopen its field: only the badge does."""
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_key_press(app, "escape", 0)
        assert mode.active and mode.writing is None

        mode.on_key_press(app, "enter", 0)

        assert not mode.active


def test_a_key_that_does_nothing_here_keeps_the_walk() -> None:
    """An arrow tried before ``W``, a bare modifier, an input-method key: the
    human saw nothing happen, so ``Enter`` must still mean what the badge says."""
    mode, app, host = _latched()
    with host:
        _walk(mode, app, "w")
        for name, mods in (("up", 0), ("lshift", MOD_SHIFT), ("f13", 0)):
            mode.on_key_press(app, name, mods)

        mode.on_key_press(app, "enter", 0)

        assert mode.active and mode.writing is not None, "Enter marked the walked widget"


def test_clicks_in_a_row_mark_each_widget_and_a_click_on_a_marked_one_opens_its_field() -> None:
    first, second = Text("AAAAAAAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = CommentMode(Comments())
        mode.on_key_press(app, "c", _ENTER)
        rects = [leaf.global_layout_rect for leaf in (first, second)]
        assert rects[0] is not None and rects[1] is not None
        centres = [(r[0] + r[2] / 2, r[1] + r[3] / 2) for r in rects if r is not None]
        _click(mode, app, *centres[0])
        _click(mode, app, *centres[1])
        assert mode.comments.members() == [first, second]

        _click(mode, app, *centres[0])

        assert mode.writing is not None and mode.writing.index == 1
        assert mode.comments.members() == [first, second]
        mode.on_key_press(app, "escape", 0)
        mode.on_key_press(app, "enter", 0)
        assert not mode.active


def test_the_field_reopens_on_the_text_already_written() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        _click(mode, app, 2, 2)
        mode.on_text(app, "wider")
        mode.on_key_press(app, "enter", 0)

        _click(mode, app, 2, 2)

        assert mode.writing is not None and mode.writing.field.text == "wider"


def test_the_mode_keys_are_the_fields_while_it_is_open() -> None:
    """``W`` types a letter rather than walking, and ``Backspace`` edits rather than unmarking."""
    mode, app, host, leaf = _marked()
    with host:
        _click(mode, app, 2, 2)
        mode.on_text(app, "w")
        mode.on_key_press(app, "backspace", 0)
        mode.on_key_press(app, "w", 0)

        assert mode.comments.members() == [leaf]
        assert mode.writing is not None and mode.writing.field.text == ""


def test_text_is_not_taken_without_a_field() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_key_press(app, "escape", 0)
        assert mode.on_text(app, "x") is False
        assert mode.on_ime_composition(app, "x", 0, 1) is False


def test_the_pointer_on_a_badge_is_tracked_and_asks_for_a_frame_once() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_mouse_motion(app, 150, 150)
        assert mode.hovered_badge is None
        before = app.invalidated

        assert mode.on_mouse_motion(app, 2, 2) is True
        assert mode.hovered_badge == 1
        assert app.invalidated > before, "the badge came under the pointer"
        settled = app.invalidated
        mode.on_mouse_motion(app, 3, 3)
        assert app.invalidated == settled, "the same badge does not repaint"


def test_a_click_on_a_hovered_badge_still_opens_its_field() -> None:
    mode, app, host, _leaf = _marked()
    with host:
        mode.on_mouse_motion(app, 2, 2)
        _click(mode, app, 2, 2)

        assert mode.writing is not None and mode.writing.index == 1
