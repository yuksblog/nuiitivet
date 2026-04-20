"""Tests for GroupButton, StandardButtonGroup, and ConnectedButtonGroup."""

from __future__ import annotations

from typing import List, Union

import pytest

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.button_group import (
    GroupButton,
    ButtonGroupPosition,
    ConnectedButtonGroup,
    StandardButtonGroup,
)
from nuiitivet.material.styles.button_group_style import (
    StandardButtonGroupStyle,
    ConnectedButtonGroupStyle,
)
from nuiitivet.observable import Observable
from tests.helpers.pointer import send_pointer_event_for_test

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(initial: bool):
    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def _make_item(
    label: str = "A",
    *,
    selected: bool = False,
    on_change=None,
    disabled: bool = False,
    style=None,
) -> GroupButton:
    return GroupButton(
        label,
        selected=selected,
        on_change=on_change,
        disabled=disabled,
        style=style,
    )


def _make_items(n: int) -> List[GroupButton]:
    return [_make_item(str(i)) for i in range(n)]


def _mount_group(group) -> None:
    """Simulate mounting the group and all children."""

    class _FakeApp:
        def invalidate(self) -> None:
            pass

        def request_focus(self, node) -> None:
            pass

    group.mount(_FakeApp())


def _click(item: GroupButton) -> None:
    send_pointer_event_for_test(item, PointerEventType.PRESS)
    send_pointer_event_for_test(item, PointerEventType.RELEASE)


# ===========================================================================
# Common — validation
# ===========================================================================


def test_validation_min_items():
    with pytest.raises(ValueError, match="at least 2"):
        StandardButtonGroup([_make_item()])


def test_validation_min_items_boundary():
    group = StandardButtonGroup(_make_items(2))
    assert group is not None


def test_validation_max_items():
    with pytest.raises(ValueError, match="at most 5"):
        StandardButtonGroup(_make_items(6))


def test_validation_max_items_boundary():
    group = StandardButtonGroup(_make_items(5))
    assert group is not None


def test_validation_item_type():
    with pytest.raises(TypeError, match="GroupButton"):
        StandardButtonGroup(["not an item", _make_item()])  # type: ignore[list-item]


# ===========================================================================
# Common — position assignment
# ===========================================================================


def test_position_assignment_two_items():
    items = _make_items(2)
    group = StandardButtonGroup(items)
    _mount_group(group)
    assert items[0]._position == "start"
    assert items[1]._position == "end"


def test_position_assignment_three_items():
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)
    assert items[0]._position == "start"
    assert items[1]._position == "middle"
    assert items[2]._position == "end"


def test_position_assignment_five_items():
    items = _make_items(5)
    group = StandardButtonGroup(items)
    _mount_group(group)
    assert items[0]._position == "start"
    assert items[1]._position == "middle"
    assert items[2]._position == "middle"
    assert items[3]._position == "middle"
    assert items[4]._position == "end"


# ===========================================================================
# Common — corner radius at idle state
# ===========================================================================


def _idle_corners(
    style: Union[StandardButtonGroupStyle, ConnectedButtonGroupStyle],
    position: ButtonGroupPosition,
):
    """Expected idle corners for a given position."""
    o = style.outer_corner_radius
    i = style.inner_corner_radius
    return {
        "start": (o, i, i, o),
        "middle": (i, i, i, i),
        "end": (i, o, o, i),
        "only": (o, o, o, o),
    }[position]


def test_corner_radius_idle_start():
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)
    style = items[0]._style
    assert items[0].corner_radius == _idle_corners(style, "start")


def test_corner_radius_idle_middle():
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)
    style = items[1]._style
    assert items[1].corner_radius == _idle_corners(style, "middle")


def test_corner_radius_idle_end():
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)
    style = items[2]._style
    assert items[2].corner_radius == _idle_corners(style, "end")


# ===========================================================================
# Common — press shape animation target
# ===========================================================================


def test_corner_radius_press_animate_target():
    """Pressing a start item targets the pressed corner values."""
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    item = items[0]  # "start" position
    s = item._style

    send_pointer_event_for_test(item, PointerEventType.PRESS)
    assert item._own_pressed is True

    tl, tr, br, bl = item._corner_anim.target
    assert tl == s.pressed_outer_corner_radius  # outer
    assert tr == s.pressed_inner_corner_radius  # inner
    assert br == s.pressed_inner_corner_radius  # inner
    assert bl == s.pressed_outer_corner_radius  # outer

    send_pointer_event_for_test(item, PointerEventType.RELEASE)
    assert item._own_pressed is False


# ===========================================================================
# Common — on_change and disabled
# ===========================================================================


def test_on_change_fires():
    called = []
    item = _make_item(on_change=lambda selected: called.append(selected))
    _click(item)
    assert called == [True]


def test_disabled_item_ignores_pointer_events():
    called = []
    item = _make_item(disabled=True, on_change=lambda selected: called.append(selected))
    _click(item)
    assert called == []
    assert item.state.pressed is False


# ===========================================================================
# Common — variant style application
# ===========================================================================


def test_variant_filled():
    item = _make_item(style=StandardButtonGroupStyle.filled())
    assert item._style.background is not None


def test_variant_tonal():
    item = _make_item(style=StandardButtonGroupStyle.tonal())
    s = item._style
    # tonal variant: background should differ from filled
    assert s.background != StandardButtonGroupStyle.filled().background


def test_variant_outlined():
    item = _make_item(style=StandardButtonGroupStyle.outlined())
    s = item._style
    assert s.border_width > 0
    assert s.border_color is not None


# ===========================================================================
# StandardButtonGroup — neighbor corner animation
# ===========================================================================


def test_standard_no_neighbor_animate_on_press():
    """Standard group: pressing an item does NOT affect adjacent item corners."""
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    start_item = items[0]  # "start"
    middle_item = items[1]  # "middle"
    s = middle_item._style

    # Press start item
    send_pointer_event_for_test(start_item, PointerEventType.PRESS)

    # Middle should remain at idle corners
    tl, tr, br, bl = middle_item._corner_anim.target
    assert tl == s.inner_corner_radius
    assert bl == s.inner_corner_radius
    assert tr == s.inner_corner_radius
    assert br == s.inner_corner_radius

    # Release
    send_pointer_event_for_test(start_item, PointerEventType.RELEASE)
    tl2, tr2, br2, bl2 = middle_item._corner_anim.target
    assert tl2 == s.inner_corner_radius
    assert bl2 == s.inner_corner_radius


def test_standard_item_selected_independent():
    """Standard group: each item's selected state is independent."""
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    _click(items[0])
    assert items[0]._selected is True
    assert items[1]._selected is False
    assert items[2]._selected is False

    _click(items[1])
    assert items[0]._selected is True
    assert items[1]._selected is True


def test_standard_selected_keeps_squarer_shape_after_release() -> None:
    """Standard item keeps selected shape (does not snap back to idle rounded)."""
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    item = items[0]  # start
    s = item._style

    _click(item)
    assert item._selected is True
    assert item._corner_anim.target == (
        s.pressed_outer_corner_radius,
        s.pressed_inner_corner_radius,
        s.pressed_inner_corner_radius,
        s.pressed_outer_corner_radius,
    )


def test_standard_unselected_returns_to_idle_rounded_shape() -> None:
    """Standard item returns to idle rounded corners when deselected."""
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    item = items[0]  # start
    s = item._style

    _click(item)
    assert item._selected is True

    _click(item)
    assert item._selected is False
    assert item._corner_anim.target == (
        s.outer_corner_radius,
        s.inner_corner_radius,
        s.inner_corner_radius,
        s.outer_corner_radius,
    )


def test_standard_preferred_size():
    """Group height matches container_height; item width respects min_item_width."""
    item = _make_item()
    _h = item._style.container_height
    assert item.preferred_size()[1] == _h
    assert item.preferred_size()[0] >= item._style.min_item_width


# ===========================================================================
# ConnectedButtonGroup — no neighbor animation
# ===========================================================================


def test_connected_no_neighbor_animate():
    """Connected group: pressing an item does NOT affect adjacent item corners."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    start_item = items[0]
    middle_item = items[1]
    s = middle_item._style

    send_pointer_event_for_test(start_item, PointerEventType.PRESS)

    # Middle should remain at idle corners
    tl, tr, br, bl = middle_item._corner_anim.target
    assert tl == s.inner_corner_radius
    assert bl == s.inner_corner_radius

    send_pointer_event_for_test(start_item, PointerEventType.RELEASE)


def test_connected_press_keeps_outer_corners_rounded() -> None:
    """Connected press should animate only inner corners, not outer corners."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    item = items[0]  # start
    s = item._style

    send_pointer_event_for_test(item, PointerEventType.PRESS)
    assert item._corner_anim.target == (
        s.outer_corner_radius,
        s.pressed_inner_corner_radius,
        s.pressed_inner_corner_radius,
        s.outer_corner_radius,
    )

    send_pointer_event_for_test(item, PointerEventType.RELEASE)


def test_connected_selected_press_keeps_selected_inner_rounding() -> None:
    """Connected selected item press should keep selected inner rounding."""
    items = _make_items(3)
    items[0]._set_selected(True)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    item = items[0]  # start
    s = item._style
    selected_inner = s.selected_inner_corner_radius if s.selected_inner_corner_radius > 0 else s.outer_corner_radius

    send_pointer_event_for_test(item, PointerEventType.PRESS)
    assert item._corner_anim.target == (
        s.outer_corner_radius,
        selected_inner,
        selected_inner,
        s.outer_corner_radius,
    )

    send_pointer_event_for_test(item, PointerEventType.RELEASE)


def test_connected_width_full():
    """Connected group items should have flex(1) width after mount."""
    from nuiitivet.rendering.sizing import Sizing

    items = _make_items(3)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    for item in items:
        assert item.width_sizing == Sizing.flex(1)


def test_connected_single_select():
    """Single-select mode: selecting one item deselects all others."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items, select_mode="single")
    _mount_group(group)

    _click(items[0])
    assert items[0]._selected is True
    assert items[1]._selected is False
    assert items[2]._selected is False

    _click(items[1])
    assert items[0]._selected is False
    assert items[1]._selected is True
    assert items[2]._selected is False


def test_connected_multi_select():
    """Multi-select mode: multiple items can be selected simultaneously."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items, select_mode="multi")
    _mount_group(group)

    _click(items[0])
    _click(items[2])
    assert items[0]._selected is True
    assert items[1]._selected is False
    assert items[2]._selected is True


def test_connected_initial_selected():
    """Items with selected=True are reflected in the initial group state."""
    items = [
        _make_item("A", selected=False),
        _make_item("B", selected=True),
        _make_item("C", selected=False),
    ]
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    assert items[1]._selected is True
    # In single-mode, no enforcement on construction — initial state is respected
    assert items[0]._selected is False
    assert items[2]._selected is False


def test_corner_animation_tick_invalidates_paint_cache() -> None:
    """Corner animation updates must invalidate cached background snapshots."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    item = items[1]
    item._paint_cache_snapshot = object()  # type: ignore[attr-defined]

    item._set_selected(True)
    item._on_corner_value_changed(item._corner_anim.target)
    assert item._paint_cache_snapshot is None  # type: ignore[attr-defined]

    item._paint_cache_snapshot = object()  # type: ignore[attr-defined]
    item._set_selected(False)
    item._on_corner_value_changed(item._corner_anim.target)
    assert item._paint_cache_snapshot is None  # type: ignore[attr-defined]
