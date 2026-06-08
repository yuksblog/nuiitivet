"""Tests for SplitButton and SplitButtonStyle."""

from __future__ import annotations

from typing import List

import pytest

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.split_button import SplitButton
from nuiitivet.material.styles.split_button_style import SplitButtonStyle, SPLIT_BUTTON_SIZE_TOKENS
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mount(widget) -> None:
    """Simulate mounting a widget and its children."""

    class _FakeApp:
        def invalidate(self) -> None:
            pass

        def request_focus(self, node, source=None) -> None:
            pass

    widget.mount(_FakeApp())


def _click(widget) -> None:
    send_pointer_event_for_test(widget, PointerEventType.PRESS)
    send_pointer_event_for_test(widget, PointerEventType.RELEASE)


# ===========================================================================
# SplitButtonStyle — factory classmethods
# ===========================================================================


class TestSplitButtonStyle:
    def test_filled_default_size(self):
        style = SplitButtonStyle.filled()
        assert style.container_height == SPLIT_BUTTON_SIZE_TOKENS["s"]["container_height"]
        assert style.between_space == 2
        assert style.background is not None

    def test_filled_xs(self):
        style = SplitButtonStyle.filled("xs")
        t = SPLIT_BUTTON_SIZE_TOKENS["xs"]
        assert style.container_height == t["container_height"]
        assert style.outer_corner_radius == t["outer_corner_radius"]
        assert style.inner_corner_radius == t["inner_corner_radius"]

    def test_filled_xl(self):
        style = SplitButtonStyle.filled("xl")
        t = SPLIT_BUTTON_SIZE_TOKENS["xl"]
        assert style.container_height == t["container_height"]
        assert style.trailing_icon_size == t["trailing_icon_size"]

    def test_elevated_has_elevation(self):
        style = SplitButtonStyle.elevated()
        assert style.elevation == 1

    def test_tonal_factory(self):
        style = SplitButtonStyle.tonal()
        assert style.background is not None
        assert style.border_width == 0.0

    def test_outlined_has_border(self):
        style = SplitButtonStyle.outlined()
        assert style.border_color is not None
        assert style.border_width == 1.0

    def test_copy_with(self):
        style = SplitButtonStyle.filled()
        new_style = style.copy_with(label_font_size=20)
        assert new_style.label_font_size == 20
        assert style.label_font_size != 20

    @pytest.mark.parametrize("size", ["xs", "s", "m", "l", "xl"])
    def test_all_sizes_filled(self, size):
        style = SplitButtonStyle.filled(size)
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        assert style.container_height == t["container_height"]
        assert style.between_space == 2

    @pytest.mark.parametrize("size", ["xs", "s", "m", "l", "xl"])
    def test_inner_corner_hovered_ge_idle(self, size):
        style = SplitButtonStyle.filled(size)
        assert style.inner_corner_hovered_radius >= style.inner_corner_radius

    @pytest.mark.parametrize("size", ["xs", "s", "m", "l", "xl"])
    def test_outer_corner_radius_is_half_height(self, size):
        style = SplitButtonStyle.filled(size)
        t = SPLIT_BUTTON_SIZE_TOKENS[size]
        assert style.outer_corner_radius == pytest.approx(t["outer_corner_radius"])


# ===========================================================================
# SplitButton — initialization
# ===========================================================================


class TestSplitButtonInit:
    def test_requires_label_or_icon(self):
        with pytest.raises(ValueError, match="at least one"):
            SplitButton()

    def test_label_only(self):
        btn = SplitButton("Action")
        assert btn is not None

    def test_icon_only(self):
        btn = SplitButton(icon="star")
        assert btn is not None

    def test_label_and_icon(self):
        btn = SplitButton("Action", icon="star")
        assert btn is not None

    def test_default_menu_open_false(self):
        btn = SplitButton("Action")
        _mount(btn)
        assert btn.menu_open is False

    def test_initial_menu_open_true(self):
        btn = SplitButton("Action", menu_open=True)
        _mount(btn)
        assert btn.menu_open is True

    def test_default_style_is_filled_s(self):
        btn = SplitButton("Action")
        _mount(btn)
        assert btn._trailing_btn._style.container_height == SPLIT_BUTTON_SIZE_TOKENS["s"]["container_height"]

    def test_custom_style_applied(self):
        style = SplitButtonStyle.tonal("m")
        btn = SplitButton("Action", style=style)
        _mount(btn)
        assert btn._trailing_btn._style.container_height == SPLIT_BUTTON_SIZE_TOKENS["m"]["container_height"]


# ===========================================================================
# SplitButton — behavior
# ===========================================================================


class TestSplitButtonBehavior:
    def test_leading_click_fires_on_click(self):
        fired: List[None] = []
        btn = SplitButton("Action", on_click=lambda: fired.append(None))
        _mount(btn)
        _click(btn._leading_btn)
        assert len(fired) == 1

    def test_leading_click_does_not_fire_on_menu_toggle(self):
        toggle_calls: List[bool] = []
        btn = SplitButton("Action", on_menu_toggle=lambda v: toggle_calls.append(v))
        _mount(btn)
        _click(btn._leading_btn)
        assert len(toggle_calls) == 0

    def test_trailing_click_toggles_menu_open(self):
        btn = SplitButton("Action")
        _mount(btn)
        assert btn.menu_open is False
        _click(btn._trailing_btn)
        assert btn.menu_open is True
        _click(btn._trailing_btn)
        assert btn.menu_open is False

    def test_trailing_click_fires_on_menu_toggle(self):
        toggle_calls: List[bool] = []
        btn = SplitButton("Action", on_menu_toggle=lambda v: toggle_calls.append(v))
        _mount(btn)
        _click(btn._trailing_btn)
        assert toggle_calls == [True]
        _click(btn._trailing_btn)
        assert toggle_calls == [True, False]

    def test_trailing_click_does_not_fire_on_click(self):
        fired: List[None] = []
        btn = SplitButton("Action", on_click=lambda: fired.append(None))
        _mount(btn)
        _click(btn._trailing_btn)
        assert len(fired) == 0


# ===========================================================================
# SplitButton — observable menu_open
# ===========================================================================


class TestSplitButtonObservable:
    def _make_obs(self, initial: bool):
        class _Tmp:
            x = Observable(initial)

        return _Tmp().x

    def test_external_observable_initial_state(self):
        obs = self._make_obs(False)
        btn = SplitButton("Action", menu_open=obs)
        _mount(btn)
        assert btn.menu_open is False

    def test_external_observable_initial_state_true(self):
        obs = self._make_obs(True)
        btn = SplitButton("Action", menu_open=obs)
        _mount(btn)
        assert btn.menu_open is True


# ===========================================================================
# Corner animation state
# ===========================================================================


class TestCornerAnimation:
    def _make_btn(self, size: str = "s") -> SplitButton:
        btn = SplitButton("Action", style=SplitButtonStyle.filled(size))
        _mount(btn)
        return btn

    def test_leading_idle_corners(self):
        btn = self._make_btn()
        style = btn._leading_btn._style
        outer = style.outer_corner_radius
        inner = style.inner_corner_radius
        # Expect (outer, inner, inner, outer) at idle
        tl, tr, br, bl = btn._leading_btn.corner_radius
        assert tl == pytest.approx(outer)
        assert tr == pytest.approx(inner)
        assert br == pytest.approx(inner)
        assert bl == pytest.approx(outer)

    def test_trailing_idle_corners(self):
        btn = self._make_btn()
        style = btn._trailing_btn._style
        outer = style.outer_corner_radius
        inner = style.inner_corner_radius
        # Expect (inner, outer, outer, inner) at idle
        tl, tr, br, bl = btn._trailing_btn.corner_radius
        assert tl == pytest.approx(inner)
        assert tr == pytest.approx(outer)
        assert br == pytest.approx(outer)
        assert bl == pytest.approx(inner)

    def test_trailing_selected_corners_are_fully_rounded(self):
        btn = self._make_btn()
        style = btn._trailing_btn._style
        outer = style.outer_corner_radius
        btn._trailing_btn._set_selected(True)
        tl, tr, br, bl = btn._trailing_btn._compute_target_corners()
        assert tl == pytest.approx(outer)
        assert tr == pytest.approx(outer)
        assert br == pytest.approx(outer)
        assert bl == pytest.approx(outer)

    def test_trailing_unselected_corners_use_inner_radius(self):
        btn = self._make_btn()
        style = btn._trailing_btn._style
        inner = style.inner_corner_radius
        outer = style.outer_corner_radius
        btn._trailing_btn._set_selected(False)
        tl, tr, br, bl = btn._trailing_btn._compute_target_corners()
        assert tl == pytest.approx(inner)
        assert tr == pytest.approx(outer)
        assert br == pytest.approx(outer)
        assert bl == pytest.approx(inner)

    def test_leading_pressed_uses_pressed_inner_radius(self):
        btn = self._make_btn()
        style = btn._leading_btn._style
        pressed_r = style.inner_corner_pressed_radius
        outer = style.outer_corner_radius
        btn._leading_btn._own_pressed = True
        tl, tr, br, bl = btn._leading_btn._compute_target_corners()
        assert tr == pytest.approx(pressed_r)
        assert br == pytest.approx(pressed_r)
        assert tl == pytest.approx(outer)
        assert bl == pytest.approx(outer)

    def test_leading_hovered_uses_hovered_inner_radius(self):
        btn = self._make_btn()
        style = btn._leading_btn._style
        hovered_r = style.inner_corner_hovered_radius
        btn._leading_btn._own_hovered = True
        btn._leading_btn._own_pressed = False
        tl, tr, br, bl = btn._leading_btn._compute_target_corners()
        assert tr == pytest.approx(hovered_r)
        assert br == pytest.approx(hovered_r)

    def test_neighbor_press_propagation(self):
        btn = self._make_btn()
        style = btn._leading_btn._style
        pressed_r = style.inner_corner_pressed_radius
        # Simulate trailing button press notification to leading button
        btn._leading_btn._on_neighbor_press(True)
        tl, tr, br, bl = btn._leading_btn._compute_target_corners()
        assert tr == pytest.approx(pressed_r)
        assert br == pytest.approx(pressed_r)

    def test_neighbor_hover_propagation(self):
        btn = self._make_btn()
        style = btn._trailing_btn._style
        hovered_r = style.inner_corner_hovered_radius
        # Simulate leading button hover notification to trailing button
        btn._trailing_btn._on_neighbor_hover(True)
        tl, tr, br, bl = btn._trailing_btn._compute_target_corners()
        assert tl == pytest.approx(hovered_r)
        assert bl == pytest.approx(hovered_r)

    def test_pressed_takes_priority_over_hovered(self):
        btn = self._make_btn()
        style = btn._leading_btn._style
        pressed_r = style.inner_corner_pressed_radius
        btn._leading_btn._own_hovered = True
        btn._leading_btn._own_pressed = True
        r = btn._leading_btn._compute_active_inner_radius()
        assert r == pytest.approx(pressed_r)

    @pytest.mark.parametrize("size", ["xs", "s", "m", "l", "xl"])
    def test_all_sizes_idle_leading_corners(self, size):
        btn = SplitButton("Action", style=SplitButtonStyle.filled(size))
        _mount(btn)
        style = btn._leading_btn._style
        outer = style.outer_corner_radius
        inner = style.inner_corner_radius
        tl, tr, br, bl = btn._leading_btn.corner_radius
        assert tl == pytest.approx(outer)
        assert tr == pytest.approx(inner)
        assert br == pytest.approx(inner)
        assert bl == pytest.approx(outer)


# ===========================================================================
# Icon rotation animation
# ===========================================================================


class TestIconRotation:
    def test_initial_rotation_closed(self):
        btn = SplitButton("Action")
        _mount(btn)
        assert btn._trailing_btn._rotation_anim.value == pytest.approx(0.0)

    def test_initial_rotation_open(self):
        btn = SplitButton("Action", menu_open=True)
        _mount(btn)
        assert btn._trailing_btn._rotation_anim.value == pytest.approx(180.0)

    def test_rotation_target_set_on_select(self):
        btn = SplitButton("Action")
        _mount(btn)
        btn._trailing_btn._set_selected(True)
        assert btn._trailing_btn._rotation_anim.target == pytest.approx(180.0)

    def test_rotation_target_reset_on_deselect(self):
        btn = SplitButton("Action", menu_open=True)
        _mount(btn)
        btn._trailing_btn._set_selected(False)
        assert btn._trailing_btn._rotation_anim.target == pytest.approx(0.0)


# ===========================================================================
# Neighbor wiring (on_mount)
# ===========================================================================


class TestNeighborWiring:
    def test_neighbor_set_after_mount(self):
        btn = SplitButton("Action")
        _mount(btn)
        assert btn._leading_btn._neighbor is btn._trailing_btn
        assert btn._trailing_btn._neighbor is btn._leading_btn
