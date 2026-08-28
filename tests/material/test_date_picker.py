"""Tests for DatePicker widgets."""

import calendar
import locale
from contextlib import contextmanager
from datetime import date

import pytest

from nuiitivet.material.date_picker import (
    DatePicker,
    DockedDatePicker,
    ModalDateInput,
    ModalDatePicker,
    ModalDateRangePicker,
    _MenuListItem,
    _MonthList,
    _MonthYearHeader,
    _MONTH_NAMES,
    _prev_month,
    _next_month,
)
from nuiitivet.material.date_format import DateFormat, is_date
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
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text import TextBase

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
    obs: Observable[str] = Observable("")
    with pytest.raises(TypeError):
        DockedDatePicker(obs)  # type: ignore[misc]


def test_docked_date_picker_binds_the_text_observable_itself():
    """The observable passed in *is* the field's cell; the widget keeps no copy."""
    obs: Observable[str] = Observable("06/10/2026")
    picker = DockedDatePicker(value=obs)
    assert picker._text_field._editable._external_str_obs is obs
    assert picker._text_field._editable.value == "06/10/2026"


def test_docked_date_picker_starts_from_whatever_text_it_is_given():
    """Unparseable initial text is displayed as-is, not corrected or flagged."""
    obs: Observable[str] = Observable("later")
    picker = DockedDatePicker(value=obs)
    assert picker._text_field._editable.value == "later"
    assert picker._draft_obs.value is None


def test_docked_date_picker_dropdown_starts_closed():
    """The calendar dropdown is closed until the icon button is tapped."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs)
    assert picker._is_open.value is False


def test_docked_date_picker_icon_button_toggles_dropdown():
    """Tapping the trailing calendar icon opens and closes the dropdown."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs)

    picker._toggle_dropdown()
    assert picker._is_open.value is True

    picker._toggle_dropdown()
    assert picker._is_open.value is False


def test_docked_date_picker_day_tap_edits_the_draft_only():
    """A day tap is a selection, not a commit: the text stays put."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True

    # Drive the embedded calendar the way a day-cell tap does.
    picker._calendar._on_day_tap(date(2026, 7, 4))

    assert picker._draft_obs.value == date(2026, 7, 4)
    assert obs.value == "06/25/2026"
    assert picker._is_open.value is True


def test_docked_date_picker_ok_writes_the_draft_back_as_text():
    """OK formats the draft into the bound observable and closes the dropdown."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 1))
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_ok()

    # Two day taps, one commit: intermediate selections never reach the text.
    assert obs.value == "07/04/2026"
    assert picker._is_open.value is False


def test_docked_date_picker_cancel_discards_the_draft():
    """Cancel abandons the selection; the text never saw it."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_cancel()

    assert obs.value == "06/25/2026"
    assert picker._is_open.value is False


def test_docked_date_picker_cancel_does_not_clear_the_text():
    """Cancel must not fall through to DatePicker's clear-the-value default."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True

    picker._calendar._on_cancel()

    assert obs.value == "06/25/2026"


def test_docked_date_picker_dismissing_by_outside_tap_discards_the_draft():
    """An outside tap closes the dropdown without committing the selection."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    # The popup drives is_open back to False on an outside tap.
    picker._is_open.value = False

    assert obs.value == "06/25/2026"


def test_docked_date_picker_reopening_reseeds_the_draft_from_the_text():
    """A draft abandoned by cancel does not survive into the next open."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 8, 1))
    picker._calendar._on_cancel()

    picker._is_open.value = True

    assert picker._draft_obs.value == date(2026, 6, 25)


def test_docked_date_picker_opening_moves_the_calendar_to_the_typed_month():
    """The dropdown opens on the month the text reads as."""
    obs: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()
    picker._calendar.show_month(2020, 1)

    picker._is_open.value = True

    assert (picker._calendar._view_year, picker._calendar._view_month) == (2026, 6)


def test_docked_date_picker_typing_moves_the_calendar_without_writing_anything():
    """Text drives the calendar one way only; the widget writes to no cell of its own."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    obs.value = "03/15/2025"

    assert picker._draft_obs.value == date(2025, 3, 15)
    assert (picker._calendar._view_year, picker._calendar._view_month) == (2025, 3)
    assert obs.value == "03/15/2025"


def test_docked_date_picker_half_typed_text_leaves_the_month_alone():
    """An incomplete date clears the selection but does not move the grid.

    Reformatting or jumping the calendar under a date being typed is what the
    old date-bound binding needed its echo guard for.
    """
    obs: Observable[str] = Observable("03/15/2025")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    obs.value = "03/1"

    assert picker._draft_obs.value is None
    assert (picker._calendar._view_year, picker._calendar._view_month) == (2025, 3)
    assert obs.value == "03/1"


def test_docked_date_picker_reports_no_errors_of_its_own():
    """Unparseable text is a normal state of a typeable field: not the widget's call."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs)
    picker.on_mount()

    obs.value = "not a date"

    assert picker._text_field.is_error is False
    assert obs.value == "not a date"


def test_docked_date_picker_takes_supporting_text_and_is_error_from_the_caller():
    """Both are parameters, so the application is their only writer."""
    obs: Observable[str] = Observable("")
    err: Observable[bool] = Observable(False)
    msg: Observable[str | None] = Observable("mm/dd/yyyy")
    picker = DockedDatePicker(value=obs, supporting_text=msg, is_error=err)
    picker.on_mount()

    assert picker._text_field._is_error_source is err
    assert picker._text_field._supporting_text_source is msg


def test_docked_date_picker_accepts_an_is_error_derived_from_the_same_text():
    """The idiom this binding exists for: one cell, error state derived from it."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(
        value=obs,
        is_error=obs.map(lambda t: bool(t) and not is_date(t)),
    )
    picker.on_mount()
    assert picker._text_field.is_error is False

    obs.value = "nope"

    assert picker._text_field.is_error is True


def test_docked_date_picker_min_max_scope_the_calendar_only():
    """Bounds constrain what can be picked; typed text is the application's to police."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs, min_date=date(2026, 1, 1), max_date=date(2026, 12, 31))
    picker.on_mount()

    assert picker._calendar._min_date == date(2026, 1, 1)
    assert picker._calendar._max_date == date(2026, 12, 31)

    obs.value = "12/31/2025"

    # Out of range, but typed: kept as text, and not flagged by the widget.
    assert obs.value == "12/31/2025"
    assert picker._text_field.is_error is False


def test_docked_date_picker_reads_the_text_with_the_given_format():
    """A custom format places the calendar, so it agrees with the caller's derivation."""
    obs: Observable[str] = Observable("15.03.2025")
    picker = DockedDatePicker(value=obs, date_format=DateFormat("dd.mm.yyyy"))
    picker.on_mount()

    assert picker._draft_obs.value == date(2025, 3, 15)


def test_docked_date_picker_writes_back_in_the_given_format():
    """The calendar emits the caller's pattern, not the default one."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs, date_format=DateFormat("dd.mm.yyyy"))
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_ok()

    assert obs.value == "04.07.2026"


def test_docked_date_picker_round_trips_through_one_format():
    """The two directions cannot disagree, because they come from one object."""
    fmt = DateFormat("yyyy-mm-dd")
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs, date_format=fmt)
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))
    picker._calendar._on_ok()

    # What the calendar wrote is what the calendar reads back on reopening.
    picker._is_open.value = True
    assert picker._draft_obs.value == date(2026, 7, 4)


def test_docked_date_picker_says_nothing_below_the_field_by_default():
    """The slot belongs to the application's error message, so the widget leaves
    it empty rather than spending it on a format hint."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs, date_format=DateFormat("dd.mm.yyyy"))
    assert picker._text_field.supporting_text is None


def test_docked_date_picker_supporting_text_is_passed_through():
    """Including the format hint, for a caller that wants one there."""
    obs: Observable[str] = Observable("")
    fmt = DateFormat("dd.mm.yyyy")
    assert DockedDatePicker(value=obs, supporting_text=str(fmt))._text_field.supporting_text == "dd.mm.yyyy"
    assert DockedDatePicker(value=obs, supporting_text="Arrival")._text_field.supporting_text == "Arrival"


def test_docked_date_picker_read_only_value_is_display_only():
    """With nowhere to write, OK is a no-op -- the same rule TextField applies."""
    source: Observable[str] = Observable("06/25/2026")
    picker = DockedDatePicker(value=source.map(lambda t: t))
    picker.on_mount()
    picker._is_open.value = True
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_ok()

    assert source.value == "06/25/2026"
    assert picker._is_open.value is False


def test_docked_date_picker_mount_does_not_write_to_the_bound_text():
    """Mounting replays the current value; that is not an edit."""
    obs: Observable[str] = Observable("06/10/2026")
    picker = DockedDatePicker(value=obs)

    picker.on_mount()

    assert obs.value == "06/10/2026"


@pytest.fixture
def picker_in_app():
    """Build a ``DockedDatePicker`` inside a real App and return it laid out.

    The popup resolves its overlay by walking to the App (#518), so the picker
    has to be genuinely attached — building it standalone leaves it with nothing
    to resolve against.

    Returns a callable taking the value Observable and yielding
    ``(picker, overlay)``, with the field's layout rect already stood in for.
    """

    def _make(obs: "Observable[str]", **kwargs):
        picker = DockedDatePicker(value=obs, **kwargs)
        app = App(Window(content=picker, width=800, height=600)).main_window
        app.root.mount(app)
        app.root.layout(800, 600)
        popup = picker.built_child
        assert isinstance(popup, PopupBox)
        # Stand in for the rect a real layout pass would assign to the field.
        popup.set_layout_rect(10, 20, 360, 56)
        return picker, app.overlay

    return _make


def test_docked_date_picker_build_anchors_the_calendar_to_the_field():
    """build() wraps the text field in a popup carrying the calendar as content."""
    obs: Observable[str] = Observable("")
    picker = DockedDatePicker(value=obs)

    popup = picker.build()

    assert isinstance(popup, PopupBox)
    assert popup._content is picker._calendar
    assert popup._is_open is picker._is_open
    assert popup._passthrough is False
    assert popup._dismiss_on_outside_tap is True
    # Dropdown hangs below the field's bottom-left corner.
    assert popup._target_anchor == "bottom-left"
    assert popup._content_anchor == "top-left"
    assert popup._offset == (0.0, picker.style.dropdown_gap)


def test_docked_date_picker_opens_an_overlay_entry(picker_in_app):
    """Tapping the icon button pushes the calendar into the overlay."""
    obs: Observable[str] = Observable("")
    picker, overlay = picker_in_app(obs)

    assert overlay.has_entries() is False

    picker._toggle_dropdown()

    assert overlay.has_entries() is True
    assert picker.built_child._handle is not None


def test_docked_date_picker_confirming_dismisses_the_overlay(picker_in_app):
    """Picking a day keeps the overlay up; OK writes through and tears it down."""
    obs: Observable[str] = Observable("")
    picker, overlay = picker_in_app(obs)
    picker._toggle_dropdown()
    assert overlay.has_entries() is True

    picker._calendar._on_day_tap(date(2026, 7, 4))
    assert overlay.has_entries() is True
    assert obs.value == ""

    picker._calendar._on_ok()

    assert obs.value == "07/04/2026"
    assert picker._is_open.value is False
    assert overlay.has_entries() is False


def test_docked_date_picker_commit_reaches_the_field_and_on_change(picker_in_app):
    """A calendar commit is announced exactly like typing: one cell, one signal."""
    obs: Observable[str] = Observable("")
    changed: list[str] = []
    picker, _ = picker_in_app(obs, on_change=changed.append)

    picker._toggle_dropdown()
    picker._calendar._on_day_tap(date(2026, 7, 4))
    picker._calendar._on_ok()

    assert picker._text_field._editable.value == "07/04/2026"
    assert changed == ["07/04/2026"]


def test_docked_date_picker_cancelling_dismisses_the_overlay(picker_in_app):
    """Cancel tears the overlay down without touching the text."""
    obs: Observable[str] = Observable("06/25/2026")
    picker, overlay = picker_in_app(obs)
    picker._toggle_dropdown()
    picker._calendar._on_day_tap(date(2026, 7, 4))

    picker._calendar._on_cancel()

    assert obs.value == "06/25/2026"
    assert overlay.has_entries() is False


def test_docked_date_picker_custom_style():
    """DockedDatePicker accepts a custom style and passes the calendar down."""
    custom = DockedDatePickerStyle().copy_with(
        field_width=280.0,
        calendar=DatePickerStyle().copy_with(corner_radius=8.0),
    )
    obs: Observable[str] = Observable("")
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


# ---------------------------------------------------------------------------
# Month names (locale independence — interim measure for #582)
# ---------------------------------------------------------------------------


@contextmanager
def _lc_time(name: str):
    """Run the block under an LC_TIME that actually translates month names.

    Skips when the locale is missing from the host C library, or when it is
    installed but leaves month names in English — in that case the test could
    not tell a locale-sensitive implementation from a fixed one.
    """
    previous = locale.setlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, name)
    except locale.Error:
        pytest.skip(f"LC_TIME={name} is not available on this machine")
    try:
        if calendar.month_name[8] == "August":
            pytest.skip(f"LC_TIME={name} does not translate month names here")
        yield
    finally:
        locale.setlocale(locale.LC_TIME, previous)


def _text_labels(widget) -> list[str]:
    """Collect the labels of every Text in a built widget tree, in tree order."""
    found: list[str] = []
    for child in widget.children_snapshot():
        if isinstance(child, TextBase) and isinstance(child.label, str):
            found.append(child.label)
        found.extend(_text_labels(child))
    return found


def _menu_item_labels(widget) -> list[str]:
    """Collect the labels of every _MenuListItem in a built widget tree."""
    found: list[str] = []
    for child in widget.children_snapshot():
        if isinstance(child, _MenuListItem):
            found.append(child._label)
        found.extend(_menu_item_labels(child))
    return found


def test_month_names_are_english():
    """_MONTH_NAMES is 0-indexed English, unlike 1-indexed calendar.month_name."""
    assert len(_MONTH_NAMES) == 12
    assert _MONTH_NAMES[0] == "January"
    assert _MONTH_NAMES[7] == "August"
    assert _MONTH_NAMES[11] == "December"


def test_month_year_header_stays_english_under_a_translating_locale():
    """The inline header reads "August 2026" whatever LC_TIME says."""
    with _lc_time("ja_JP.UTF-8"):
        header = _MonthYearHeader(
            2026,
            8,
            on_prev=lambda: None,
            on_next=lambda: None,
            style=CalendarStyle(),
        )
        assert _text_labels(header.build()) == ["August", "2026"]


def test_month_list_stays_english_under_a_translating_locale():
    """The month dropdown lists English month names whatever LC_TIME says."""
    with _lc_time("ja_JP.UTF-8"):
        month_list = _MonthList(
            8,
            on_select=lambda _m: None,
            list_height=200,
            item_width=100.0,
            style=DatePickerStyle(),
        )
        assert _menu_item_labels(month_list.build()) == list(_MONTH_NAMES)
