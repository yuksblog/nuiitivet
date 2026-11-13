"""The semantics tree: what a window says to assistive technology."""

from __future__ import annotations

from typing import Optional

from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import Checkbox, Menu, MenuItem, Switch, Text, TextField
from nuiitivet.material.buttons import Button, IconButton, ToggleButton
from nuiitivet.material.selection_controls import RadioButton, RadioGroup
from nuiitivet.material.slider import HorizontalRangeSlider, HorizontalSlider
from nuiitivet.modifiers.semantics import semantics
from nuiitivet.modifiers.visible import visible
from nuiitivet.observable import State
from nuiitivet.runtime.app import App
from nuiitivet.runtime.semantics_tree import ROOT_ID, SemanticsEntry, SemanticsTree
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.interaction import FocusNode, FocusSource
from nuiitivet.widgets.semantics import SemanticsAction, SemanticsRole, ToggleState


def _mounted(root) -> Window:
    window = App(Window(content=root, title="Demo")).main_window
    assert window.root is not None
    window.root.mount(window)
    window.root.layout(400, 400)
    return window


def _entries(tree: SemanticsTree, parent: int = ROOT_ID) -> list[SemanticsEntry]:
    return [tree.entries[child] for child in tree.entries[parent].children]


def _only(tree: SemanticsTree, role: SemanticsRole, label: Optional[str] = None) -> SemanticsEntry:
    found = [
        entry
        for entry in tree.entries.values()
        if entry.semantics.role is role and (label is None or entry.semantics.label == label)
    ]
    assert len(found) == 1, found
    return found[0]


def _handles(tree: SemanticsTree) -> list[SemanticsEntry]:
    """The entries beneath the one range slider at the top of ``tree``."""
    (slider,) = _entries(tree)
    assert slider.semantics.role is SemanticsRole.GROUP
    return _entries(tree, slider.id)


def _focus_node(widget) -> FocusNode:
    node = widget.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    return node


# --- what a widget says -------------------------------------------------------


def test_the_window_is_the_root_entry_and_carries_its_title() -> None:
    tree = _mounted(Column([])).semantics_tree()

    root = tree.entries[ROOT_ID]
    assert root.semantics.label == "Demo"
    assert tree.focus == ROOT_ID


def test_a_button_takes_its_text_as_its_label_and_the_text_has_no_entry() -> None:
    tree = _mounted(Column([Button("Save", on_click=lambda: None)])).semantics_tree()

    (entry,) = _entries(tree)
    assert entry.semantics.role is SemanticsRole.BUTTON
    assert entry.semantics.label == "Save"
    assert entry.children == ()


def test_a_text_on_its_own_is_an_entry() -> None:
    tree = _mounted(Column([Text("Hello"), Text("")])).semantics_tree()

    (entry,) = _entries(tree)
    assert entry.semantics.role is SemanticsRole.TEXT
    assert entry.semantics.label == "Hello"


def test_an_entry_carries_the_rect_the_widget_is_painted_at() -> None:
    button = Button("Save", on_click=lambda: None)
    window = _mounted(Column([Text("Title"), button]))

    entry = _only(window.semantics_tree(), SemanticsRole.BUTTON)

    painted = button.global_visual_rect
    assert painted is not None
    assert entry.rect == tuple(float(v) for v in painted)
    assert entry.rect[1] > 0


def test_semantics_labels_a_control_that_has_no_text() -> None:
    close = IconButton("close", on_click=lambda: None).modifier(semantics(label="Close"))

    tree = _mounted(Column([close])).semantics_tree()

    assert _only(tree, SemanticsRole.BUTTON).semantics.label == "Close"


def test_semantics_on_a_layout_makes_it_one_group_that_hides_its_text() -> None:
    cart = Column([Text("3"), Text("items")]).modifier(semantics(label="Cart, 3 items"))

    tree = _mounted(Column([cart])).semantics_tree()

    (entry,) = _entries(tree)
    assert entry.semantics.role is SemanticsRole.GROUP
    assert entry.semantics.label == "Cart, 3 items"
    assert entry.children == ()


def test_semantics_follows_an_state_label() -> None:
    label = State("Unread: 1")
    window = _mounted(Column([Column([]).modifier(semantics(label=label, role=SemanticsRole.IMAGE))]))

    label.value = "Unread: 2"

    assert _only(window.semantics_tree(), SemanticsRole.IMAGE).semantics.label == "Unread: 2"


def test_a_later_semantics_keeps_what_an_earlier_one_wrote() -> None:
    button = IconButton("close", on_click=lambda: None)
    close = button.modifier(semantics(label="Close")).modifier(semantics(role=SemanticsRole.IMAGE))

    tree = _mounted(Column([close])).semantics_tree()

    assert _only(tree, SemanticsRole.IMAGE).semantics.label == "Close"


def test_a_control_without_a_click_handler_is_still_a_button() -> None:
    tree = _mounted(Column([Button("Save")])).semantics_tree()

    assert _only(tree, SemanticsRole.BUTTON).semantics.label == "Save"


def test_toggles_say_their_role_and_state() -> None:
    tree = _mounted(
        Column(
            [
                Checkbox(indeterminate=True),
                Switch(checked=True),
                ToggleButton("Bold", selected=False),
            ]
        )
    ).semantics_tree()

    checkbox, switch, toggle = _entries(tree)
    assert (checkbox.semantics.role, checkbox.semantics.toggled) == (SemanticsRole.CHECKBOX, ToggleState.MIXED)
    assert (switch.semantics.role, switch.semantics.toggled) == (SemanticsRole.SWITCH, ToggleState.ON)
    assert (toggle.semantics.role, toggle.semantics.toggled) == (SemanticsRole.BUTTON, ToggleState.OFF)
    assert toggle.semantics.label == "Bold"


def test_a_text_field_is_one_entry_with_its_label_and_text() -> None:
    tree = _mounted(Column([TextField(value="Ada", label="Name")])).semantics_tree()

    entry = _only(tree, SemanticsRole.TEXT_FIELD)
    assert entry.semantics.label == "Name"
    assert entry.semantics.value == "Ada"
    assert SemanticsAction.FOCUS in entry.actions


def test_a_masked_text_field_never_says_its_text() -> None:
    tree = _mounted(Column([TextField(value="secret", label="Password", obscure_text=True)])).semantics_tree()

    assert _only(tree, SemanticsRole.TEXT_FIELD).semantics.value == "••••••"


def test_a_slider_says_its_value_and_range() -> None:
    tree = _mounted(Column([HorizontalSlider(value=30.0, min_value=0.0, max_value=100.0)])).semantics_tree()

    said = _only(tree, SemanticsRole.SLIDER).semantics
    assert (said.numeric_value, said.min_value, said.max_value) == (30.0, 0.0, 100.0)


# --- what is in the tree ------------------------------------------------------


def test_a_disabled_control_stays_in_the_tree_and_takes_no_action() -> None:
    tree = _mounted(Column([Button("Save", on_click=lambda: None, disabled=True)])).semantics_tree()

    entry = _only(tree, SemanticsRole.BUTTON, "Save")
    assert entry.semantics.disabled is True
    assert entry.actions == frozenset()


def test_hidden_content_is_not_in_the_tree() -> None:
    hidden = Button("Hidden", on_click=lambda: None).modifier(visible(False))

    tree = _mounted(Column([hidden, Button("Shown", on_click=lambda: None)])).semantics_tree()

    assert [entry.semantics.label for entry in _entries(tree)] == ["Shown"]


def test_a_closed_section_with_a_label_keeps_its_entry_and_hides_what_is_inside() -> None:
    section = Collapsible(Column([Text("Body"), Button("Inside", on_click=lambda: None)]), opened=False)

    tree = _mounted(Column([section.modifier(semantics(label="Details"))])).semantics_tree()

    (entry,) = _entries(tree)
    assert entry.semantics.label == "Details"
    assert entry.children == ()
    assert len(tree.entries) == 2


def test_a_text_field_and_its_icon_are_one_field_with_a_button_inside() -> None:
    field = TextField(value="", label="Search", trailing_icon="close", on_tap_trailing_icon=lambda: None)

    tree = _mounted(Column([field])).semantics_tree()

    (entry,) = _entries(tree)
    assert entry.semantics.role is SemanticsRole.TEXT_FIELD
    (icon,) = _entries(tree, entry.id)
    assert icon.semantics.role is SemanticsRole.BUTTON


def test_an_open_modal_is_the_whole_tree() -> None:
    window = _mounted(Column([Button("Behind", on_click=lambda: None)]))
    window.overlay.show(Button("In front", on_click=lambda: None))
    window.root.layout(400, 400)

    tree = window.semantics_tree()

    assert [entry.semantics.label for entry in _entries(tree)] == ["In front"]


def test_an_entry_keeps_its_id_across_builds() -> None:
    window = _mounted(Column([Button("Save", on_click=lambda: None)]))

    first = _only(window.semantics_tree(), SemanticsRole.BUTTON)
    second = _only(window.semantics_tree(), SemanticsRole.BUTTON)

    assert first.id == second.id


# --- focus --------------------------------------------------------------------


def test_the_focused_entry_follows_tab() -> None:
    window = _mounted(Column([Button("One", on_click=lambda: None), Button("Two", on_click=lambda: None)]))

    window._dispatch_key_press("tab")
    assert window.semantics_tree().focus == _only(window.semantics_tree(), SemanticsRole.BUTTON, "One").id

    window._dispatch_key_press("tab")
    assert window.semantics_tree().focus == _only(window.semantics_tree(), SemanticsRole.BUTTON, "Two").id


def test_the_focused_entry_follows_the_members_of_a_radio_group() -> None:
    first, second = RadioButton("a"), RadioButton("b")
    group = RadioGroup(Column([first, second]), value="a")
    window = _mounted(Column([group]))

    window._dispatch_key_press("tab")
    tree = window.semantics_tree()
    group_entry = _only(tree, SemanticsRole.RADIO_GROUP)
    radios = _entries(tree, group_entry.id)
    assert [radio.semantics.toggled for radio in radios] == [ToggleState.ON, ToggleState.OFF]
    assert tree.focus == radios[0].id

    window._dispatch_key_press("down")
    tree = window.semantics_tree()
    radios = _entries(tree, group_entry.id)
    assert [radio.semantics.toggled for radio in radios] == [ToggleState.OFF, ToggleState.ON]
    assert tree.focus == radios[1].id


def test_a_range_slider_has_an_entry_per_handle_with_its_own_label() -> None:
    slider = HorizontalRangeSlider(value_start=20.0, value_end=80.0, min_value=0.0, max_value=100.0)
    named = slider.modifier(semantics(label=["Lowest price", "Highest price"]))

    tree = _mounted(Column([named])).semantics_tree()

    start, end = _handles(tree)
    assert (start.semantics.role, start.semantics.label, start.semantics.numeric_value) == (
        SemanticsRole.SLIDER,
        "Lowest price",
        20.0,
    )
    assert (end.semantics.label, end.semantics.numeric_value) == ("Highest price", 80.0)
    # Each handle stops at the other.
    assert (start.semantics.max_value, end.semantics.min_value) == (80.0, 20.0)


def test_a_range_slider_names_its_handles_itself_until_a_list_names_them() -> None:
    tree = _mounted(Column([HorizontalRangeSlider(value_start=0.2, value_end=0.8)])).semantics_tree()

    assert [handle.semantics.label for handle in _handles(tree)] == ["Range start", "Range end"]


def test_a_list_of_labels_names_the_parts_and_leaves_the_widget_unnamed() -> None:
    slider = HorizontalRangeSlider(value_start=0.2, value_end=0.8).modifier(semantics(label=["Low"]))

    tree = _mounted(Column([slider])).semantics_tree()

    (group,) = _entries(tree)
    assert group.semantics.label is None
    assert [handle.semantics.label for handle in _handles(tree)] == ["Low", "Range end"]


def test_the_focused_entry_follows_the_handles_of_a_range_slider() -> None:
    slider = HorizontalRangeSlider(value_start=0.2, value_end=0.8)
    window = _mounted(Column([slider]))
    start, end = _handles(window.semantics_tree())

    window._dispatch_key_press("tab")
    assert window.semantics_tree().focus == start.id

    window._dispatch_key_press("tab")
    assert window.semantics_tree().focus == end.id


def test_a_menu_opened_by_the_pointer_focuses_the_menu_itself() -> None:
    menu = Menu(items=[MenuItem("Cut"), MenuItem("Copy", disabled=True), MenuItem("Paste")])
    window = _mounted(Container(width=400, height=400))
    window._last_input_source = FocusSource.POINTER
    window.overlay.show(menu, passthrough=True)
    window.root.layout(400, 400)

    tree = window.semantics_tree()

    menu_entry = _only(tree, SemanticsRole.MENU)
    items = _entries(tree, menu_entry.id)
    assert [(item.semantics.role, item.semantics.label) for item in items] == [
        (SemanticsRole.MENU_ITEM, "Cut"),
        (SemanticsRole.MENU_ITEM, "Copy"),
        (SemanticsRole.MENU_ITEM, "Paste"),
    ]
    assert items[1].semantics.disabled is True
    assert tree.focus == menu_entry.id


def test_a_menu_opened_from_the_keyboard_focuses_its_first_item() -> None:
    menu = Menu(items=[MenuItem("Cut"), MenuItem("Paste")])
    window = _mounted(Container(width=400, height=400))
    window.overlay.show(menu, passthrough=True)
    window.root.layout(400, 400)

    tree = window.semantics_tree()

    assert tree.focus == _only(tree, SemanticsRole.MENU_ITEM, "Cut").id


# --- actions ------------------------------------------------------------------


def test_activate_runs_the_click_and_counts_as_keyboard_input() -> None:
    clicks: list[bool] = []
    window = _mounted(Column([Button("Save", on_click=lambda: clicks.append(True))]))
    window._last_input_source = FocusSource.POINTER
    entry = _only(window.semantics_tree(), SemanticsRole.BUTTON)

    assert window.perform_semantics_action(entry.id, SemanticsAction.ACTIVATE) is True

    assert clicks == [True]
    assert window._last_input_source is FocusSource.KEYBOARD


def test_focus_moves_the_focus_to_the_entry() -> None:
    two = Button("Two", on_click=lambda: None)
    window = _mounted(Column([Button("One", on_click=lambda: None), two]))
    entry = _only(window.semantics_tree(), SemanticsRole.BUTTON, "Two")

    assert window.perform_semantics_action(entry.id, SemanticsAction.FOCUS) is True

    assert window._focused_node is _focus_node(two)
    assert two.should_show_focus_ring is True


def test_increment_on_a_handle_moves_that_handle() -> None:
    changes: list[tuple[float, float]] = []
    slider = HorizontalRangeSlider(
        value_start=20.0, value_end=60.0, min_value=0.0, max_value=100.0, on_change=changes.append
    )
    window = _mounted(Column([slider]))
    _, end = _handles(window.semantics_tree())

    assert window.perform_semantics_action(end.id, SemanticsAction.INCREMENT) is True

    assert slider.value_start == 20.0
    assert slider.value_end > 60.0
    assert changes == [(20.0, slider.value_end)]


def test_an_action_the_entry_does_not_take_is_refused() -> None:
    clicks: list[bool] = []
    window = _mounted(Column([Button("Save", on_click=lambda: clicks.append(True), disabled=True), Text("Note")]))
    tree = window.semantics_tree()

    assert window.perform_semantics_action(_only(tree, SemanticsRole.BUTTON).id, SemanticsAction.ACTIVATE) is False
    assert window.perform_semantics_action(_only(tree, SemanticsRole.TEXT).id, SemanticsAction.ACTIVATE) is False
    assert window.perform_semantics_action(10**9, SemanticsAction.ACTIVATE) is False
    assert clicks == []
