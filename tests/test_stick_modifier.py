"""Tests for stick modifier behavior."""

from nuiitivet.modifiers import stick
from nuiitivet.widgeting.widget import Widget


class _FixedWidget(Widget):
    def __init__(self, pref_w: int, pref_h: int) -> None:
        super().__init__()
        self._pref_w = int(pref_w)
        self._pref_h = int(pref_h)

    def preferred_size(self, max_width=None, max_height=None):
        return (self._pref_w, self._pref_h)


def test_stick_default_places_badge_on_top_right() -> None:
    target = _FixedWidget(24, 24)
    badge = _FixedWidget(6, 6)

    wrapped = target.modifier(stick(badge))
    wrapped.layout(24, 24)

    assert target.layout_rect == (0, 0, 24, 24)
    assert badge.layout_rect == (21, -3, 6, 6)


def test_stick_with_alignment_anchor_offset() -> None:
    target = _FixedWidget(40, 20)
    badge = _FixedWidget(10, 8)

    wrapped = target.modifier(
        stick(
            badge,
            alignment="center",
            anchor="center",
            offset=(3.0, -2.0),
        )
    )
    wrapped.layout(40, 20)

    # Center(20,10) - anchor(5,4) + offset(3,-2) = (18,4)
    assert badge.layout_rect == (18, 4, 10, 8)
