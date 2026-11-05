"""The MatplotlibFigure draws its figure at the device size, in the theme's colors, from an observable.

It hands the pointer and the keyboard to the figure as matplotlib events and answers ``draw_idle``.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

matplotlib = pytest.importorskip("matplotlib", reason="the matplotlib extra is not installed")

from matplotlib.backend_bases import MouseButton  # noqa: E402
from matplotlib.colors import to_hex, to_rgba  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import nuiitivet.material.matplotlib_figure as figure_mod  # noqa: E402
import nuiitivet.widgets.raster_surface as raster_mod  # noqa: E402
from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_RIGHT, MOD_CTRL, MOD_META, MOD_SHIFT  # noqa: E402
from nuiitivet.input.pointer import PointerEvent, PointerEventType  # noqa: E402
from nuiitivet.material.matplotlib_figure import MatplotlibFigure, _mpl_key  # noqa: E402
from nuiitivet.material.theme.color_role import ColorRole  # noqa: E402
from nuiitivet.material.theme.material_theme import MaterialThemeFactory  # noqa: E402
from nuiitivet.observable import Observable  # noqa: E402
from nuiitivet.theme.theme import Theme  # noqa: E402
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks  # noqa: E402
from nuiitivet.widgets.interaction import FocusNode  # noqa: E402

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


# --- Events ------------------------------------------------------------------


def _pixel_axes(figure: Figure, width_px: int, height_px: int):
    """Axes filling the figure whose data coordinates are its pixels."""
    ax = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, width_px)
    ax.set_ylim(0, height_px)
    return ax


def _shown(widget: MatplotlibFigure, width: int = 160, height: int = 100) -> None:
    """Laid out at the window's origin and drawn, so pointer events have a rect to land in."""
    widget.set_layout_rect(0, 0, width, height)
    _rendered(widget, width, height)


def _pointer(kind: PointerEventType, x: float, y: float, **fields: object) -> PointerEvent:
    return PointerEvent.mouse_event(1, kind, x, y, **fields)  # type: ignore[arg-type]


def test_the_pointer_reaches_the_figure_in_its_pixels_and_data_coordinates(theme: list[Theme]) -> None:
    figure = Figure()
    ax = _pixel_axes(figure, 280, 160)
    seen: list[tuple] = []

    def on_press(e: Any) -> None:
        seen.append((e.name, e.x, e.y, e.xdata, e.ydata, e.button, e.inaxes))

    def on_move(e: Any) -> None:
        seen.append((e.name, e.x, e.buttons))

    def on_release(e: Any) -> None:
        seen.append((e.name, e.button))

    figure.canvas.mpl_connect("button_press_event", on_press)
    figure.canvas.mpl_connect("motion_notify_event", on_move)
    figure.canvas.mpl_connect("button_release_event", on_release)
    # 160x100 with a padding of 10 at a 2x ratio: a 280x160 figure.
    widget = MatplotlibFigure(figure, width=160, height=100, padding=10)
    _shown(widget)
    assert widget.hit_test(5, 5) is widget

    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 50, 30, button=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.MOVE, 60, 30, buttons=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.RELEASE, 60, 30, button=BUTTON_LEFT))

    # x counts from the figure's left edge, y from its bottom edge, both in device pixels.
    name, x, y, xdata, ydata, button, inaxes = seen[0]
    assert (name, x, y, button, inaxes) == ("button_press_event", 80, 120, MouseButton.LEFT, ax)
    assert (xdata, ydata) == (pytest.approx(80.0, abs=0.5), pytest.approx(120.0, abs=0.5))
    assert seen[1] == ("motion_notify_event", 100, frozenset({MouseButton.LEFT}))
    assert seen[2] == ("button_release_event", MouseButton.LEFT)
    assert widget.state.focused


def test_a_picker_artist_fires_pick_event_on_a_press(theme: list[Theme]) -> None:
    figure = Figure()
    ax = _pixel_axes(figure, 320, 200)
    (bar,) = ax.bar([100], [150], width=40, picker=True)
    picked: list[object] = []
    figure.canvas.mpl_connect("pick_event", lambda e: picked.append(e.artist))
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)

    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 50, 60, button=BUTTON_RIGHT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 50, 10, button=BUTTON_RIGHT))

    # The first press lands on the bar (pixel 100, 80), the second above it (100, 180).
    assert picked == [bar]


def test_the_wheel_is_a_scroll_event_with_matplotlib_s_direction(theme: list[Theme]) -> None:
    figure = Figure()
    _pixel_axes(figure, 320, 200)
    seen: list[tuple] = []
    figure.canvas.mpl_connect("scroll_event", lambda e: seen.append((e.button, e.step)))
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)

    # A wheel step toward the user is positive for the framework and "down" for matplotlib.
    consumed = widget.dispatch_pointer_event(PointerEvent.scroll_event(1, 50, 50, 0.0, 1.0))
    widget.dispatch_pointer_event(PointerEvent.scroll_event(1, 50, 50, 0.0, -2.0))

    assert consumed
    assert seen == [("down", -1.0), ("up", 2.0)]


def test_enter_and_leave_reach_the_figure(theme: list[Theme]) -> None:
    figure = Figure()
    _pixel_axes(figure, 320, 200)
    seen: list[str] = []
    figure.canvas.mpl_connect("figure_enter_event", lambda e: seen.append(e.name))
    figure.canvas.mpl_connect("figure_leave_event", lambda e: seen.append(e.name))
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)

    widget.dispatch_pointer_event(_pointer(PointerEventType.ENTER, 50, 50))
    widget.dispatch_pointer_event(_pointer(PointerEventType.LEAVE, 500, 50))

    assert seen == ["figure_enter_event", "figure_leave_event"]


def test_a_key_reaches_the_figure_at_the_pointer_and_goes_on_to_the_app(theme: list[Theme]) -> None:
    figure = Figure()
    _pixel_axes(figure, 320, 200)
    seen: list[tuple] = []

    def on_key(e: Any) -> None:
        seen.append((e.name, e.key, e.x, e.y))

    figure.canvas.mpl_connect("key_press_event", on_key)
    figure.canvas.mpl_connect("key_release_event", lambda e: seen.append((e.name, e.key)))
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)
    widget.dispatch_pointer_event(_pointer(PointerEventType.HOVER, 50, 30))
    node = widget.get_node(FocusNode)
    assert isinstance(node, FocusNode)

    consumed = node.handle_key_event("a", MOD_SHIFT)
    node.handle_key_release_event("a", MOD_SHIFT)

    assert seen == [("key_press_event", "A", 100, 140), ("key_release_event", "A")]
    assert not consumed


@pytest.mark.parametrize(
    ("key", "modifier_keys", "expected"),
    [
        ("a", 0, "a"),
        ("a", MOD_CTRL, "ctrl+a"),
        ("a", MOD_CTRL | MOD_SHIFT | MOD_META, "ctrl+super+A"),
        ("lshift", MOD_SHIFT, "shift"),
        ("control", MOD_CTRL, "control"),
        ("space", 0, " "),
        ("_1", MOD_SHIFT, "shift+1"),
        ("minus", 0, "-"),
        ("escape", 0, "escape"),
        ("left", 0, "left"),
    ],
)
def test_key_names_are_spelled_as_matplotlib_spells_them(key: str, modifier_keys: int, expected: str) -> None:
    assert _mpl_key(key, modifier_keys) == expected


def test_draw_idle_draws_once_on_the_next_frame_and_not_from_inside_a_draw(theme: list[Theme]) -> None:
    figure = Figure()
    figure.subplots().plot([0, 1], [0, 1])
    draws: list[str] = []

    def on_draw(event: object) -> None:
        draws.append("draw")
        figure.canvas.draw_idle()  # a handler asking again from inside the draw

    figure.canvas.mpl_connect("draw_event", on_draw)
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)
    assert draws == ["draw"]

    figure.canvas.draw_idle()
    figure.canvas.draw_idle()
    assert draws == ["draw"]
    flush_size_change_callbacks()
    assert draws == ["draw", "draw"]

    flush_size_change_callbacks()
    assert draws == ["draw", "draw"]


def test_a_raising_handler_is_logged_and_the_widget_goes_on(
    theme: list[Theme], caplog: pytest.LogCaptureFixture
) -> None:
    figure = Figure()
    _pixel_axes(figure, 320, 200)

    def boom(event: object) -> None:
        raise RuntimeError("handler")

    figure.canvas.mpl_connect("button_press_event", boom)
    widget = MatplotlibFigure(figure, width=160, height=100)
    _shown(widget)

    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 50, 50, button=BUTTON_LEFT))

    assert "matplotlib event handler raised" in caplog.text
