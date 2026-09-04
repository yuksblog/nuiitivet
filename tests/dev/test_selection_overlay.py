"""Tests for the inspect-mode overlay.

The load-bearing property is negative: the human's designations are drawn for
the human only, and must never reach the assistant's perception. If they did,
the assistant would read its own human's annotations back as app content.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet._interaction.perception import describe_tree
from nuiitivet.dev import selection_overlay as so
from nuiitivet.dev.inspect import InspectMode
from nuiitivet.dev.selection import Selection
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
    def __init__(self, root: Any, mode: Any = None) -> None:
        self.root = root
        self.width = 300
        self.height = 200
        self._inspect_mode = mode


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NUIITIVET_DEV_ACTION_OVERLAY", raising=False)


@pytest.fixture
def designating() -> Iterator[tuple[_App, InspectMode]]:
    """An app with inspect mode latched on and one widget already designated."""
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        mode = InspectMode(Selection())
        app = _App(host.root, mode)
        mode.on_key_press(app, "c", _ENTER)
        mode.on_mouse_press(app, 2, 2)
        mode.on_mouse_release(app, 2, 2)
        yield (app, mode)


def test_the_overlay_never_enters_the_widget_tree(
    designating: tuple[_App, InspectMode]
) -> None:
    """The invariant: it holds no widgets, so ``describe_tree`` cannot see it."""
    app, _mode = designating
    before = describe_tree(app.root)

    so.paint_selection(app, _Canvas(), app.width, app.height)

    assert describe_tree(app.root) == before


def test_paints_something_while_designating(designating: tuple[_App, InspectMode]) -> None:
    app, _mode = designating
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert canvas.calls, "a designated widget must be marked on screen"


def test_paints_nothing_without_an_inspect_mode() -> None:
    """Production, and any run without the dev runner."""
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        so.paint_selection(_App(host.root), canvas, 300, 200)

        assert canvas.calls == []


def test_paints_nothing_when_idle_with_nothing_designated() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)
        canvas = _Canvas()

        so.paint_selection(_App(host.root, InspectMode(Selection())), canvas, 300, 200)

        assert canvas.calls == []


def test_the_env_kill_switch_disables_it(
    designating: tuple[_App, InspectMode], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, _mode = designating
    monkeypatch.setenv("NUIITIVET_DEV_ACTION_OVERLAY", "0")
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert canvas.calls == []


def test_a_committed_designation_still_marks_the_screen(
    designating: tuple[_App, InspectMode]
) -> None:
    """Leaving commits, so the badges survive the mode being switched off."""
    app, mode = designating
    mode.on_key_press(app, "enter", 0)
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert canvas.calls, "committed designations keep their numbered badges"


def test_painting_never_raises_on_a_broken_canvas(
    designating: tuple[_App, InspectMode]
) -> None:
    """A decoration must never break the frame."""

    class _Broken:
        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("boom")

    app, _mode = designating

    so.paint_selection(app, _Broken(), app.width, app.height)


def test_a_region_is_marked_on_screen(designating: tuple[_App, InspectMode]) -> None:
    app, mode = designating
    mode.selection.add_region((10.0, 10.0, 40.0, 30.0))
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert "drawRect" in canvas.calls, "a designated area needs its own wash"


def test_a_region_only_selection_still_paints(designating: tuple[_App, InspectMode]) -> None:
    """Regions and nodes are independent, so either alone must be drawable."""
    app, mode = designating
    mode.selection.clear()
    mode.selection.add_region((10.0, 10.0, 40.0, 30.0))
    mode.on_key_press(app, "enter", 0)
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert canvas.calls


def test_the_rubber_band_is_drawn_while_dragging(
    designating: tuple[_App, InspectMode]
) -> None:
    app, mode = designating
    mode.on_mouse_press(app, 10, 10)
    mode.on_mouse_motion(app, 60, 40)
    canvas = _Canvas()

    so.paint_selection(app, canvas, app.width, app.height)

    assert mode.band is not None
    assert "drawRect" in canvas.calls


def test_the_hud_names_every_gesture_the_mode_binds() -> None:
    """The badge is the only place a human can learn these, so an omission hides
    a feature completely.

    ``Backspace`` went undiscovered in real use precisely because the HUD never
    mentioned it. The list has since widened past "ways to unmake a designation":
    the source jump is discoverable the same way and nowhere else, which
    is what let it be a modifier rather than a button on the glass.
    """
    assert set(so._HINTS) == {
        "Enter keep",
        "Esc discard",
        "Backspace remove",
        "Ctrl+Backspace clear",
        "Ctrl+Click source",
    }


def test_the_hud_wraps_instead_of_running_off_a_narrow_window() -> None:
    """A dev app is often a few hundred pixels wide; a hint off the edge teaches
    nothing."""
    from nuiitivet.rendering.skia.font import (
        get_default_font_fallbacks,
        get_typeface,
        measure_text_width,
    )

    typeface = get_typeface(family_candidates=get_default_font_fallbacks(), fallback_to_default=True)
    limit = 200.0

    lines = so._wrap(so._HINTS, typeface, limit)

    assert len(lines) > 1
    for line in lines:
        assert measure_text_width(typeface, so._FONT_SIZE, line) <= limit


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

            caption = so._describe(leaf)
    finally:
        source.uninstall()

    assert "test_selection_overlay.py:" in caption


def test_the_caption_omits_the_location_when_none_was_recorded() -> None:
    """A production-shaped run reads exactly as it did before source capture."""
    leaf = Text("AAA")

    assert "·" not in so._describe(leaf)


def test_a_node_mark_paints_only_in_its_own_window() -> None:
    """The selection is shared across windows; the rect must not ghost into
    windows that do not contain the node."""
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    main_content = Container(width=50, height=40)
    app = App(Window(content=main_content, width=300, height=200))
    second = Window(content=Container(), width=300, height=200).open()
    main_win = app.main_window
    main_win.root.layout(300, 200)

    selection = Selection()
    selection.toggle(main_content, root=main_win.root)
    main_win._inspect_mode = InspectMode(selection)
    second._inspect_mode = InspectMode(selection)

    own_canvas, foreign_canvas = _Canvas(), _Canvas()
    so.paint_selection(main_win, own_canvas, 300, 200)
    so.paint_selection(second, foreign_canvas, 300, 200)

    assert own_canvas.calls
    assert foreign_canvas.calls == []
