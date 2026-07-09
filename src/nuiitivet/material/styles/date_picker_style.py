"""Date picker widget styles.

Each MD3 date-picker widget has its own immutable style dataclass. The calendar
based pickers share a common :class:`CalendarStyle` base (calendar cell, colors,
header, navigation button) and add only the fields their distinct selection
views need:

- :class:`DatePickerStyle`        — adds the inline month/year list-menu tokens.
- :class:`ModalDatePickerStyle`   — adds the modal year-chip selection tokens.
- :class:`ModalDateRangePickerStyle` — extends the modal style with range-header
  tokens.

:class:`DockedDatePickerStyle` *composes* a :class:`DatePickerStyle` rather than
inheriting one: its dropdown content literally is a :class:`DatePicker`, so the
calendar tokens stay on their own plane instead of being flattened onto the
text-field tokens.

:class:`ModalDateInputStyle` is independent: the date-input dialog is a
text-field form, not a calendar, so it shares none of the calendar tokens.

MD3 token references: ``md.comp.date-picker.*``
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TypeVar

from nuiitivet.theme.types import ColorSpec
from ..theme.color_role import ColorRole

_S = TypeVar("_S", bound="CalendarStyle")


@dataclass(frozen=True)
class CalendarStyle:
    """Shared style base for the calendar-based date pickers (MD3 Expressive).

    Holds the tokens consumed by the calendar widgets shared across
    :class:`DatePickerStyle`, :class:`ModalDatePickerStyle` and
    :class:`ModalDateRangePickerStyle` (the calendar grid, day cells and the
    month/year navigation header). Variant-specific selection views add their
    own tokens in the respective subclass.

    Not exported from ``nuiitivet.material``: users only ever need the concrete
    styles. Import it from this module for type hints and subclassing.

    Defaults match the MD3 docked picker. Subclasses override the container and
    header dimensions for their variant.
    """

    # --- Container ---
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGH
    elevation: int = 3  # MD3 level 3 = 6dp shadow
    corner_radius: float = 16.0  # Large rounding (docked default)
    container_width: float = 360.0
    container_height: float = (
        460.0  # Docked default: 460dp (measurement image; token value 456dp appears to be a spec bug)
    )

    # --- Date cell ---
    date_cell_size: int = (
        40  # Selection circle size: 40dp (docked and modal). Outer touch target is 40+4+4=48dp due to 4dp gap.
    )
    date_cell_radius: float = 20.0  # Fully rounded = date_cell_size / 2
    state_layer_size: int = 40  # Always 40dp per spec
    date_font_size: int = 16  # Roboto 16pt per spec

    # --- Date colors ---
    date_selected_background: ColorSpec = ColorRole.PRIMARY
    date_selected_text: ColorSpec = ColorRole.ON_PRIMARY
    date_today_outline_color: ColorSpec = ColorRole.PRIMARY
    date_today_text: ColorSpec = ColorRole.PRIMARY
    date_unselected_text: ColorSpec = ColorRole.ON_SURFACE
    date_outside_month_opacity: float = 0.38
    weekday_text: ColorSpec = ColorRole.ON_SURFACE

    # --- Range band (painted by the shared day cell; only a range picker
    #     actually activates it, but the band is part of the cell rendering) ---
    range_active_indicator_background: ColorSpec = ColorRole.SECONDARY_CONTAINER
    range_date_in_range_text: ColorSpec = ColorRole.ON_SECONDARY_CONTAINER

    # --- Header ---
    header_height: float = 64.0  # docked: 64dp, modal: 120dp
    header_headline_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    header_supporting_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT

    # --- State layer opacities ---
    hover_state_layer_opacity: float = 0.08
    focus_state_layer_opacity: float = 0.1
    pressed_state_layer_opacity: float = 0.1

    # --- Header typography sizes ---
    header_supporting_text_font_size: float = 14.0
    header_headline_font_size: float = 32.0

    # --- Month/year navigation button (docked + modal nav header) ---
    menu_button_height: float = 40.0
    menu_button_font_size: int = 14  # md.comp.date-picker.docked.menu-button.label-text: 14pt/20pt, 500
    menu_button_icon_size: int = 18  # Dropdown arrow icon size; from md.comp.date-picker.docked.menu-button.icon.size
    menu_button_text: ColorSpec = ColorRole.ON_SURFACE_VARIANT

    def copy_with(self: _S, **changes) -> _S:
        """Return a new style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            New style instance of the same type with applied changes.
        """
        return replace(self, **changes)


@dataclass(frozen=True)
class DatePickerStyle(CalendarStyle):
    """Style for :class:`DatePicker` (inline calendar).

    MD3 calendar: 360×460dp container, Large corner rounding (16dp). Adds the
    month/year inline list-menu tokens to the shared calendar base.
    """

    # --- Month/year selection list item (inline grids) ---
    menu_list_item_height: float = 48.0
    menu_list_item_selected_background: ColorSpec = ColorRole.SECONDARY_CONTAINER
    menu_list_item_text: ColorSpec = ColorRole.ON_SURFACE
    menu_list_item_selected_text: ColorSpec = ColorRole.ON_SECONDARY_CONTAINER


@dataclass(frozen=True)
class DockedDatePickerStyle:
    """Style for :class:`DockedDatePicker` (text field + anchored calendar).

    Composes — rather than inherits — a :class:`DatePickerStyle` for the
    dropdown calendar, keeping the calendar tokens separate from the text-field
    and dropdown tokens.
    """

    # --- Dropdown calendar ---
    calendar: DatePickerStyle = field(default_factory=DatePickerStyle)

    # --- Text field ---
    field_width: float = 360.0

    # --- Dropdown placement ---
    dropdown_gap: float = 4.0  # Vertical gap between the field and the calendar

    def copy_with(self, **changes) -> "DockedDatePickerStyle":
        """Return a new style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            New ``DockedDatePickerStyle`` instance with applied changes.
        """
        return replace(self, **changes)


@dataclass(frozen=True)
class ModalDatePickerStyle(CalendarStyle):
    """Style for :class:`ModalDatePicker` (single-date dialog).

    MD3 modal picker: 360×524dp container, Extra-large corner rounding (28dp).
    Adds the year-chip selection tokens to the shared calendar base.
    """

    # --- Container (modal overrides) ---
    corner_radius: float = 28.0
    container_height: float = 524.0
    header_height: float = 120.0

    # --- Year chip (modal year-selection, 72×36dp per spec) ---
    year_chip_width: float = 72.0
    year_chip_height: float = 36.0
    year_chip_radius: float = 18.0
    year_chip_gap: int = 30  # Gap between chips (main and cross), from measurement image
    year_chip_selected_background: ColorSpec = ColorRole.PRIMARY
    year_chip_selected_text: ColorSpec = ColorRole.ON_PRIMARY
    year_chip_unselected_text: ColorSpec = ColorRole.ON_SURFACE_VARIANT


@dataclass(frozen=True)
class ModalDateRangePickerStyle(ModalDatePickerStyle):
    """Style for :class:`ModalDateRangePicker` (date-range dialog).

    Extends :class:`ModalDatePickerStyle` (same calendar, year chips and
    container) with the taller range-selection header tokens.
    """

    # --- Range selection header ---
    range_header_height: float = 128.0  # Range selection header: 128dp per spec
    range_headline_font_size: float = 22.0  # Range picker headline: 22pt / 28pt per spec


@dataclass(frozen=True)
class ModalDateInputStyle:
    """Style for :class:`ModalDateInput` (text-field date entry dialog).

    Independent of the calendar pickers: the date-input dialog is a text-field
    form, so it shares none of the calendar/selection tokens — only the dialog
    container and header typography.

    MD3 modal input: 328×512dp container, Extra-large corner rounding (28dp).
    """

    # --- Container ---
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGH
    elevation: int = 3  # MD3 level 3 = 6dp shadow
    corner_radius: float = 28.0
    container_width: float = 328.0
    container_height: float = 512.0

    # --- Header ---
    header_headline_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    header_supporting_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    header_supporting_text_font_size: float = 14.0
    header_headline_font_size: float = 32.0

    def copy_with(self, **changes) -> "ModalDateInputStyle":
        """Return a new style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            New ``ModalDateInputStyle`` instance with applied changes.
        """
        return replace(self, **changes)
