"""The MatplotlibFigure draws its figure at the device size, in the theme's colors, from an observable."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

matplotlib = pytest.importorskip("matplotlib", reason="the matplotlib extra is not installed")

from matplotlib.colors import to_hex, to_rgba  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import nuiitivet.material.matplotlib_figure as figure_mod  # noqa: E402
import nuiitivet.widgets.raster_surface as raster_mod  # noqa: E402
from nuiitivet.material.matplotlib_figure import MatplotlibFigure  # noqa: E402
from nuiitivet.material.theme.color_role import ColorRole  # noqa: E402
from nuiitivet.material.theme.material_theme import MaterialThemeFactory  # noqa: E402
from nuiitivet.observable import Observable  # noqa: E402
from nuiitivet.theme.theme import Theme  # noqa: E402
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks  # noqa: E402

LIGHT, DARK = MaterialThemeFactory.from_seed_pair("#6750A4")


def _role(theme: Theme, role: ColorRole) -> str:
    return str(role.resolve(theme)).lower()


@pytest.fixture
def theme(monkeypatch: pytest.MonkeyPatch) -> list[Theme]:
    """The theme the widget reads, as a one-element list so a test can swap it."""
    current = [LIGHT]
    generation = [0]

    def of(_context: object) -> Theme:
        return current[0]

    monkeypatch.setattr(figure_mod, "Theme", SimpleNamespace(of=of))
    monkeypatch.setattr(figure_mod, "theme_generation", lambda _context: generation[0])
    monkeypatch.setattr(raster_mod, "make_raster_image", lambda pixels, w, h: (w, h))
    monkeypatch.setattr(raster_mod, "find_window", lambda _widget: SimpleNamespace(pixel_ratio=2.0))

    class _Swap(list):
        def switch(self, theme: Theme) -> None:
            current[0] = theme
            generation[0] += 1

    swap = _Swap([LIGHT])
    return swap


def _rendered(widget: MatplotlibFigure, width: int = 160, height: int = 100) -> None:
    widget.layout(width, height)
    flush_size_change_callbacks()


def test_the_figure_is_drawn_at_the_device_size_with_logical_points(theme: list[Theme]) -> None:
    figure = Figure()
    figure.subplots().plot([0, 1], [0, 1])
    widget = MatplotlibFigure(figure, width=161, height=99)

    _rendered(widget, 161, 99)

    # 161x99 logical at a 2x ratio: an odd device size, drawn exactly.
    assert figure.canvas.get_width_height() == (322, 198)
    assert figure.dpi == 192
    assert widget._image_px == (322, 198)


def test_series_in_stock_colors_take_the_theme_s_accents_and_a_set_color_stays(theme: list[Theme]) -> None:
    figure = Figure()
    ax = figure.subplots()
    (first,) = ax.plot([0, 1], [0, 1])
    (second,) = ax.plot([0, 1], [1, 0])
    (mine,) = ax.plot([0, 1], [0.5, 0.5], color="#123456")
    ax.set_title("t")
    widget = MatplotlibFigure(figure, width=160, height=100)

    _rendered(widget)

    assert to_hex(first.get_color()) == _role(LIGHT, ColorRole.PRIMARY)
    assert to_hex(second.get_color()) == _role(LIGHT, ColorRole.TERTIARY)
    assert to_hex(mine.get_color()) == "#123456"
    assert to_hex(ax.title.get_color()) == _role(LIGHT, ColorRole.ON_SURFACE)
    assert to_hex(ax.spines["left"].get_edgecolor()) == _role(LIGHT, ColorRole.OUTLINE_VARIANT)
    assert to_rgba(figure.patch.get_facecolor())[3] == 0.0


def test_a_theme_change_recolors_the_series(theme: list[Theme]) -> None:
    figure = Figure()
    ax = figure.subplots()
    (line,) = ax.plot([0, 1], [0, 1])
    widget = MatplotlibFigure(figure, width=160, height=100)
    _rendered(widget)
    assert to_hex(line.get_color()) == _role(LIGHT, ColorRole.PRIMARY)

    theme.switch(DARK)  # type: ignore[attr-defined]
    _rendered(widget)

    assert to_hex(line.get_color()) == _role(DARK, ColorRole.PRIMARY)
    assert to_hex(ax.title.get_color()) == _role(DARK, ColorRole.ON_SURFACE)


def test_an_unthemed_figure_keeps_its_colors(theme: list[Theme]) -> None:
    figure = Figure()
    (line,) = figure.subplots().plot([0, 1], [0, 1])
    stock = to_hex(line.get_color())
    widget = MatplotlibFigure(figure, themed=False, width=160, height=100)

    _rendered(widget)

    assert to_hex(line.get_color()) == stock
    assert to_rgba(figure.patch.get_facecolor())[3] == 1.0


def test_plot_runs_on_each_value_before_the_draw_and_not_on_a_resize(theme: list[Theme]) -> None:
    figure = Figure()
    ax = figure.subplots()
    (line,) = ax.plot([0, 1], [0, 0])
    data: Observable[float] = Observable(1.0)
    plotted: list[float] = []

    def plot(fig: Figure, value: float) -> None:
        assert fig is figure
        plotted.append(value)
        line.set_ydata([0, value])

    widget = MatplotlibFigure.plot(figure, data, plot, width=160, height=100)
    _rendered(widget)
    assert plotted == [1.0]
    assert to_hex(line.get_color()) == _role(LIGHT, ColorRole.PRIMARY)

    data.value = 2.0
    flush_size_change_callbacks()
    assert plotted == [1.0, 2.0]

    _rendered(widget, 320, 200)
    assert plotted == [1.0, 2.0]
    assert widget._image_px == (640, 400)


def test_without_matplotlib_the_error_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "matplotlib.backends.backend_agg", None)

    with pytest.raises(ImportError, match=r"nuiitivet\[matplotlib\]"):
        MatplotlibFigure(Figure())
