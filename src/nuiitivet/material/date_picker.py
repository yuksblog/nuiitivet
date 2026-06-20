"""Material Design 3 DatePicker widgets.

This module provides three date-picker variants following MD3 Expressive spec:

- :class:`DockedDatePicker`: Inline calendar picker.
- :class:`ModalDatePicker`: Dialog-based single-date picker.
  Works with :class:`OverlayHandle` when displayed via
  ``overlay.dialog(ModalDatePicker())``.
- :class:`ModalDateRangePicker`: Dialog-based date range picker.
  Works with :class:`OverlayHandle` when displayed via
  ``overlay.dialog(ModalDateRangePicker())``.
- :class:`ModalDateInput`: Text-field-based date entry dialog.  Works with
  :class:`OverlayHandle` when displayed via ``overlay.dialog(ModalDateInput())``.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date as _Date, datetime as _DateTime, timedelta as _TimeDelta
from typing import Callable, Literal, Optional, Tuple, TYPE_CHECKING

from nuiitivet.animation import Animatable
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroller import Scroller
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.material.buttons import Button, IconButton
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL
from nuiitivet.modifiers.transform import rotate
from nuiitivet.modifiers.visible import visible
from nuiitivet.material.icon import Icon
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.divider import Divider
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.theme.elevation import md3_elevation_to_shadow
from nuiitivet.observable import Observable, ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.overlay import OverlayAware
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import VoidCallback
from nuiitivet.common.logging_once import exception_once

if TYPE_CHECKING:
    from nuiitivet.material.styles.date_picker_style import (
        DatePickerStyle,
        DockedDatePickerStyle,
        ModalDatePickerStyle,
        ModalDateRangePickerStyle,
        ModalDateInputStyle,
    )

_logger = logging.getLogger(__name__)

# Weekday column headers — Sunday first, matching the MD3 spec.
_WEEKDAY_LABELS: Tuple[str, ...] = ("S", "M", "T", "W", "T", "F", "S")


def _prev_month(year: int, month: int) -> Tuple[int, int]:
    """Return (year, month) for the month preceding the given one."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> Tuple[int, int]:
    """Return (year, month) for the month following the given one."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _fill_six_weeks(year: int, month: int) -> list[list[_Date]]:
    """Return exactly 6 weeks of dates for the calendar grid.

    Fills leading and trailing empty slots with dates from adjacent months so
    the grid always has 6 full weeks (42 cells), starting on Sunday.

    Args:
        year: Calendar year.
        month: Calendar month (1\u201312).

    Returns:
        List of 6 weeks, each containing 7 :class:`datetime.date` objects.
    """
    first_day = _Date(year, month, 1)
    # ``isoweekday() % 7`` maps Sunday→0, Monday→1, …, Saturday→6 so the grid
    # always begins on the Sunday on or before the first of the month.
    start = first_day - _TimeDelta(days=first_day.isoweekday() % 7)
    return [[start + _TimeDelta(days=w * 7 + d) for d in range(7)] for w in range(6)]


def _make_day_tap(day: _Date, callback: Callable[[_Date], None]) -> VoidCallback:
    """Bind ``day`` to ``callback`` as a zero-argument tap handler.

    Defined at module scope so the captured ``day`` is bound per call rather
    than leaking the loop variable from the calendar grid builder.
    """

    def _tap() -> None:
        callback(day)

    return _tap


# ---------------------------------------------------------------------------
# Internal: _DayCell
# ---------------------------------------------------------------------------


class _DayCell(InteractiveWidget):
    """A single clickable day cell rendered with circular MD3 styling.

    Args:
        day: Day-of-month value (1–31). Must be > 0; cells with ``day=0`` are
            empty placeholders.
        is_selected: Whether this day is the currently selected date.
        is_today: Whether this day is today.
        is_outside_month: Whether this day belongs to an adjacent month.
        is_disabled: Whether this day is outside the allowed date range.
        is_in_range: Whether this day falls between the range start and end.
        is_range_start: Whether this day is the first day of the selection range.
        is_range_end: Whether this day is the last day of the selection range.
        on_tap: Callback invoked when the cell is tapped.
        style: DatePickerStyle controlling sizes and colors.
    """

    def __init__(
        self,
        day: int,
        *,
        is_selected: bool = False,
        is_today: bool = False,
        is_outside_month: bool = False,
        is_disabled: bool = False,
        is_in_range: bool = False,
        is_range_start: bool = False,
        is_range_end: bool = False,
        on_tap: Optional[VoidCallback] = None,
        cell_width: Optional[int] = None,
        style: "DatePickerStyle",
    ) -> None:
        """Initialize _DayCell.

        Args:
            day: Day number (1-31), or 0 for empty placeholder.
            is_selected: Day is the selected date.
            is_today: Day is today.
            is_outside_month: Day belongs to adjacent month.
            is_disabled: Day is outside the allowed range.
            is_in_range: Day falls between range start and end (exclusive).
            is_range_start: Day is the range start.
            is_range_end: Day is the range end.
            on_tap: Click callback.
            cell_width: Cell width in px. Defaults to the 40dp selection circle
                size. The range band spans the full width, so passing the 48dp
                column slot makes the band continuous across adjacent in-range
                days (the circle/state layer stay 40dp, centred).
            style: Date picker style.
        """
        effective_disabled = day <= 0 or is_disabled
        if is_selected or is_range_start or is_range_end:
            state_layer = ColorRole.ON_PRIMARY
        elif is_today:
            state_layer = ColorRole.PRIMARY
        else:
            state_layer = ColorRole.ON_SURFACE_VARIANT
        super().__init__(
            on_click=on_tap if not effective_disabled else None,
            disabled=effective_disabled,
            width=cell_width if cell_width is not None else style.date_cell_size,
            height=style.date_cell_size,
            state_layer_color=state_layer,
        )
        self._day = day
        self._is_selected = is_selected
        self._is_today = is_today
        self._is_outside_month = is_outside_month
        self._is_in_range = is_in_range
        self._is_range_start = is_range_start
        self._is_range_end = is_range_end
        self._style = style

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Render the day cell with circle background, text, and state layer.

        Args:
            canvas: Skia canvas.
            x: Left edge in pixels.
            y: Top edge in pixels.
            width: Allocated width in pixels.
            height: Allocated height in pixels.
        """
        self.set_last_rect(x, y, width, height)
        if self._day <= 0:
            return

        from nuiitivet.theme.theme import Theme
        from nuiitivet.rendering.skia import (
            draw_oval,
            get_default_font_fallbacks,
            get_typeface,
            make_font,
            make_paint,
            make_rect,
            make_text_blob,
            measure_text_ink_bounds,
        )
        from nuiitivet.theme.resolver import resolve_color_to_rgba

        theme = Theme.of(self)
        style = self._style

        cx = float(x) + width / 2.0
        cy = float(y) + height / 2.0
        cell_r = float(style.date_cell_radius)
        state_r = float(style.state_layer_size) / 2.0

        # 1. Range background band (height = state_layer_size)
        is_range_member = self._is_in_range or self._is_range_start or self._is_range_end
        if is_range_member:
            bg_color = resolve_color_to_rgba(style.range_active_indicator_background, theme=theme)
            if bg_color:
                band_h = float(style.state_layer_size)
                band_y = cy - band_h / 2.0
                rng_paint = make_paint(color=bg_color, style="fill")
                if rng_paint:
                    if self._is_range_start and not self._is_range_end:
                        # Right half only
                        canvas.drawRect(
                            make_rect(cx, band_y, float(x + width) - cx, band_h),
                            rng_paint,
                        )
                    elif self._is_range_end and not self._is_range_start:
                        # Left half only
                        canvas.drawRect(
                            make_rect(float(x), band_y, cx - float(x), band_h),
                            rng_paint,
                        )
                    else:
                        # Full width (strictly in-range, or same-day start==end)
                        canvas.drawRect(
                            make_rect(float(x), band_y, float(width), band_h),
                            rng_paint,
                        )

        # 2. Selection circle or today outline
        if self._is_selected or self._is_range_start or self._is_range_end:
            sel_bg = resolve_color_to_rgba(style.date_selected_background, theme=theme)
            if sel_bg:
                paint = make_paint(color=sel_bg, style="fill", aa=True)
                if paint:
                    draw_oval(
                        canvas,
                        make_rect(cx - cell_r, cy - cell_r, cell_r * 2.0, cell_r * 2.0),
                        paint,
                    )
        elif self._is_today:
            outline = resolve_color_to_rgba(style.date_today_outline_color, theme=theme)
            if outline:
                paint = make_paint(color=outline, style="stroke", stroke_width=1.0, aa=True)
                if paint:
                    r = cell_r - 0.5
                    draw_oval(
                        canvas,
                        make_rect(cx - r, cy - r, r * 2.0, r * 2.0),
                        paint,
                    )

        # 3. Day number text
        if self._is_selected or self._is_range_start or self._is_range_end:
            text_spec = style.date_selected_text
        elif self._is_today:
            text_spec = style.date_today_text
        elif self._is_in_range:
            text_spec = style.range_date_in_range_text
        else:
            text_spec = style.date_unselected_text

        text_color = resolve_color_to_rgba(text_spec, theme=theme)
        if self._is_outside_month and text_color:
            r_c, g_c, b_c, a_c = text_color
            text_color = (int(r_c), int(g_c), int(b_c), int(a_c * style.date_outside_month_opacity))
        elif self.disabled and text_color:
            r_c, g_c, b_c, a_c = text_color
            text_color = (int(r_c), int(g_c), int(b_c), int(a_c * 0.38))

        if text_color:
            try:
                font_fallbacks = get_default_font_fallbacks()
                typeface = get_typeface(family_candidates=tuple(font_fallbacks) if font_fallbacks else None)
                font_size = float(style.date_font_size)
                font = make_font(typeface, font_size)
                text_str = str(self._day)
                bounds = measure_text_ink_bounds(typeface, font_size, text_str)
                # Center text at (cx, cy): baseline = cy - midpoint(top, bottom)
                draw_x = cx - (bounds[0] + bounds[2]) / 2.0
                draw_y = cy - (bounds[1] + bounds[3]) / 2.0
                blob = make_text_blob(text_str, font)
                if blob:
                    text_paint = make_paint(color=text_color, style="fill", aa=True)
                    if text_paint:
                        canvas.drawTextBlob(blob, draw_x, draw_y, text_paint)
            except Exception:
                exception_once(_logger, "day_cell_text_exc", "Failed to draw day cell text")

        # 4. State layer (circular)
        if not self.disabled:
            opacity = self._get_active_state_layer_opacity()
            if opacity > 0.0:
                try:
                    from nuiitivet.theme.resolver import resolve_color_to_rgba as _resolve

                    state_c = _resolve(self.state_layer_color, theme=theme)
                    if state_c:
                        r_s, g_s, b_s, a_s = state_c
                        sl_paint = make_paint(color=(r_s, g_s, b_s, a_s * opacity), style="fill", aa=True)
                        if sl_paint:
                            draw_oval(
                                canvas,
                                make_rect(cx - state_r, cy - state_r, state_r * 2.0, state_r * 2.0),
                                sl_paint,
                            )
                except Exception:
                    exception_once(_logger, "day_cell_state_layer_exc", "Failed to draw state layer")

        # 5. Focus ring (circular)
        if not self.disabled and self.should_show_focus_ring:
            try:
                from nuiitivet.theme.resolver import resolve_color_to_rgba as _resolve

                focus_c = _resolve(self._FOCUS_RING_COLOR, theme=theme)
                if focus_c:
                    thickness = self._FOCUS_RING_THICKNESS
                    offset = self._FOCUS_RING_OFFSET
                    ring_r = state_r + offset + thickness / 2.0
                    fr_paint = make_paint(color=focus_c, style="stroke", stroke_width=thickness, aa=True)
                    if fr_paint:
                        draw_oval(
                            canvas,
                            make_rect(cx - ring_r, cy - ring_r, ring_r * 2.0, ring_r * 2.0),
                            fr_paint,
                        )
            except Exception:
                exception_once(_logger, "day_cell_focus_ring_exc", "Failed to draw focus ring")


# ---------------------------------------------------------------------------
# Internal grid constants
# ---------------------------------------------------------------------------

_YEAR_GRID_COLS = 4
_YEAR_GRID_ROWS = 5  # 20 years per page (4 × 5)
_YEAR_CHIP_COLS = 3  # MD3 modal year grid: 3 × 72dp + 2 × 30dp gap + 2 × 30dp pad = 336dp
_YEAR_LIST_PAGE_SIZE = 7  # 7 years per page for docked year list


def _centered_scroll_controller(
    *, selected_index: int, item_height: int, viewport_height: int
) -> ScrollController:
    """Return a vertical :class:`ScrollController` that centres the selected row.

    The initial offset positions the selected item's centre at the viewport
    centre. ``initial_offsets`` is used (rather than ``scroll_to``) so the
    offset is not pre-clamped against a max-extent that is still zero before
    the first layout; the viewport clamps it into range once measured.

    Args:
        selected_index: Zero-based index of the selected row.
        item_height: Height of each row in pixels.
        viewport_height: Visible scroller height in pixels.
    """
    item_center = (selected_index + 0.5) * item_height
    offset = max(0.0, item_center - viewport_height / 2.0)
    return ScrollController(
        axes=(ScrollDirection.VERTICAL,),
        primary_axis=ScrollDirection.VERTICAL,
        initial_offsets={ScrollDirection.VERTICAL: offset},
    )


def _modal_calendar_body_height(style: "DatePickerStyle") -> int:
    """Return the modal calendar body height (weekday row + 6-week grid).

    Used to size the year-selection grid so the dialog height stays stable when
    toggling between the calendar and year views. Mirrors the paddings applied in
    :meth:`_CalendarGrid.build`: weekday row padded (12, 15, 12, 8) around a 14dp
    glyph, date grid padded (12, 8, 12, 4) around six 40dp rows with 8dp inter-row
    gaps.
    """
    weekday_block = 15 + 14 + 8
    grid_block = 8 + (6 * int(style.date_cell_size) + 5 * 8) + 4
    return weekday_block + grid_block


# Modal action row height: text buttons (48dp container) inside (12, 4, 12, 12)
# padding -> 4 + 48 + 12. The year-selection view hides the action row, so the
# year grid is grown by this amount to keep the dialog height constant across
# the calendar/year toggle.
_MODAL_ACTION_ROW_HEIGHT = 4 + 48 + 12


# ---------------------------------------------------------------------------
# Internal: _YearChip (modal year-selection chip, 72×36dp pill)
# ---------------------------------------------------------------------------


class _YearChip(InteractiveWidget):
    """A 72×36dp pill-shaped year chip for the modal year-selection grid."""

    def __init__(
        self,
        year: int,
        *,
        is_selected: bool = False,
        on_tap: Optional[VoidCallback] = None,
        style: "ModalDatePickerStyle",
    ) -> None:
        super().__init__(
            on_click=on_tap,
            width=int(style.year_chip_width),
            height=int(style.year_chip_height),
            state_layer_color=ColorRole.ON_PRIMARY if is_selected else ColorRole.ON_SURFACE_VARIANT,
        )
        self._year = year
        self._is_selected = is_selected
        self._style = style

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Render the year chip with pill background and centred year text."""
        self.set_last_rect(x, y, width, height)
        from nuiitivet.theme.theme import Theme
        from nuiitivet.rendering.skia import (
            get_default_font_fallbacks,
            get_typeface,
            make_font,
            make_paint,
            make_rect,
            make_text_blob,
            measure_text_ink_bounds,
        )
        from nuiitivet.theme.resolver import resolve_color_to_rgba

        theme = Theme.of(self)
        cx = float(x) + width / 2.0
        cy = float(y) + height / 2.0
        r = self._style.year_chip_radius

        # Selected: fill the full chip with PRIMARY
        if self._is_selected:
            bg = resolve_color_to_rgba(self._style.year_chip_selected_background, theme=theme)
            if bg:
                p = make_paint(color=bg, style="fill", aa=True)
                if p:
                    try:
                        canvas.drawRoundRect(
                            make_rect(float(x), float(y), float(width), float(height)),
                            r,
                            r,
                            p,
                        )
                    except Exception:
                        exception_once(_logger, "year_chip_bg_exc", "Failed to draw year chip background")

        # Year text
        text_spec = self._style.year_chip_selected_text if self._is_selected else self._style.year_chip_unselected_text
        text_color = resolve_color_to_rgba(text_spec, theme=theme)
        if text_color:
            try:
                ff = get_default_font_fallbacks()
                typeface = get_typeface(family_candidates=tuple(ff) if ff else None)
                fs = float(self._style.date_font_size)
                font = make_font(typeface, fs)
                year_str = str(self._year)
                bounds = measure_text_ink_bounds(typeface, fs, year_str)
                draw_x = cx - (bounds[0] + bounds[2]) / 2.0
                draw_y = cy - (bounds[1] + bounds[3]) / 2.0
                blob = make_text_blob(year_str, font)
                if blob:
                    tp = make_paint(color=text_color, style="fill", aa=True)
                    if tp:
                        canvas.drawTextBlob(blob, draw_x, draw_y, tp)
            except Exception:
                exception_once(_logger, "year_chip_text_exc", "Failed to draw year chip text")

        # State layer (full chip)
        if not self.disabled:
            opacity = self._get_active_state_layer_opacity()
            if opacity > 0.0:
                try:
                    from nuiitivet.theme.resolver import resolve_color_to_rgba as _r

                    sc = _r(self.state_layer_color, theme=theme)
                    if sc:
                        r_c, g_c, b_c, a_c = sc
                        sl_p = make_paint(color=(r_c, g_c, b_c, a_c * opacity), style="fill", aa=True)
                        if sl_p:
                            canvas.drawRoundRect(
                                make_rect(float(x), float(y), float(width), float(height)),
                                r,
                                r,
                                sl_p,
                            )
                except Exception:
                    exception_once(_logger, "year_chip_sl_exc", "Failed to draw year chip state layer")


# ---------------------------------------------------------------------------
# Internal: _YearChipGrid (modal year-selection chip grid, 5 columns)
# ---------------------------------------------------------------------------


class _YearChipGrid(ComposableWidget):
    """Scrollable 3-column year chip grid for the modal picker.

    Mirrors the docked year list (:class:`_YearList`) continuous-scroll model
    but renders 72×36dp pill chips in a 3-column grid per the MD3 modal
    year-selection measurement: ``UniformFlow`` with 3 columns, 30dp main/cross
    gaps and 30dp inner padding, wrapped in a ``Scroller`` padded
    ``(12, 15, 12, 4)`` with the scrollbar hidden. The selected year's row is
    centred in the viewport on open.

    Args:
        selected_year: Currently selected year.
        on_select: Callback invoked with the selected year.
        list_height: Pixel height for the :class:`Scroller` viewport.
        style: DatePickerStyle.
    """

    # Symmetric year range shown around the selected year.
    _YEAR_RANGE = 60

    def __init__(
        self,
        selected_year: int,
        *,
        on_select: Callable[[int], None],
        list_height: int,
        style: "ModalDatePickerStyle",
    ) -> None:
        super().__init__()
        self._selected_year = selected_year
        self._on_select = on_select
        self._list_height = list_height
        self._style = style

    def build(self) -> Widget:
        """Build the scrollable 3-column year chip grid."""
        style = self._style
        chip_gap = int(style.year_chip_gap)
        start_year = self._selected_year - self._YEAR_RANGE
        end_year = self._selected_year + self._YEAR_RANGE

        chips: list[Widget] = []
        for year in range(start_year, end_year + 1):
            _y = year
            chips.append(
                _YearChip(
                    year,
                    is_selected=(year == self._selected_year),
                    on_tap=lambda _y=_y: self._on_select(_y),
                    style=style,
                )
            )

        grid = UniformFlow(
            chips,
            columns=_YEAR_CHIP_COLS,
            main_gap=chip_gap,
            cross_gap=chip_gap,
            padding=chip_gap,
            item_alignment="center",
        )

        # Centre the selected year's row in the viewport. Row pitch = chip height
        # + main gap; the selected year sits at ``selected_row`` from the top.
        selected_index = self._selected_year - start_year
        selected_row = selected_index // _YEAR_CHIP_COLS
        row_pitch = int(style.year_chip_height) + chip_gap
        controller = _centered_scroll_controller(
            selected_index=selected_row,
            item_height=row_pitch,
            viewport_height=self._list_height,
        )

        return Scroller(
            grid,
            scroll_controller=controller,
            scrollbar_enabled=False,
            width=int(style.container_width),
            height=self._list_height,
            padding=(12, 15, 12, 4),
        )


# ---------------------------------------------------------------------------
# Internal: _MenuListItem, _MonthList, _YearList  (docked picker list menus)
# ---------------------------------------------------------------------------


class _MenuListItem(InteractiveWidget):
    """Full-width list item for docked picker month/year menus.

    MD3 layout per row:
    - Left 16dp  |  check icon 24dp  |  Left 16dp  |  label (left-aligned)  |  Right 16dp
    - Height 48dp, text vertically centred.
    Selected row shows full-width SECONDARY_CONTAINER background and a
    ``check`` leading icon; non-selected rows show no background and no icon.

    Args:
        label: Display text.
        is_selected: Whether this item is currently selected.
        on_tap: Tap callback.
        item_width: Item width in dp.
        style: DatePickerStyle.
    """

    # MD3 layout constants (dp)
    _PADDING_LEADING: int = 16
    _CHECK_ICON_SIZE: int = 24
    _PADDING_BETWEEN: int = 16

    def __init__(
        self,
        label: str,
        *,
        is_selected: bool = False,
        on_tap: Optional[VoidCallback] = None,
        item_width: float,
        style: "DockedDatePickerStyle",
    ) -> None:
        # Paint-only: no child widget tree. The MD3 visual (full-width selected
        # background, state layer, focus ring) is drawn by InteractiveWidget;
        # the check glyph + label are drawn directly in draw_children(). This
        # avoids building a Row/Box/Text/Icon subtree per row, which dominates
        # the cost of the year list (~101 rows).
        super().__init__(
            on_click=on_tap,
            width=int(item_width),
            height=int(style.menu_list_item_height),
            state_layer_color=ColorRole.ON_SURFACE,
            background_color=style.menu_list_item_selected_background if is_selected else None,
        )
        self._label = label
        self._is_selected = is_selected
        self._style = style

        # Only the selected row shows a check glyph. Reuse the Icon widget's
        # robust glyph-rendering path (one instance, painted directly) rather
        # than duplicating Material Symbols font resolution here.
        self._check_icon: Optional[Icon] = None
        if is_selected:
            icon = Icon("check", size=self._CHECK_ICON_SIZE)
            icon._parent = self  # parent link so Theme.of() resolves during paint
            self._check_icon = icon

    def draw_children(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Draw the leading check glyph (selected only) and the left-aligned label."""
        from nuiitivet.theme.theme import Theme
        from nuiitivet.rendering.skia import (
            get_default_font_fallbacks,
            get_typeface,
            make_font,
            make_paint,
            make_text_blob,
            measure_text_ink_bounds,
        )
        from nuiitivet.theme.resolver import resolve_color_to_rgba

        style = self._style

        # Leading check glyph (selected row only), vertically centred in the row.
        if self._check_icon is not None:
            icon_x = x + self._PADDING_LEADING
            icon_y = y + (height - self._CHECK_ICON_SIZE) // 2
            try:
                self._check_icon.set_last_rect(icon_x, icon_y, self._CHECK_ICON_SIZE, self._CHECK_ICON_SIZE)
                self._check_icon.paint(canvas, icon_x, icon_y, self._CHECK_ICON_SIZE, self._CHECK_ICON_SIZE)
            except Exception:
                exception_once(_logger, "menu_item_icon_exc", "Failed to draw menu item check icon")

        # Label text, left-aligned after the 16dp + 24dp icon + 16dp slot,
        # vertically centred (MD3 docked menu list item).
        text_spec = style.menu_list_item_selected_text if self._is_selected else style.menu_list_item_text
        text_color = resolve_color_to_rgba(text_spec, theme=Theme.of(self))
        if not text_color:
            return
        try:
            ff = get_default_font_fallbacks()
            typeface = get_typeface(family_candidates=tuple(ff) if ff else None)
            fs = float(style.date_font_size)
            font = make_font(typeface, fs)
            bounds = measure_text_ink_bounds(typeface, fs, self._label)
            text_left = x + self._PADDING_LEADING + self._CHECK_ICON_SIZE + self._PADDING_BETWEEN
            # Align the ink-left edge to text_left; centre vertically at the row mid.
            draw_x = float(text_left) - bounds[0]
            cy = float(y) + height / 2.0
            draw_y = cy - (bounds[1] + bounds[3]) / 2.0
            blob = make_text_blob(self._label, font)
            if blob:
                tp = make_paint(color=text_color, style="fill", aa=True)
                if tp:
                    canvas.drawTextBlob(blob, draw_x, draw_y, tp)
        except Exception:
            exception_once(_logger, "menu_item_text_exc", "Failed to draw menu item text")


class _MonthList(ComposableWidget):
    """Scrollable list of all 12 months for the docked picker.

    Args:
        current_month: Currently selected month (1–12).
        on_select: Callback invoked with the selected month number.
        list_height: Pixel height for the :class:`Scroller` viewport.
        item_width: Width of each list item (inner container width).
        style: DatePickerStyle.
    """

    def __init__(
        self,
        current_month: int,
        *,
        on_select: Callable[[int], None],
        list_height: int,
        item_width: float,
        style: "DockedDatePickerStyle",
    ) -> None:
        super().__init__()
        self._current_month = current_month
        self._on_select = on_select
        self._list_height = list_height
        self._item_width = item_width
        self._style = style

    def build(self) -> Widget:
        """Build a scrollable column of 12 month list items."""
        style = self._style
        item_w = self._item_width
        items: list[Widget] = []
        for m in range(1, 13):
            _m = m
            items.append(
                _MenuListItem(
                    calendar.month_name[m],
                    is_selected=(m == self._current_month),
                    on_tap=lambda _m=_m: self._on_select(_m),
                    item_width=item_w,
                    style=style,
                )
            )
        controller = _centered_scroll_controller(
            selected_index=self._current_month - 1,
            item_height=int(style.menu_list_item_height),
            viewport_height=self._list_height,
        )
        return Scroller(
            Column(items, gap=0, width=int(item_w)),
            scroll_controller=controller,
            width=int(item_w),
            height=self._list_height,
        )


class _YearList(ComposableWidget):
    """Scrollable list of years for the docked picker.

    Displays a scrollable column of years centered on ``current_year``.

    Args:
        current_year: Currently selected year.
        on_select: Callback invoked with the selected year.
        list_height: Pixel height for the :class:`Scroller` viewport.
        item_width: Width of each list item (inner container width).
        style: DatePickerStyle.
    """

    # Symmetric range around the current year shown in the list
    _YEAR_RANGE = 50

    def __init__(
        self,
        current_year: int,
        *,
        on_select: Callable[[int], None],
        list_height: int,
        item_width: float,
        style: "DockedDatePickerStyle",
    ) -> None:
        super().__init__()
        self._current_year = current_year
        self._on_select = on_select
        self._list_height = list_height
        self._item_width = item_width
        self._style = style

    def build(self) -> Widget:
        """Build a scrollable column of years."""
        style = self._style
        item_w = self._item_width
        items: list[Widget] = []
        for year in range(self._current_year - self._YEAR_RANGE, self._current_year + self._YEAR_RANGE + 1):
            _y = year
            items.append(
                _MenuListItem(
                    str(year),
                    is_selected=(year == self._current_year),
                    on_tap=lambda _y=_y: self._on_select(_y),
                    item_width=item_w,
                    style=style,
                )
            )
        controller = _centered_scroll_controller(
            selected_index=self._YEAR_RANGE,
            item_height=int(style.menu_list_item_height),
            viewport_height=self._list_height,
        )
        return Scroller(
            Column(items, gap=0, width=int(item_w)),
            scroll_controller=controller,
            width=int(item_w),
            height=self._list_height,
        )


# ---------------------------------------------------------------------------
# Internal: _MonthYearHeader
# ---------------------------------------------------------------------------


class _MonthYearHeader(ComposableWidget):
    """Navigation header for the date picker.

    Supports two layout variants:

    - ``"docked"``: Two separate clickable ``[Month ▾]`` / ``[Year ▾]``
      buttons flanked by prev/next chevrons.
    - ``"modal"``: A single combined ``[Month Year ▾/▴]`` button on the left
      with prev/next chevrons on the right.

    Args:
        year: Current view year.
        month: Current view month (1–12).
        on_prev: Callback for the previous-month button.
        on_next: Callback for the next-month button.
        on_month_tap: (docked) Callback when the Month button is tapped.
        on_year_tap: (docked) Callback when the Year button is tapped.
        on_toggle_year_picker: (modal) Callback to toggle the year picker.
        year_picker_active: (modal) Whether the year picker is currently shown.
        active_view: (docked) Which list menu is open (``"month"``/``"year"``),
            or ``None`` for the calendar. The open group's dropdown arrow points
            up; the opposite group's controls hide and its label greys out.
        month_rotation: (docked) Observable degrees for the month dropdown arrow.
        year_rotation: (docked) Observable degrees for the year dropdown arrow.
        variant: ``"docked"`` or ``"modal"``.
        nav_padding: (modal) Outer padding (left, top, right, bottom) of the
            nav row. MD3 modal measurement: ``(12, 6, 12, 2)`` in the calendar
            view, ``(12, 6, 12, 8)`` in the year-selection view.
        style: DatePickerStyle.
    """

    def __init__(
        self,
        year: int,
        month: int,
        *,
        on_prev: VoidCallback,
        on_next: VoidCallback,
        on_prev_year: Optional[VoidCallback] = None,
        on_next_year: Optional[VoidCallback] = None,
        on_month_tap: Optional[VoidCallback] = None,
        on_year_tap: Optional[VoidCallback] = None,
        on_toggle_year_picker: Optional[VoidCallback] = None,
        year_picker_active: bool = False,
        active_view: Optional[Literal["month", "year"]] = None,
        month_rotation: Optional[ReadOnlyObservableProtocol[float]] = None,
        year_rotation: Optional[ReadOnlyObservableProtocol[float]] = None,
        variant: Literal["docked", "modal"] = "docked",
        nav_padding: Tuple[int, int, int, int] = (12, 6, 12, 2),
        style: "DatePickerStyle",
    ) -> None:
        super().__init__()
        self._year = year
        self._month = month
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_prev_year = on_prev_year
        self._on_next_year = on_next_year
        self._on_month_tap = on_month_tap
        self._on_year_tap = on_year_tap
        self._on_toggle_year_picker = on_toggle_year_picker
        self._year_picker_active = year_picker_active
        self._active_view = active_view
        self._month_rotation = month_rotation
        self._year_rotation = year_rotation
        self._variant = variant
        self._nav_padding = nav_padding
        self._style = style

    def build(self) -> Widget:
        """Build the navigation header row."""
        month_name = calendar.month_name[self._month]
        s = self._style

        if self._variant == "docked":
            # Layout (measurement image):
            #   [← Month ▾ →]  [spacer]  [← Year ▾ →]
            # Each group: chevron_left | Text(label) | IconButton(arrow_drop_down) | chevron_right
            # Dropdown icon: 18dp per md.comp.date-picker.docked.menu-button.icon.size token.
            #
            # When one list menu is open (``active_view``), that group's dropdown
            # arrow rotates to point up while the opposite group collapses to a
            # greyed-out (disabled-looking) label with its chevrons/dropdown hidden.
            icon_size = s.menu_button_icon_size
            dropdown_style = IconButtonStyle.standard().copy_with(icon_size=icon_size)

            month_active = self._active_view == "month"
            year_active = self._active_view == "year"
            # A group is "dimmed" while the *other* group's menu is open.
            month_dimmed = year_active
            year_dimmed = month_active
            # While any selection menu is open, prev/next chevrons are
            # meaningless (selection is via the grid), so both groups hide them.
            any_active = self._active_view is not None
            # MD3 disabled menu-button label: ON_SURFACE at 0.38 opacity.
            disabled_text_color = (ColorRole.ON_SURFACE, 0.38)

            def _label(text: str, dimmed: bool) -> Widget:
                return Text(
                    text,
                    style=TextStyle(
                        font_size=int(s.menu_button_font_size),
                        color=disabled_text_color if dimmed else s.menu_button_text,
                    ),
                )

            def _dropdown(
                on_tap: Optional[VoidCallback],
                rotation: Optional[ReadOnlyObservableProtocol[float]],
            ) -> Widget:
                btn: Widget = IconButton("arrow_drop_down", on_click=on_tap, style=dropdown_style)
                if rotation is not None:
                    btn = btn.modifier(rotate(rotation))
                return btn

            def _nav_group(
                label_text: str,
                *,
                dimmed: bool,
                on_prev: Optional[VoidCallback],
                on_next: Optional[VoidCallback],
                on_tap: Optional[VoidCallback],
                rotation: Optional[ReadOnlyObservableProtocol[float]],
            ) -> Widget:
                # The full chevron/dropdown structure is always built so the label
                # keeps its position; hidden parts are merely made invisible via
                # visible() (opacity 0 + no input), preserving their layout space.
                # Chevrons hide whenever any selection menu is open; the dropdown
                # only hides when this group is dimmed (so the active group keeps
                # its rotated arrow). The dimmed group greys its label.
                show_chevrons = not any_active
                show_dropdown = not dimmed
                return Row(
                    [
                        IconButton("chevron_left", on_click=on_prev).modifier(visible(show_chevrons)),
                        Container(width=12),
                        _label(label_text, dimmed),
                        _dropdown(on_tap, rotation).modifier(visible(show_dropdown)),
                        Container(width=1),
                        IconButton("chevron_right", on_click=on_next).modifier(visible(show_chevrons)),
                    ],
                    gap=0,
                    cross_alignment="center",
                )

            month_nav: Widget = _nav_group(
                month_name,
                dimmed=month_dimmed,
                on_prev=self._on_prev,
                on_next=self._on_next,
                on_tap=self._on_month_tap,
                rotation=self._month_rotation,
            )
            year_nav: Widget = _nav_group(
                str(self._year),
                dimmed=year_dimmed,
                on_prev=self._on_prev_year,
                on_next=self._on_next_year,
                on_tap=self._on_year_tap,
                rotation=self._year_rotation,
            )
            # Padding order is (left, top, right, bottom). The chevron/dropdown
            # navigation are 40dp IconButtons (= MD3 menu-button.container.height);
            # we size the row to that 40dp content with 20dp above and 15dp below
            # (MD3 docked header measurement) -> header block = 20 + 40 + 15 = 75dp.
            return Row(
                [month_nav, year_nav],
                main_alignment="space-between",
                cross_alignment="center",
                padding=(4, 20, 4, 15),
                width=s.container_width,
            )
        else:
            # Modal: [Text("Month Year") IconButton(▾/▴)]   [← →]
            arrow_icon = "arrow_drop_up" if self._year_picker_active else "arrow_drop_down"
            dropdown_style = IconButtonStyle.standard().copy_with(icon_size=s.menu_button_icon_size)
            toggle_btn: Widget = Row(
                [
                    Text(
                        f"{month_name} {self._year}",
                        style=TextStyle(
                            font_size=int(s.menu_button_font_size),
                            color=s.menu_button_text,
                        ),
                    ),
                    IconButton(arrow_icon, on_click=self._on_toggle_year_picker, style=dropdown_style),
                ],
                gap=0,
                cross_alignment="center",
            )
            # MD3 modal nav measurement: the row content is 48dp tall, driven by
            # the prev/next chevron icon buttons (48dp; the default icon button is
            # 40dp). Padding is (12, 6, 12, 2). The toggle button (40dp) and the
            # chevrons are cross-centred within the 48dp content row.
            chevron_style = IconButtonStyle.standard().copy_with(container_height=48, min_height=48)
            return Row(
                [
                    toggle_btn,
                    Row(
                        [
                            IconButton("chevron_left", on_click=self._on_prev, style=chevron_style),
                            IconButton("chevron_right", on_click=self._on_next, style=chevron_style),
                        ],
                        gap=0,
                        cross_alignment="center",
                    ),
                ],
                main_alignment="space-between",
                cross_alignment="center",
                padding=self._nav_padding,
                width=s.container_width,
            )


# ---------------------------------------------------------------------------
# Internal: _CalendarGrid
# ---------------------------------------------------------------------------


class _CalendarGrid(ComposableWidget):
    """Monthly calendar grid displaying weekday headers and day cells.

    Args:
        year: Year to display.
        month: Month to display (1–12).
        selected_date: Currently selected date (single-select mode).
        range_start: Start of the selected date range.
        range_end: End of the selected date range.
        min_date: Earliest selectable date.
        max_date: Latest selectable date.
        on_day_tap: Callback invoked with the tapped :class:`datetime.date`.
        style: DatePickerStyle.
    """

    def __init__(
        self,
        year: int,
        month: int,
        *,
        selected_date: Optional[_Date] = None,
        range_start: Optional[_Date] = None,
        range_end: Optional[_Date] = None,
        min_date: Optional[_Date] = None,
        max_date: Optional[_Date] = None,
        on_day_tap: Optional[Callable[[_Date], None]] = None,
        style: "DatePickerStyle",
    ) -> None:
        """Initialize _CalendarGrid.

        Args:
            year: Year to display.
            month: Month to display (1-12).
            selected_date: Currently selected date.
            range_start: Range selection start date.
            range_end: Range selection end date.
            min_date: Minimum selectable date.
            max_date: Maximum selectable date.
            on_day_tap: Callback for day cell taps.
            style: Date picker style.
        """
        super().__init__()
        self._year = year
        self._month = month
        self._selected_date = selected_date
        self._range_start = range_start
        self._range_end = range_end
        self._min_date = min_date
        self._max_date = max_date
        self._on_day_tap = on_day_tap
        self._style = style

    def build(self) -> Widget:
        """Build the calendar grid with weekday headers and day cells.

        Always renders exactly 6 weeks so the grid height is constant.
        Adjacent-month dates fill leading/trailing empty slots and are
        displayed greyed-out and non-interactive.
        """
        style = self._style
        today = _Date.today()
        weeks = _fill_six_weeks(self._year, self._month)

        # Each calendar column occupies a 48dp-wide slot: a 40dp date container
        # (MD3 ``date.container`` token) with 4dp on each side. Date cells are
        # tiled vertically at 48dp too (40dp circle + 4dp top/bottom), matching
        # the MD3 48x48 date container. Padding order is (left, top, right, bottom).
        _CELL_SLOT = 48  # 40dp visual cell + 4dp padding each side
        _DATE_SLOT_H = style.date_cell_size  # 40dp circle / state-layer per row
        _WEEKDAY_H = 14  # MD3 weekdays label-text glyph height (Roboto 16pt)

        # Weekday header row: one text-line slot per column, centred in 48dp slot.
        header_cells: list[Widget] = []
        for label in _WEEKDAY_LABELS:
            header_cells.append(
                Box(
                    width=_CELL_SLOT,
                    height=_WEEKDAY_H,
                    alignment="center",
                    child=Text(
                        label,
                        style=TextStyle(
                            font_size=style.date_font_size,
                            color=style.weekday_text,
                            text_alignment="center",
                        ),
                    ),
                )
            )
        # Docked and modal calendars share the same weekday/grid spacing: 15dp
        # above the weekday row, 8dp below, then an 8dp gap to the day grid
        # (the modal measurement does not specify these, so we keep the docked
        # calendar treatment for a consistent look across variants).
        weekday_padding = (12, 15, 12, 8)
        grid_padding = (12, 8, 12, 4)
        header_row = Row(header_cells, gap=0, padding=weekday_padding)

        # 6 week rows. Adjacent-month days are rendered as blank slots (not
        # greyed-out dates) to match the MD3 reference calendars and avoid
        # showing day numbers that look tappable but are not. Each cell occupies
        # a 48dp-wide slot; gap=0 between slots.
        date_rows: list[Widget] = []
        for week in weeks:
            cells: list[Widget] = []
            for d in week:
                is_outside_month = d.month != self._month
                if is_outside_month:
                    cells.append(Box(width=_CELL_SLOT, height=_DATE_SLOT_H))
                    continue
                is_today = d == today
                is_out_of_range = (self._min_date is not None and d < self._min_date) or (
                    self._max_date is not None and d > self._max_date
                )
                is_disabled = is_outside_month or is_out_of_range
                has_complete_range = self._range_start is not None and self._range_end is not None
                is_range_start = has_complete_range and self._range_start == d
                is_range_end = has_complete_range and self._range_end == d
                is_in_range = has_complete_range and self._range_start < d < self._range_end  # type: ignore[operator]
                # Pending start: show selection circle only (no range band)
                is_pending_start = not has_complete_range and self._range_start is not None and self._range_start == d
                is_selected = self._selected_date == d or is_pending_start

                on_tap: Optional[VoidCallback] = None
                if self._on_day_tap is not None and not is_disabled:
                    on_tap = _make_day_tap(d, self._on_day_tap)

                # The cell fills the full 48dp column slot (not just the 40dp
                # circle) so the range band is continuous across adjacent
                # in-range days; the circle/state layer stay 40dp and centred.
                cells.append(
                    _DayCell(
                        day=d.day,
                        is_selected=is_selected,
                        is_today=is_today,
                        is_outside_month=is_outside_month,
                        is_disabled=is_disabled,
                        is_in_range=is_in_range,
                        is_range_start=is_range_start,
                        is_range_end=is_range_end,
                        on_tap=on_tap,
                        cell_width=_CELL_SLOT,
                        style=style,
                    )
                )
            date_rows.append(Row(cells, gap=0))

        # Calendar grid container. Date cells are 40dp with an 8dp inter-row gap
        # (48dp MD3 pitch); the container's own padding provides the gap to the
        # weekday row above (8dp) and the action row below (4dp).
        date_grid = Box(
            padding=grid_padding,
            child=Column(date_rows, gap=8),
        )

        return Column([header_row, date_grid], gap=0)


# ---------------------------------------------------------------------------
# Public: DockedDatePicker
# ---------------------------------------------------------------------------


class DockedDatePicker(ComposableWidget):
    """Material Design 3 Docked Date Picker.

    An inline calendar widget that updates a shared observable value when the
    user selects a date.  The picker always stays visible (not a dialog).

    MD3 container: 360×456dp, Large corner rounding (16dp).

    Args:
        value: Observable holding the currently selected :class:`datetime.date`
            (or ``None``).  Both reads and writes are performed on this object.
        on_change: Optional callback invoked after the value is updated.
        min_date: Earliest selectable date.
        max_date: Latest selectable date.
        style: Visual style.  Defaults to :class:`DockedDatePickerStyle`.
    """

    def __init__(
        self,
        value: ObservableProtocol[Optional[_Date]],
        *,
        on_change: Optional[Callable[[Optional[_Date]], None]] = None,
        min_date: Optional[_Date] = None,
        max_date: Optional[_Date] = None,
        style: Optional["DockedDatePickerStyle"] = None,
    ) -> None:
        """Initialize DockedDatePicker.

        Args:
            value: Observable holding the selected date (or None).
            on_change: Callback invoked when the user selects a date.
            min_date: Minimum selectable date.
            max_date: Maximum selectable date.
            style: Optional style override.
        """
        super().__init__()
        self._value_obs = value
        self._on_change = on_change
        self._min_date = min_date
        self._max_date = max_date
        self._user_style = style

        # Initialise view to the currently selected month, or the current month.
        today = _Date.today()
        initial = getattr(value, "value", None)
        ref = initial if isinstance(initial, _Date) else today
        self._view_year = ref.year
        self._view_month = ref.month

        # View mode: "calendar" | "month" | "year"
        self._view_mode: Literal["calendar", "month", "year"] = "calendar"
        self._year_page_start: int = today.year - 3

        # Dropdown-arrow rotation: 0° (pointing down / menu closed) → 180°
        # (pointing up / menu open). Held on the persistent picker so the
        # animation survives the rebuild() triggered when toggling views.
        self._month_rotation: Animatable[float] = Animatable(0.0, motion=EXPRESSIVE_DEFAULT_SPATIAL)
        self._year_rotation: Animatable[float] = Animatable(0.0, motion=EXPRESSIVE_DEFAULT_SPATIAL)

    @property
    def style(self) -> "DockedDatePickerStyle":
        """Return the resolved date picker style."""
        if self._user_style is not None:
            return self._user_style
        from nuiitivet.material.styles.date_picker_style import DockedDatePickerStyle

        return DockedDatePickerStyle()

    def on_mount(self) -> None:
        """Subscribe to external value changes to keep the display in sync."""
        super().on_mount()
        self.observe(self._value_obs, lambda _: self.rebuild())

    def _go_prev_month(self) -> None:
        self._view_year, self._view_month = _prev_month(self._view_year, self._view_month)
        self.rebuild()

    def _go_next_month(self) -> None:
        self._view_year, self._view_month = _next_month(self._view_year, self._view_month)
        self.rebuild()

    def _sync_rotation(self) -> None:
        """Drive the dropdown-arrow rotation to match the current view mode."""
        self._month_rotation.target = 180.0 if self._view_mode == "month" else 0.0
        self._year_rotation.target = 180.0 if self._view_mode == "year" else 0.0

    def _toggle_month_view(self) -> None:
        self._view_mode = "month" if self._view_mode != "month" else "calendar"
        self._sync_rotation()
        self.rebuild()

    def _toggle_year_view(self) -> None:
        self._view_mode = "year" if self._view_mode != "year" else "calendar"
        self._sync_rotation()
        self.rebuild()

    def _select_month(self, month: int) -> None:
        self._view_month = month
        self._view_mode = "calendar"
        self._sync_rotation()
        self.rebuild()

    def _select_year(self, year: int) -> None:
        self._view_year = year
        self._view_mode = "calendar"
        self._sync_rotation()
        self.rebuild()

    def _prev_year_page(self) -> None:
        self._year_page_start -= _YEAR_LIST_PAGE_SIZE
        self.rebuild()

    def _next_year_page(self) -> None:
        self._year_page_start += _YEAR_LIST_PAGE_SIZE
        self.rebuild()

    def _go_prev_year(self) -> None:
        self._view_year -= 1
        self.rebuild()

    def _go_next_year(self) -> None:
        self._view_year += 1
        self.rebuild()

    def _on_day_tap(self, d: _Date) -> None:
        try:
            self._value_obs.value = d  # type: ignore[attr-defined]
        except AttributeError:
            pass
        if self._on_change is not None:
            self._on_change(d)
        self.rebuild()

    def _on_cancel(self) -> None:
        try:
            self._value_obs.value = None  # type: ignore[attr-defined]
        except AttributeError:
            pass
        if self._on_change is not None:
            self._on_change(None)
        self.rebuild()

    def build(self) -> Widget:
        """Build the docked picker container with navigation header and calendar."""
        style = self.style
        selected = getattr(self._value_obs, "value", None)
        shadow = md3_elevation_to_shadow(style.elevation)

        nav_header = _MonthYearHeader(
            self._view_year,
            self._view_month,
            on_prev=self._go_prev_month,
            on_next=self._go_next_month,
            on_prev_year=self._go_prev_year,
            on_next_year=self._go_next_year,
            on_month_tap=self._toggle_month_view,
            on_year_tap=self._toggle_year_view,
            active_view=self._view_mode if self._view_mode in ("month", "year") else None,  # type: ignore[arg-type]
            month_rotation=self._month_rotation,
            year_rotation=self._year_rotation,
            variant="docked",
            style=style,
        )

        # Vertical layout per MD3 docked measurement (padding order = left, top,
        # right, bottom). Sections stack with no inter-section gap; the gaps come
        # from each section's own padding (component-box to component-box), and
        # sum to exactly the 460dp container:
        #   nav_header   : pad (4, 20, 4, 15)  -> 75dp  (20 + menu-button 40 + 15)
        #   weekday row  : pad (12, 15, 12, 8) -> 37dp  (15 + text 14 + 8)
        #   calendar grid: pad (12, 8, 12, 4)  -> 292dp (8 + 6*40+5*8 + 4)
        #   action row   : pad (12, 4, 12, 12) -> 56dp  (4 + button 40 + 12)
        # Resulting box gaps: top 20, below-header 30, below-weekday 16,
        # below-grid 8, below-button 12.
        # The docked nav header block is 75dp tall (20dp top + 40dp menu-button
        # + 15dp bottom). In a list view there is no action row (it is hidden,
        # matching MD3), so the list fills the remaining container height.
        _HEADER_BLOCK_H = 75
        list_height = int(style.container_height) - _HEADER_BLOCK_H

        if self._view_mode == "month":
            # Full container width so the scrollbar sits flush against the right
            # container edge with no dead margin beside it.
            body: Widget = _MonthList(
                self._view_month,
                on_select=self._select_month,
                list_height=list_height,
                item_width=style.container_width,
                style=style,
            )
        elif self._view_mode == "year":
            body = _YearList(
                self._view_year,
                on_select=self._select_year,
                list_height=list_height,
                item_width=style.container_width,
                style=style,
            )
        else:
            body = _CalendarGrid(
                self._view_year,
                self._view_month,
                selected_date=selected if isinstance(selected, _Date) else None,
                min_date=self._min_date,
                max_date=self._max_date,
                on_day_tap=self._on_day_tap,
                style=style,
            )

        # MD3 docked action buttons are 40dp tall; ButtonStyle.text() enforces a
        # 48dp min touch-target by default, so override min_height to keep the
        # visible button box at 40dp (12dp gap below it = MD3 action bottom).
        # The action row is only shown in the calendar view; the month/year list
        # menus replace the calendar area and hide the Cancel/OK buttons per MD3.
        column_children: list[Widget] = [nav_header, body]
        if self._view_mode == "calendar":
            action_btn_style = ButtonStyle.text().copy_with(container_height=40, min_height=40)
            action_row = Row(
                [
                    Box(width=0),  # spacer to push buttons right
                    Button("Cancel", on_click=self._on_cancel, style=action_btn_style),
                    Button("OK", on_click=lambda: None, style=action_btn_style),
                ],
                gap=16,
                main_alignment="end",
                padding=(12, 4, 12, 12),
                width=int(style.container_width),
            )
            column_children.append(action_row)

        return Box(
            background_color=style.background,
            corner_radius=style.corner_radius,
            shadow_blur=shadow.sigma,
            shadow_color=shadow.color,
            shadow_offset=shadow.offset,
            width=style.container_width,
            height=style.container_height,
            child=Column(
                column_children,
                gap=0,
                height=int(style.container_height),
            ),
        )


# ---------------------------------------------------------------------------
# Public: ModalDatePicker
# ---------------------------------------------------------------------------


class ModalDatePicker(ComposableWidget, OverlayAware[Optional[_Date]]):
    """Material Design 3 Modal Date Picker (single date selection).

    When shown via ``overlay.dialog(ModalDatePicker(...))``, the returned
    :class:`OverlayHandle` resolves to the selected date on confirmation or
    ``None`` on cancellation::

        result = await overlay.dialog(ModalDatePicker())
        if result.value is not None:
            selected_date: datetime.date = result.value

    MD3 container: 360×524dp, Extra large corner rounding (28dp).

    .. note::
        **Experimental implementation.**  This class does not yet fully comply with the
        MD3 Expressive specification.  Known limitation: the icon button that toggles
        between :class:`ModalDatePicker` and :class:`ModalDateInput` is not implemented.
        See `#230 <https://github.com/yuksblog/nuiitivet/issues/230>`_ for tracking.

    Args:
        init_value: Pre-selected date shown when the picker opens.
        supporting_text: Small label shown at the top of the header (14pt).
        min_date: Earliest selectable date.
        max_date: Latest selectable date.
        style: Visual style.  Defaults to :class:`ModalDatePickerStyle`.
    """

    def __init__(
        self,
        *,
        init_value: Optional[_Date] = None,
        supporting_text: str = "Select date",
        min_date: Optional[_Date] = None,
        max_date: Optional[_Date] = None,
        style: Optional["ModalDatePickerStyle"] = None,
    ) -> None:
        """Initialize ModalDatePicker.

        Args:
            init_value: Initial selected date.
            supporting_text: Small label shown at the top of the header (14pt).
            min_date: Minimum selectable date.
            max_date: Maximum selectable date.
            style: Optional style override.
        """
        super().__init__()
        self._supporting_text = supporting_text
        self._min_date = min_date
        self._max_date = max_date
        self._user_style = style

        today = _Date.today()
        self._selected_date: Optional[_Date] = init_value

        if init_value is not None:
            self._view_year = init_value.year
            self._view_month = init_value.month
        else:
            self._view_year = today.year
            self._view_month = today.month

        self._showing_year_picker: bool = False

    @property
    def style(self) -> "ModalDatePickerStyle":
        """Return the resolved date picker style."""
        if self._user_style is not None:
            return self._user_style
        from nuiitivet.material.styles.date_picker_style import ModalDatePickerStyle

        return ModalDatePickerStyle()

    def _go_prev_month(self) -> None:
        self._view_year, self._view_month = _prev_month(self._view_year, self._view_month)
        self.rebuild()

    def _go_next_month(self) -> None:
        self._view_year, self._view_month = _next_month(self._view_year, self._view_month)
        self.rebuild()

    def _toggle_year_picker(self) -> None:
        self._showing_year_picker = not self._showing_year_picker
        self.rebuild()

    def _select_year(self, year: int) -> None:
        self._view_year = year
        self._showing_year_picker = False
        self.rebuild()

    def _on_day_tap(self, d: _Date) -> None:
        self._selected_date = d
        self.rebuild()

    def _on_confirm(self) -> None:
        try:
            self.overlay_handle.close(self._selected_date)
        except RuntimeError:
            pass  # Not displayed via overlay

    def _on_cancel(self) -> None:
        try:
            self.overlay_handle.close(None)
        except RuntimeError:
            pass

    def _build_header(self, style: "ModalDatePickerStyle", *, year_view: bool = False) -> Widget:
        date_str = self._selected_date.strftime("%b %d, %Y") if self._selected_date is not None else "—"
        # Header layout (MD3 measurement): supporting text on top, then the
        # headline row, 36dp apart. The trailing edit icon (24dp per MD3) lives
        # in the headline row and is cross-centred on the headline so it aligns
        # with the date text (the measurement's 92dp bottom-aligned container
        # assumed a 48dp glyph; with a 24dp glyph it would sit too low).
        #   - Calendar view : header padding (24, 16, 12, 6).
        #   - Year-selection: header padding (24, 16, 24, 6).
        header_padding = (24, 16, 24, 6) if year_view else (24, 16, 12, 6)
        inner_width = int(style.container_width) - header_padding[0] - header_padding[2]
        return Box(
            width=style.container_width,
            height=style.header_height,
            child=Column(
                [
                    Text(
                        self._supporting_text,
                        style=TextStyle(
                            font_size=int(style.header_supporting_text_font_size),
                            color=style.header_supporting_text_color,
                        ),
                    ),
                    Row(
                        [
                            Text(
                                date_str,
                                style=TextStyle(
                                    font_size=int(style.header_headline_font_size),
                                    color=style.header_headline_color,
                                ),
                            ),
                            Icon("edit", size=24),
                        ],
                        main_alignment="space-between",
                        cross_alignment="center",
                        width=inner_width,
                    ),
                ],
                gap=36,
                cross_alignment="start",
                padding=header_padding,
                width=int(style.container_width),
            ),
        )

    def build(self) -> Widget:
        """Build the modal picker with header, calendar (or year grid), and action buttons."""
        style = self.style
        shadow = md3_elevation_to_shadow(style.elevation)

        nav_header = _MonthYearHeader(
            self._view_year,
            self._view_month,
            on_prev=self._go_prev_month,
            on_next=self._go_next_month,
            on_toggle_year_picker=self._toggle_year_picker,
            year_picker_active=self._showing_year_picker,
            variant="modal",
            # Same nav padding in both views so the dialog height is unchanged
            # when toggling the year picker (paired with growing the year grid
            # by the hidden action-row height). The 28dp left inset aligns the
            # "Month Year" label's left edge with the first weekday letter (the
            # weekday letters are centred in 48dp columns starting at 12dp, so
            # the first letter sits ~17dp in; 12 + 17 ≈ 29). The measurement does
            # not give a number, so this is a best-fit alignment.
            nav_padding=(28, 6, 12, 2),
            style=style,
        )

        # The dialog sizes to its content (Flex) so the 6-week calendar grid gets
        # its full height with the MD3 section paddings intact (a fixed token
        # height was sized for 5 weeks and clipped the action row).
        column_children: list[Widget] = [
            self._build_header(style, year_view=self._showing_year_picker),
            Divider(),
            nav_header,
        ]

        if self._showing_year_picker:
            # Actions are hidden during year selection (no date is confirmable
            # in this view). The year grid is grown by the action-row height so
            # the dialog height stays constant when toggling the year picker.
            column_children.append(
                _YearChipGrid(
                    self._view_year,
                    on_select=self._select_year,
                    list_height=_modal_calendar_body_height(style) + _MODAL_ACTION_ROW_HEIGHT,
                    style=style,
                )
            )
        else:
            column_children.append(
                _CalendarGrid(
                    self._view_year,
                    self._view_month,
                    selected_date=self._selected_date,
                    min_date=self._min_date,
                    max_date=self._max_date,
                    on_day_tap=self._on_day_tap,
                    style=style,
                )
            )
            column_children.append(
                Row(
                    [
                        Button("Cancel", on_click=self._on_cancel, style=ButtonStyle.text()),
                        Button("OK", on_click=self._on_confirm, style=ButtonStyle.text()),
                    ],
                    gap=8,
                    main_alignment="end",
                    padding=(12, 4, 12, 12),
                    width=int(style.container_width),
                )
            )

        return Box(
            background_color=style.background,
            corner_radius=style.corner_radius,
            shadow_blur=shadow.sigma,
            shadow_color=shadow.color,
            shadow_offset=shadow.offset,
            width=style.container_width,
            child=Column(column_children, gap=0),
        )


# ---------------------------------------------------------------------------
# Public: ModalDateRangePicker
# ---------------------------------------------------------------------------


class ModalDateRangePicker(
    ComposableWidget,
    OverlayAware[Optional[Tuple[_Date, _Date]]],
):
    """Material Design 3 Modal Date Range Picker.

    Allows the user to select a start and end date via two sequential taps.
    When shown via ``overlay.dialog(ModalDateRangePicker(...))``, the returned
    :class:`OverlayHandle` resolves to ``(start, end)`` on confirmation or
    ``None`` on cancellation::

        result = await overlay.dialog(ModalDateRangePicker())
        if result.value is not None:
            start, end = result.value

    MD3 container: 360×524dp, Extra large corner rounding (28dp).

    Range selection flow:
        - First tap sets the **start** date.
        - Second tap sets the **end** date (must be ≥ start; tapping before
          the start resets and begins a new selection from that date).

    .. note::
        **Experimental implementation.**  This class does not yet fully comply with the
        MD3 Expressive specification.  Known limitations: the icon button that toggles
        between :class:`ModalDateRangePicker` and a range-input variant
        (``ModalDateRangeInput``) is not implemented, and ``ModalDateRangeInput``
        does not yet exist.
        See `#230 <https://github.com/yuksblog/nuiitivet/issues/230>`_ for tracking.

    Args:
        init_value: Pre-selected date range as ``(start, end)`` tuple.
        supporting_text: Small label shown at the top of the header (14pt).
        min_date: Earliest selectable date.
        max_date: Latest selectable date.
        style: Visual style.  Defaults to :class:`ModalDateRangePickerStyle`.
    """

    def __init__(
        self,
        *,
        init_value: Optional[Tuple[_Date, _Date]] = None,
        supporting_text: str = "Select range",
        min_date: Optional[_Date] = None,
        max_date: Optional[_Date] = None,
        style: Optional["ModalDateRangePickerStyle"] = None,
    ) -> None:
        """Initialize ModalDateRangePicker.

        Args:
            init_value: Initial date range as (start, end) tuple.
            supporting_text: Small label shown at the top of the header (14pt).
            min_date: Minimum selectable date.
            max_date: Maximum selectable date.
            style: Optional style override.
        """
        super().__init__()
        self._supporting_text = supporting_text
        self._min_date = min_date
        self._max_date = max_date
        self._user_style = style

        today = _Date.today()
        self._range_start: Optional[_Date] = None
        self._range_end: Optional[_Date] = None
        # "first": waiting for start; "second": waiting for end.
        self._range_state: Literal["first", "second"] = "first"

        if init_value is not None and len(init_value) == 2:
            self._range_start, self._range_end = init_value
            self._view_year = self._range_start.year
            self._view_month = self._range_start.month
        else:
            self._view_year = today.year
            self._view_month = today.month

        self._showing_year_picker: bool = False

    @property
    def style(self) -> "ModalDateRangePickerStyle":
        """Return the resolved date picker style."""
        if self._user_style is not None:
            return self._user_style
        from nuiitivet.material.styles.date_picker_style import ModalDateRangePickerStyle

        return ModalDateRangePickerStyle()

    def _go_prev_month(self) -> None:
        self._view_year, self._view_month = _prev_month(self._view_year, self._view_month)
        self.rebuild()

    def _go_next_month(self) -> None:
        self._view_year, self._view_month = _next_month(self._view_year, self._view_month)
        self.rebuild()

    def _toggle_year_picker(self) -> None:
        self._showing_year_picker = not self._showing_year_picker
        self.rebuild()

    def _select_year(self, year: int) -> None:
        self._view_year = year
        self._showing_year_picker = False
        self.rebuild()

    def _on_day_tap(self, d: _Date) -> None:
        if self._range_state == "first":
            self._range_start = d
            self._range_end = None
            self._range_state = "second"
        else:
            if self._range_start is not None and d >= self._range_start:
                self._range_end = d
                self._range_state = "first"
            else:
                # Clicked before start — restart with new start date.
                self._range_start = d
                self._range_end = None
                # _range_state stays "second" (waiting for end)
        self.rebuild()

    def _on_confirm(self) -> None:
        if self._range_start is not None and self._range_end is not None:
            result: Optional[Tuple[_Date, _Date]] = (self._range_start, self._range_end)
        else:
            result = None
        try:
            self.overlay_handle.close(result)
        except RuntimeError:
            pass  # Not displayed via overlay

    def _on_cancel(self) -> None:
        try:
            self.overlay_handle.close(None)
        except RuntimeError:
            pass

    def _build_header(self, style: "ModalDateRangePickerStyle", *, year_view: bool = False) -> Widget:
        if self._range_start is not None and self._range_end is not None:
            date_str = f"{self._range_start.strftime('%b %d')} – " f"{self._range_end.strftime('%b %d, %Y')}"
        elif self._range_start is not None:
            date_str = f"{self._range_start.strftime('%b %d, %Y')} – ?"
        else:
            date_str = "—"

        # Header layout (MD3 measurement): see ModalDatePicker._build_header.
        # The 24dp edit icon shares the headline row and is cross-centred on it.
        header_padding = (24, 16, 24, 6) if year_view else (24, 16, 12, 6)
        inner_width = int(style.container_width) - header_padding[0] - header_padding[2]
        return Box(
            width=style.container_width,
            height=style.range_header_height,
            child=Column(
                [
                    Text(
                        self._supporting_text,
                        style=TextStyle(
                            font_size=int(style.header_supporting_text_font_size),
                            color=style.header_supporting_text_color,
                        ),
                    ),
                    Row(
                        [
                            Text(
                                date_str,
                                style=TextStyle(
                                    font_size=int(style.range_headline_font_size),
                                    color=style.header_headline_color,
                                ),
                            ),
                            Icon("edit", size=24),
                        ],
                        main_alignment="space-between",
                        cross_alignment="center",
                        width=inner_width,
                    ),
                ],
                gap=36,
                cross_alignment="start",
                padding=header_padding,
                width=int(style.container_width),
            ),
        )

    def build(self) -> Widget:
        """Build the modal range picker with header, calendar (or year grid), and action buttons."""
        style = self.style
        shadow = md3_elevation_to_shadow(style.elevation)

        ok_disabled = self._range_start is None or self._range_end is None

        nav_header = _MonthYearHeader(
            self._view_year,
            self._view_month,
            on_prev=self._go_prev_month,
            on_next=self._go_next_month,
            on_toggle_year_picker=self._toggle_year_picker,
            year_picker_active=self._showing_year_picker,
            variant="modal",
            # Same nav padding in both views so the dialog height is unchanged
            # when toggling the year picker (paired with growing the year grid
            # by the hidden action-row height). The 28dp left inset aligns the
            # "Month Year" label's left edge with the first weekday letter (the
            # weekday letters are centred in 48dp columns starting at 12dp, so
            # the first letter sits ~17dp in; 12 + 17 ≈ 29). The measurement does
            # not give a number, so this is a best-fit alignment.
            nav_padding=(28, 6, 12, 2),
            style=style,
        )

        # Content-sized (Flex) so the 6-week grid keeps its full height and MD3
        # section paddings (the fixed token height was sized for 5 weeks).
        column_children: list[Widget] = [
            self._build_header(style, year_view=self._showing_year_picker),
            Divider(),
            nav_header,
        ]

        if self._showing_year_picker:
            # Actions hidden during year selection; grow the grid by the action
            # row height so the dialog height is unchanged when toggling.
            column_children.append(
                _YearChipGrid(
                    self._view_year,
                    on_select=self._select_year,
                    list_height=_modal_calendar_body_height(style) + _MODAL_ACTION_ROW_HEIGHT,
                    style=style,
                )
            )
        else:
            column_children.append(
                _CalendarGrid(
                    self._view_year,
                    self._view_month,
                    range_start=self._range_start,
                    range_end=self._range_end,
                    min_date=self._min_date,
                    max_date=self._max_date,
                    on_day_tap=self._on_day_tap,
                    style=style,
                )
            )
            column_children.append(
                Row(
                    [
                        Button("Cancel", on_click=self._on_cancel, style=ButtonStyle.text()),
                        Button("OK", on_click=self._on_confirm, style=ButtonStyle.text(), disabled=ok_disabled),
                    ],
                    gap=8,
                    main_alignment="end",
                    padding=(12, 4, 12, 12),
                    width=int(style.container_width),
                )
            )

        return Box(
            background_color=style.background,
            corner_radius=style.corner_radius,
            shadow_blur=shadow.sigma,
            shadow_color=shadow.color,
            shadow_offset=shadow.offset,
            width=style.container_width,
            child=Column(column_children, gap=0),
        )


# ---------------------------------------------------------------------------
# Public: ModalDateInput
# ---------------------------------------------------------------------------


def _parse_date(text: str) -> Optional[_Date]:
    """Attempt to parse ``text`` as a date using common formats.

    Args:
        text: Raw user input.

    Returns:
        Parsed :class:`datetime.date` or ``None`` if parsing fails.
    """
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return _DateTime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


class ModalDateInput(ComposableWidget, OverlayAware[Optional[_Date]]):
    """Material Design 3 Modal Date Input.

    Allows the user to type a date directly into a text field.  When shown via
    ``overlay.dialog(ModalDateInput(...))``, the returned
    :class:`OverlayHandle` resolves to the entered date on confirmation or
    ``None`` on cancellation::

        result = await overlay.dialog(ModalDateInput())
        if result.value is not None:
            entered: datetime.date = result.value

    MD3 container: 328×512dp, Extra large corner rounding (28dp).

    .. note::
        **Experimental implementation.**  This class does not yet fully comply with the
        MD3 Expressive specification.  Known limitations: the icon button that toggles
        between :class:`ModalDateInput` and :class:`ModalDatePicker` is not implemented,
        and the range-input variant (``ModalDateRangeInput``) does not yet exist.
        See `#230 <https://github.com/yuksblog/nuiitivet/issues/230>`_ for tracking.

    Args:
        init_value: Optional initial date used to pre-populate the text field.
        supporting_text: Small label shown at the top of the header (14pt).
        input_label: Label for the date text field.
        date_format: Format hint shown as supporting text (e.g. ``"mm/dd/yyyy"``).
        min_date: Earliest acceptable date.
        max_date: Latest acceptable date.
        style: Visual style.  Defaults to :class:`ModalDateInputStyle`.
    """

    def __init__(
        self,
        *,
        init_value: Optional[_Date] = None,
        supporting_text: str = "Enter date",
        input_label: str = "Date",
        date_format: str = "mm/dd/yyyy",
        min_date: Optional[_Date] = None,
        max_date: Optional[_Date] = None,
        style: Optional["ModalDateInputStyle"] = None,
    ) -> None:
        """Initialize ModalDateInput.

        Args:
            init_value: Initial date to pre-populate the text field.
            supporting_text: Small label shown at the top of the header (14pt).
            input_label: Text field label.
            date_format: Format hint shown below the text field.
            min_date: Minimum acceptable date.
            max_date: Maximum acceptable date.
            style: Optional style override.
        """
        super().__init__()
        self._init_value = init_value
        self._supporting_text = supporting_text
        self._input_label = input_label
        self._date_format = date_format
        self._min_date = min_date
        self._max_date = max_date
        self._user_style = style

        # Internal observables for the text field
        init_text = init_value.strftime("%m/%d/%Y") if init_value else ""
        self._text_obs: Observable[str] = Observable(init_text)
        self._supporting_text_obs: Observable[Optional[str]] = Observable(date_format)

        # Build the TextField once and reuse across rebuild cycles to preserve
        # focus state and cursor position.
        from nuiitivet.material.text_fields import TextField
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        self._text_field: TextField = TextField.two_way(
            self._text_obs,
            label=input_label,
            supporting_text=self._supporting_text_obs,
            style=TextFieldStyle.outlined(),
            width=self._resolved_field_width,
        )

    @property
    def _resolved_field_width(self) -> float:
        """Return the text field width based on the container width."""
        if self._user_style is not None:
            return self._user_style.container_width - 48.0
        from nuiitivet.material.styles.date_picker_style import ModalDateInputStyle

        return ModalDateInputStyle().container_width - 48.0

    @property
    def style(self) -> "ModalDateInputStyle":
        """Return the resolved date picker style."""
        if self._user_style is not None:
            return self._user_style
        from nuiitivet.material.styles.date_picker_style import ModalDateInputStyle

        return ModalDateInputStyle()

    def _on_confirm(self) -> None:
        parsed = _parse_date(self._text_obs.value)
        if parsed is None:
            self._supporting_text_obs.value = "Invalid date"
            return
        if self._min_date and parsed < self._min_date:
            self._supporting_text_obs.value = f"Date must be on or after {self._min_date.strftime('%b %d, %Y')}"
            return
        if self._max_date and parsed > self._max_date:
            self._supporting_text_obs.value = f"Date must be on or before {self._max_date.strftime('%b %d, %Y')}"
            return
        self._supporting_text_obs.value = self._date_format
        try:
            self.overlay_handle.close(parsed)
        except RuntimeError:
            pass

    def _on_cancel(self) -> None:
        try:
            self.overlay_handle.close(None)
        except RuntimeError:
            pass

    def on_mount(self) -> None:
        """Subscribe to text changes to keep the header date display in sync."""
        super().on_mount()
        self.observe(self._text_obs, lambda _: self.rebuild())

    def build(self) -> Widget:
        """Build the modal date input with header, text field, and action buttons."""
        style = self.style
        shadow = md3_elevation_to_shadow(style.elevation)

        parsed_date = _parse_date(self._text_obs.value)
        date_str = parsed_date.strftime("%b %d, %Y") if parsed_date is not None else "—"
        # Header layout (measurement image):
        # Supporting text: padding=(16, 24, 18, 24)
        # Headline row: headline + calendar_today icon (24dp, right-aligned)
        #   padding=(18, 24, 5, 24)
        # The header sizes to its content (supporting text + headline row); the
        # measurement reference does not box it to a fixed height, and forcing
        # ``header_height`` (120dp) here would leave ~11dp of dead slack that
        # shows up as an oversized gap above the divider.
        header = Box(
            width=style.container_width,
            child=Column(
                [
                    Box(
                        padding=(24, 16, 24, 18),
                        child=Text(
                            self._supporting_text,
                            style=TextStyle(
                                font_size=int(style.header_supporting_text_font_size),
                                color=style.header_supporting_text_color,
                            ),
                        ),
                    ),
                    Row(
                        [
                            # Pin the headline to its MD3 line-height box (32pt /
                            # 40dp). Centring the icon against this fixed line box
                            # (rather than the text's ink bounds, which grow with
                            # descenders like the "y" in "May") keeps the icon on
                            # the cap-height centre regardless of the month name.
                            Box(
                                height=40,
                                alignment="center-left",
                                child=Text(
                                    date_str,
                                    style=TextStyle(
                                        font_size=int(style.header_headline_font_size),
                                        color=style.header_headline_color,
                                    ),
                                ),
                            ),
                            Icon("calendar_today", size=24),
                        ],
                        gap=8,
                        cross_alignment="center",
                        main_alignment="space-between",
                        padding=(24, 18, 24, 0),
                        width=int(style.container_width),
                    ),
                ],
                gap=0,
            ),
        )

        action_row = Row(
            [
                Button("Cancel", on_click=self._on_cancel, style=ButtonStyle.text()),
                Button("OK", on_click=self._on_confirm, style=ButtonStyle.text()),
            ],
            gap=16,
            main_alignment="end",
            padding=(24, 4, 24, 12),
            width=int(style.container_width),
        )

        # Unlike the calendar/range modals, the date-input dialog has no fixed
        # body to fill: it sizes to its content (header + text field + actions).
        # The MD3 ``512dp`` container token would leave a large empty band, so
        # the height is intentionally left to wrap the content (the measurement
        # reference likewise sets no height on the outer box).
        return Box(
            background_color=style.background,
            corner_radius=style.corner_radius,
            shadow_blur=shadow.sigma,
            shadow_color=shadow.color,
            shadow_offset=shadow.offset,
            width=style.container_width,
            child=Column(
                [
                    header,
                    # The divider owns its 10dp margins (top to the headline line
                    # box, bottom toward the field). The outlined field's floating
                    # label floats ~7dp above its outline, so an extra 7dp top
                    # inset on the field keeps the *label text top* 10dp below the
                    # divider line (not just the outline).
                    Divider(padding=(0, 10, 0, 10)),
                    Box(
                        padding=(24, 6, 24, 4),
                        child=self._text_field,
                    ),
                    action_row,
                ],
                gap=0,
                width=int(style.container_width),
            ),
        )
