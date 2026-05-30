"""Tests for modeless()/light_dismiss() modifiers."""

from __future__ import annotations

from typing import Optional, Tuple

from nuiitivet.modifiers.popup import PopupBox, PopupModifier, modeless, light_dismiss
from nuiitivet.overlay.overlay_position import (
    AnchoredOverlayPosition,
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
# AnchoredOverlayPosition
# ---------------------------------------------------------------------------


class TestAnchoredOverlayPosition:
    def test_anchored_factory_returns_instance(self) -> None:
        pos = AnchoredOverlayPosition.anchored(lambda: (0, 0, 100, 50))
        assert isinstance(pos, AnchoredOverlayPosition)

    def test_make_position_content_returns_anchored_widget(self) -> None:
        pos = AnchoredOverlayPosition.anchored(lambda: (10, 20, 100, 50))
        content = _FixedWidget(60, 40)
        wrapped = pos.make_position_content(content)
        assert isinstance(wrapped, _AnchoredPositionedContent)

    def test_default_alignment_bottom_left_to_top_left(self) -> None:
        """With alignment=bottom-left and anchor=top-left, content should
        appear directly below the anchor widget."""
        anchor_rect = (50, 100, 80, 30)  # x=50, y=100, w=80, h=30
        pos = AnchoredOverlayPosition.anchored(lambda: anchor_rect)
        content = _FixedWidget(60, 40)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)

        # alignment "bottom-left" on anchor → point (0, 30) relative to anchor
        # anchor "top-left" on content → point (0, 0)
        # expected: (50 + 0 - 0, 100 + 30 - 0) = (50, 130)
        assert content.layout_rect == (50, 130, 60, 40)

    def test_alignment_top_right_to_top_left(self) -> None:
        """Content pinned to the right edge of the anchor."""
        anchor_rect = (20, 40, 100, 50)
        pos = AnchoredOverlayPosition.anchored(
            lambda: anchor_rect,
            alignment="top-right",
            anchor="top-left",
        )
        content = _FixedWidget(80, 30)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)

        # alignment "top-right" on anchor → (100, 0) relative; anchor "top-left" → (0, 0)
        # expected: (20+100-0, 40+0-0) = (120, 40)
        assert content.layout_rect == (120, 40, 80, 30)

    def test_offset_applied(self) -> None:
        anchor_rect = (50, 100, 80, 30)
        pos = AnchoredOverlayPosition.anchored(
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
        pos = AnchoredOverlayPosition.anchored(lambda: None)
        content = _FixedWidget(50, 30)
        placed = pos.make_position_content(content)
        placed.layout(800, 600)
        assert content.layout_rect == (0, 0, 50, 30)


# ---------------------------------------------------------------------------
# _AnchoredPositionedContent preferred_size / hit_test
# ---------------------------------------------------------------------------


class TestAnchoredPositionedContent:
    def test_preferred_size_is_zero(self) -> None:
        content = _FixedWidget(100, 80)
        pos = AnchoredOverlayPosition.anchored(lambda: (0, 0, 50, 50))
        placed = pos.make_position_content(content)
        assert placed.preferred_size() == (0, 0)

    def test_hit_test_returns_none_for_self(self) -> None:
        content = _FixedWidget(100, 80)
        pos = AnchoredOverlayPosition.anchored(lambda: (0, 0, 50, 50))
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
        modifier = modeless(content)
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)

    def test_apply_passes_alignment(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = modeless(content, alignment="top-right", anchor="bottom-right")
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        box: PopupBox = result
        assert box._alignment == "top-right"
        assert box._anchor == "bottom-right"

    def test_apply_passes_offset(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = modeless(content, offset=(3.0, -5.0))
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        assert result._offset == (3.0, -5.0)

    def test_apply_with_external_is_open(self) -> None:
        from nuiitivet.observable.value import Observable

        is_open: "Observable[bool]" = Observable(False)
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = modeless(content, is_open=is_open)
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        assert result._is_open is is_open

    def test_apply_light_dismiss_sets_behavior_flag(self) -> None:
        child = _FixedWidget(80, 40)
        content = _FixedWidget(120, 80)
        modifier = light_dismiss(content)
        result = modifier.apply(child)
        assert isinstance(result, PopupBox)
        assert result._light_dismiss is True


# ---------------------------------------------------------------------------
# modeless()/light_dismiss() factory functions
# ---------------------------------------------------------------------------


class TestPopupFactory:
    def test_returns_popup_modifier(self) -> None:
        content = _FixedWidget(50, 30)
        result = modeless(content)
        assert isinstance(result, PopupModifier)

    def test_light_dismiss_returns_popup_modifier(self) -> None:
        content = _FixedWidget(50, 30)
        result = light_dismiss(content)
        assert isinstance(result, PopupModifier)
        assert result.light_dismiss is True

    def test_default_alignment_and_anchor(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = modeless(content)
        assert modifier.alignment == "bottom-left"
        assert modifier.anchor == "top-left"

    def test_default_offset(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = modeless(content)
        assert modifier.offset == (0.0, 0.0)

    def test_custom_parameters_forwarded(self) -> None:
        content = _FixedWidget(50, 30)
        modifier = modeless(
            content,
            alignment="top-right",
            anchor="bottom-left",
            offset=(2.0, 4.0),
        )
        assert modifier.alignment == "top-right"
        assert modifier.anchor == "bottom-left"
        assert modifier.offset == (2.0, 4.0)


# ---------------------------------------------------------------------------
# Export from nuiitivet.modifiers
# ---------------------------------------------------------------------------


def test_modeless_and_light_dismiss_exported_from_modifiers() -> None:
    import nuiitivet.modifiers as m

    assert hasattr(m, "modeless"), "modeless must be exported from nuiitivet.modifiers"
    assert hasattr(m, "light_dismiss"), "light_dismiss must be exported from nuiitivet.modifiers"
    assert "modeless" in m.__all__
    assert "light_dismiss" in m.__all__
