"""Each widget declared safe to replay is replayed in a scroll row, and shows a change on the next frame."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, NamedTuple, Tuple
from unittest.mock import patch

import pytest
import skia

from nuiitivet.animation import LinearMotion
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern
from nuiitivet.layout import layout_utils
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.spacer import Spacer
from nuiitivet.material.badge import LargeBadge, SmallBadge
from nuiitivet.material.divider import HorizontalDivider, VerticalDivider
from nuiitivet.material.icon import Icon
from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.progress_indicators import (
    CircularProgressIndicator,
    IndeterminateCircularProgressIndicator,
    IndeterminateLinearProgressIndicator,
    LinearProgressIndicator,
)
from nuiitivet.material.selection_controls import RadioButton, RadioGroup
from nuiitivet.material.text import Text
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.modifiers.context_menu import context_menu
from nuiitivet.modifiers.stick import stick
from nuiitivet.modifiers.tooltip import tooltip
from nuiitivet.modifiers.transform import opacity, rotate
from nuiitivet.modifiers.visible import visible
from nuiitivet.modifiers.will_pop import will_pop
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.image import Image
from nuiitivet.widgets.text_field import TextFieldBase

WIDTH = 300
HEIGHT = 200


class _Case(NamedTuple):
    """A widget for one row, and the changes to what it draws."""

    widget: Widget
    changes: Tuple[Callable[[], None], ...] = ()


def _png(color: int) -> bytes:
    surface_type: Any = skia.Surface  # the local stub declares no constructor
    surface = surface_type(16, 16)
    surface.getCanvas().clear(color)
    return bytes(surface.makeImageSnapshot().encodeToData())


def _set(observable: Any, value: Any) -> Callable[[], None]:
    def change() -> None:
        observable.value = value

    return change


def _radio() -> _Case:
    selected: Observable[object] = Observable(1)
    disabled = Observable(False)
    group = RadioGroup(Row(children=[RadioButton(1), RadioButton(2, disabled=disabled)]), value=selected)
    return _Case(group, (_set(selected, 2), _set(disabled, True)))


def _icon() -> _Case:
    name = Observable("star")
    return _Case(Icon(name), (_set(name, "home"),))


def _grid() -> _Case:
    label = Observable("cell")
    return _Case(Grid([GridItem(Text(label), 0, 0)], rows=["auto"], columns=["auto"]), (_set(label, "changed"),))


def _rotated() -> _Case:
    angle = Observable(10.0)
    return _Case(Text("turned").modifier(rotate(angle)), (_set(angle, 40.0),))


def _transform_without_effect() -> _Case:
    label = Observable("opaque")
    return _Case(Text(label).modifier(opacity(1.0)), (_set(label, "changed"),))


def _visible() -> _Case:
    shown = Observable(True)
    transition = TransitionDefinition(motion=LinearMotion(0.2), pattern=FadePattern())
    return _Case(Text("fades").modifier(visible(shown, transition=transition)), (_set(shown, False),))


def _will_pop() -> _Case:
    label = Observable("guarded")
    return _Case(Text(label).modifier(will_pop(lambda: True)), (_set(label, "changed"),))


def _linear_progress() -> _Case:
    value = Observable(0.2)
    disabled = Observable(False)
    widget = LinearProgressIndicator(value, disabled=disabled, width=200)
    return _Case(widget, (_set(value, 0.8), _set(disabled, True)))


def _circular_progress() -> _Case:
    value = Observable(0.2)
    disabled = Observable(False)
    return _Case(CircularProgressIndicator(value, disabled=disabled), (_set(value, 0.8), _set(disabled, True)))


def _for_each() -> _Case:
    items = Observable(["a", "b"])
    return _Case(ForEach(items, lambda item, _index: Text(str(item))), (_set(items, ["a", "b", "c"]),))


def _image() -> _Case:
    source: Observable[bytes | None] = Observable(_png(0xFFFF0000))
    return _Case(Image(source, width=16, height=16), (_set(source, _png(0xFF0000FF)),))


def _tooltip() -> _Case:
    label = Observable("hover me")
    return _Case(Text(label).modifier(tooltip(Text("tip"))), (_set(label, "changed"),))


def _context_menu() -> _Case:
    label = Observable("right-click me")
    return _Case(Text(label).modifier(context_menu(Text("menu"))), (_set(label, "changed"),))


def _stick() -> _Case:
    label = Observable("inbox")
    return _Case(Text(label).modifier(stick(SmallBadge())), (_set(label, "changed"),))


def _collapsible() -> _Case:
    opened = Observable(True)
    return _Case(Collapsible(Text("folds"), opened=opened), (_set(opened, False),))


def _text_field_base() -> _Case:
    text = Observable("typed")
    return _Case(TextFieldBase(text), (_set(text, "changed"),))


CASES: Dict[str, Callable[[], _Case]] = {
    "radio button": _radio,
    "icon": _icon,
    "grid": _grid,
    "transform": _rotated,
    "transform without an effect": _transform_without_effect,
    "visible": _visible,
    "will_pop": _will_pop,
    "horizontal divider": lambda: _Case(HorizontalDivider(width=200)),
    "vertical divider": lambda: _Case(VerticalDivider(height=24)),
    "small badge": lambda: _Case(SmallBadge()),
    "large badge": lambda: _Case(LargeBadge("3")),
    "linear progress": _linear_progress,
    "circular progress": _circular_progress,
    "indeterminate linear progress": lambda: _Case(IndeterminateLinearProgressIndicator(width=200)),
    "indeterminate circular progress": lambda: _Case(IndeterminateCircularProgressIndicator()),
    "loading indicator": lambda: _Case(LoadingIndicator()),
    "spacer": lambda: _Case(Spacer(width=24, height=24)),
    "for each": _for_each,
    "image": _image,
    "tooltip": _tooltip,
    "context menu": _context_menu,
    "stick": _stick,
    "collapsible": _collapsible,
    "text field base": _text_field_base,
}

# These draw a new frame of their animation on every tick, so their row is never still.
ALWAYS_ANIMATING = {"indeterminate linear progress", "indeterminate circular progress", "loading indicator"}


class _Scene:
    """The cases as the first rows of a scrolled list, painted to a surface."""

    def __init__(self, names: List[str], scale: int = 1) -> None:
        self.cases = [CASES[name]() for name in names]
        # A themed Text beside each widget: a theme change repaints the row whatever the widget draws.
        self.rows = [Row(gap=8, padding=4, children=[case.widget, Text("beside")]) for case in self.cases]
        filler: List[Widget] = [Row(padding=4, children=[Text(f"row {i}")]) for i in range(40)]
        self.controller = ScrollController()
        self.viewport = ScrollViewport(
            child=Column(children=[*self.rows, *filler]),
            controller=self.controller,
            direction=ScrollDirection.VERTICAL,
            width=Sizing.fixed(WIDTH),
            height=Sizing.fixed(HEIGHT),
        )
        surface_type: Any = skia.Surface
        self._surface = surface_type(WIDTH * scale, HEIGHT * scale)
        self._canvas = self._surface.getCanvas()
        self._canvas.scale(scale, scale)

    def frame(self) -> bytes:
        self._canvas.clear(0xFFFFFFFF)
        self.viewport.paint(self._canvas, 0, 0, WIDTH, HEIGHT)
        return bytes(self._surface.makeImageSnapshot().tobytes())

    def scroll(self, host: Any, offset: float) -> None:
        self.controller.scroll_to(offset, axis=ScrollDirection.VERTICAL)
        host.settle()


@pytest.mark.parametrize("name", [name for name in CASES if name not in ALWAYS_ANIMATING])
def test_a_row_holding_the_widget_is_painted_once_and_then_replayed(name) -> None:
    scene = _Scene([name])
    row = scene.rows[0]
    with mount(scene.viewport, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
        host.layout(WIDTH, HEIGHT)
        scene.frame()
        picture = row._replay_picture
        assert picture is not None

        scene.frame()
        assert row._replay_picture is picture

        scene.scroll(host, 3)
        scene.frame()
        assert row._replay_picture is picture


def _frames(names: List[str], replay: bool, scale: int) -> List[bytes]:
    """Return the pixels of a frame after every change to the cases, a theme change and a scroll."""
    out: List[bytes] = []
    # The harness clock reads the wall clock; a time the test owns makes both runs tick alike.
    now = [1000.0]
    with patch("nuiitivet.testing.clock.time.monotonic", lambda: now[0]), patch.object(
        layout_utils, "_ROW_REPLAY", replay
    ):
        scene = _Scene(names, scale)
        with mount(scene.viewport, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
            host.layout(WIDTH, HEIGHT)
            out.append(scene.frame())
            out.append(scene.frame())
            scene.scroll(host, 3)
            out.append(scene.frame())
            for case in scene.cases:
                for change in case.changes:
                    change()
                    # A change may start its animation in the layout pass; then give it time to finish.
                    host.settle()
                    now[0] += 1.0
                    host.clock.pump()
                    host.settle()
                    out.append(scene.frame())
            host.push_theme(MaterialThemeFactory.dark("#6750A4"))
            out.append(scene.frame())
            scene.scroll(host, 9)
            out.append(scene.frame())
    return out


@pytest.mark.parametrize("name", list(CASES))
def test_a_change_to_the_widget_shows_on_the_next_frame(name) -> None:
    direct = _frames([name], False, 1)
    replayed = _frames([name], True, 1)

    assert replayed == direct
    # Every change, the theme change included, drew a frame that differs from the one before it.
    changes = len(CASES[name]().changes) + 1
    after_scroll = direct[2 : 3 + changes]
    assert all(a != b for a, b in zip(after_scroll, after_scroll[1:]))


@pytest.mark.parametrize("scale", [1, 2, 3])
def test_a_list_of_every_declared_widget_replays_to_the_pixels_of_a_direct_paint(scale) -> None:
    names = list(CASES)

    assert _frames(names, True, scale) == _frames(names, False, scale)


def _scrolled(name: str, replay: bool, scale: int) -> List[bytes]:
    with patch.object(layout_utils, "_ROW_REPLAY", replay):
        scene = _Scene([name], scale)
        with mount(scene.viewport, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
            host.layout(WIDTH, HEIGHT)
            out = [scene.frame()]
            for offset in range(1, 40):
                scene.scroll(host, offset)
                out.append(scene.frame())
    return out


@pytest.mark.parametrize("scale", [2, 3])
@pytest.mark.parametrize("name", ["radio button", "circular progress"])
def test_a_widget_of_curves_replays_to_the_same_pixels_at_every_scroll_offset(name, scale) -> None:
    # A stroked curve replayed at another position can differ at these scales, at some positions only.
    assert _scrolled(name, True, scale) == _scrolled(name, False, scale)
