"""Tests for DatePicker widgets."""

from datetime import date

import pytest

from nuiitivet.material.date_picker import (
    DockedDatePicker,
    ModalDateInput,
    ModalDatePicker,
    ModalDateRangePicker,
    _parse_date,
    _prev_month,
    _next_month,
)
from nuiitivet.material.styles.date_picker_style import (
    DockedDatePickerStyle,
    ModalDatePickerStyle,
    ModalDateRangePickerStyle,
    ModalDateInputStyle,
)
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box

# ---------------------------------------------------------------------------
# DatePickerStyle
# ---------------------------------------------------------------------------


def test_docked_date_picker_style_defaults():
    """DockedDatePickerStyle has correct MD3 docked token values."""
    style = DockedDatePickerStyle()
    assert style.corner_radius == 16.0
    assert style.container_width == 360.0
    assert style.container_height == 460.0  # Measurement image value; token 456dp is a spec bug
    assert style.date_cell_size == 40  # Selection circle size; touch target is 40+4+4=48dp with gaps
    assert style.date_cell_radius == 20.0
    assert style.header_height == 64.0
    assert style.elevation == 3
    # Docked-only selection-view token.
    assert style.menu_list_item_height == 48.0


def test_modal_date_picker_style_defaults():
    """ModalDatePickerStyle has correct MD3 modal token values."""
    style = ModalDatePickerStyle()
    assert style.corner_radius == 28.0
    assert style.container_width == 360.0
    assert style.container_height == 524.0
    assert style.date_cell_size == 40
    assert style.date_cell_radius == 20.0
    assert style.header_height == 120.0
    # Modal-only year-chip token.
    assert style.year_chip_width == 72.0


def test_modal_date_range_picker_style_defaults():
    """ModalDateRangePickerStyle extends the modal style with range-header tokens."""
    style = ModalDateRangePickerStyle()
    # Inherited modal tokens.
    assert style.corner_radius == 28.0
    assert style.year_chip_width == 72.0
    # Range-only header tokens.
    assert style.range_header_height == 128.0
    assert style.range_headline_font_size == 22.0


def test_modal_date_input_style_defaults():
    """ModalDateInputStyle has correct MD3 modal input token values."""
    style = ModalDateInputStyle()
    assert style.corner_radius == 28.0
    assert style.container_width == 328.0
    assert style.container_height == 512.0
    # Independent of the calendar pickers: carries no calendar tokens.
    assert not hasattr(style, "date_cell_size")


def test_date_picker_style_copy_with():
    """copy_with() creates a modified copy of the same subclass type."""
    base = DockedDatePickerStyle()
    modified = base.copy_with(corner_radius=8.0, date_font_size=12)
    assert isinstance(modified, DockedDatePickerStyle)
    assert modified.corner_radius == 8.0
    assert modified.date_font_size == 12
    # Unmodified fields are preserved
    assert modified.container_width == base.container_width
    assert modified.elevation == base.elevation


# ---------------------------------------------------------------------------
# Month navigation helpers
# ---------------------------------------------------------------------------


def test_prev_month_normal():
    """_prev_month decrements month."""
    assert _prev_month(2026, 6) == (2026, 5)


def test_prev_month_year_boundary():
    """_prev_month wraps from January to December of prior year."""
    assert _prev_month(2026, 1) == (2025, 12)


def test_next_month_normal():
    """_next_month increments month."""
    assert _next_month(2026, 6) == (2026, 7)


def test_next_month_year_boundary():
    """_next_month wraps from December to January of next year."""
    assert _next_month(2026, 12) == (2027, 1)


# ---------------------------------------------------------------------------
# DockedDatePicker
# ---------------------------------------------------------------------------


def test_docked_date_picker_init():
    """DockedDatePicker can be constructed with an Observable."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(obs)
    assert picker is not None


def test_docked_date_picker_view_follows_value():
    """DockedDatePicker initialises view month from the observable value."""
    initial = date(2025, 3, 15)
    obs: Observable[date | None] = Observable(initial)
    picker = DockedDatePicker(obs)
    assert picker._view_year == 2025
    assert picker._view_month == 3


def test_docked_date_picker_view_defaults_to_today_when_no_value():
    """DockedDatePicker uses today's month when value is None."""
    today = date.today()
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(obs)
    assert picker._view_year == today.year
    assert picker._view_month == today.month


def test_docked_date_picker_month_navigation():
    """_go_prev_month and _go_next_month update view state."""
    obs: Observable[date | None] = Observable(date(2026, 6, 1))
    picker = DockedDatePicker(obs)

    picker._go_prev_month()
    assert picker._view_month == 5
    assert picker._view_year == 2026

    picker._go_next_month()
    picker._go_next_month()
    assert picker._view_month == 7
    assert picker._view_year == 2026


def test_docked_date_picker_month_navigation_year_boundary():
    """Month navigation wraps correctly across year boundaries."""
    obs: Observable[date | None] = Observable(date(2026, 1, 1))
    picker = DockedDatePicker(obs)
    picker._go_prev_month()
    assert picker._view_year == 2025
    assert picker._view_month == 12


def test_docked_date_picker_on_day_tap_updates_observable():
    """Tapping a day updates the observable and calls on_change."""
    obs: Observable[date | None] = Observable(None)
    changed: list[date | None] = []
    picker = DockedDatePicker(obs, on_change=changed.append)

    picker._on_day_tap(date(2026, 6, 10))
    assert obs.value == date(2026, 6, 10)
    assert changed == [date(2026, 6, 10)]


def test_docked_date_picker_build_returns_box():
    """DockedDatePicker.build() returns a Box."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(obs)
    result = picker.build()
    assert isinstance(result, Box)


def test_docked_date_picker_custom_style():
    """DockedDatePicker accepts a custom style."""
    custom = DockedDatePickerStyle().copy_with(corner_radius=8.0)
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(obs, style=custom)
    assert picker.style.corner_radius == 8.0


# ---------------------------------------------------------------------------
# ModalDatePicker
# ---------------------------------------------------------------------------


def test_modal_date_picker_init():
    """ModalDatePicker initialises with no selection."""
    picker = ModalDatePicker()
    assert picker._selected_date is None


def test_modal_date_picker_init_value():
    """ModalDatePicker uses init_value for pre-selection."""
    init = date(2026, 5, 20)
    picker = ModalDatePicker(init_value=init)
    assert picker._selected_date == init
    assert picker._view_year == 2026
    assert picker._view_month == 5


def test_modal_date_picker_day_selection():
    """Tapping a day updates _selected_date."""
    picker = ModalDatePicker()
    picker._on_day_tap(date(2026, 6, 15))
    assert picker._selected_date == date(2026, 6, 15)


def test_modal_date_picker_confirm():
    """_on_confirm closes overlay with selected date (no overlay guard)."""
    picker = ModalDatePicker()
    picker._on_day_tap(date(2026, 6, 10))
    picker._on_confirm()  # Must not raise


def test_modal_date_picker_cancel():
    """_on_cancel does not raise when not displayed via overlay."""
    picker = ModalDatePicker()
    picker._on_cancel()  # Must not raise


def test_modal_date_picker_build_returns_box():
    """ModalDatePicker.build() returns a Box."""
    picker = ModalDatePicker()
    result = picker.build()
    assert isinstance(result, Box)


def test_modal_date_picker_month_navigation():
    """Month navigation updates view state."""
    picker = ModalDatePicker(init_value=date(2026, 6, 1))
    picker._go_prev_month()
    assert picker._view_month == 5
    picker._go_next_month()
    picker._go_next_month()
    assert picker._view_month == 7


# ---------------------------------------------------------------------------
# ModalDateRangePicker
# ---------------------------------------------------------------------------


def test_modal_date_range_picker_init():
    """ModalDateRangePicker initialises with no selection."""
    picker = ModalDateRangePicker()
    assert picker._range_start is None
    assert picker._range_end is None
    assert picker._range_state == "first"


def test_modal_date_range_picker_init_value():
    """ModalDateRangePicker parses tuple init_value."""
    start = date(2026, 5, 1)
    end = date(2026, 5, 15)
    picker = ModalDateRangePicker(init_value=(start, end))
    assert picker._range_start == start
    assert picker._range_end == end
    assert picker._view_year == 2026
    assert picker._view_month == 5


def test_modal_date_range_picker_two_click_selection():
    """Two taps select start and end."""
    picker = ModalDateRangePicker()
    assert picker._range_state == "first"

    picker._on_day_tap(date(2026, 6, 5))
    assert picker._range_start == date(2026, 6, 5)
    assert picker._range_end is None
    assert picker._range_state == "second"

    picker._on_day_tap(date(2026, 6, 15))
    assert picker._range_start == date(2026, 6, 5)
    assert picker._range_end == date(2026, 6, 15)
    assert picker._range_state == "first"


def test_modal_date_range_picker_restart_when_end_before_start():
    """Tapping before start resets range from new start."""
    picker = ModalDateRangePicker()
    picker._on_day_tap(date(2026, 6, 15))  # start
    picker._on_day_tap(date(2026, 6, 5))  # before start → restarts
    assert picker._range_start == date(2026, 6, 5)
    assert picker._range_end is None
    assert picker._range_state == "second"


def test_modal_date_range_picker_confirm():
    """_on_confirm closes overlay with (start, end) tuple (no overlay guard)."""
    picker = ModalDateRangePicker()
    picker._on_day_tap(date(2026, 6, 1))
    picker._on_day_tap(date(2026, 6, 30))
    picker._on_confirm()  # Must not raise


def test_modal_date_range_picker_cancel():
    """_on_cancel does not raise when not displayed via overlay."""
    picker = ModalDateRangePicker()
    picker._on_cancel()  # Must not raise


def test_modal_date_range_picker_build_returns_box():
    """ModalDateRangePicker.build() returns a Box."""
    picker = ModalDateRangePicker()
    result = picker.build()
    assert isinstance(result, Box)


# ---------------------------------------------------------------------------
# ModalDateInput
# ---------------------------------------------------------------------------


def test_parse_date_valid_formats():
    """_parse_date handles common date formats."""
    assert _parse_date("06/10/2026") == date(2026, 6, 10)
    assert _parse_date("06-10-2026") == date(2026, 6, 10)
    assert _parse_date("2026-06-10") == date(2026, 6, 10)


def test_parse_date_invalid_returns_none():
    """_parse_date returns None for unparseable input."""
    assert _parse_date("not-a-date") is None
    assert _parse_date("") is None
    assert _parse_date("13/40/2026") is None


def test_modal_date_input_init():
    """ModalDateInput constructs successfully."""
    picker = ModalDateInput()
    assert picker is not None


def test_modal_date_input_init_value_populates_text():
    """ModalDateInput pre-populates the text field from init_value."""
    picker = ModalDateInput(init_value=date(2026, 6, 10))
    assert picker._text_obs.value == "06/10/2026"


def test_modal_date_input_confirm_valid_date():
    """_on_confirm does not raise for a valid date (no overlay guard)."""
    picker = ModalDateInput()
    picker._text_obs.value = "06/10/2026"
    picker._on_confirm()  # Must not raise


def test_modal_date_input_confirm_invalid_date_sets_error():
    """_on_confirm sets error supporting text for invalid input."""
    picker = ModalDateInput()
    picker._text_obs.value = "not-a-date"
    picker._on_confirm()
    assert picker._supporting_text_obs.value == "Invalid date"


def test_modal_date_input_confirm_before_min_date_sets_error():
    """_on_confirm rejects dates before min_date."""
    picker = ModalDateInput(min_date=date(2026, 6, 1))
    picker._text_obs.value = "05/31/2026"
    picker._on_confirm()
    assert "on or after" in (picker._supporting_text_obs.value or "")


def test_modal_date_input_confirm_after_max_date_sets_error():
    """_on_confirm rejects dates after max_date."""
    picker = ModalDateInput(max_date=date(2026, 6, 30))
    picker._text_obs.value = "07/01/2026"
    picker._on_confirm()
    assert "on or before" in (picker._supporting_text_obs.value or "")


def test_modal_date_input_cancel():
    """_on_cancel does not raise when not displayed via overlay."""
    picker = ModalDateInput()
    picker._on_cancel()  # Must not raise


def test_modal_date_input_build_returns_box():
    """ModalDateInput.build() returns a Box."""
    picker = ModalDateInput()
    result = picker.build()
    assert isinstance(result, Box)
