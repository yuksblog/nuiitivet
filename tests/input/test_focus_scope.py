"""Focus traversal groups: traversable vs focusable, and the FocusScope model."""

from __future__ import annotations

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import Checkbox, Menu, MenuItem, SubMenuItem
from nuiitivet.material.slider import HorizontalRangeSlider, HorizontalSlider
from nuiitivet.overlay import Overlay
from nuiitivet.runtime.app import App
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode, FocusSource
from tests.helpers.pointer import send_pointer_event_for_test

SHIFT = 1


def _focus_node(widget) -> FocusNode:
    node = widget.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    return node


def _mounted_app(root) -> App:
    app = App(root)
    root.mount(app)
    return app


# --- traversable vs focusable -------------------------------------------------


def test_non_traversable_node_is_not_a_tab_stop() -> None:
    """A non-traversable widget is skipped by the global Tab sequence."""
    a = Clickable()
    b = Clickable(traversable=False)
    c = Clickable()
    app = App(Column([a, b, c]))

    nodes = app._collect_focus_nodes()

    assert nodes == [_focus_node(a), _focus_node(c)]


def test_non_traversable_node_still_focuses_and_receives_keys() -> None:
    """Skipping Tab traversal must not stop the node from holding focus."""
    keys: list[str] = []

    def _on_key(key: str, _modifier_keys: int) -> bool:
        keys.append(key)
        return True

    widget = Clickable(traversable=False)
    node = _focus_node(widget)
    node._on_key = _on_key
    app = App(Column([widget]))

    app.request_focus(node, FocusSource.KEYBOARD)
    app._dispatch_key_press("enter")

    assert widget.state.focused is True
    assert keys == ["enter"]


def test_unrelated_widgets_keep_one_tab_stop_each() -> None:
    """Regression: ordinary widgets are one Tab stop each, in tree order."""
    button = Checkbox()
    slider = HorizontalSlider(value=0.5, min_value=0.0, max_value=1.0)
    app = App(Column([button, slider]))

    nodes = app._collect_focus_nodes()

    assert nodes == [_focus_node(button), _focus_node(slider)]


# --- Menu ---------------------------------------------------------------------


def _menu(**kwargs) -> Menu:
    return Menu(
        items=[MenuItem("Cut"), MenuItem("Copy", disabled=True), MenuItem("Paste")],
        **kwargs,
    )


def _menu_in_overlay(menu: Menu) -> App:
    """Show ``menu`` the way it is really used: as a laid-out overlay entry."""
    app = App(content=Container(width=400, height=400))
    app.root.mount(app)
    Overlay.root().show_modeless(menu)
    app.root.layout(400, 400)
    return app


def test_a_popup_menu_is_not_in_the_tab_sequence() -> None:
    """A popup is entered by opening it: neither surface nor items are Tab stops."""
    menu = _menu()
    app = _menu_in_overlay(menu)

    assert app._collect_focus_nodes() == []


def test_an_inline_menu_is_a_single_tab_stop() -> None:
    """An inline menu is one stop in the page — never one stop per item."""
    button = Checkbox()
    menu = _menu()
    app = _mounted_app(Column([button, menu]))

    assert app._collect_focus_nodes() == [_focus_node(button), _focus_node(menu)]


def test_tab_enters_an_inline_menu_at_its_first_item_and_leaves_from_the_last() -> None:
    """Tab into the menu focuses an item; Tab out of it moves on, without dismissing."""
    before = Checkbox()
    menu = _menu()
    after = Checkbox()
    app = _mounted_app(Column([before, menu, after]))
    app.request_focus(_focus_node(before), FocusSource.KEYBOARD)

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(menu._focusable_items[0])

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)

    # Shift+Tab back in enters at the last item.
    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(menu._focusable_items[2])

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(before)


def test_opening_a_menu_focuses_the_first_enabled_item() -> None:
    """Keyboard entry no longer depends on Tab landing on an item."""
    menu = _menu()
    app = _menu_in_overlay(menu)

    assert app._focused_node is _focus_node(menu._focusable_items[0])
    assert menu._focusable_items[0].state.focused is True


def test_an_inline_menu_does_not_take_focus() -> None:
    """Only a popup takes focus when it appears; a menu placed in the page does not."""
    menu = _menu()
    app = _mounted_app(Column([menu]))

    assert app._focused_node is None
    assert all(not item.state.focused for item in menu._focusable_items)


def test_focused_item_is_not_marked_selected() -> None:
    """Roving is focus, not selection: the focused item paints the focus layer."""
    menu = _menu()
    _menu_in_overlay(menu)
    first = menu._focusable_items[0]

    assert first.state.focused is True
    assert first._selected is False
    assert first._get_active_state_layer_opacity() == first._FOCUS_OPACITY


def test_menu_arrow_keys_rove_and_skip_disabled_items() -> None:
    """Down/Up rove between enabled items and wrap at the ends."""
    menu = _menu()
    app = _menu_in_overlay(menu)

    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(menu._focusable_items[2])  # skips "Copy"

    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(menu._focusable_items[0])  # wraps

    app._dispatch_key_press("up")
    assert app._focused_node is _focus_node(menu._focusable_items[2])


def test_tab_inside_a_menu_dismisses_it() -> None:
    """The menu is a single dismiss-on-Tab stop (WAI-ARIA popup menu)."""
    dismissed: list[bool] = []
    menu = _menu(on_dismiss=lambda: dismissed.append(True))
    app = _menu_in_overlay(menu)

    assert app._dispatch_key_press("tab") is True
    assert dismissed == [True]

    assert app._dispatch_key_press("tab", modifier_keys=SHIFT) is True
    assert dismissed == [True, True]


def test_menu_escape_still_dismisses() -> None:
    dismissed: list[bool] = []
    menu = _menu(on_dismiss=lambda: dismissed.append(True))
    _menu_in_overlay(menu)

    menu.on_key_event("escape")

    assert dismissed == [True]


def test_clicking_an_item_syncs_the_roving_index() -> None:
    """Focus arriving from a pointer keeps the menu's current member in step."""
    menu = _menu()
    app = _menu_in_overlay(menu)
    last = menu._focusable_items[2]

    _focus_node(last).request_focus(FocusSource.POINTER)

    assert menu._focus_index == 2
    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(menu._focusable_items[0])


def test_closing_a_menu_releases_focus_and_reopening_starts_over() -> None:
    """A reused menu instance (light_dismiss keeps one) re-focuses on each open."""
    menu = _menu()
    app = _menu_in_overlay(menu)

    menu._move_focus(1)
    assert app._focused_node is _focus_node(menu._focusable_items[2])

    menu.unmount()
    assert app._focused_node is None
    assert all(not item.state.focused for item in menu._focusable_items)

    menu.mount(app)
    assert app._focused_node is _focus_node(menu._focusable_items[0])


# --- Submenu (nested scope) ---------------------------------------------------


def test_right_enters_the_submenu_and_left_returns_to_its_parent_item() -> None:
    """The submenu is a nested scope: focus walks across the boundary both ways."""
    sub = SubMenuItem("Share", items=[MenuItem("Mail"), MenuItem("Chat")])
    app = _menu_in_overlay(Menu(items=[sub]))
    assert app._focused_node is _focus_node(sub)

    assert app._dispatch_key_press("right") is True
    submenu = sub._submenu
    assert submenu is not None
    assert app._focused_node is _focus_node(submenu._focusable_items[0])

    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(submenu._focusable_items[1])

    assert app._dispatch_key_press("left") is True
    assert app._focused_node is _focus_node(sub)


def test_tab_in_a_submenu_dismisses_the_whole_chain() -> None:
    """The innermost scope handles Tab, and a submenu's dismissal chains up."""
    dismissed: list[bool] = []
    sub = SubMenuItem("Share", items=[MenuItem("Mail")])
    app = _menu_in_overlay(Menu(items=[sub], on_dismiss=lambda: dismissed.append(True)))
    app._dispatch_key_press("right")
    assert sub._submenu is not None
    assert sub._submenu._focusable_items[0].state.focused is True

    assert app._dispatch_key_press("tab") is True
    assert dismissed == [True]


# --- RangeSlider --------------------------------------------------------------


def test_tab_roves_range_slider_handles_then_escapes() -> None:
    """The handles are the scope's members; Tab leaves only past the last one."""
    slider = HorizontalRangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    after = Checkbox()
    app = _mounted_app(Column([slider, after]))

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(slider)
    assert slider._active_handle_index == 0

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(slider)
    assert slider._active_handle_index == 1

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)


def test_shift_tab_enters_the_range_slider_at_its_last_handle() -> None:
    """Entry direction: Shift+Tab enters a scope at its last member."""
    slider = HorizontalRangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0)
    after = Checkbox()
    app = _mounted_app(Column([slider, after]))
    app.request_focus(_focus_node(after), FocusSource.KEYBOARD)

    app._dispatch_key_press("tab", modifier_keys=SHIFT)

    assert app._focused_node is _focus_node(slider)
    assert slider._active_handle_index == 1

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert slider._active_handle_index == 0


def test_tab_after_dragging_a_handle_roves_visibly_to_the_next_one() -> None:
    """Dragging makes the focus pointer-driven; the next Tab makes it keyboard-driven again.

    Without that, Tab moves to the second handle with the ring still suppressed —
    the focus looks lost, and the *next* Tab appears to skip the handle entirely.
    """
    slider = HorizontalRangeSlider(value_start=0.2, value_end=0.8, min_value=0.0, max_value=1.0, width=200)
    after = Checkbox()
    app = _mounted_app(Column([slider, after]))
    slider.set_layout_rect(0, 0, 200, 48)
    slider.layout(200, 48)

    app._dispatch_key_press("tab")
    assert slider.should_show_focus_ring is True

    send_pointer_event_for_test(slider, PointerEventType.PRESS, x=40.0, y=24.0)
    send_pointer_event_for_test(slider, PointerEventType.RELEASE, x=55.0, y=24.0)
    assert slider.should_show_focus_ring is False  # pointer-driven now

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(slider)
    assert slider._active_handle_index == 1
    assert slider.should_show_focus_ring is True

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)


def test_single_handle_slider_is_a_pass_through_stop() -> None:
    """A one-member scope hands Tab straight back to the global sequence."""
    slider = HorizontalSlider(value=0.5, min_value=0.0, max_value=1.0)
    after = Checkbox()
    app = _mounted_app(Column([slider, after]))

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(slider)

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)
