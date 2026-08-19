"""Tests for the inspect-mode overlay (#591).

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
    mode.on_key_press(app, "escape", 0)
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
