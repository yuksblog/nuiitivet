"""Layout tests for NavigationRail widget."""

from contextlib import contextmanager
from typing import Callable, Generator

from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import runtime as observable_runtime


# ---------------------------------------------------------------------------
# Fake clock helper (same pattern as test_animatable_vector_driven.py)
# ---------------------------------------------------------------------------


class _FakeClock:
    """Deterministic clock that drives animation ticks manually."""

    def __init__(self) -> None:
        self._interval_callbacks: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        del fn, delay

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        del interval
        if fn not in self._interval_callbacks:
            self._interval_callbacks.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._interval_callbacks = [cb for cb in self._interval_callbacks if cb is not fn]

    def advance(self, dt: float) -> None:
        for cb in list(self._interval_callbacks):
            cb(dt)

    def advance_frames(self, count: int, fps: float = 60.0) -> None:
        """Step *count* frames at *fps*."""
        dt = 1.0 / fps
        for _ in range(count):
            self.advance(dt)


@contextmanager
def _fake_clock() -> Generator[_FakeClock, None, None]:
    prev = observable_runtime.clock
    fake = _FakeClock()
    observable_runtime.set_clock(fake)
    try:
        yield fake
    finally:
        observable_runtime.set_clock(prev)


def test_navigation_rail_layout_common_metrics():
    """Test common layout metrics for NavigationRail."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items)
    rail.layout(800, 600)

    # Check common item properties
    item_button = rail._item_buttons[0]
    assert item_button._indicator_rect is not None

    # "Nav rail item active indicator shape md.sys.shape.corner.full"
    # Corner radius should be half of height (16 for 32dp height).
    assert item_button._indicator_radius == 16

    # "Nav rail collapsed container color md.sys.color.surface"
    rail_bg = rail.children[0]
    # Box uses .bgcolor property
    assert rail_bg.bgcolor == ColorRole.SURFACE

    # "Nav rail collapsed container shape md.sys.shape.corner.none"
    assert rail_bg.corner_radius == 0
    assert rail_bg.shadow_blur == 0  # Elevation 0


def test_navigation_rail_layout_collapsed():
    """Test layout metrics specifically for Collapsed state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)
    rail.layout(800, 600)

    # "Nav rail collapsed container width 96dp"
    assert rail._calculate_width() == 96

    item_button = rail._item_buttons[0]
    assert item_button._indicator_rect is not None
    ind_x, _ind_y, _ind_w, ind_h = item_button._indicator_rect

    # "Nav rail item vertical active indicator height 32dp"
    assert ind_h == 32

    # "Nav rail item vertical label text font size 12pt"
    # Vertical label is used in collapsed mode
    label = item_button._vertical_label
    assert label.style.font_size == 12

    # "Nav rail item vertical icon label space 4dp"
    icon = item_button._icon_widget
    label_container = item_button._horizontal_label_container
    assert icon.layout_rect is not None
    assert label_container.layout_rect is not None
    icon_x, _icon_y, icon_w, _icon_h = icon.layout_rect
    label_x, _label_y, _label_w, _label_h = label_container.layout_rect
    assert label_x - (icon_x + icon_w) == 4

    # "Nav rail item vertical leading-space 16dp" check internal padding
    assert icon_x - ind_x == 16


def test_navigation_rail_layout_expanded():
    """Test layout metrics specifically for Expanded state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)
    rail.layout(800, 600)

    # "Nav rail expanded container width minimum 220dp"
    assert rail._calculate_width() == 220

    # "Nav rail expanded container elevation 0"
    rail_bg = rail.children[0]
    assert rail_bg.shadow_blur == 0

    item_button = rail._item_buttons[0]

    # "Nav rail item horizontal label text font size 14pt"
    h_label = item_button._horizontal_label
    assert h_label.style.font_size == 14

    # "Nav rail item horizontal active indicator height 56dp"
    assert item_button._indicator_rect is not None
    ind_x, _ind_y, _ind_w, ind_h = item_button._indicator_rect
    assert ind_h == 56

    # "Nav rail item horizontal icon-label-space 8dp"
    icon = item_button._icon_widget
    label_container = item_button._horizontal_label_container
    assert icon.layout_rect is not None
    assert label_container.layout_rect is not None
    icon_x, _icon_y, icon_w, _icon_h = icon.layout_rect
    label_x, _label_y, _label_w, _label_h = label_container.layout_rect
    assert label_x - (icon_x + icon_w) == 8

    # "Nav rail item horizontal full width leading space 16dp"
    assert icon_x - ind_x == 16


# ---------------------------------------------------------------------------
# Icon / Text position tests
# ---------------------------------------------------------------------------


def _get_item_button(rail):
    """Helper: return the first _RailItemButton after layout."""
    return rail._item_buttons[0]


def test_icon_position_when_collapsed():
    """Icon should be centred within the collapsed indicator (32dp tall)."""
    # margin=(96-56)/2=20, icon_x=20+16=36, icon_y=(32-24)/2=4
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)
    rail.layout(96, 600)

    icon = _get_item_button(rail)._icon_widget
    assert icon.layout_rect is not None
    x, y, w, h = icon.layout_rect
    assert x == 36
    assert y == 4
    assert w == 24
    assert h == 24


def test_icon_position_when_expanded():
    """Icon should be centred vertically within the expanded indicator (56dp tall)."""
    # icon_x=36 (unchanged), icon_y=(56-24)/2=16
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)
    rail.layout(220, 600)

    icon = _get_item_button(rail)._icon_widget
    assert icon.layout_rect is not None
    x, y, w, h = icon.layout_rect
    assert x == 36
    assert y == 16
    assert w == 24
    assert h == 24


def test_horizontal_label_hidden_when_collapsed():
    """Horizontal label window width must be 0 (fully hidden) in collapsed state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)
    rail.layout(96, 600)

    label_container = _get_item_button(rail)._horizontal_label_container
    assert label_container.layout_rect is not None
    _x, _y, w, _h = label_container.layout_rect
    assert w == 0


def test_horizontal_label_position_when_expanded():
    """Horizontal label window should be fully visible and correctly placed
    when expanded.

    Expected: x=icon_x+icon_size+label_gap_expanded=36+24+8=68,
              y=(56-20)/2=18, w=110, h=20.
    """
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)
    rail.layout(220, 600)

    label_container = _get_item_button(rail)._horizontal_label_container
    assert label_container.layout_rect is not None
    x, y, w, h = label_container.layout_rect
    assert x == 68
    assert y == 18
    assert w == 110
    assert h == 20


def test_vertical_label_position_when_collapsed():
    """Vertical label should be visible just below the collapsed indicator.

    Expected: x=0, y=indicator_height+gap_collapsed=32+4=36, w=96, h=20.
    """
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)
    rail.layout(96, 600)

    v_label_container = _get_item_button(rail)._vertical_label_container
    assert v_label_container.layout_rect is not None
    x, y, w, h = v_label_container.layout_rect
    assert x == 0
    assert y == 36
    assert w == 96
    assert h == 20


def test_vertical_label_hidden_when_expanded():
    """Vertical label height must be 0 (fully hidden) in expanded state."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)
    rail.layout(220, 600)

    v_label_container = _get_item_button(rail)._vertical_label_container
    assert v_label_container.layout_rect is not None
    _x, _y, _w, h = v_label_container.layout_rect
    assert h == 0


# ---------------------------------------------------------------------------
# Container width tests
# ---------------------------------------------------------------------------


def test_container_width_sizing_collapsed():
    """Rail width_sizing should resolve to 96dp when collapsed."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=False)

    # width_sizing is driven by the animation map; at t=0 it produces Sizing.fixed(96).
    assert rail.width_sizing.kind == "fixed"
    assert rail.width_sizing.value == 96


def test_container_width_sizing_expanded():
    """Rail width_sizing should resolve to 220dp when expanded."""
    items = [RailItem(icon="home", label="Home")]
    rail = NavigationRail(children=items, expanded=True)

    # width_sizing is driven by the animation map; at t=1 it produces Sizing.fixed(220).
    assert rail.width_sizing.kind == "fixed"
    assert rail.width_sizing.value == 220


# ---------------------------------------------------------------------------
# Animation transition tests
# ---------------------------------------------------------------------------
# EXPRESSIVE_DEFAULT_SPATIAL duration = 0.50s
# EXPRESSIVE_DEFAULT_EFFECTS duration  = 0.20s
# Advancing 90 frames @ 60fps = 1.5s → both animations fully settled.
_SETTLE_FRAMES = 90


def test_animation_transition_collapsed_to_expanded_icon_position():
    """After collapsed→expanded animation completes, icon must be at expanded position."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=False)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(220, 600)
    icon = rail._item_buttons[0]._icon_widget
    assert icon.layout_rect is not None
    x, y, w, h = icon.layout_rect
    assert x == 36
    assert y == 16  # (56-24)//2 == 16


def test_animation_transition_collapsed_to_expanded_horizontal_label():
    """After collapsed→expanded animation, horizontal label must be fully visible."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=False)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(220, 600)
    label_container = rail._item_buttons[0]._horizontal_label_container
    assert label_container.layout_rect is not None
    x, y, w, h = label_container.layout_rect
    assert x == 68  # icon_x(36) + icon_size(24) + label_gap_expanded(8)
    assert y == 18  # (56-20)//2 == 18
    assert w == 110
    assert h == 20


def test_animation_transition_collapsed_to_expanded_vertical_label_hidden():
    """After collapsed→expanded animation, vertical label height must be 0."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=False)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(220, 600)
    v_container = rail._item_buttons[0]._vertical_label_container
    assert v_container.layout_rect is not None
    _x, _y, _w, h = v_container.layout_rect
    assert h == 0


def test_animation_transition_collapsed_to_expanded_container_width():
    """After collapsed→expanded animation, width_sizing must be 220dp."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=False)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    assert rail.width_sizing.kind == "fixed"
    assert rail.width_sizing.value == 220


def test_animation_transition_expanded_to_collapsed_icon_position():
    """After expanded→collapsed animation completes, icon must be at collapsed position."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=True)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(96, 600)
    icon = rail._item_buttons[0]._icon_widget
    assert icon.layout_rect is not None
    x, y, w, h = icon.layout_rect
    assert x == 36
    assert y == 4  # (32-24)//2 == 4


def test_animation_transition_expanded_to_collapsed_vertical_label():
    """After expanded→collapsed animation, vertical label must be visible at correct position."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=True)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(96, 600)
    v_container = rail._item_buttons[0]._vertical_label_container
    assert v_container.layout_rect is not None
    x, y, w, h = v_container.layout_rect
    assert x == 0
    assert y == 36  # indicator_height_collapsed(32) + gap_collapsed(4)
    assert w == 96
    assert h == 20


def test_animation_transition_expanded_to_collapsed_horizontal_label_hidden():
    """After expanded→collapsed animation, horizontal label width must be 0."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=True)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    rail.layout(96, 600)
    label_container = rail._item_buttons[0]._horizontal_label_container
    assert label_container.layout_rect is not None
    _x, _y, w, _h = label_container.layout_rect
    assert w == 0


def test_animation_transition_expanded_to_collapsed_container_width():
    """After expanded→collapsed animation, width_sizing must be 96dp."""
    items = [RailItem(icon="home", label="Home")]
    with _fake_clock() as clock:
        rail = NavigationRail(children=items, expanded=True)
        rail._toggle_expanded()
        clock.advance_frames(_SETTLE_FRAMES)

    assert rail.width_sizing.kind == "fixed"
    assert rail.width_sizing.value == 96
