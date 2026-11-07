"""The MatplotlibController pans, zooms and keeps the view history of a figure from the app's buttons.

The MatplotlibFigure showing the figure paints the zoom rectangle; a later widget of the figure takes over.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

import pytest

matplotlib = pytest.importorskip("matplotlib", reason="the matplotlib extra is not installed")

from matplotlib.figure import Figure  # noqa: E402

import nuiitivet.matplotlib.figure as figure_mod  # noqa: E402
import nuiitivet.widgets.raster_surface as raster_mod  # noqa: E402
from nuiitivet.input.codes import BUTTON_LEFT  # noqa: E402
from nuiitivet.input.pointer import PointerEvent, PointerEventType  # noqa: E402
from nuiitivet.matplotlib.controller import MatplotlibController  # noqa: E402
from nuiitivet.matplotlib.figure import MatplotlibFigure  # noqa: E402
from nuiitivet.material.theme.material_theme import MaterialThemeFactory  # noqa: E402
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks  # noqa: E402

LIGHT, _DARK = MaterialThemeFactory.from_seed_pair("#6750A4")


@pytest.fixture(autouse=True)
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fixed theme, a 2x display and no Skia image, so the figure draws without a window."""
    monkeypatch.setattr(figure_mod, "Theme", SimpleNamespace(of=lambda _context: LIGHT))
    monkeypatch.setattr(figure_mod, "theme_generation", lambda _context: 0)
    monkeypatch.setattr(raster_mod, "make_raster_image", lambda pixels, w, h: (w, h))
    monkeypatch.setattr(raster_mod, "find_window", lambda _widget: SimpleNamespace(pixel_ratio=2.0))


def _shown(figure: Figure) -> MatplotlibFigure:
    """A 160x100 widget at the window's origin, drawn; its figure is 320x200 pixels."""
    widget = MatplotlibFigure(figure, width=160, height=100)
    widget.set_layout_rect(0, 0, 160, 100)
    widget.layout(160, 100)
    flush_size_change_callbacks()
    return widget


def _pixel_figure() -> tuple[Figure, Any]:
    """A figure whose one axes fills it, with data coordinates equal to its 320x200 pixels."""
    figure = Figure()
    ax = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, 320)
    ax.set_ylim(0, 200)
    return figure, ax


def _pointer(kind: PointerEventType, x: float, y: float, **fields: object) -> PointerEvent:
    return PointerEvent.mouse_event(1, kind, x, y, **fields)  # type: ignore[arg-type]


def _drag(widget: MatplotlibFigure, start: tuple[float, float], end: tuple[float, float]) -> None:
    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, *start, button=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.MOVE, *end, buttons=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.RELEASE, *end, button=BUTTON_LEFT))


def _limits(ax: Any) -> Any:
    """``(x0, x1, y0, y1)`` to half a pixel: the figure is drawn half a pixel larger than its size."""
    return pytest.approx((*ax.get_xlim(), *ax.get_ylim()), abs=0.5)


def test_pan_drags_the_view_and_the_history_buttons_follow() -> None:
    figure, ax = _pixel_figure()
    controller = MatplotlibController(figure)
    widget = _shown(figure)
    assert (controller.can_back.value, controller.can_forward.value) == (False, False)

    controller.pan()
    assert controller.panning.value is True
    _drag(widget, (50, 50), (70, 50))  # 20 logical pixels to the right: 40 figure pixels

    assert _limits(ax) == (-40.0, 280.0, 0.0, 200.0)
    assert (controller.can_back.value, controller.can_forward.value) == (True, False)

    controller.back()
    assert _limits(ax) == (0.0, 320.0, 0.0, 200.0)
    assert (controller.can_back.value, controller.can_forward.value) == (False, True)

    controller.forward()
    assert _limits(ax) == (-40.0, 280.0, 0.0, 200.0)

    controller.home()
    assert _limits(ax) == (0.0, 320.0, 0.0, 200.0)


def test_the_zoom_rectangle_shows_on_the_widget_and_zooms_in_on_release() -> None:
    figure, ax = _pixel_figure()
    controller = MatplotlibController(figure)
    widget = _shown(figure)

    controller.zoom()
    assert controller.zooming.value is True
    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 20, 20, button=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.MOVE, 60, 60, buttons=BUTTON_LEFT))

    assert widget._rubberband == (40.0, 160.0, 120.0, 80.0)  # figure pixels, from the bottom-left

    widget.dispatch_pointer_event(_pointer(PointerEventType.RELEASE, 60, 60, button=BUTTON_LEFT))

    assert widget._rubberband is None
    assert _limits(ax) == (40.0, 120.0, 80.0, 160.0)
    assert controller.can_back.value is True


def test_the_rubberband_is_painted_over_the_raster_in_logical_pixels(monkeypatch: pytest.MonkeyPatch) -> None:
    figure, _ax = _pixel_figure()
    widget = _shown(figure)
    monkeypatch.setattr(figure_mod, "make_rect", lambda *bounds: bounds)
    monkeypatch.setattr(figure_mod, "make_paint", lambda **paint: paint)
    drawn: list[tuple[Any, Any]] = []
    canvas = SimpleNamespace(drawImageRect=lambda *a: None, drawRect=lambda rect, paint: drawn.append((rect, paint)))

    widget.paint(canvas, 0, 0, 160, 100)
    assert drawn == []

    widget._set_rubberband((40.0, 160.0, 120.0, 80.0))
    widget.paint(canvas, 0, 0, 160, 100)

    # (40, 160)-(120, 80) figure pixels from the bottom-left is a 40x40 logical square at (20, 20).
    assert len(drawn) == 2
    for rect, _paint in drawn:
        assert rect == pytest.approx((20.0, 20.0, 40.0, 40.0), abs=0.5)
    assert [paint["style"] for _rect, paint in drawn] == ["fill", "stroke"]
    assert drawn[0][1]["color"][3] < 255 and drawn[1][1]["color"][3] == 255


def test_the_wheel_zooms_around_the_pointer_once_the_figure_has_a_controller() -> None:
    figure, ax = _pixel_figure()
    widget = _shown(figure)

    widget.dispatch_pointer_event(PointerEvent.scroll_event(1, 80, 50, 0.0, -1.0))
    assert _limits(ax) == (0.0, 320.0, 0.0, 200.0)  # no controller: the wheel is the figure's

    controller = MatplotlibController(figure)  # made after the widget, found all the same
    widget.dispatch_pointer_event(PointerEvent.scroll_event(1, 80, 50, 0.0, -1.0))  # wheel away: zoom in

    # One step is 1.25x around (160, 100), the point under the pointer.
    assert _limits(ax) == (32.0, 288.0, 20.0, 180.0)
    assert controller.can_back.value is True

    widget.dispatch_pointer_event(PointerEvent.scroll_event(1, 80, 50, 0.0, 1.0))  # wheel toward: zoom out
    assert _limits(ax) == (0.0, 320.0, 0.0, 200.0)

    controller.zoom()  # the later controller serves the widget: the rectangle shows on it
    widget.dispatch_pointer_event(_pointer(PointerEventType.PRESS, 20, 20, button=BUTTON_LEFT))
    widget.dispatch_pointer_event(_pointer(PointerEventType.MOVE, 60, 60, buttons=BUTTON_LEFT))
    assert widget._rubberband == (40.0, 160.0, 120.0, 80.0)


def test_zoom_turns_pan_off_and_a_tool_keeps_the_pick_quiet() -> None:
    figure, ax = _pixel_figure()
    bar = ax.bar([160], [200], width=100, picker=True)[0]
    picked: list[Any] = []
    figure.canvas.mpl_connect("pick_event", lambda e: picked.append(e.artist))
    controller = MatplotlibController(figure)
    widget = _shown(figure)

    controller.pan()
    controller.zoom()
    assert (controller.panning.value, controller.zooming.value) == (False, True)

    _drag(widget, (80, 50), (80, 50))
    assert picked == []

    controller.zoom()
    assert (controller.panning.value, controller.zooming.value) == (False, False)
    _drag(widget, (80, 50), (80, 50))
    assert picked == [bar]


def test_the_switches_written_from_outside_turn_the_tools_on_and_off() -> None:
    figure, _ax = _pixel_figure()
    controller = MatplotlibController(figure)

    controller.panning.value = True  # a toggle button bound to it, or a restored state
    assert controller.mode == "pan/zoom"

    controller.zooming.value = True
    assert controller.mode == "zoom rect"
    assert controller.panning.value is False

    controller.zooming.value = False
    assert controller.mode == ""


def test_the_message_is_the_pointer_s_data_coordinates() -> None:
    figure, _ax = _pixel_figure()
    controller = MatplotlibController(figure)
    widget = _shown(figure)

    widget.dispatch_pointer_event(_pointer(PointerEventType.MOVE, 80, 50))

    # matplotlib's format_coord, e.g. "(x, y) = (159.8, 99.8)": the pointer at (160, 100) of the pixel axes.
    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", controller.message.value)]
    assert numbers == pytest.approx([160.0, 100.0], abs=0.5)


def test_a_figure_has_one_controller_kept_by_a_later_widget() -> None:
    figure, ax = _pixel_figure()
    controller = MatplotlibController(figure)
    with pytest.raises(ValueError):
        MatplotlibController(figure)
    _shown(figure)
    controller.pan()

    second = _shown(figure)  # as a rebuild makes one
    assert controller.canvas is figure.canvas
    assert controller.panning.value is True

    _drag(second, (50, 50), (70, 50))
    assert _limits(ax) == (-40.0, 280.0, 0.0, 200.0)

    controller.pan()
    second.dispatch_pointer_event(PointerEvent.scroll_event(1, 80, 50, 0.0, -1.0))
    assert _limits(ax) == (-8.0, 248.0, 20.0, 180.0)  # one 1.25x step around (160, 100), not two
