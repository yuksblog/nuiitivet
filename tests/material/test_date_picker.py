"""Tests for DatePicker widgets."""

from datetime import date

import pytest

from nuiitivet.material.date_picker import (
    DatePicker,
    DockedDatePicker,
    ModalDateInput,
    ModalDatePicker,
    ModalDateRangePicker,
    _format_date,
    _parse_date,
    _prev_month,
    _next_month,
)
from nuiitivet.material.styles.date_picker_style import (
    CalendarStyle,
    DatePickerStyle,
    DockedDatePickerStyle,
    ModalDatePickerStyle,
    ModalDateRangePickerStyle,
    ModalDateInputStyle,
)
from nuiitivet.modifiers.popup import PopupBox
from nuiitivet.observable import Observable
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.widgets.box import Box

# ---------------------------------------------------------------------------
# DatePickerStyle
# ---------------------------------------------------------------------------


def test_date_picker_style_defaults():
    """DatePickerStyle has correct MD3 calendar token values."""
    style = DatePickerStyle()
    assert style.corner_radius == 16.0
    assert style.container_width == 360.0
    assert style.container_height == 460.0  # Measurement image value; token 456dp is a spec bug
    assert style.date_cell_size == 40  # Selection circle size; touch target is 40+4+4=48dp with gaps
    assert style.date_cell_radius == 20.0
    assert style.header_height == 64.0
    assert style.elevation == 3
    # Inline-only selection-view token.
    assert style.menu_list_item_height == 48.0


def test_calendar_style_is_the_shared_base():
    """The calendar-based picker styles all derive from CalendarStyle."""
    assert issubclass(DatePickerStyle, CalendarStyle)
    assert issubclass(ModalDatePickerStyle, CalendarStyle)
    assert issubclass(ModalDateRangePickerStyle, CalendarStyle)


def test_calendar_style_is_not_exported():
    """CalendarStyle stays out of the material namespace; only concrete styles are public."""
    import nuiitivet.material as material

    assert "CalendarStyle" not in material.__all__


def test_docked_date_picker_style_composes_a_calendar():
    """DockedDatePickerStyle composes a DatePickerStyle rather than inheriting one."""
    style = DockedDatePickerStyle()
    assert isinstance(style.calendar, DatePickerStyle)
    assert not isinstance(style, CalendarStyle)
    # Text-field / dropdown tokens live beside the calendar, not flattened onto it.
    assert style.field_width == 360.0
    assert style.dropdown_gap == 4.0
    assert not hasattr(style, "date_cell_size")


def test_docked_date_picker_style_copy_with_replaces_calendar():
    """The composed calendar can be swapped without touching the field tokens."""
    calendar = DatePickerStyle().copy_with(corner_radius=8.0)
    style = DockedDatePickerStyle().copy_with(calendar=calendar)
    assert style.calendar.corner_radius == 8.0
    assert style.field_width == 360.0


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
    base = DatePickerStyle()
    modified = base.copy_with(corner_radius=8.0, date_font_size=12)
    assert isinstance(modified, DatePickerStyle)
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
# DatePicker (inline calendar)
# ---------------------------------------------------------------------------


def test_date_picker_init():
    """DatePicker can be constructed with an Observable."""
    obs: Observable[date | None] = Observable(None)
    picker = DatePicker(obs)
    assert picker is not None


def test_date_picker_view_follows_value():
    """DatePicker initialises view month from the observable value."""
    initial = date(2025, 3, 15)
    obs: Observable[date | None] = Observable(initial)
    picker = DatePicker(obs)
    assert picker._view_year == 2025
    assert picker._view_month == 3


def test_date_picker_view_defaults_to_today_when_no_value():
    """DatePicker uses today's month when value is None."""
    today = date.today()
    obs: Observable[date | None] = Observable(None)
    picker = DatePicker(obs)
    assert picker._view_year == today.year
    assert picker._view_month == today.month


def test_date_picker_month_navigation():
    """_go_prev_month and _go_next_month update view state."""
    obs: Observable[date | None] = Observable(date(2026, 6, 1))
    picker = DatePicker(obs)

    picker._go_prev_month()
    assert picker._view_month == 5
    assert picker._view_year == 2026

    picker._go_next_month()
    picker._go_next_month()
    assert picker._view_month == 7
    assert picker._view_year == 2026


def test_date_picker_month_navigation_year_boundary():
    """Month navigation wraps correctly across year boundaries."""
    obs: Observable[date | None] = Observable(date(2026, 1, 1))
    picker = DatePicker(obs)
    picker._go_prev_month()
    assert picker._view_year == 2025
    assert picker._view_month == 12


def test_date_picker_on_day_tap_updates_observable():
    """Tapping a day updates the observable and calls on_change."""
    obs: Observable[date | None] = Observable(None)
    changed: list[date | None] = []
    picker = DatePicker(obs, on_change=changed.append)

    picker._on_day_tap(date(2026, 6, 10))
    assert obs.value == date(2026, 6, 10)
    assert changed == [date(2026, 6, 10)]


def test_date_picker_show_month_moves_view_without_changing_value():
    """show_month() retargets the calendar and leaves the selection alone."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    picker = DatePicker(obs)
    picker._view_mode = "year"

    picker.show_month(2030, 11)

    assert (picker._view_year, picker._view_month) == (2030, 11)
    assert picker._view_mode == "calendar"
    assert obs.value == date(2026, 6, 10)


def test_date_picker_ok_is_inert_without_on_confirm():
    """Standalone there is nothing to confirm to, so OK leaves the value alone."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    picker = DatePicker(obs)

    picker._on_ok()

    assert obs.value == date(2026, 6, 10)


def test_date_picker_ok_invokes_on_confirm_with_the_selected_date():
    """An embedder takes over OK via on_confirm."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    confirmed: list[date | None] = []
    picker = DatePicker(obs, on_confirm=confirmed.append)

    picker._on_ok()

    assert confirmed == [date(2026, 6, 10)]


def test_date_picker_cancel_clears_the_value_by_default():
    """Standalone, Cancel means "clear the selection"."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    changed: list[date | None] = []
    picker = DatePicker(obs, on_change=changed.append)

    picker._on_cancel()

    assert obs.value is None
    assert changed == [None]


def test_date_picker_on_cancel_replaces_the_clear_behavior():
    """An embedder takes over Cancel; the value is left for it to decide."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    cancelled: list[bool] = []
    picker = DatePicker(obs, on_cancel=lambda: cancelled.append(True))

    picker._on_cancel()

    assert cancelled == [True]
    assert obs.value == date(2026, 6, 10)


def test_date_picker_build_returns_box():
    """DatePicker.build() returns a Box."""
    obs: Observable[date | None] = Observable(None)
    picker = DatePicker(obs)
    result = picker.build()
    assert isinstance(result, Box)


def test_date_picker_custom_style():
    """DatePicker accepts a custom style."""
    custom = DatePickerStyle().copy_with(corner_radius=8.0)
    obs: Observable[date | None] = Observable(None)
    picker = DatePicker(obs, style=custom)
    assert picker.style.corner_radius == 8.0


# ---------------------------------------------------------------------------
# DockedDatePicker (text field + anchored calendar dropdown)
# ---------------------------------------------------------------------------


def test_docked_date_picker_value_is_keyword_only():
    """A positional value argument raises, so pre-rename call sites fail loudly."""
    obs: Observable[date | None] = Observable(None)
    with pytest.raises(TypeError):
        DockedDatePicker(obs)  # type: ignore[misc]


def test_docked_date_picker_init_populates_text_from_value():
    """The text field starts showing the observable's date."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    picker = DockedDatePicker(value=obs)
    assert picker._text_obs.value == "06/10/2026"
    assert picker._is_error_obs.value is False


def test_docked_date_picker_init_with_no_value_has_empty_text():
    """A None value renders as an empty text field."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    assert picker._text_obs.value == ""


def test_docked_date_picker_dropdown_starts_closed():
    """The calendar dropdown is closed until the icon button is tapped."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    assert picker._is_open.value is False


def test_docked_date_picker_icon_button_toggles_dropdown():
    """Tapping the trailing calendar icon opens and closes the dropdown."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)

    picker._toggle_dropdown()
    assert picker._is_open.value is True

    picker._toggle_dropdown()
    assert picker._is_open.value is False


def test_docked_date_picker_day_tap_edits_the_draft_only():
    """A day tap is a selection, not a commit: value, field and on_change stay put."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()
    picker._is_open.value = True

    # Drive the embedded calendar the way a day-cell tap does.
    picker._calendar._on_day_tap(date(2026, 7, 4))

    assert picker._draft_obs.value == date(2026, 7, 4)
    assert obs.value == date(2026, 6, 25)
    assert picker._text_obs.value == "06/25/2026"
    assert picker._is_open.value is True
    assert changed == []


def test_docked_date_picker_ok_commits_the_draft_and_closes():
    """OK copies the draft into value, updates the field and fires on_change once."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 1))
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_ok()

    assert obs.value == date(2026, 7, 4)
    assert picker._text_obs.value == "07/04/2026"
    assert picker._is_open.value is False
    # Two day taps, one commit: intermediate selections never reach on_change.
    assert changed == [date(2026, 7, 4)]


def test_docked_date_picker_ok_without_a_new_selection_does_not_fire_on_change():
    """Opening and confirming without picking a different day is a no-op."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()
    picker._is_open.value = True

    picker._calendar._on_ok()

    assert obs.value == date(2026, 6, 25)
    assert changed == []


def test_docked_date_picker_cancel_discards_the_draft():
    """Cancel abandons the selection; value never saw it."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_cancel()

    assert obs.value == date(2026, 6, 25)
    assert picker._text_obs.value == "06/25/2026"
    assert picker._is_open.value is False
    assert changed == []


def test_docked_date_picker_cancel_does_not_clear_the_value():
    """Cancel must not fall through to DatePicker's clear-the-value default."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True

    picker._calendar._on_cancel()

    assert obs.value == date(2026, 6, 25)


def test_docked_date_picker_dismissing_by_outside_tap_discards_the_draft():
    """An outside tap closes the dropdown without committing the selection."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    # light_dismiss drives is_open back to False on an outside tap.
    picker._is_open.value = False

    assert obs.value == date(2026, 6, 25)
    assert picker._text_obs.value == "06/25/2026"
    assert changed == []


def test_docked_date_picker_reopening_reseeds_the_draft_from_value():
    """A draft abandoned by cancel does not survive into the next open."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 8, 1))
    picker._calendar._on_cancel()

    picker._is_open.value = True

    assert picker._draft_obs.value == date(2026, 6, 25)


def test_docked_date_picker_opening_moves_the_calendar_to_the_selected_month():
    """The dropdown opens on the month of the current value."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._calendar.show_month(2020, 1)

    picker._is_open.value = True

    assert (picker._calendar._view_year, picker._calendar._view_month) == (2026, 6)


def test_docked_date_picker_typing_valid_date_writes_through():
    """A parseable date is written to value and moves the calendar to its month."""
    obs: Observable[date | None] = Observable(None)
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)

    picker._on_text_changed("03/15/2025")

    assert obs.value == date(2025, 3, 15)
    assert changed == [date(2025, 3, 15)]
    assert picker._is_error_obs.value is False
    assert picker._draft_obs.value == date(2025, 3, 15)
    assert (picker._calendar._view_year, picker._calendar._view_month) == (2025, 3)


def test_docked_date_picker_typing_invalid_date_sets_error_and_keeps_value():
    """An unparseable date surfaces as an error state; value is untouched."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)

    picker._on_text_changed("not a date")

    assert obs.value == date(2026, 6, 10)
    assert changed == []
    assert picker._is_error_obs.value is True
    assert picker._supporting_text_obs.value == "Invalid date"


def test_docked_date_picker_typing_date_before_min_sets_error():
    """A date before min_date is rejected with a supporting-text message."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs, min_date=date(2026, 1, 1))

    picker._on_text_changed("12/31/2025")

    assert obs.value is None
    assert picker._is_error_obs.value is True
    assert "on or after" in (picker._supporting_text_obs.value or "")


def test_docked_date_picker_typing_date_after_max_sets_error():
    """A date after max_date is rejected with a supporting-text message."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs, max_date=date(2026, 1, 1))

    picker._on_text_changed("01/02/2026")

    assert obs.value is None
    assert picker._is_error_obs.value is True
    assert "on or before" in (picker._supporting_text_obs.value or "")


def test_docked_date_picker_clearing_text_clears_value():
    """Emptying the field clears the selection and the error state."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    picker = DockedDatePicker(value=obs)
    picker._on_text_changed("nope")
    assert picker._is_error_obs.value is True

    picker._on_text_changed("")

    assert obs.value is None
    assert picker._is_error_obs.value is False
    assert picker._supporting_text_obs.value == "mm/dd/yyyy"


def test_docked_date_picker_recovers_from_error_on_valid_input():
    """Correcting an invalid entry clears the error and restores the format hint."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    picker._on_text_changed("13/45/2026")
    assert picker._is_error_obs.value is True

    picker._on_text_changed("06/10/2026")

    assert picker._is_error_obs.value is False
    assert picker._supporting_text_obs.value == "mm/dd/yyyy"
    assert obs.value == date(2026, 6, 10)


def test_docked_date_picker_external_value_change_updates_text():
    """Writing to value from outside re-renders the text field."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    obs.value = date(2026, 6, 10)

    assert picker._text_obs.value == "06/10/2026"


def test_docked_date_picker_external_value_change_does_not_call_on_change():
    """on_change reports user interaction, not programmatic writes."""
    obs: Observable[date | None] = Observable(None)
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)
    picker.on_mount()

    obs.value = date(2026, 6, 10)

    assert changed == []


def test_docked_date_picker_mount_does_not_fire_on_change():
    """Mounting replays the current observable values; that is not a user edit."""
    obs: Observable[date | None] = Observable(date(2026, 6, 10))
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)

    picker.on_mount()

    assert changed == []
    assert obs.value == date(2026, 6, 10)
    assert picker._text_obs.value == "06/10/2026"


def test_docked_date_picker_mount_with_no_value_does_not_write_through():
    """An empty field at mount time must not be mistaken for the user clearing it."""
    obs: Observable[date | None] = Observable(None)
    changed: list[date | None] = []
    picker = DockedDatePicker(value=obs, on_change=changed.append)

    picker.on_mount()

    assert changed == []


@pytest.fixture
def overlay_root():
    """Install a root Overlay for the duration of a test."""
    previous = Overlay._root_overlay
    overlay = Overlay()
    Overlay.set_root(overlay)
    yield overlay
    Overlay._root_overlay = previous


def test_docked_date_picker_build_anchors_the_calendar_to_the_field():
    """build() wraps the text field in a popup carrying the calendar as content."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)

    popup = picker.build()

    assert isinstance(popup, PopupBox)
    assert popup._content is picker._calendar
    assert popup._is_open is picker._is_open
    assert popup._light_dismiss is True
    # Dropdown hangs below the field's bottom-left corner.
    assert popup._alignment == "bottom-left"
    assert popup._anchor == "top-left"
    assert popup._offset == (0.0, picker.style.dropdown_gap)


def test_docked_date_picker_opens_an_overlay_entry(overlay_root):
    """Tapping the icon button pushes the calendar into the overlay."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    popup = picker.build()
    # Stand in for the rect a real layout pass would assign to the field.
    popup.set_layout_rect(10, 20, 360, 56)
    popup.on_mount()

    assert overlay_root.has_entries() is False

    picker._toggle_dropdown()

    assert overlay_root.has_entries() is True
    assert popup._handle is not None


def test_docked_date_picker_confirming_dismisses_the_overlay(overlay_root):
    """Picking a day keeps the overlay up; OK writes through and tears it down."""
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs)
    popup = picker.build()
    popup.set_layout_rect(10, 20, 360, 56)
    popup.on_mount()
    picker.on_mount()
    picker._toggle_dropdown()
    assert overlay_root.has_entries() is True

    picker._calendar._on_day_tap(date(2026, 7, 4))
    assert overlay_root.has_entries() is True
    assert obs.value is None

    picker._calendar._on_ok()

    assert obs.value == date(2026, 7, 4)
    assert picker._text_obs.value == "07/04/2026"
    assert picker._is_open.value is False
    assert overlay_root.has_entries() is False


def test_docked_date_picker_cancelling_dismisses_the_overlay(overlay_root):
    """Cancel tears the overlay down without touching value."""
    obs: Observable[date | None] = Observable(date(2026, 6, 25))
    picker = DockedDatePicker(value=obs)
    popup = picker.build()
    popup.set_layout_rect(10, 20, 360, 56)
    popup.on_mount()
    picker.on_mount()
    picker._toggle_dropdown()
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_cancel()

    assert obs.value == date(2026, 6, 25)
    assert overlay_root.has_entries() is False


def test_docked_date_picker_custom_style():
    """DockedDatePicker accepts a custom style and passes the calendar down."""
    custom = DockedDatePickerStyle().copy_with(
        field_width=280.0,
        calendar=DatePickerStyle().copy_with(corner_radius=8.0),
    )
    obs: Observable[date | None] = Observable(None)
    picker = DockedDatePicker(value=obs, style=custom)
    assert picker.style.field_width == 280.0
    assert picker._calendar.style.corner_radius == 8.0


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


def test_format_date_round_trips_through_parse_date():
    """_format_date emits text that _parse_date reads back unchanged."""
    original = date(2026, 6, 10)
    assert _format_date(original) == "06/10/2026"
    assert _parse_date(_format_date(original)) == original


def test_format_date_of_none_is_empty():
    """_format_date renders an unset date as an empty string."""
    assert _format_date(None) == ""


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
