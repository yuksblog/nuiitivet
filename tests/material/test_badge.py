"""Tests for badge widgets."""

import pytest

from nuiitivet.material.badge import LargeBadge, SmallBadge
from nuiitivet.widgeting.widget import Widget


class _FixedWidget(Widget):
    def __init__(self, pref_w: int, pref_h: int) -> None:
        super().__init__()
        self._pref_w = int(pref_w)
        self._pref_h = int(pref_h)

    def preferred_size(self, max_width=None, max_height=None):
        return (self._pref_w, self._pref_h)


def test_large_badge_creates_with_text() -> None:
    badge = LargeBadge("42")
    assert badge.text == "42"


def test_large_badge_validates_empty_text() -> None:
    with pytest.raises(ValueError):
        LargeBadge("")


def test_small_badge_stick_modifier_defaults() -> None:
    modifier = SmallBadge().stick_modifier()
    assert modifier.alignment == "top-right"
    assert modifier.anchor == "bottom-left"
    assert modifier.offset == (-6.0, 6.0)


def test_large_badge_stick_modifier_defaults() -> None:
    modifier = LargeBadge("1").stick_modifier()
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
    badge = LargeBadge("12")
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
