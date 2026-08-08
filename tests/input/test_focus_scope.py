"""Focus traversal groups: traversable vs focusable, and the FocusScope model."""

from __future__ import annotations

from nuiitivet.input.pointer import PointerEventType
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import Checkbox, Menu, MenuItem, SubMenuItem
from nuiitivet.material.button_group import ConnectedButtonGroup, GroupButton, StandardButtonGroup
from nuiitivet.material.selection_controls import RadioButton, RadioGroup
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
    Overlay.root().show(menu, passthrough=True)
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


def test_tab_enters_an_inline_menu_roves_it_and_leaves_from_the_last_item() -> None:
    """Tab walks into the menu, through its items, and out — it dismisses nothing."""
    before = Checkbox()
    menu = _menu()
    after = Checkbox()
    app = _mounted_app(Column([before, menu, after]))
    app.request_focus(_focus_node(before), FocusSource.KEYBOARD)

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(menu._focusable_items[0])

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(menu._focusable_items[2])  # skips "Copy"

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)

    # Shift+Tab back in enters at the last item and walks back out the same way.
    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(menu._focusable_items[2])

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(menu._focusable_items[0])

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


def _popup_menu_opened_with(menu: Menu, source: FocusSource) -> App:
    """Open ``menu`` as a popup as if the user had opened it with ``source``."""
    app = App(content=Container(width=400, height=400))
    app.root.mount(app)
    app._last_input_source = source
    Overlay.root().show(menu, passthrough=True)
    app.root.layout(400, 400)
    return app


def test_a_mouse_opened_menu_makes_no_item_current() -> None:
    """Like a desktop menu: opening with the pointer highlights nothing.

    Focus enters the menu — the surface holds it, so the arrows, Escape and Tab
    all reach the menu — but no item is current, so Enter has nothing to activate.
    """
    menu = _menu()
    app = _popup_menu_opened_with(menu, FocusSource.POINTER)

    assert app._focused_node is _focus_node(menu)
    assert menu._focus_index == -1
    assert all(not item.state.focused for item in menu._focusable_items)

    # The arrow keys pick the first item up from there.
    app._dispatch_key_press("down")
    first = menu._focusable_items[0]
    assert app._focused_node is _focus_node(first)
    assert first.should_show_focus_ring is True


def test_a_mouse_opened_menu_does_not_activate_an_item_on_enter() -> None:
    """Nothing is highlighted, so Enter must not fire the first item."""
    clicked: list[str] = []
    menu = Menu(items=[MenuItem("Cut", on_click=lambda: clicked.append("Cut"))])
    app = _popup_menu_opened_with(menu, FocusSource.POINTER)

    app._dispatch_key_press("enter")

    assert clicked == []


def test_a_keyboard_opened_menu_focuses_its_first_item() -> None:
    """Opening from the keyboard continues the keyboard interaction: first item, ring on."""
    menu = _menu()
    app = _popup_menu_opened_with(menu, FocusSource.KEYBOARD)
    first = menu._focusable_items[0]

    assert app._focused_node is _focus_node(first)
    assert first.should_show_focus_ring is True


def test_up_enters_a_menu_from_the_end() -> None:
    """Up enters at the last item when nothing is current yet."""
    menu = _menu()
    app = _popup_menu_opened_with(menu, FocusSource.POINTER)

    app._dispatch_key_press("up")

    assert app._focused_node is _focus_node(menu._focusable_items[2])


def test_tab_in_a_mouse_opened_menu_enters_it_rather_than_closing_it() -> None:
    """Tab is the key the user presses to be given the focus: it must land on an item."""
    dismissed: list[bool] = []
    menu = _menu(on_dismiss=lambda: dismissed.append(True))
    app = _popup_menu_opened_with(menu, FocusSource.POINTER)

    app._dispatch_key_press("tab")

    assert app._focused_node is _focus_node(menu._focusable_items[0])
    assert menu._focusable_items[0].should_show_focus_ring is True
    assert dismissed == []


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


def test_tab_roves_a_menu_and_dismisses_it_at_the_end() -> None:
    """Tab moves between the items (no wrap) and leaves the popup only past the last one."""
    dismissed: list[bool] = []
    menu = _menu(on_dismiss=lambda: dismissed.append(True))
    app = _menu_in_overlay(menu)  # keyboard-opened: the first item is current

    assert app._dispatch_key_press("tab") is True
    assert app._focused_node is _focus_node(menu._focusable_items[2])  # skips "Copy"
    assert dismissed == []

    assert app._dispatch_key_press("tab") is True  # past the last item
    assert dismissed == [True]


def test_shift_tab_at_the_first_item_dismisses_the_menu() -> None:
    dismissed: list[bool] = []
    menu = _menu(on_dismiss=lambda: dismissed.append(True))
    app = _menu_in_overlay(menu)

    assert app._dispatch_key_press("tab", modifier_keys=SHIFT) is True

    assert dismissed == [True]


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
    """A reused menu instance (the popup keeps one) re-focuses on each open."""
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


# --- RadioGroup ---------------------------------------------------------------


def _radio_group(value: object | None = None, disabled_second: bool = False) -> tuple[RadioGroup, list[RadioButton]]:
    radios = [
        RadioButton("a"),
        RadioButton("b", disabled=disabled_second),
        RadioButton("c"),
    ]
    return RadioGroup(child=Column(list(radios)), value=value), radios


def test_a_radio_group_is_a_single_tab_stop() -> None:
    """WAI-ARIA: the group is one stop, not one stop per radio."""
    before = Checkbox()
    group, _radios = _radio_group()
    app = _mounted_app(Column([before, group]))

    assert app._collect_focus_nodes() == [_focus_node(before), _focus_node(group)]


def test_tab_enters_a_radio_group_at_its_selected_radio() -> None:
    """The selected radio is the group's stop — not the first one."""
    group, radios = _radio_group(value="c")
    app = _mounted_app(Column([group]))

    app._dispatch_key_press("tab")

    assert app._focused_node is _focus_node(radios[2])


def test_tab_enters_an_unselected_radio_group_at_its_first_radio() -> None:
    """With nothing selected there is no selected radio to enter at."""
    group, radios = _radio_group()
    app = _mounted_app(Column([group]))

    app._dispatch_key_press("tab")

    assert app._focused_node is _focus_node(radios[0])


def test_radio_arrow_keys_rove_and_move_the_selection_with_the_focus() -> None:
    """Selection follows focus (WAI-ARIA), on both axes, wrapping at the ends."""
    changed: list[object | None] = []
    radios = [RadioButton("a"), RadioButton("b"), RadioButton("c")]
    group = RadioGroup(child=Column(list(radios)), value="a", on_change=changed.append)
    app = _mounted_app(Column([group]))
    app._dispatch_key_press("tab")

    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(radios[1])
    assert group.value == "b"

    # Either axis roves: a radio group may be laid out as a Row or a Column.
    app._dispatch_key_press("right")
    assert app._focused_node is _focus_node(radios[2])
    assert group.value == "c"

    # The ends wrap.
    app._dispatch_key_press("down")
    assert app._focused_node is _focus_node(radios[0])
    assert group.value == "a"

    app._dispatch_key_press("up")
    assert app._focused_node is _focus_node(radios[2])
    assert group.value == "c"

    assert changed == ["b", "c", "a", "c"]


def test_radio_arrow_keys_skip_a_disabled_radio() -> None:
    """A disabled radio is not selectable, so roving must not stop on it."""
    group, radios = _radio_group(value="a", disabled_second=True)
    app = _mounted_app(Column([group]))
    app._dispatch_key_press("tab")

    app._dispatch_key_press("down")

    assert app._focused_node is _focus_node(radios[2])
    assert group.value == "c"


def test_tab_leaves_a_radio_group_rather_than_roving_it() -> None:
    """Tab is how the group is left; the arrows are how it is roved."""
    group, radios = _radio_group(value="a")
    after = Checkbox()
    app = _mounted_app(Column([group, after]))

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(radios[0])

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(radios[0])


def test_a_radio_outside_a_group_stays_an_ordinary_tab_stop() -> None:
    """Only group membership takes a radio out of the global sequence."""
    radio = RadioButton("a")
    app = _mounted_app(Column([radio]))

    assert app._collect_focus_nodes() == [_focus_node(radio)]


# --- ButtonGroup --------------------------------------------------------------


def test_a_button_group_is_a_single_tab_stop() -> None:
    """Both group types are one stop, entered at the first item."""
    items = [GroupButton(label="One"), GroupButton(label="Two"), GroupButton(label="Three")]
    group = ConnectedButtonGroup(items=items)
    app = _mounted_app(Column([group]))

    assert app._collect_focus_nodes() == [_focus_node(group)]

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(items[0])


def test_button_group_arrows_rove_and_stop_at_the_edges() -> None:
    """The toolbar pattern: Left/Right rove the items, and the ends do not wrap."""
    items = [GroupButton(label="One"), GroupButton(label="Two"), GroupButton(label="Three")]
    group = StandardButtonGroup(items=items)
    app = _mounted_app(Column([group]))
    app._dispatch_key_press("tab")

    app._dispatch_key_press("left")
    assert app._focused_node is _focus_node(items[0])  # already at the first item

    app._dispatch_key_press("right")
    assert app._focused_node is _focus_node(items[1])

    app._dispatch_key_press("right")
    assert app._focused_node is _focus_node(items[2])

    app._dispatch_key_press("right")
    assert app._focused_node is _focus_node(items[2])  # stops at the last item


def test_button_group_selection_does_not_follow_the_focus() -> None:
    """Unlike a radio group, roving a button group toggles nothing: Enter does."""
    toggled: list[tuple[str, bool]] = []
    items = [
        GroupButton(label="One", on_change=lambda v: toggled.append(("One", v))),
        GroupButton(label="Two", on_change=lambda v: toggled.append(("Two", v))),
    ]
    group = StandardButtonGroup(items=items)
    app = _mounted_app(Column([group]))

    app._dispatch_key_press("tab")
    app._dispatch_key_press("right")
    assert toggled == []

    app._dispatch_key_press("enter")
    assert toggled == [("Two", True)]


def test_tab_leaves_a_button_group_rather_than_roving_it() -> None:
    """Tab is a boundary for the group: it leaves for the next widget."""
    items = [GroupButton(label="One"), GroupButton(label="Two")]
    group = ConnectedButtonGroup(items=items)
    after = Checkbox()
    app = _mounted_app(Column([group, after]))

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(items[0])

    app._dispatch_key_press("tab")
    assert app._focused_node is _focus_node(after)

    app._dispatch_key_press("tab", modifier_keys=SHIFT)
    assert app._focused_node is _focus_node(items[1])  # Shift+Tab enters at the last item
