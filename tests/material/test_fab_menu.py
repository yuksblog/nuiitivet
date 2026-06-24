"""Unit tests for the FabMenu / FabMenuItem widgets."""

import pytest

from nuiitivet.material.fab_menu import FabMenu, FabMenuItem
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import Observable, runtime


class _FakeCanvas:
    """A no-op canvas used for headless paint passes in tests."""

    def __getattr__(self, _name):
        def _noop(*args, **kwargs):
            return None

        return _noop


class _FakeClock:
    """Deterministic clock capturing scheduled callbacks for assertions."""

    def __init__(self) -> None:
        self.scheduled: list = []
        self.intervals: list = []

    def schedule_once(self, fn, delay) -> None:
        self.scheduled.append((fn, float(delay)))

    def schedule_interval(self, fn, interval) -> None:
        self.intervals.append((fn, float(interval)))

    def unschedule(self, fn) -> None:
        self.scheduled = [(f, d) for (f, d) in self.scheduled if f is not fn]
        self.intervals = [(f, i) for (f, i) in self.intervals if f is not fn]


def _menu(**kwargs) -> FabMenu:
    items = kwargs.pop("items", None) or [
        FabMenuItem(icon="edit", label="Compose"),
        FabMenuItem(icon="share", label="Share"),
        FabMenuItem(icon="save", label="Save"),
    ]
    return FabMenu("add", items=items, **kwargs)


def _rows(menu: FabMenu) -> list:
    """Return the internal item-row widgets (unwrapping the transform boxes)."""
    return [wrapped.children[0] for wrapped in menu._list._column.children]


# --- Construction ---------------------------------------------------------


def test_items_required_positionally():
    with pytest.raises(TypeError):
        FabMenu("add")  # type: ignore[call-arg]


def test_default_is_open_is_false():
    menu = _menu()
    assert menu.is_open.value is False


def test_internal_observable_created_when_none():
    menu = _menu()
    assert isinstance(menu.is_open, Observable)


def test_external_is_open_is_source_of_truth():
    state = Observable(False)
    menu = _menu(is_open=state)
    assert menu.is_open is state
    state.value = True
    assert menu.is_open.value is True


def test_one_row_per_item():
    menu = _menu(
        items=[
            FabMenuItem(icon="edit", label="A"),
            FabMenuItem(icon="share", label="B"),
        ]
    )
    assert len(_rows(menu)) == 2


def test_preferred_size_matches_fab_footprint():
    """FabMenu occupies only the FAB footprint; the menu lives in the overlay."""
    menu = _menu(style=FabStyle.primary("s"))
    assert menu.preferred_size() == (56, 56)


# --- Open / close state ---------------------------------------------------


def test_toggle_flips_is_open():
    menu = _menu()
    menu._toggle()
    assert menu.is_open.value is True
    menu._toggle()
    assert menu.is_open.value is False


def test_fab_click_toggles_open():
    """Clicking the morphing FAB flips the single source-of-truth observable."""
    from nuiitivet.material.app import MaterialApp as App
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app_events import dispatch_mouse_press, dispatch_mouse_release

    menu = _menu()
    app = App(content=Container(padding=24, child=menu), title="t", width=300, height=300)
    app.root.mount(app)
    try:
        app.root.layout(300, 300)
        app.root.clear_needs_layout()
        app.root.paint(_FakeCanvas(), 0, 0, 300, 300)

        rx, ry, rw, rh = menu._fab.last_rect
        cx, cy = rx + rw // 2, ry + rh // 2
        dispatch_mouse_press(app, cx, cy)
        dispatch_mouse_release(app, cx, cy)
        assert menu.is_open.value is True
    finally:
        app.root.unmount()


def test_item_select_invokes_on_click_and_auto_closes():
    clicks: list = []
    menu = _menu(
        items=[FabMenuItem(icon="edit", label="Compose", on_click=lambda: clicks.append(1))],
    )
    menu.is_open.value = True
    _rows(menu)[0]._handle_click()
    assert clicks == [1]
    assert menu.is_open.value is False


def test_auto_close_false_keeps_menu_open():
    menu = _menu(
        items=[FabMenuItem(icon="edit", label="Compose")],
        auto_close=False,
    )
    menu.is_open.value = True
    _rows(menu)[0]._handle_click()
    assert menu.is_open.value is True


def test_item_without_on_click_does_not_raise():
    menu = _menu(items=[FabMenuItem(icon="edit", label="Compose")])
    menu.is_open.value = True
    _rows(menu)[0]._handle_click()  # should not raise
    assert menu.is_open.value is False


# --- Styling --------------------------------------------------------------


def test_list_items_use_container_color_for_each_family():
    cases = {
        FabStyle.primary(): (ColorRole.PRIMARY_CONTAINER, ColorRole.ON_PRIMARY_CONTAINER),
        FabStyle.secondary_solid(): (ColorRole.SECONDARY_CONTAINER, ColorRole.ON_SECONDARY_CONTAINER),
        FabStyle.tertiary(): (ColorRole.TERTIARY_CONTAINER, ColorRole.ON_TERTIARY_CONTAINER),
    }
    for style, (bg, fg) in cases.items():
        menu = _menu(style=style)
        row_style = _rows(menu)[0].style
        assert row_style.background == bg
        assert row_style.foreground == fg


def test_unsupported_color_family_falls_back_to_primary_with_warning(caplog):
    """An unsupported style background falls back to primary and warns once."""
    import logging

    from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests

    _clear_log_once_keys_for_tests()
    # Surface colours are not a valid FAB-menu family.
    style = FabStyle.primary().copy_with(background=ColorRole.SURFACE)
    with caplog.at_level(logging.WARNING, logger="nuiitivet.material.fab_menu"):
        menu = _menu(style=style)
    assert menu._fab.style.background == ColorRole.PRIMARY
    assert _rows(menu)[0].style.background == ColorRole.PRIMARY_CONTAINER
    assert any("falls back to primary" in r.message for r in caplog.records)


def test_close_button_uses_solid_color_distinct_from_items():
    """The close button (FAB) is solid; items are tonal container -- not equal."""
    cases = {
        FabStyle.primary(): (ColorRole.PRIMARY, ColorRole.ON_PRIMARY),
        FabStyle.secondary(): (ColorRole.SECONDARY, ColorRole.ON_SECONDARY),
        FabStyle.tertiary_solid(): (ColorRole.TERTIARY, ColorRole.ON_TERTIARY),
    }
    for style, (bg, fg) in cases.items():
        menu = _menu(style=style)
        assert menu._fab.style.background == bg
        assert menu._fab.style.foreground == fg
        # The FAB (solid) and the items (container) must differ in colour.
        assert menu._fab.style.background != _rows(menu)[0].style.background


def test_list_item_geometry_follows_md3_tokens():
    menu = _menu()
    row_style = _rows(menu)[0].style
    assert row_style.container_height == 56
    assert row_style.corner_radius == pytest.approx(28.0)
    assert row_style.icon_size == 24
    assert row_style.label_font_size == 16
    assert row_style.padding == (24, 0, 24, 0)


def test_style_variants_resolve():
    for style in (
        FabStyle.primary(),
        FabStyle.secondary(),
        FabStyle.tertiary(),
        FabStyle.primary_solid(),
        FabStyle.secondary_solid(),
        FabStyle.tertiary_solid(),
    ):
        menu = _menu(style=style)
        assert menu.preferred_size()[1] == 56


# --- Shape / size morph ---------------------------------------------------


def test_closed_fab_uses_style_size_and_shape():
    """Closed: the FAB keeps the style's size and rounded-square corner."""
    menu = _menu(style=FabStyle.primary("m"))
    fab = menu._fab
    # MD3 FAB size "m": 80dp container, 20dp corner.
    assert fab._closed_size == pytest.approx(80.0)
    assert fab._closed_corner == pytest.approx(20.0)
    # The opened close button is always size "s": 56dp circle (28dp corner).
    assert fab._open_size == pytest.approx(56.0)
    assert fab._open_corner == pytest.approx(28.0)
    # Progress starts closed.
    assert fab._morph_anim.value == pytest.approx(0.0)
    assert fab.preferred_size() == (80, 80)


def test_open_close_button_is_always_size_s():
    """Opened: the close button shrinks to a 56dp circle for every size."""
    for size, closed in (("s", 56), ("m", 80), ("l", 96)):
        menu = _menu(style=FabStyle.primary(size))
        fab = menu._fab
        assert fab.preferred_size() == (closed, closed)  # closed footprint
        fab._morph_anim.snap_to(1.0)
        assert fab.preferred_size() == (56, 56)  # opened close button
        assert fab._morph_corner_value() == pytest.approx(28.0)
        fab._morph_anim.snap_to(0.0)


def test_morph_retargets_with_open_state():
    menu = _menu(style=FabStyle.primary("m"))
    fab = menu._fab
    try:
        fab._retarget(True)
        assert fab._morph_anim.target == pytest.approx(1.0)
        fab._retarget(False)
        assert fab._morph_anim.target == pytest.approx(0.0)
    finally:
        fab._morph_anim.stop()


def test_footprint_stays_closed_size_regardless_of_open_state():
    """The FabMenu footprint stays the closed size so layout is stable."""
    menu = _menu(style=FabStyle.primary("m"))
    assert menu.preferred_size() == (80, 80)
    menu._fab._morph_anim.snap_to(1.0)
    assert menu.preferred_size() == (80, 80)
    menu._fab._morph_anim.stop()


def test_open_close_button_aligns_top_trailing():
    """Opened, the 56dp close button sits at the footprint's top-trailing corner."""
    menu = _menu(style=FabStyle.primary("m"))
    menu._fab._morph_anim.snap_to(1.0)
    # Footprint is 80x80; the 56dp close button is top-right aligned.
    bx, by, bw, bh = menu._fab_box(80, 80)
    assert (bw, bh) == (56, 56)
    assert (bx, by) == (24, 0)  # 24dp leading/bottom margin grows underneath
    menu._fab._morph_anim.stop()


def test_fab_corner_radius_tracks_shape_morph():
    """The FAB container corner radius follows the shape morph when mounted.

    Mounting matters: the FAB's theme application resets the container corner to
    the static style value, so the morph subscription must be (re)established
    after mount to win.
    """
    from nuiitivet.material.app import MaterialApp as App
    from nuiitivet.layout.container import Container

    menu = _menu(style=FabStyle.primary("s"))
    app = App(content=Container(padding=8, child=menu), title="t", width=200, height=200)
    app.root.mount(app)
    try:
        app.root.layout(200, 200)
        app.root.clear_needs_layout()
        app.root.paint(_FakeCanvas(), 0, 0, 200, 200)
        # Closed: rounded square (16dp).
        assert float(menu._fab.corner_radius) == pytest.approx(16.0, abs=0.5)
        # Open: morph toward the circular close button (28dp).
        menu.is_open.value = True
        for _ in range(240):
            menu._fab._morph_anim._tick(1 / 60)
        assert float(menu._fab.corner_radius) == pytest.approx(28.0, abs=0.5)
    finally:
        menu._fab._morph_anim.stop()
        app.root.unmount()


# --- Staggered reveal -----------------------------------------------------


def test_reveal_schedules_one_per_item_bottom_first():
    """Mounting the list schedules a staggered reveal, nearest-FAB item first."""
    menu = _menu(
        items=[
            FabMenuItem(icon="edit", label="A"),
            FabMenuItem(icon="share", label="B"),
            FabMenuItem(icon="save", label="C"),
        ]
    )
    fake = _FakeClock()
    original = runtime.clock
    runtime.set_clock(fake)
    try:
        menu._list.on_mount()
        delays = [delay for (_fn, delay) in fake.scheduled]
        assert len(delays) == 3
        # Scheduled in item order; the visually-bottom (last) item reveals
        # first (delay 0), so delays decrease across the item order.
        assert delays == sorted(delays, reverse=True)
        assert delays[-1] == pytest.approx(0.0)
        assert min(delays) == pytest.approx(0.0)
    finally:
        runtime.set_clock(original)


def test_reveal_callback_drives_item_to_visible():
    menu = _menu(items=[FabMenuItem(icon="edit", label="A")])
    fake = _FakeClock()
    original = runtime.clock
    runtime.set_clock(fake)
    try:
        menu._list.on_mount()
        anim = menu._list._anims[0]
        assert anim.value == pytest.approx(0.0)
        # Fire the scheduled reveal, then drive the animation to completion.
        for fn, _delay in fake.scheduled:
            fn(0.0)
        for _ in range(240):
            anim._tick(1 / 60)
        assert anim.value == pytest.approx(1.0)
    finally:
        anim.stop()
        runtime.set_clock(original)
