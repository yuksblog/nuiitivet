"""Material widgets must adopt the *theme's* style, not a frozen default.

Resolving a style in ``__init__`` cannot work: the widget has no parent yet, so
``Theme.of`` cannot reach the ``AppScope`` and silently returns the light
default. The style therefore has to be adopted once the widget is attached --
and it has to keep following the theme after that. See issue #473.

The other half is #475: a widget whose style accessor never consults the theme
at all is just as wrong, only more quietly -- an app installing a customised
``MaterialThemeData`` cannot restyle it globally. Both halves are checked here,
because the fix is the same pull: the widget reads the theme where the style is
consumed (``build`` if it has one, otherwise ``preferred_size`` / ``paint``) and
never holds the result. See ``docs/design/THEME_CONSUMPTION.md``.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterator

import pytest

from nuiitivet.common.logging_once import set_log_once_enabled
from nuiitivet.material.buttons import (
    Button,
    ExtendedFab,
    Fab,
    IconButton,
    IconToggleButton,
    ToggleButton,
)
from nuiitivet.material.button_group import (
    ConnectedButtonGroup,
    GroupButton,
    StandardButtonGroup,
)
from nuiitivet.material.card import Card
from nuiitivet.material.chip import AssistChip, FilterChip, InputChip, SuggestionChip
from nuiitivet.material.menu import Menu, MenuItem
from nuiitivet.material.selection_controls import Checkbox, RadioButton, Switch
from nuiitivet.material.styles.button_group_style import (
    ConnectedButtonGroupStyle,
    StandardButtonGroupStyle,
)
from nuiitivet.material.styles.button_style import IconToggleButtonStyle
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material.styles.chip_style import ChipStyle
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
from nuiitivet.material.styles.toolbar_style import ToolbarStyle
from nuiitivet.material.text import Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.material.toolbar import (
    DockedToolbar,
    HorizontalFloatingToolbar,
    VerticalFloatingToolbar,
)
from nuiitivet.testing import WidgetHost, mount
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import Widget

_THEME_LOGGER = "nuiitivet.theme.theme"


def _theme_with(**theme_data_fields) -> Theme:
    """Build a light theme whose Material data carries the given overrides."""
    return Theme(
        mode="light",
        extensions=[MaterialThemeData(roles={}, **theme_data_fields)],
    )


_HOSTS: list[WidgetHost] = []


@pytest.fixture(autouse=True)
def _close_hosts() -> Iterator[None]:
    """Unmount whatever ``_mount`` built, whether the test passed or failed."""
    try:
        yield
    finally:
        while _HOSTS:
            _HOSTS.pop().close()


def _mount(widget: Widget, theme: Theme) -> ThemeManager:
    """Attach ``widget`` under an ``AppScope`` serving ``theme``.

    A thin adapter over :func:`nuiitivet.testing.mount`, which is the object this
    module used to hand-roll -- a stub app, an ``AppScope`` built by hand, and
    the scope stashed on the widget to keep it alive, with two ``type: ignore``s
    for the stub that was not an ``App``. What is left here is only the return
    value this file's vocabulary wants: the manager, so a test can push a
    *later* theme through it and assert the widget followed.
    """
    host = mount(widget, theme=theme)
    _HOSTS.append(host)
    return host.theme_manager


# --- Card -------------------------------------------------------------------

_CUSTOM_CARD_STYLE = CardStyle(
    background=ColorRole.TERTIARY_CONTAINER,
    border_color=ColorRole.TERTIARY,
    border_width=3.0,
    border_radius=28.0,
    elevation=4,
)


def test_card_adopts_the_themes_filled_card_style() -> None:
    card = Card(None)
    _mount(card, _theme_with(_filled_card_style=_CUSTOM_CARD_STYLE))

    assert card.style == _CUSTOM_CARD_STYLE
    assert card.corner_radius == 28.0
    assert card.border_width == 3.0
    assert card.bgcolor == ColorRole.TERTIARY_CONTAINER
    # Elevation 4 must reach the Box as a real shadow, not stay in the style.
    assert card.shadow_blur > 0


def test_card_uses_the_preset_before_it_is_mounted() -> None:
    card = Card(None)

    assert card.style == CardStyle.filled()


def test_card_explicit_style_wins_over_the_theme() -> None:
    explicit = CardStyle.outlined()
    card = Card(None, style=explicit)
    _mount(card, _theme_with(_filled_card_style=_CUSTOM_CARD_STYLE))

    assert card.style == explicit
    assert card.corner_radius == explicit.border_radius


def test_card_follows_a_later_theme_change() -> None:
    card = Card(None)
    manager = _mount(card, _theme_with())
    assert card.corner_radius == CardStyle.filled().border_radius

    manager.set_theme(_theme_with(_filled_card_style=_CUSTOM_CARD_STYLE))

    assert card.style == _CUSTOM_CARD_STYLE
    assert card.corner_radius == 28.0


# --- Chips ------------------------------------------------------------------

_CUSTOM_CHIP_STYLE = ChipStyle(
    background=ColorRole.TERTIARY_CONTAINER,
    foreground=ColorRole.ON_TERTIARY_CONTAINER,
    border_color=ColorRole.TERTIARY,
    border_width=2.0,
    corner_radius=20,
    container_height=40,
)

_CHIP_CASES: list[tuple[str, str, Callable[[], Widget]]] = [
    ("assist", "_assist_chip_style", lambda: AssistChip("a")),
    ("filter", "_filter_chip_style", lambda: FilterChip("a")),
    ("input", "_input_chip_style", lambda: InputChip("a", trailing_icon="close")),
    ("suggestion", "_suggestion_chip_style", lambda: SuggestionChip("a")),
]


@pytest.mark.parametrize(
    "variant,field,factory",
    _CHIP_CASES,
    ids=[variant for variant, _, _ in _CHIP_CASES],
)
def test_chip_adopts_the_themes_variant_style(variant, field, factory) -> None:
    chip = factory()
    _mount(chip, _theme_with(**{field: _CUSTOM_CHIP_STYLE}))

    assert chip.style == _CUSTOM_CHIP_STYLE
    assert chip.corner_radius == 20
    assert chip.border_width == 2.0
    assert chip.bgcolor == ColorRole.TERTIARY_CONTAINER
    assert int(chip.height_sizing.value) == 40


@pytest.mark.parametrize(
    "variant,field,factory",
    _CHIP_CASES,
    ids=[variant for variant, _, _ in _CHIP_CASES],
)
def test_chip_uses_the_variant_preset_before_it_is_mounted(variant, field, factory) -> None:
    chip = factory()

    assert chip.style == ChipStyle.preset(variant)


def test_chip_content_is_rebuilt_for_the_themes_style() -> None:
    """The label colour comes from the style, so content -- not just the
    container -- must be rebuilt when the theme supplies a different one."""
    chip = AssistChip("a")
    _mount(chip, _theme_with(_assist_chip_style=_CUSTOM_CHIP_STYLE))
    chip.preferred_size()

    content = chip.children_snapshot()[0]
    row = content.children_snapshot()[0]
    label = row.children_snapshot()[0]

    assert isinstance(label, Text)
    assert label.style.color == ColorRole.ON_TERTIARY_CONTAINER


def test_filter_chip_keeps_selected_visuals_over_the_themes_style() -> None:
    selected_style = _CUSTOM_CHIP_STYLE.copy_with(
        selected_background=ColorRole.SECONDARY_CONTAINER,
        selected_border_color=ColorRole.SECONDARY,
    )
    chip = FilterChip("a", selected=True)
    _mount(chip, _theme_with(_filter_chip_style=selected_style))
    chip.preferred_size()

    assert chip.selected is True
    assert chip.bgcolor == ColorRole.SECONDARY_CONTAINER
    assert chip.border_color == ColorRole.SECONDARY
    # The rest of the container still comes from the theme's style.
    assert chip.corner_radius == 20


def test_chip_explicit_style_wins_over_the_theme() -> None:
    explicit = ChipStyle.assist().copy_with(corner_radius=4)
    chip = AssistChip("a", style=explicit)
    _mount(chip, _theme_with(_assist_chip_style=_CUSTOM_CHIP_STYLE))

    assert chip.style == explicit
    assert chip.corner_radius == 4


def test_chip_follows_a_later_theme_change() -> None:
    chip = AssistChip("a")
    manager = _mount(chip, _theme_with())
    assert chip.corner_radius == ChipStyle.assist().corner_radius

    manager.set_theme(_theme_with(_assist_chip_style=_CUSTOM_CHIP_STYLE))

    assert chip.style == _CUSTOM_CHIP_STYLE
    assert chip.corner_radius == 20


# --- TextField --------------------------------------------------------------


def test_text_field_adopts_the_themes_style_and_hands_it_to_the_editable() -> None:
    custom = TextFieldStyle.filled().copy_with(
        text_color=ColorRole.ON_TERTIARY_CONTAINER,
        cursor_color=ColorRole.TERTIARY,
        selection_color=ColorRole.TERTIARY_CONTAINER,
    )
    field = TextField(label="a")
    _mount(field, _theme_with(_filled_text_field_style=custom))

    assert field.style == custom
    # The editable was built from the preset, so mounting has to hand it the
    # theme's colours or the text would stay the preset's forever.
    assert field._editable.text_color == ColorRole.ON_TERTIARY_CONTAINER
    assert field._editable.cursor_color == ColorRole.TERTIARY
    assert field._editable.selection_color == ColorRole.TERTIARY_CONTAINER


def test_text_field_uses_the_preset_before_it_is_mounted() -> None:
    assert TextField(label="a").style == TextFieldStyle.filled()


# --- FABs -------------------------------------------------------------------

_CUSTOM_FAB_STYLE = FabStyle.primary().copy_with(
    background=ColorRole.TERTIARY_CONTAINER,
    foreground=ColorRole.ON_TERTIARY_CONTAINER,
    corner_radius=8.0,
)


def test_fab_adopts_the_themes_fab_style() -> None:
    fab = Fab("star")
    _mount(fab, _theme_with(_fab_style=_CUSTOM_FAB_STYLE))

    assert fab.style == _CUSTOM_FAB_STYLE
    fab.preferred_size()
    assert fab.corner_radius == 8.0


def test_fab_uses_the_preset_before_it_is_mounted() -> None:
    assert Fab("star").style == FabStyle.preset()


def test_fab_explicit_style_wins_over_the_theme() -> None:
    explicit = FabStyle.secondary()
    fab = Fab("star", style=explicit)
    _mount(fab, _theme_with(_fab_style=_CUSTOM_FAB_STYLE))

    assert fab.style == explicit


def test_fab_follows_a_later_theme_change() -> None:
    fab = Fab("star")
    manager = _mount(fab, _theme_with())
    assert fab.style == FabStyle.preset()

    manager.set_theme(_theme_with(_fab_style=_CUSTOM_FAB_STYLE))

    assert fab.style == _CUSTOM_FAB_STYLE


def test_extended_fab_adopts_the_themes_fab_style() -> None:
    """The theme carries the *circular* FAB style, so the pill has to keep its
    own size tokens while taking the theme's colours."""
    fab = ExtendedFab("a")
    _mount(fab, _theme_with(_fab_style=_CUSTOM_FAB_STYLE))

    assert fab.style.background == ColorRole.TERTIARY_CONTAINER
    assert fab.style.foreground == ColorRole.ON_TERTIARY_CONTAINER
    # Extended-FAB metrics, not the circular ones the theme's style carries.
    assert fab.style == fab._adapt_style(_CUSTOM_FAB_STYLE)


def test_extended_fab_uses_the_preset_before_it_is_mounted() -> None:
    fab = ExtendedFab("a")

    assert fab.style == fab._adapt_style(FabStyle.preset())


# --- Toggle buttons ---------------------------------------------------------

_CUSTOM_TOGGLE_STYLE = ToggleButtonStyle.filled("s").copy_with(
    unselected_background=ColorRole.TERTIARY_CONTAINER,
    unselected_foreground=ColorRole.ON_TERTIARY_CONTAINER,
    selected_background=ColorRole.TERTIARY,
    selected_foreground=ColorRole.ON_TERTIARY,
    corner_radius=6,
)


def test_toggle_button_adopts_the_themes_style() -> None:
    button = ToggleButton("a")
    _mount(button, _theme_with(_toggle_button_style=_CUSTOM_TOGGLE_STYLE))

    assert button.style == _CUSTOM_TOGGLE_STYLE.for_selected(False)
    assert button.style.background == ColorRole.TERTIARY_CONTAINER


def test_toggle_button_adopts_the_themes_selected_colours() -> None:
    button = ToggleButton("a", selected=True)
    _mount(button, _theme_with(_toggle_button_style=_CUSTOM_TOGGLE_STYLE))

    assert button.style.background == ColorRole.TERTIARY
    assert button.style.foreground == ColorRole.ON_TERTIARY


def test_toggle_button_uses_the_preset_before_it_is_mounted() -> None:
    assert ToggleButton("a").style == ToggleButtonStyle.preset().for_selected(False)


def test_toggle_button_explicit_style_wins_over_the_theme() -> None:
    explicit = ToggleButtonStyle.outlined("s")
    button = ToggleButton("a", style=explicit)
    _mount(button, _theme_with(_toggle_button_style=_CUSTOM_TOGGLE_STYLE))

    assert button.style == explicit.for_selected(False)


def test_toggle_button_follows_a_later_theme_change() -> None:
    button = ToggleButton("a")
    manager = _mount(button, _theme_with())
    assert button.style == ToggleButtonStyle.preset().for_selected(False)

    manager.set_theme(_theme_with(_toggle_button_style=_CUSTOM_TOGGLE_STYLE))

    assert button.style == _CUSTOM_TOGGLE_STYLE.for_selected(False)


_STANDARD_ICON_TOGGLE = IconToggleButtonStyle.standard()
_CUSTOM_ICON_TOGGLE_STYLE = IconToggleButtonStyle(
    selected=_STANDARD_ICON_TOGGLE.selected.copy_with(background=ColorRole.TERTIARY),
    unselected=_STANDARD_ICON_TOGGLE.unselected.copy_with(foreground=ColorRole.TERTIARY),
)


def test_icon_toggle_button_adopts_the_themes_style() -> None:
    button = IconToggleButton("star")
    _mount(button, _theme_with(_icon_toggle_button_style=_CUSTOM_ICON_TOGGLE_STYLE))

    assert button.style == _CUSTOM_ICON_TOGGLE_STYLE.unselected
    assert button.style.foreground == ColorRole.TERTIARY


def test_icon_toggle_button_uses_the_preset_before_it_is_mounted() -> None:
    assert IconToggleButton("star").style == IconToggleButtonStyle.preset().unselected


def test_icon_toggle_button_explicit_style_wins_over_the_theme() -> None:
    explicit = IconToggleButtonStyle.filled("s")
    button = IconToggleButton("star", style=explicit)
    _mount(button, _theme_with(_icon_toggle_button_style=_CUSTOM_ICON_TOGGLE_STYLE))

    assert button.style == explicit.unselected


def test_icon_toggle_button_follows_a_later_theme_change() -> None:
    button = IconToggleButton("star")
    manager = _mount(button, _theme_with())
    assert button.style == IconToggleButtonStyle.preset().unselected

    manager.set_theme(_theme_with(_icon_toggle_button_style=_CUSTOM_ICON_TOGGLE_STYLE))

    assert button.style == _CUSTOM_ICON_TOGGLE_STYLE.unselected


# --- Toolbars ---------------------------------------------------------------

_CUSTOM_TOOLBAR_STYLE = ToolbarStyle.standard().copy_with(
    background=ColorRole.TERTIARY_CONTAINER,
    foreground=ColorRole.ON_TERTIARY_CONTAINER,
    container_height=72,
    item_gap=20,
    corner_radius=16,
)

_TOOLBAR_CASES: list[tuple[str, Callable[..., Widget]]] = [
    ("DockedToolbar", lambda style=None: DockedToolbar([IconButton("add")], style=style)),
    (
        "HorizontalFloatingToolbar",
        lambda style=None: HorizontalFloatingToolbar([IconButton("add")], style=style),
    ),
    (
        "VerticalFloatingToolbar",
        lambda style=None: VerticalFloatingToolbar([IconButton("add")], style=style),
    ),
]


@pytest.mark.parametrize("name,factory", _TOOLBAR_CASES, ids=[name for name, _ in _TOOLBAR_CASES])
def test_toolbar_adopts_the_themes_style(name, factory) -> None:
    toolbar = factory()
    _mount(toolbar, _theme_with(_toolbar_style=_CUSTOM_TOOLBAR_STYLE))
    toolbar.preferred_size()

    assert toolbar.style == _CUSTOM_TOOLBAR_STYLE


@pytest.mark.parametrize("name,factory", _TOOLBAR_CASES, ids=[name for name, _ in _TOOLBAR_CASES])
def test_toolbar_uses_the_preset_before_it_is_mounted(name, factory) -> None:
    assert factory().style == ToolbarStyle.preset()


@pytest.mark.parametrize("name,factory", _TOOLBAR_CASES, ids=[name for name, _ in _TOOLBAR_CASES])
def test_toolbar_explicit_style_wins_over_the_theme(name, factory) -> None:
    explicit = ToolbarStyle.vibrant()
    toolbar = factory(explicit)
    _mount(toolbar, _theme_with(_toolbar_style=_CUSTOM_TOOLBAR_STYLE))
    toolbar.preferred_size()

    assert toolbar.style == explicit


def test_docked_toolbar_pushes_the_themes_style_onto_the_container() -> None:
    toolbar = DockedToolbar([IconButton("add")])
    _mount(toolbar, _theme_with(_toolbar_style=_CUSTOM_TOOLBAR_STYLE))
    toolbar.preferred_size()

    assert toolbar.bgcolor == ColorRole.TERTIARY_CONTAINER
    assert toolbar.corner_radius == 16
    assert int(toolbar.height_sizing.value) == 72
    assert toolbar._content.gap == 20


def test_floating_toolbar_pushes_the_themes_style_onto_the_inner_container() -> None:
    toolbar = HorizontalFloatingToolbar([IconButton("add")])
    _mount(toolbar, _theme_with(_toolbar_style=_CUSTOM_TOOLBAR_STYLE))
    toolbar.preferred_size()

    assert toolbar._inner_container.bgcolor == ColorRole.TERTIARY_CONTAINER
    assert int(toolbar._inner_container.height_sizing.value) == 72
    assert toolbar._layout_content.gap == 20


def test_toolbar_follows_a_later_theme_change() -> None:
    toolbar = DockedToolbar([IconButton("add")])
    manager = _mount(toolbar, _theme_with())
    toolbar.preferred_size()
    assert toolbar.style == ToolbarStyle.preset()

    manager.set_theme(_theme_with(_toolbar_style=_CUSTOM_TOOLBAR_STYLE))
    toolbar.preferred_size()

    assert toolbar.style == _CUSTOM_TOOLBAR_STYLE
    assert toolbar.bgcolor == ColorRole.TERTIARY_CONTAINER


# --- Menu -------------------------------------------------------------------

_CUSTOM_MENU_STYLE = MenuStyle.standard().copy_with(
    background=ColorRole.TERTIARY_CONTAINER,
    label_color=ColorRole.ON_TERTIARY_CONTAINER,
    corner_radius=8,
    min_width=200,
)


def test_menu_adopts_the_themes_style() -> None:
    menu = Menu(items=[MenuItem("a")])
    _mount(menu, _theme_with(_menu_style=_CUSTOM_MENU_STYLE))

    assert menu.style == _CUSTOM_MENU_STYLE
    assert menu.bgcolor == ColorRole.TERTIARY_CONTAINER
    assert menu.corner_radius == 8


def test_menu_uses_the_preset_before_it_is_mounted() -> None:
    assert Menu(items=[MenuItem("a")]).style == MenuStyle.preset()


def test_menu_explicit_style_wins_over_the_theme() -> None:
    explicit = MenuStyle.vibrant()
    menu = Menu(items=[MenuItem("a")], style=explicit)
    _mount(menu, _theme_with(_menu_style=_CUSTOM_MENU_STYLE))

    assert menu.style == explicit


def test_menu_follows_a_later_theme_change() -> None:
    menu = Menu(items=[MenuItem("a")])
    manager = _mount(menu, _theme_with())
    assert menu.style == MenuStyle.preset()

    manager.set_theme(_theme_with(_menu_style=_CUSTOM_MENU_STYLE))

    assert menu.style == _CUSTOM_MENU_STYLE
    assert menu.bgcolor == ColorRole.TERTIARY_CONTAINER


def test_menu_items_are_rebuilt_for_the_themes_style() -> None:
    """An item's colours are baked into its content, so the items -- not just
    the surface -- have to be rebuilt when the theme supplies a style."""
    item = MenuItem("a")
    menu = Menu(items=[item])
    _mount(menu, _theme_with(_menu_style=_CUSTOM_MENU_STYLE))
    menu.style

    assert item._menu_style == _CUSTOM_MENU_STYLE


# --- Button groups ----------------------------------------------------------

_CUSTOM_STANDARD_GROUP_STYLE = StandardButtonGroupStyle.filled("s").copy_with(
    background=ColorRole.TERTIARY_CONTAINER,
    foreground=ColorRole.ON_TERTIARY_CONTAINER,
    selected_background=ColorRole.TERTIARY,
    item_gap=20,
)

_CUSTOM_CONNECTED_GROUP_STYLE = ConnectedButtonGroupStyle.filled("s").copy_with(
    background=ColorRole.TERTIARY_CONTAINER,
    foreground=ColorRole.ON_TERTIARY_CONTAINER,
    item_gap=6,
)


def _group_items() -> list[GroupButton]:
    return [GroupButton(label="a"), GroupButton(label="b")]


def test_standard_button_group_adopts_the_themes_style() -> None:
    group = StandardButtonGroup(_group_items())
    _mount(group, _theme_with(_standard_button_group_style=_CUSTOM_STANDARD_GROUP_STYLE))
    group.preferred_size()

    assert group._style == _CUSTOM_STANDARD_GROUP_STYLE
    # Every segment follows the group, so the row stays visually coherent.
    assert all(item._style == _CUSTOM_STANDARD_GROUP_STYLE for item in group._items)
    assert group._row.gap == 20


def test_standard_button_group_uses_the_preset_before_it_is_mounted() -> None:
    group = StandardButtonGroup(_group_items())

    assert group._style == StandardButtonGroupStyle.preset()


def test_standard_button_group_explicit_style_wins_over_the_theme() -> None:
    explicit = StandardButtonGroupStyle.outlined("s")
    group = StandardButtonGroup(_group_items(), style=explicit)
    _mount(group, _theme_with(_standard_button_group_style=_CUSTOM_STANDARD_GROUP_STYLE))
    group.preferred_size()

    assert group._style == explicit


def test_standard_button_group_follows_a_later_theme_change() -> None:
    group = StandardButtonGroup(_group_items())
    manager = _mount(group, _theme_with())
    group.preferred_size()
    assert group._style == StandardButtonGroupStyle.preset()

    manager.set_theme(_theme_with(_standard_button_group_style=_CUSTOM_STANDARD_GROUP_STYLE))
    group.preferred_size()

    assert group._style == _CUSTOM_STANDARD_GROUP_STYLE


def test_connected_button_group_adopts_the_themes_style() -> None:
    group = ConnectedButtonGroup(_group_items())
    _mount(group, _theme_with(_connected_button_group_style=_CUSTOM_CONNECTED_GROUP_STYLE))
    group.preferred_size()

    assert group._style == _CUSTOM_CONNECTED_GROUP_STYLE
    assert all(item._style == _CUSTOM_CONNECTED_GROUP_STYLE for item in group._items)


def test_connected_button_group_uses_the_preset_before_it_is_mounted() -> None:
    group = ConnectedButtonGroup(_group_items())

    assert group._style == ConnectedButtonGroupStyle.preset()


def test_connected_button_group_explicit_style_wins_over_the_theme() -> None:
    explicit = ConnectedButtonGroupStyle.outlined("s")
    group = ConnectedButtonGroup(_group_items(), style=explicit)
    _mount(group, _theme_with(_connected_button_group_style=_CUSTOM_CONNECTED_GROUP_STYLE))
    group.preferred_size()

    assert group._style == explicit


def test_lone_group_button_adopts_the_themes_standard_group_style() -> None:
    """A group button outside a group has nobody to push a style down to it, so
    it pulls the standard-group style itself."""
    item = GroupButton(label="a")
    _mount(item, _theme_with(_standard_button_group_style=_CUSTOM_STANDARD_GROUP_STYLE))
    item.preferred_size()

    assert item._style == _CUSTOM_STANDARD_GROUP_STYLE


def test_lone_group_button_uses_the_preset_before_it_is_mounted() -> None:
    assert GroupButton(label="a")._style == StandardButtonGroupStyle.preset()


def test_group_button_explicit_style_wins_over_the_theme() -> None:
    explicit = StandardButtonGroupStyle.tonal("s")
    item = GroupButton(label="a", style=explicit)
    _mount(item, _theme_with(_standard_button_group_style=_CUSTOM_STANDARD_GROUP_STYLE))
    item.preferred_size()

    assert item._style == explicit


# --- No premature lookups ---------------------------------------------------


@pytest.fixture()
def every_warning() -> Iterator[None]:
    """Defeat the once-per-process de-dup so each widget is judged on its own."""
    set_log_once_enabled(False)
    try:
        yield
    finally:
        set_log_once_enabled(True)


def _material_widget_factories() -> list[tuple[str, Callable[[], Widget]]]:
    """One instance of every widget the premature-lookup audit covered."""
    return [
        ("Card", lambda: Card(Text("x"))),
        ("AssistChip", lambda: AssistChip("a")),
        ("FilterChip", lambda: FilterChip("a")),
        ("InputChip", lambda: InputChip("a", trailing_icon="close")),
        ("SuggestionChip", lambda: SuggestionChip("a")),
        ("ToggleButton", lambda: ToggleButton("a")),
        ("IconToggleButton", lambda: IconToggleButton("star")),
        ("Fab", lambda: Fab("star")),
        ("ExtendedFab", lambda: ExtendedFab("a")),
        ("Button", lambda: Button("a")),
        ("IconButton", lambda: IconButton("star")),
        ("Checkbox", lambda: Checkbox()),
        ("RadioButton", lambda: RadioButton(value="v")),
        ("Switch", lambda: Switch()),
        ("DockedToolbar", lambda: DockedToolbar([IconButton("add")])),
        ("HorizontalFloatingToolbar", lambda: HorizontalFloatingToolbar([IconButton("add")])),
        ("VerticalFloatingToolbar", lambda: VerticalFloatingToolbar([IconButton("add")])),
        # A floating toolbar measures its buttons to derive the edge inset, and
        # measuring a bare Text reaches for the theme -- so the measurement must
        # not happen while the buttons are still unattached.
        ("HorizontalFloatingToolbar/Text", lambda: HorizontalFloatingToolbar([Text("b")])),
        ("VerticalFloatingToolbar/Text", lambda: VerticalFloatingToolbar([Text("b")])),
        ("Menu", lambda: Menu(items=[MenuItem("a")])),
        ("GroupButton", lambda: GroupButton(label="a")),
        ("StandardButtonGroup", lambda: StandardButtonGroup(_group_items())),
        ("ConnectedButtonGroup", lambda: ConnectedButtonGroup(_group_items())),
        ("TextField", lambda: TextField(label="a")),
    ]


@pytest.mark.parametrize(
    "name,factory",
    _material_widget_factories(),
    ids=[name for name, _ in _material_widget_factories()],
)
def test_constructing_and_mounting_never_looks_up_the_theme_too_early(
    name, factory, caplog, every_warning
) -> None:
    with caplog.at_level(logging.WARNING, logger=_THEME_LOGGER):
        _mount(factory(), _theme_with())

    premature = [r.getMessage() for r in caplog.records if "before it was mounted" in r.getMessage()]
    assert premature == [], f"{name} reached Theme.of before it could resolve: {premature}"


def test_button_follows_a_theme_mutated_in_place_and_reinstalled() -> None:
    """A button resolves its colour endpoints to concrete RGBA, so it is the one
    widget whose held value cannot self-correct on the next read. Its freshness
    check must therefore survive a change that arrives on the *same* ``Theme``
    object -- ``extensions`` and ``roles`` are mutable, so that is possible."""
    roles = {role: "#FFFFFF" for role in ColorRole}
    shared = Theme(mode="light", extensions=[MaterialThemeData(roles=roles)])

    button = Button("a")
    manager = _mount(button, shared)
    button.preferred_size()
    before = button.bgcolor

    roles[ColorRole.PRIMARY] = "#101010"
    manager.set_theme(shared)  # same object, mutated contents
    button.preferred_size()

    assert button.bgcolor != before
