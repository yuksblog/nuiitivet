"""Unit tests for the ExtendedFab widget."""

import pytest

from nuiitivet.material.buttons import ExtendedFab
from nuiitivet.material.icon import Icon
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.layout.row import Row
from nuiitivet.observable import Observable
from nuiitivet.widgets.text import TextBase


def test_label_required():
    """`label` is a required positional argument."""
    with pytest.raises(TypeError):
        ExtendedFab()  # type: ignore[call-arg]


def test_icon_optional_builds_label_only_child():
    """Without an icon the child is the bare label text."""
    fab = ExtendedFab("Compose")
    assert len(fab.children) == 1
    assert isinstance(fab.children[0], TextBase)


def test_icon_builds_leading_icon_and_label_row():
    """With an icon the child is a Row of [icon, label]."""
    fab = ExtendedFab("Compose", icon="edit")
    assert isinstance(fab.children[0], Row)
    row = fab.children[0]
    assert isinstance(row.children[0], Icon)
    assert isinstance(row.children[1], TextBase)


def test_expanded_defaults_to_true():
    fab = ExtendedFab("Compose", icon="edit")
    assert fab.expanded is True


def test_collapsed_preferred_size_is_circle():
    """A collapsed ExtendedFab reports the circular container footprint."""
    fab = ExtendedFab("Compose", icon="edit", expanded=False, style=FabStyle.primary("s"))
    assert fab.preferred_size() == (56, 56)


def test_collapsed_circle_tracks_size_preset():
    """Collapsed footprint follows the size preset (s/m/l)."""
    assert ExtendedFab("X", icon="edit", expanded=False, style=FabStyle.primary("m")).preferred_size() == (80, 80)
    assert ExtendedFab("X", icon="edit", expanded=False, style=FabStyle.primary("l")).preferred_size() == (96, 96)


def test_expanded_is_wider_than_collapsed():
    """The expanded pill is content-driven and wider than the circle."""
    fab = ExtendedFab("Compose", icon="edit", style=FabStyle.primary("s"))
    width, height = fab.preferred_size()
    assert height == 56
    assert width > 56


def test_internal_expanded_setter_retargets_morph():
    """Toggling the `expanded` property retargets the morph animation."""
    fab = ExtendedFab("Compose", icon="edit", expanded=True)
    try:
        assert fab._morph_anim.target == pytest.approx(1.0)
        fab.expanded = False
        assert fab._morph_anim.target == pytest.approx(0.0)
        fab.expanded = True
        assert fab._morph_anim.target == pytest.approx(1.0)
    finally:
        # Stop the global clock interval started by retargeting the morph.
        fab._morph_anim.stop()


def test_observable_expanded_drives_morph():
    """An external observable drives collapse/expand after mount."""
    expanded = Observable(True)
    fab = ExtendedFab("Compose", icon="edit", expanded=expanded)
    fab.on_mount()
    try:
        assert fab._morph_anim.target == pytest.approx(1.0)
        expanded.value = False
        assert fab._morph_anim.target == pytest.approx(0.0)
        expanded.value = True
        assert fab._morph_anim.target == pytest.approx(1.0)
    finally:
        fab._morph_anim.stop()


def test_collapse_then_expand_roundtrips_width():
    """Toggling the observable collapses, then expands the width back."""
    expanded = Observable(True)
    fab = ExtendedFab("Compose", icon="edit", expanded=expanded, style=FabStyle.primary("s"))
    fab.on_mount()
    try:
        expanded_width = fab.preferred_size()[0]
        assert expanded_width > 56

        # Collapse and drive the morph to completion.
        expanded.value = False
        for _ in range(120):
            fab._morph_anim._tick(1 / 60)
        assert fab.preferred_size() == (56, 56)

        # Expand again: the pill width must come back.
        expanded.value = True
        for _ in range(120):
            fab._morph_anim._tick(1 / 60)
        assert fab.preferred_size()[0] == expanded_width
    finally:
        fab._morph_anim.stop()


def test_collapse_is_noop_without_icon():
    """Without an icon, collapsing keeps the pill (no circular footprint)."""
    fab = ExtendedFab("Compose", expanded=False)
    assert fab._effective_expanded() is True
    assert fab._morph_anim.value == pytest.approx(1.0)
    # Preferred width stays content-driven (wider than any circle).
    assert fab.preferred_size()[0] > 56


def test_solid_style_variants_resolve():
    """The six color mappings (tonal + solid) all construct."""
    for style in (
        FabStyle.primary(),
        FabStyle.secondary(),
        FabStyle.tertiary(),
        FabStyle.primary_solid(),
        FabStyle.secondary_solid(),
        FabStyle.tertiary_solid(),
    ):
        fab = ExtendedFab("Compose", icon="edit", style=style)
        assert fab.preferred_size()[1] == 56


def test_disabled_flag_is_applied():
    fab = ExtendedFab("Compose", icon="edit", disabled=True)
    assert fab.disabled is True


def test_click_fires_when_offset_inside_layout():
    """The FAB stays clickable when laid out at a non-zero offset.

    Regression for the clipped-container hit-test: an ExtendedFab nested inside
    a padded Row must route pointer clicks to ``on_click``.
    """
    from nuiitivet.material.app import MaterialApp as App
    from nuiitivet.layout.row import Row
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app_events import dispatch_mouse_press, dispatch_mouse_release

    class _FakeCanvas:
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None

            return _noop

    clicks: list[int] = []
    fab = ExtendedFab("Compose", icon="edit", on_click=lambda: clicks.append(1))
    app = App(content=Container(padding=24, child=Row(children=[fab])), title="t", width=400, height=120)
    app.root.mount(app)
    try:
        app.root.layout(400, 120)
        app.root.clear_needs_layout()
        app.root.paint(_FakeCanvas(), 0, 0, 400, 120)

        rx, ry, rw, rh = fab.last_rect
        assert rx > 0  # actually offset from the origin
        cx, cy = rx + rw // 2, ry + rh // 2
        dispatch_mouse_press(app, cx, cy)
        dispatch_mouse_release(app, cx, cy)
        assert clicks == [1]
    finally:
        app.root.unmount()
