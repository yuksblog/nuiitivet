"""Tests for the popup() modifier."""

from __future__ import annotations

from typing import Optional, Tuple

import pytest

from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.modifiers.popup import PopupBox, PopupModifier, popup
from nuiitivet.overlay.overlay_position import (
    OverlayPosition,
    _AnchoredPositionedContent,
)
from nuiitivet.widgeting.widget import Widget


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FixedWidget(Widget):
    """Widget with a fixed preferred size for testing."""

    def __init__(self, pref_w: int = 0, pref_h: int = 0) -> None:
        super().__init__()
        self._pref_w = int(pref_w)
        self._pref_h = int(pref_h)

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        return (self._pref_w, self._pref_h)


# ---------------------------------------------------------------------------
# OverlayPosition.anchored()
# ---------------------------------------------------------------------------


class TestOverlayPositionAnchored:
    def test_anchored_factory_returns_instance(self) -> None:
        pos = OverlayPosition.anchored(lambda: (0, 0, 100, 50))
        assert isinstance(pos, OverlayPosition)

    def test_make_position_content_returns_anchored_widget(self) -> None:
        pos = OverlayPosition.anchored(lambda: (10, 20, 100, 50))
        content = _FixedWidget(60, 40)
        wrapped = pos.make_position_content(content)
        assert isinstance(wrapped, _AnchoredPositionedContent)

    def test_default_anchors_place_content_below(self) -> None:
        """With target_anchor=bottom-left and content_anchor=top-left, content
        should appear directly below the anchor widget."""
        anchor_rect = (50, 100, 80, 30)  # x=50, y=100, w=80, h=30
        pos = OverlayPosition.anchored(lambda: anchor_rect)
        content = _FixedWidget(60, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)

        # target_anchor "bottom-left" → point (0, 30) relative to the anchor
        # content_anchor "top-left" → point (0, 0) on the content
        # expected: (50 + 0 - 0, 100 + 30 - 0) = (50, 130)
        assert content.layout_rect == (50, 130, 60, 40)

    def test_target_anchor_top_right(self) -> None:
        """Content pinned to the right edge of the anchor."""
        anchor_rect = (20, 40, 100, 50)
        pos = OverlayPosition.anchored(
            lambda: anchor_rect,
            target_anchor="top-right",
            content_anchor="top-left",
        )
        content = _FixedWidget(80, 30)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)

        # target_anchor "top-right" → (100, 0) relative; content_anchor "top-left" → (0, 0)
        # expected: (20+100-0, 40+0-0) = (120, 40)
        assert content.layout_rect == (120, 40, 80, 30)

    def test_offset_applied(self) -> None:
        anchor_rect = (50, 100, 80, 30)
        pos = OverlayPosition.anchored(
            lambda: anchor_rect,
            offset=(5.0, -3.0),
        )
        content = _FixedWidget(60, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)

        # Without offset: (50, 130). With offset (+5, -3): (55, 127)
        assert content.layout_rect == (55, 127, 60, 40)

    def test_rect_none_falls_back_to_origin(self) -> None:
        """When the rect provider returns None, content is placed at (0, 0)."""
        pos = OverlayPosition.anchored(lambda: None)
        content = _FixedWidget(50, 30)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (0, 0, 50, 30)


# ---------------------------------------------------------------------------
# OverlayPosition.at_point() / at_pointer()
# ---------------------------------------------------------------------------


class TestOverlayPositionAtPoint:
    def test_content_top_left_lands_on_the_point(self) -> None:
        pos = OverlayPosition.at_point(120, 200)
        content = _FixedWidget(60, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (120, 200, 60, 40)

    def test_content_anchor_shifts_the_content_off_the_point(self) -> None:
        """bottom-center puts the point at the middle of the content's bottom edge."""
        pos = OverlayPosition.at_point(300, 300, content_anchor="bottom-center")
        content = _FixedWidget(80, 20)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (260, 280, 80, 20)

    def test_offset_applied_to_the_point(self) -> None:
        pos = OverlayPosition.at_point(100, 100, offset=(-8.0, 12.0))
        content = _FixedWidget(30, 30)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (92, 112, 30, 30)

    def test_at_pointer_uses_screen_not_local_coordinates(self) -> None:
        """The event carries both pairs; only the screen pair positions overlays."""
        event = PointerEvent(
            id=1,
            type=PointerEventType.PRESS,
            x=400.0,
            y=250.0,
            local_x=12.0,
            local_y=9.0,
        )
        pos = OverlayPosition.at_pointer(event)
        content = _FixedWidget(50, 50)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (400, 250, 50, 50)


# ---------------------------------------------------------------------------
# Viewport clamping
# ---------------------------------------------------------------------------


class TestViewportClamping:
    def test_content_past_the_right_edge_is_pulled_back(self) -> None:
        pos = OverlayPosition.at_point(780, 100)
        content = _FixedWidget(100, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        # Would have run to x=880; clamped so the right edge sits at 800.
        assert content.layout_rect == (700, 100, 100, 40)

    def test_content_past_the_bottom_edge_is_pulled_back(self) -> None:
        pos = OverlayPosition.at_point(100, 590)
        content = _FixedWidget(40, 80)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (100, 520, 40, 80)

    def test_negative_position_is_pulled_to_the_origin(self) -> None:
        pos = OverlayPosition.at_point(10, 10, content_anchor="bottom-right")
        content = _FixedWidget(60, 60)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (0, 0, 60, 60)

    def test_content_larger_than_the_viewport_pins_to_the_origin(self) -> None:
        pos = OverlayPosition.at_point(400, 300)
        content = _FixedWidget(1000, 900)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (0, 0, 1000, 900)

    def test_shift_false_leaves_the_content_off_screen(self) -> None:
        pos = OverlayPosition.at_point(780, 100, shift=False)
        content = _FixedWidget(100, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (780, 100, 100, 40)

    def test_anchored_content_flips_instead_of_covering_its_anchor(self) -> None:
        """No room below, so it opens above -- never slid up over the anchor."""
        pos = OverlayPosition.anchored(lambda: (760, 560, 40, 40))
        content = _FixedWidget(120, 90)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        # y: 560 - 90 = 470, against the anchor's top edge.
        # x: shifted along the cross axis to keep the right edge at 800.
        assert content.layout_rect == (680, 470, 120, 90)

    def test_anchored_content_keeps_its_side_when_neither_fits(self) -> None:
        """Nowhere to go: stay put and overflow, rather than pick a surprise."""
        pos = OverlayPosition.anchored(lambda: (100, 300, 40, 40))
        content = _FixedWidget(100, 5000)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (100, 340, 100, 5000)

    def test_flip_false_stays_below_and_overflows(self) -> None:
        pos = OverlayPosition.anchored(lambda: (760, 560, 40, 40), flip=False)
        content = _FixedWidget(120, 90)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (680, 600, 120, 90)

    def test_flip_mirrors_the_offset_so_the_gap_stays_a_gap(self) -> None:
        """A 10px gap below has to become a 10px gap above, not a 10px overlap."""
        pos = OverlayPosition.anchored(lambda: (100, 560, 40, 40), offset=(0.0, 10.0))
        content = _FixedWidget(50, 100)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        # anchor top is 560, so the content's bottom sits at 550.
        assert content.layout_rect == (100, 450, 50, 100)


# ---------------------------------------------------------------------------
# _AnchoredPositionedContent preferred_size / hit_test
# ---------------------------------------------------------------------------


class TestAnchoredPositionedContent:
    def test_preferred_size_is_zero(self) -> None:
        content = _FixedWidget(100, 80)
        pos = OverlayPosition.anchored(lambda: (0, 0, 50, 50))
        placed = pos.make_position_content(content)
        assert placed.preferred_size() == (0, 0)

    def test_hit_test_returns_none_for_self(self) -> None:
        content = _FixedWidget(100, 80)
        pos = OverlayPosition.anchored(lambda: (0, 0, 50, 50))
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        # No child is at (500, 500) in this layout; super().hit_test returns self
        # which should be converted to None
        result = placed.hit_test(500, 500)
        assert result is None or result is not placed


# ---------------------------------------------------------------------------
# PopupBox creation and layout
# ---------------------------------------------------------------------------


class TestPopupBox:
    def test_preferred_size_follows_child(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        assert box.preferred_size() == (80, 40)

    def test_layout_applies_to_child(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        box.layout(80, 40)
        assert box._child.layout_rect == (0, 0, 80, 40)

    def test_initial_rect_provider_is_none_without_layout(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        assert box._rect_provider() is None

    def test_rect_provider_uses_global_layout_rect(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        box.set_layout_rect(12, 34, 80, 40)
        assert box._rect_provider() == (12, 34, 80, 40)

    def test_is_open_none_default_internal_state(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=None)
        assert box._is_open.value is False

    def test_external_observable_reflects_state(self) -> None:
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=is_open)

        assert box._is_open.value is False
        is_open.value = True
        assert box._is_open.value is True

    def test_open_without_layout_rect_keeps_popup_closed(self) -> None:
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=is_open)

        # Trigger open before any layout rect is available.
        is_open.value = True
        box._do_open()
        assert box._handle is None

    def test_do_open_requires_overlay_in_tree(self) -> None:
        """_do_open should silently return when no root Overlay is initialized."""
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=is_open)
        box.set_layout_rect(10, 20, 80, 40)

        # No overlay in tree – should not raise
        box._do_open()
        assert box._handle is None

    def test_do_close_cancels_callbacks_without_open_handle(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        box._open_retry_callback = lambda _dt: None
        box._handle_monitor_callback = lambda _dt: None

        box._do_close()
        assert box._open_retry_callback is None
        assert box._handle_monitor_callback is None

    def test_do_close_noop_when_not_open(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content)
        # Should not raise when already closed
        box._do_close()

    def test_is_open_observable_can_be_toggled(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=None)

        assert box._is_open.value is False
        box._is_open.value = True
        assert box._is_open.value is True
        box._is_open.value = False
        assert box._is_open.value is False

    def test_external_observable_is_shared_with_box(self) -> None:
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        box = PopupBox(child, content, is_open=is_open)

        # _is_open IS the provided observable – same object
        assert box._is_open is is_open

        box._is_open.value = True
        assert is_open.value is True

        box._is_open.value = False
        assert is_open.value is False


# ---------------------------------------------------------------------------
# PopupModifier
# ---------------------------------------------------------------------------


class TestPopupModifier:
    def test_apply_returns_popup_box(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = popup(content)
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)

    def test_apply_passes_anchors(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = popup(content, target_anchor="top-right", content_anchor="bottom-right")
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        box: PopupBox = result
        assert box._target_anchor == "top-right"
        assert box._content_anchor == "bottom-right"

    def test_apply_passes_offset(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = popup(content, offset=(3.0, -5.0))
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        assert result._offset == (3.0, -5.0)

    def test_apply_with_external_is_open(self) -> None:
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = popup(content, is_open=is_open)
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        assert result._is_open is is_open

    def test_apply_forwards_input_axes(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        result = popup(content, passthrough=True).apply(child)
        assert isinstance(result, PopupBox)
        assert result._passthrough is True
        assert result._dismiss_on_outside_tap is False


# ---------------------------------------------------------------------------
# popup() factory function
# ---------------------------------------------------------------------------


class TestPopupFactory:
    def test_returns_popup_modifier(self) -> None:
        content = _FixedWidget(50, 30)
        result = popup(content)
        assert isinstance(result, PopupModifier)

    def test_default_blocks_and_dismisses(self) -> None:
        """``popup(x)`` is the menu shape: block input, close on outside tap."""
        box = popup(_FixedWidget(50, 30)).apply(_FixedWidget(80, 40))
        assert isinstance(box, PopupBox)
        assert box._passthrough is False
        assert box._dismiss_on_outside_tap is True

    def test_passthrough_resolves_dismissal_to_false(self) -> None:
        """``popup(x, passthrough=True)`` is the toast/tooltip shape."""
        box = popup(_FixedWidget(50, 30), passthrough=True).apply(_FixedWidget(80, 40))
        assert isinstance(box, PopupBox)
        assert box._passthrough is True
        assert box._dismiss_on_outside_tap is False

    def test_explicit_dismissal_overrides_the_resolved_default(self) -> None:
        box = popup(_FixedWidget(50, 30), dismiss_on_outside_tap=False).apply(_FixedWidget(80, 40))
        assert isinstance(box, PopupBox)
        assert box._passthrough is False
        assert box._dismiss_on_outside_tap is False

    def test_passthrough_with_explicit_dismissal_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot also observe it"):
            popup(_FixedWidget(50, 30), passthrough=True, dismiss_on_outside_tap=True)

    def test_anchor_passthrough_defaults_to_false(self) -> None:
        """``popup(x)`` keeps the toggle-anchor shape: a re-tap dismisses."""
        box = popup(_FixedWidget(50, 30)).apply(_FixedWidget(80, 40))
        assert isinstance(box, PopupBox)
        assert box._anchor_passthrough is False

    def test_anchor_passthrough_is_forwarded(self) -> None:
        box = popup(_FixedWidget(50, 30), anchor_passthrough=True).apply(_FixedWidget(80, 40))
        assert isinstance(box, PopupBox)
        assert box._anchor_passthrough is True

    def test_default_anchors(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = popup(content)
        assert modifier.target_anchor == "bottom-left"
        assert modifier.content_anchor == "top-left"

    def test_default_offset(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = popup(content)
        assert modifier.offset == (0.0, 0.0)

    def test_custom_parameters_forwarded(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = popup(
            content,
            target_anchor="top-right",
            content_anchor="bottom-left",
            offset=(2.0, 4.0),
        )
        assert modifier.target_anchor == "top-right"
        assert modifier.content_anchor == "bottom-left"
        assert modifier.offset == (2.0, 4.0)


# ---------------------------------------------------------------------------
# Export from nuiitivet.modifiers
# ---------------------------------------------------------------------------


def test_popup_exported_from_modifiers() -> None:
    import nuiitivet.modifiers as m
    import nuiitivet

    assert hasattr(m, "popup"), "popup must be exported from nuiitivet.modifiers"
    assert "popup" in m.__all__
    assert hasattr(nuiitivet, "popup"), "popup must be exported from nuiitivet"
    assert "popup" in nuiitivet.__all__
    assert not hasattr(m, "modeless")
    assert not hasattr(m, "light_dismiss")
