"""A Material button animates every style change it shows.

Selecting a toggle, switching the theme and pressing the container all move
through an ``Animatable``: colours cross-fade, the corner radius morphs. The
harness clock holds the tickers, so each test steps them by hand and reads the
value in flight. The first theme resolve is the one exception: the preset the
constructor used was never shown, so it snaps.

A button resolves its theme where it is measured, so every test mounts it in
a ``Row``: a root is laid out at the host's size and never measured.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import Button, IconToggleButton, ToggleButton
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle, IconToggleButtonStyle
from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.theme import Theme

_WHITE = (255, 255, 255, 255)
_DARK = (16, 16, 16, 255)
_GREY = (240, 240, 240, 255)


def _theme(overrides: dict[ColorRole, str] | None = None) -> Theme:
    roles = {role: "#FFFFFF" for role in ColorRole}
    roles.update(overrides or {})
    return Theme(mode="light", extensions=[MaterialThemeData(roles=roles)])


def _tick(clock, dt: float) -> None:
    """Advance every running animation by ``dt`` seconds."""
    for pending in clock.pending():
        if pending.is_interval:
            pending.fn(dt)


def _running(clock) -> bool:
    return any(pending.is_interval for pending in clock.pending())


def _paint(widget) -> None:
    widget.paint(MagicMock(), 0, 0, 200, 48)


def _between(value: float, a: float, b: float) -> bool:
    return min(a, b) < value < max(a, b)


def _rgba(widget) -> tuple[int, int, int, int]:
    """The container colour, once the theme has resolved it to RGBA."""
    color = widget.bgcolor
    assert isinstance(color, tuple)
    return color


def _radius(widget) -> float:
    """The container corner radius; every style here is a scalar."""
    radius = widget.corner_radius
    assert isinstance(radius, (int, float))
    return float(radius)


# --- Colour ------------------------------------------------------------------


def test_first_resolve_snaps_to_the_theme_colour(nuiitivet_mount, nuiitivet_clock) -> None:
    button = Button("a", style=ButtonStyle.filled())
    host = nuiitivet_mount(Row(children=[button]), theme=_theme({ColorRole.PRIMARY: "#101010"}))
    host.layout(200, 48)

    assert button.bgcolor == _DARK
    assert not _running(nuiitivet_clock)


def test_toggle_click_cross_fades_the_colours(nuiitivet_app, nuiitivet_clock) -> None:
    button = ToggleButton("a", style=ToggleButtonStyle.filled(), key="t")
    app = nuiitivet_app(
        Row(children=[button]),
        size=(300, 100),
        theme=_theme({ColorRole.PRIMARY: "#101010", ColorRole.SURFACE_CONTAINER_HIGHEST: "#F0F0F0"}),
    )
    assert button.bgcolor == _GREY

    app.click(key="t")
    assert button.selected is True
    assert button.bgcolor == _GREY

    _tick(nuiitivet_clock, 0.05)
    assert _between(_rgba(button)[0], _GREY[0], _DARK[0])

    _tick(nuiitivet_clock, 1.0)
    assert button.bgcolor == _DARK


def test_theme_switch_cross_fades_the_colours(nuiitivet_mount, nuiitivet_clock) -> None:
    button = Button("a", style=ButtonStyle.filled())
    host = nuiitivet_mount(Row(children=[button]), theme=_theme())
    host.layout(200, 48)
    assert button.bgcolor == _WHITE

    host.push_theme(_theme({ColorRole.PRIMARY: "#101010"}))
    host.layout(200, 48)
    assert button.bgcolor == _WHITE

    _tick(nuiitivet_clock, 0.05)
    assert _between(_rgba(button)[0], _WHITE[0], _DARK[0])

    _tick(nuiitivet_clock, 1.0)
    assert button.bgcolor == _DARK


# --- Shape -------------------------------------------------------------------


def test_press_morphs_the_corner_and_release_restores_it(nuiitivet_mount, nuiitivet_clock) -> None:
    button = Button("a", style=ButtonStyle.filled("s"))
    host = nuiitivet_mount(Row(children=[button]), theme=_theme())
    host.layout(200, 48)
    assert button.corner_radius == 20

    button.state.pressed = True
    _paint(button)
    _tick(nuiitivet_clock, 0.02)
    assert _between(_radius(button), 20, 8)

    _tick(nuiitivet_clock, 2.0)
    assert _radius(button) == pytest.approx(8, abs=0.5)

    button.state.pressed = False
    _paint(button)
    _tick(nuiitivet_clock, 2.0)
    assert _radius(button) == pytest.approx(20, abs=0.5)


def test_toggle_select_morphs_round_to_square(nuiitivet_app, nuiitivet_clock) -> None:
    button = ToggleButton("a", style=ToggleButtonStyle.filled("s"), key="t")
    app = nuiitivet_app(Row(children=[button]), size=(300, 100), theme=_theme())
    assert button.corner_radius == 20

    app.click(key="t")
    _paint(button)
    _tick(nuiitivet_clock, 0.02)
    assert _between(_radius(button), 20, 12)

    _tick(nuiitivet_clock, 2.0)
    assert _radius(button) == pytest.approx(12, abs=0.5)

    app.click(key="t")
    _paint(button)
    _tick(nuiitivet_clock, 2.0)
    assert _radius(button) == pytest.approx(20, abs=0.5)


def test_icon_toggle_select_morphs_round_to_square(nuiitivet_app, nuiitivet_clock) -> None:
    button = IconToggleButton("star", style=IconToggleButtonStyle.filled("m"), key="t")
    app = nuiitivet_app(Row(children=[button]), size=(300, 100), theme=_theme())
    assert button.corner_radius == 28

    app.click(key="t")
    _paint(button)
    _tick(nuiitivet_clock, 2.0)
    assert _radius(button) == pytest.approx(16, abs=0.5)


def test_disabled_button_keeps_its_resting_shape(nuiitivet_mount, nuiitivet_clock) -> None:
    button = Button("a", style=ButtonStyle.filled("s"), disabled=True)
    host = nuiitivet_mount(Row(children=[button]), theme=_theme())
    host.layout(200, 48)

    button.state.pressed = True
    _paint(button)
    assert not _running(nuiitivet_clock)
    assert button.corner_radius == 20


# --- Presets carry the shape tokens -------------------------------------------

_BUTTON_FACTORIES = (
    ButtonStyle.filled,
    ButtonStyle.outlined,
    ButtonStyle.text,
    ButtonStyle.elevated,
    ButtonStyle.tonal,
)
_ICON_FACTORIES = (
    IconButtonStyle.standard,
    IconButtonStyle.filled,
    IconButtonStyle.outlined,
    IconButtonStyle.tonal,
)


@pytest.mark.parametrize(
    "size,square,pressed",
    [("xs", 12, 8), ("s", 12, 8), ("m", 16, 12), ("l", 28, 16), ("xl", 28, 16)],
)
def test_button_presets_carry_the_pressed_shape(size, square, pressed) -> None:
    for factory in _BUTTON_FACTORIES:
        assert factory(size).pressed_corner_radius == pressed
    for factory in _ICON_FACTORIES:
        assert factory(size).pressed_corner_radius == pressed

    toggle = ToggleButtonStyle.filled(size)
    assert toggle.selected_corner_radius == square
    assert toggle.pressed_corner_radius == pressed
    assert toggle.for_selected(False).corner_radius == toggle.corner_radius
    assert toggle.for_selected(True).corner_radius == square

    icon_toggle = IconToggleButtonStyle.filled(size)
    assert icon_toggle.unselected.corner_radius == IconButtonStyle.filled(size).corner_radius
    assert icon_toggle.selected.corner_radius == square
    assert icon_toggle.selected.pressed_corner_radius == pressed
