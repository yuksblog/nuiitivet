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

        def request_focus(self, node, source=None) -> None:
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


def test_standard_neighbor_corners_unaffected_on_press():
    """Standard group: pressing an item must NOT alter a neighbor's corners.

    Per MD3, the adjacent interaction adjusts neighbor **width**, not shape.
    """
    items = _make_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    start_item = items[0]  # "start"
    middle_item = items[1]  # "middle"
    s = middle_item._style

    # Press start item — its corners morph, but the middle neighbor's corners
    # stay at idle.
    send_pointer_event_for_test(start_item, PointerEventType.PRESS)

    tl, tr, br, bl = middle_item._corner_anim.target
    assert tl == s.inner_corner_radius
    assert tr == s.inner_corner_radius
    assert br == s.inner_corner_radius
    assert bl == s.inner_corner_radius

    # Release — still idle.
    send_pointer_event_for_test(start_item, PointerEventType.RELEASE)
    assert middle_item._corner_anim.target == (
        s.inner_corner_radius,
        s.inner_corner_radius,
        s.inner_corner_radius,
        s.inner_corner_radius,
    )


# ===========================================================================
# StandardButtonGroup — adjacent width interaction
# ===========================================================================


def _make_wide_items(n: int) -> List[GroupButton]:
    """Items sharing a wide, identical-width label so their base widths match.

    Equal base widths keep the growth/shrink arithmetic exact: the per-neighbor
    shrink room equals the active item's growth share, so no capping kicks in.
    """
    return [_make_item("Wide Label") for _ in range(n)]


def _group_row(group):
    """Return the group's interaction-aware row (Standard groups only)."""
    from nuiitivet.material.button_group import _ButtonGroupRow

    for child in group.children:
        if isinstance(child, _ButtonGroupRow):
            return child
    raise AssertionError("interaction row not found")


def _computed_widths(group):
    """Run the parent's single-pass width computation for the current progress."""
    row = _group_row(group)
    return row._interaction_widths(list(group._items))


def _set_active(item, active: bool = True) -> None:
    """Force an item's active progress (bypassing animation) to 0 or 1."""
    item._press_progress.snap_to(1.0 if active else 0.0)


def _side_growth(active, neighbor) -> float:
    """Expected per-side growth: half the multiplier, capped by neighbor padding."""
    half = active._style.pressed_width_multiplier * active._base_width / 2.0
    pad = float(getattr(neighbor._style, "inner_padding", 12))
    return min(half, pad)


def test_standard_press_sets_active_progress():
    """Pressing an item drives its active progress toward 1.0."""
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    item = items[1]  # middle
    send_pointer_event_for_test(item, PointerEventType.PRESS)
    assert item._press_progress.target == pytest.approx(1.0)
    # Releasing without selecting returns toward 0.0 (independent action item).


def test_standard_active_item_grows():
    """An active item's computed width grows by both-side growth."""
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    start, middle, end = items
    _set_active(middle)

    widths = _computed_widths(group)
    expected = middle._base_width + _side_growth(middle, start) + _side_growth(middle, end)
    assert widths[1] == pytest.approx(expected)
    assert widths[1] > middle._base_width


def test_standard_neighbors_compress_to_compensate():
    """An active middle item compresses both neighbors by its per-side growth."""
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    start, middle, end = items
    _set_active(middle)

    widths = _computed_widths(group)
    assert widths[0] == pytest.approx(start._base_width - _side_growth(middle, start))
    assert widths[2] == pytest.approx(end._base_width - _side_growth(middle, end))
    # Total width is conserved (no group bulge).
    assert sum(widths) == pytest.approx(sum(it._base_width for it in items))


def test_standard_edge_item_compresses_single_neighbor():
    """An edge item grows only on its one available side, compressing one neighbor."""
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    start, middle, end = items
    _set_active(start)

    widths = _computed_widths(group)
    g = _side_growth(start, middle)
    assert widths[0] == pytest.approx(start._base_width + g)
    assert widths[1] == pytest.approx(middle._base_width - g)
    assert widths[2] == pytest.approx(end._base_width)


def test_standard_width_expands_on_press_only():
    """Width grows only while pressed; on release it returns to idle width.

    MD3 defines only a *pressed* width token — selection is conveyed by colour
    and corner shape, not by a persistent width change.
    """
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    item = items[1]
    # Press → peak expansion.
    send_pointer_event_for_test(item, PointerEventType.PRESS)
    assert item._press_progress.target == pytest.approx(1.0)
    # Release (click) → selected, but width returns to idle.
    send_pointer_event_for_test(item, PointerEventType.RELEASE)
    assert item._selected is True
    assert item._press_progress.target == pytest.approx(0.0)


def test_standard_selected_item_rests_at_idle_width():
    """Selecting / deselecting never leaves a persistent width expansion."""
    items = _make_wide_items(3)
    group = StandardButtonGroup(items)
    _mount_group(group)

    middle = items[1]
    _click(middle)  # select
    assert middle._selected is True
    assert middle._press_progress.target == pytest.approx(0.0)

    _click(middle)  # deselect
    assert middle._selected is False
    assert middle._press_progress.target == pytest.approx(0.0)

    # With progress settled at 0 (no active item), computed widths equal bases.
    for it in items:
        _set_active(it, False)
    widths = _computed_widths(group)
    assert widths == pytest.approx([it._base_width for it in items])


def test_standard_side_space_reserved_via_centering():
    """Standard items reserve side space as centred margin, not box padding.

    The MD3 button leading/trailing-space (m → 24dp) is reserved in the item's
    preferred width and rendered by centring the content (box padding stays 0),
    so the pressed-width interaction compresses neighbours symmetrically.
    """
    items = _make_items(2)
    group = StandardButtonGroup(items, style=StandardButtonGroupStyle.filled("m"))
    _mount_group(group)

    item = items[0]
    # No box padding: the space is centred margin, not an inset inner rect.
    assert item.padding == (0, 0, 0, 0)
    # Preferred width reserves 2 × 24dp around the bare content width.
    content_w = item.children[0].preferred_size()[0]
    assert item.preferred_size()[0] == content_w + 2 * 24


def test_standard_content_centered_in_item():
    """Content sits centred in the item, with equal left/right margins."""
    items = _make_items(2)
    group = StandardButtonGroup(items, style=StandardButtonGroupStyle.filled("m"))
    _mount_group(group)

    item = items[0]
    iw, ih = item.preferred_size()
    item.layout(iw, ih)
    cx, _cy, cw, _ch = item.children[0].layout_rect
    left_margin = cx
    right_margin = iw - (cx + cw)
    assert left_margin == pytest.approx(right_margin, abs=1)


def test_connected_width_interaction_disabled():
    """Connected group: pressing an item leaves neighbor widths untouched."""
    items = _make_items(3)
    group = ConnectedButtonGroup(items)
    _mount_group(group)

    start, middle, end = items
    # Connected items keep flex sizing; the width animation must not engage.
    send_pointer_event_for_test(middle, PointerEventType.PRESS)
    assert start.width_sizing.kind == "flex"
    assert end.width_sizing.kind == "flex"


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
    """Standard item keeps the pressed (squared) shape while selected.

    The MD3 button-group spec defines no separate selected shape for standard
    groups, and the official demo shows a selected segment at the same roundness
    as a pressed one, so selection reuses the pressed corners (it does not snap
    back to the idle rounded pill).
    """
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
    """Standard item height matches container_height; width is content-fit.

    The 48dp spec value is a tap-target requirement, not a visual width floor,
    so a Standard item is free to be narrower than ``min_item_width``.
    """
    items = _make_items(2)
    group = StandardButtonGroup(items)
    _mount_group(group)
    item = items[0]
    assert item.preferred_size()[1] == item._style.container_height
    # Content-fit: a short label may render narrower than min_item_width.
    assert item.preferred_size()[0] == item._base_width


def test_standard_preferred_size_correct_before_mount():
    """A group reports its sized width before mount (window auto-sizing).

    Window auto-sizing measures the unmounted content tree.  The group must
    propagate its size-specific style to items at construction so a larger size
    is not under-measured at the default ("s") size (regression: only width was
    affected because height comes from container_height).
    """
    items = [GroupButton(icon="event", label="Week") for _ in range(3)]
    group = StandardButtonGroup(items, style=StandardButtonGroupStyle.filled("l"))

    pre = group.preferred_size()
    _mount_group(group)
    post = group.preferred_size()

    assert pre == post
    # Larger size really is wider than the default "s" group of the same labels.
    s_items = [GroupButton(icon="event", label="Week") for _ in range(3)]
    s_group = StandardButtonGroup(s_items, style=StandardButtonGroupStyle.filled("s"))
    assert pre[0] > s_group.preferred_size()[0]


def test_connected_preferred_size_enforces_min_width():
    """Connected items still enforce the 48dp visual minimum width."""
    items = _make_items(2)
    group = ConnectedButtonGroup(items)
    _mount_group(group)
    item = items[0]
    assert item.preferred_size()[0] >= item._style.min_item_width


def test_standard_group_width_preserved_with_short_labels():
    """Short-label / icon-only segments must not bulge the group on press.

    The parent computes all widths in one pass: the active item's growth is
    exactly the neighbors' compression, so the summed width is conserved and the
    rightmost item cannot accumulate jitter.
    """
    items = _make_items(3)  # short labels "0","1","2"
    group = StandardButtonGroup(items)
    _mount_group(group)

    initial_total = sum(it._base_width for it in items)

    _set_active(items[1])  # middle active
    widths = _computed_widths(group)

    # Active grows, both neighbors compress, total unchanged (no bulge).
    assert sum(widths) == pytest.approx(initial_total)
    assert widths[1] > items[1]._base_width
    assert widths[0] < items[0]._base_width
    assert widths[2] < items[2]._base_width


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
