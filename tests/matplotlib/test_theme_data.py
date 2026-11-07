"""The MatplotlibFigure takes its colors from the MatplotlibFigureThemeData of the theme it is under.

Each design system registers one; a theme without one draws the neutral defaults.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

matplotlib = pytest.importorskip("matplotlib", reason="the matplotlib extra is not installed")

from matplotlib.colors import to_hex  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import nuiitivet.matplotlib.figure as figure_mod  # noqa: E402
import nuiitivet.widgets.raster_surface as raster_mod  # noqa: E402
from nuiitivet.matplotlib.figure import MatplotlibFigure  # noqa: E402
from nuiitivet.matplotlib.theme_data import MatplotlibFigureThemeData  # noqa: E402
from nuiitivet.theme.plain_theme import PlainColorRole, PlainTheme  # noqa: E402
from nuiitivet.theme.theme import Theme  # noqa: E402
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks  # noqa: E402

PLAIN = PlainTheme.light()


@pytest.fixture
def theme(monkeypatch: pytest.MonkeyPatch) -> list[Theme]:
    """The theme the widget reads, as a one-element list a test fills; a 2x display and no Skia image."""
    current: list[Theme] = [PLAIN]
    monkeypatch.setattr(figure_mod, "Theme", SimpleNamespace(of=lambda _context: current[0]))
    monkeypatch.setattr(figure_mod, "theme_generation", lambda _context: 0)
    monkeypatch.setattr(raster_mod, "make_raster_image", lambda pixels, w, h: (w, h))
    monkeypatch.setattr(raster_mod, "find_window", lambda _widget: SimpleNamespace(pixel_ratio=2.0))
    return current


def _drawn(widget: MatplotlibFigure) -> None:
    widget.layout(160, 100)
    flush_size_change_callbacks()


def _plotted() -> tuple[Figure, Any, Any]:
    figure = Figure()
    ax = figure.subplots()
    (line,) = ax.plot([0, 1], [0, 1])
    ax.set_title("t")
    return figure, ax, line


def test_the_plain_theme_colors_the_text_on_surface_and_keeps_matplotlib_s_series(theme: list[Theme]) -> None:
    figure, ax, line = _plotted()
    stock = to_hex(line.get_color())

    _drawn(MatplotlibFigure(figure))

    assert to_hex(ax.title.get_color()) == str(PlainColorRole.ON_SURFACE.resolve(PLAIN)).lower()
    assert to_hex(line.get_color()) == stock  # the Plain palette names no series colors


def test_a_theme_without_the_palette_draws_the_neutral_defaults(theme: list[Theme]) -> None:
    theme[0] = Theme(mode="light", extensions=[], name="bare")
    figure, ax, line = _plotted()
    stock = to_hex(line.get_color())

    _drawn(MatplotlibFigure(figure))

    assert to_hex(ax.title.get_color()) == "#000000"
    assert to_hex(line.get_color()) == stock


def test_the_palette_registered_in_the_theme_recolors_the_series(theme: list[Theme]) -> None:
    palette = MatplotlibFigureThemeData(series=("#ff0000", "#00ff00"), rubberband="#0000ff")
    theme[0] = Theme(mode="light", extensions=[palette], name="custom")
    figure, _ax, line = _plotted()

    _drawn(MatplotlibFigure(figure))

    assert to_hex(line.get_color()) == "#ff0000"
    assert figure_mod._palette(theme[0]) is palette
