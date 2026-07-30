"""Material widgets must adopt the *theme's* style, not a frozen default.

Resolving a style in ``__init__`` cannot work: the widget has no parent yet, so
``Theme.of`` cannot reach the ``AppScope`` and silently returns the light
default. The style therefore has to be adopted once the widget is attached --
and it has to keep following the theme after that. See issue #473.
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
from nuiitivet.material.button_group import GroupButton
from nuiitivet.material.card import Card
from nuiitivet.material.chip import AssistChip, FilterChip, InputChip, SuggestionChip
from nuiitivet.material.menu import Menu, MenuItem
from nuiitivet.material.selection_controls import Checkbox, RadioButton, Switch
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material.styles.chip_style import ChipStyle
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text import Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.material.toolbar import (
    DockedToolbar,
    HorizontalFloatingToolbar,
    VerticalFloatingToolbar,
)
from nuiitivet.runtime.app import AppScope
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


class _StubApp:
    """Minimum an ``AppScope`` needs: a theme manager and a weak-referenceable
    identity."""

    def __init__(self, manager: ThemeManager) -> None:
        self._theme_manager = manager


def _mount(widget: Widget, theme: Theme) -> ThemeManager:
    """Attach ``widget`` under an ``AppScope`` serving ``theme``.

    Returns the manager so a test can push a later theme through it. The scope
    is kept alive on the widget: the whole point is that the widget can still
    walk up to it after the call returns.
    """
    manager = ThemeManager(theme)
    app = _StubApp(manager)
    scope = AppScope(app, widget)  # type: ignore[arg-type]
    scope.mount(app)
    widget._test_scope = scope  # type: ignore[attr-defined]
    return manager


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
