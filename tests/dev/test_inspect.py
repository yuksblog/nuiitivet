"""Tests for inspect mode -- the gesture layer over the designation buffer (#591)."""

from __future__ import annotations

from typing import Any

from nuiitivet.dev.inspect import InspectMode
from nuiitivet.dev.interaction import InteractionJournal
from nuiitivet.dev.selection import Selection
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

    def invalidate(self) -> None:
        self.invalidated += 1


def _mode() -> tuple[InspectMode, Selection, _App]:
    """A mode with no tree under it, for the tests that only exercise keys."""
    selection = Selection()
    return (InspectMode(selection), selection, _App())


def _click(mode: InspectMode, app: _App, x: float, y: float) -> None:
    mode.on_mouse_press(app, x, y)
    mode.on_mouse_release(app, x, y)


# --- latching ---------------------------------------------------------------


def test_the_shortcut_latches_the_mode_on() -> None:
    mode, selection, app = _mode()

    assert mode.on_key_press(app, "c", _ENTER) is True
    assert selection.active is True


def test_the_meta_accelerator_also_enters() -> None:
    """Ctrl on Windows/Linux, Cmd on macOS -- one shortcut, spelled per platform."""
    mode, selection, app = _mode()

    mode.on_key_press(app, "c", MOD_META | MOD_SHIFT)

    assert selection.active is True


def test_a_bare_c_does_not_enter() -> None:
    mode, selection, app = _mode()

    assert mode.on_key_press(app, "c", 0) is False
    assert selection.active is False


def test_the_wrong_chord_does_not_enter() -> None:
    mode, selection, app = _mode()

    assert mode.on_key_press(app, "c", MOD_CTRL | MOD_ALT) is False
    assert selection.active is False


def test_escape_leaves_and_commits() -> None:
    """Leaving is the commit; the designation outlives the mode."""
    root = Column(children=[Text("AAA")])
    with mount(root) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)

        mode.on_key_press(app, "escape", 0)

        assert selection.active is False
        assert len(selection.members()) == 1


def test_keys_pass_through_while_the_mode_is_off() -> None:
    mode, _selection, app = _mode()

    assert mode.on_key_press(app, "enter", 0) is False


def test_every_key_is_consumed_while_latched() -> None:
    """A half-passed-through keyboard would let the app act on picker input."""
    mode, _selection, app = _mode()
    mode.on_key_press(app, "c", _ENTER)

    assert mode.on_key_press(app, "enter", 0) is True
    assert mode.on_key_press(app, "a", 0) is True


# --- designation ------------------------------------------------------------


def test_a_click_designates_the_widget_under_the_cursor() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        _click(mode, app, 2, 2)

        assert selection.members() == [leaf]


def test_clicking_a_designated_widget_removes_it() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        _click(mode, app, 2, 2)
        _click(mode, app, 2, 2)

        assert selection.members() == []


def test_pointer_events_pass_through_while_the_mode_is_off() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()

        assert mode.on_mouse_press(app, 2, 2) is False
        assert mode.on_mouse_release(app, 2, 2) is False
        assert selection.members() == []


def test_a_drag_does_not_fall_back_to_a_click() -> None:
    """A drag designates a region (the second half of #591), so it must not
    quietly mean something else in the meantime."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)

        mode.on_mouse_press(app, 2, 2)
        mode.on_mouse_release(app, 80, 60)

        assert selection.members() == []


def test_backspace_removes_the_newest_designation() -> None:
    first, second = Text("AAA"), Text("BBBBBBBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        first_rect = first.global_layout_rect
        assert first_rect is not None
        _click(mode, app, 2, 2)
        _click(mode, app, 2, first_rect[3] + 2)
        assert len(selection.members()) == 2

        mode.on_key_press(app, "backspace", 0)

        assert selection.members() == [first]


def test_hover_tracks_the_pick_candidate() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = InspectMode(Selection())
        mode.on_key_press(app, "c", _ENTER)

        assert mode.on_mouse_motion(app, 2, 2) is True
        assert mode.hovered is leaf


# --- ancestor walk ----------------------------------------------------------


def test_up_replaces_the_member_with_its_parent() -> None:
    leaf = Text("AAA")
    column = Column(children=[leaf])
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)

        mode.on_key_press(app, "up", 0)

        assert selection.members() == [column]


def test_down_retraces_the_way_up_came() -> None:
    """``down`` is only meaningful as the inverse of ``up``: one child of the
    current node lies on the path back to where the human started."""
    leaf = Text("AAA")
    column = Column(children=[leaf])
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)
        mode.on_key_press(app, "up", 0)
        mode.on_key_press(app, "up", 0)

        mode.on_key_press(app, "down", 0)
        assert selection.members() == [column]
        mode.on_key_press(app, "down", 0)
        assert selection.members() == [leaf]


def test_down_without_a_walk_does_nothing() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode, selection, _stub = _mode()
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)

        mode.on_key_press(app, "down", 0)

        assert selection.members() == [leaf]


# --- journal ----------------------------------------------------------------


def test_a_designation_leaves_a_content_free_marker() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        journal = InteractionJournal()
        mode = InspectMode(Selection(), journal=journal)
        mode.on_key_press(app, "c", _ENTER)

        _click(mode, app, 2, 2)

        (event,) = journal.recent()
        assert event.kind == "select"
        assert event.target is None


# --- repainting -------------------------------------------------------------


def test_latching_the_mode_asks_for_a_frame() -> None:
    """The overlay is a pure function of state read at paint time.

    So a state change that requests no frame is simply invisible: the mode
    latches, clicks stop reaching the app, and the human sees no reason why
    until something else happens to force a redraw.
    """
    mode, _selection, app = _mode()

    mode.on_key_press(app, "c", _ENTER)

    assert app.invalidated > 0


def test_every_designation_change_asks_for_a_frame() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = InspectMode(Selection())
        mode.on_key_press(app, "c", _ENTER)

        for act in (
            lambda: _click(mode, app, 2, 2),
            lambda: mode.on_key_press(app, "up", 0),
            lambda: mode.on_key_press(app, "down", 0),
            lambda: mode.on_key_press(app, "backspace", 0),
            lambda: mode.on_key_press(app, "escape", 0),
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
        mode = InspectMode(Selection())
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_motion(app, 2, 2)

        settled = app.invalidated
        mode.on_mouse_motion(app, 3, 3)

        assert app.invalidated == settled


def test_key_releases_are_swallowed_while_latched() -> None:
    """The press half is consumed, so a lone key-up must not reach the app.

    A widget that acts on key-up would otherwise fire from a keystroke whose
    beginning it never saw.
    """
    mode, _selection, app = _mode()

    assert mode.on_key_release(app, "c", _ENTER) is False
    mode.on_key_press(app, "c", _ENTER)
    assert mode.on_key_release(app, "c", _ENTER) is True


def test_escape_release_passes_through_after_leaving() -> None:
    """Leaving happens on the press, so the release lands with the mode already
    off -- and must not be swallowed, or the app's own escape latch never sees
    the key-up it gates on."""
    mode, _selection, app = _mode()
    mode.on_key_press(app, "c", _ENTER)
    mode.on_key_press(app, "escape", 0)

    assert mode.on_key_release(app, "escape", 0) is False


def test_a_walked_designation_still_survives_a_reload() -> None:
    """The walk must carry the structural path, or the refinement is unresolvable.

    A designation refined with the ancestor walk looks identical to one made by
    clicking, so a missing path here is invisible until a reload silently drops
    the member -- exactly the quiet truncation `lost` exists to prevent.
    """
    leaf = Text("AAA")
    column = Column(children=[leaf])
    selection = Selection()
    with mount(column) as host:
        host.layout(300, 200)
        app = _App(host.root)
        mode = InspectMode(selection)
        mode.on_key_press(app, "c", _ENTER)
        _click(mode, app, 2, 2)
        mode.on_key_press(app, "up", 0)
        assert selection.members() == [column]

    rebuilt = Column(children=[Text("AAA")])
    with mount(rebuilt) as host:
        host.layout(300, 200)

        assert selection.restore(host.root) == 1
        assert selection.lost == 0
        assert selection.members() == [rebuilt]
