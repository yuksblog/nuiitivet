"""A fixed size declared on a RasterSurface or a ComposableWidget is its preferred size."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.stack import Stack
from nuiitivet.material.text import Text
from nuiitivet.observable import State
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.raster_surface import RasterSurface


def _surface(**kwargs: object) -> RasterSurface:
    return RasterSurface.draw(State(0), lambda _value, w, h: None, **kwargs)  # type: ignore[arg-type]


def test_a_raster_surface_reports_its_fixed_size() -> None:
    assert _surface(width=300, height=160).preferred_size() == (300, 160)
    assert _surface(width="wt", height=160).preferred_size(672, 800) == (0, 160)


def test_a_raster_surface_without_a_fixed_size_reports_its_padding() -> None:
    assert _surface(width="wt", height="wt", padding=(1, 2, 3, 4)).preferred_size() == (4, 6)


class _Editor(ComposableWidget):
    def __init__(self, **sizing: object) -> None:
        super().__init__(**sizing)  # type: ignore[arg-type]

    def build(self) -> Widget:
        return Text("short")


def test_a_composable_reports_the_fixed_height_it_declares() -> None:
    with AppHarness(lambda: Column([_Editor(width="wt", height=160, key="editor")]), size=(672, 800)) as app:
        editor = app.get(key="editor").widget
        assert editor.preferred_size(672, 800)[1] == 160


def test_a_composable_without_a_declared_size_reports_the_built_child() -> None:
    with AppHarness(lambda: Column([_Editor(key="editor")]), size=(672, 800)) as app:
        editor = app.get(key="editor").widget
        built = editor._built
        assert built is not None
        assert editor.preferred_size(672, 800) == built.preferred_size(672, 800)


class _SurfaceEditor(ComposableWidget):
    def __init__(self) -> None:
        super().__init__(width="wt", height=160, key="editor")

    def build(self) -> Widget:
        return Stack([_surface(width="wt", height=160), Text("no image", padding=12)], width="wt", alignment="center")


def test_a_column_holds_a_fixed_height_composable_and_what_follows() -> None:
    """The issue's reproduction: the last row stays inside the column."""

    def build() -> Widget:
        # Nested, so the column takes its preferred height rather than the window's.
        return Column(
            [
                Column(
                    [Text("Title"), _SurfaceEditor(), Text("below", key="below")],
                    gap=8,
                    padding=24,
                    width=480,
                    key="column",
                )
            ]
        )

    with AppHarness(build, size=(672, 800)) as app:
        column = app.get(key="column").rect
        editor = app.get(key="editor").rect
        below = app.get(key="below").rect
        assert column is not None and editor is not None and below is not None
        _cx, column_y, _cw, column_h = column
        assert editor[3] == 160
        _bx, below_y, _bw, below_h = below
        assert below_y + below_h <= column_y + column_h
