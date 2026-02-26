"""Tests for badge widgets and BadgeValue."""

import pytest

from nuiitivet.material.badge import BadgeValue, LargeBadge, SmallBadge
from nuiitivet.widgeting.widget import Widget


class _FixedWidget(Widget):
    def __init__(self, pref_w: int, pref_h: int) -> None:
        super().__init__()
        self._pref_w = int(pref_w)
        self._pref_h = int(pref_h)

    def preferred_size(self, max_width=None, max_height=None):
        return (self._pref_w, self._pref_h)


def test_large_badge_format_count_within_max() -> None:
    assert LargeBadge.format_count(9, 999) == "9"


def test_large_badge_format_count_over_max() -> None:
    assert LargeBadge.format_count(1000, 999) == "999+"


def test_large_badge_validates_count() -> None:
    with pytest.raises(ValueError):
        LargeBadge(0)


def test_badge_value_none_to_widget() -> None:
    assert BadgeValue.none().to_widget() is None
    assert BadgeValue.NONE.to_widget() is None


def test_badge_value_small_to_widget() -> None:
    widget = BadgeValue.small().to_widget()
    assert isinstance(widget, SmallBadge)


def test_badge_value_large_to_widget() -> None:
    widget = BadgeValue.large(1200, max=999).to_widget()
    assert isinstance(widget, LargeBadge)
    assert widget.count == 1200
    assert widget.max == 999


def test_badge_value_large_validates() -> None:
    with pytest.raises(ValueError):
        BadgeValue.large(0)
    with pytest.raises(ValueError):
        BadgeValue.large(1, max=0)


def test_small_badge_stick_modifier_defaults() -> None:
    modifier = SmallBadge().stick_modifier()
    assert modifier.alignment == "top-right"
    assert modifier.anchor == "bottom-left"
    assert modifier.offset == (-6.0, 6.0)


def test_large_badge_stick_modifier_defaults() -> None:
    modifier = LargeBadge(1).stick_modifier()
    assert modifier.alignment == "top-right"
    assert modifier.anchor == "bottom-left"
    assert modifier.offset == (-12.0, 14.0)


def test_small_badge_stick_modifier_layout_matches_spec_vector() -> None:
    target = _FixedWidget(24, 24)
    badge = SmallBadge()
    wrapped = target.modifier(badge.stick_modifier())

    wrapped.layout(24, 24)
    assert badge.layout_rect is not None
    bx, by, bw, bh = badge.layout_rect

    # spec vector from icon top-right to badge bottom-left: (-6, +6)
    top_right_x = 24
    top_right_y = 0
    bottom_left_x = bx
    bottom_left_y = by + bh
    assert (bottom_left_x - top_right_x, bottom_left_y - top_right_y) == (-6, 6)


def test_large_badge_stick_modifier_layout_matches_spec_vector() -> None:
    target = _FixedWidget(24, 24)
    badge = LargeBadge(12)
    wrapped = target.modifier(badge.stick_modifier())

    wrapped.layout(24, 24)
    assert badge.layout_rect is not None
    bx, by, bw, bh = badge.layout_rect

    # spec vector from icon top-right to badge bottom-left: (-12, +14)
    top_right_x = 24
    top_right_y = 0
    bottom_left_x = bx
    bottom_left_y = by + bh
    assert (bottom_left_x - top_right_x, bottom_left_y - top_right_y) == (-12, 14)
