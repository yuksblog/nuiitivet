"""Tests for StandardSideSheet widget."""

import pytest

from nuiitivet.material.sheet import StandardSideSheet
from nuiitivet.material.styles.sheet_style import StandardSideSheetStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.widgets.box import Box

# ---------------------------------------------------------------------------
# StandardSideSheetStyle tests
# ---------------------------------------------------------------------------


def test_standard_side_sheet_style_defaults():
    style = StandardSideSheetStyle()
    assert style.width == 256
    assert style.height == "100%"
    assert style.corner_radius == 0.0
    assert style.background_color == ColorRole.SURFACE


def test_standard_side_sheet_style_copy_with():
    style = StandardSideSheetStyle().copy_with(width=320, corner_radius=8.0)
    assert style.width == 320
    assert style.height == "100%"
    assert style.corner_radius == 8.0


def test_standard_side_sheet_style_is_immutable():
    style = StandardSideSheetStyle()
    with pytest.raises((AttributeError, TypeError)):
        style.width = 100  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StandardSideSheet initialization tests
# ---------------------------------------------------------------------------


def test_standard_side_sheet_defaults():
    content = Box(width=100, height=100)
    sheet = StandardSideSheet(content)
    assert sheet.side == "right"
    assert sheet._headline is None
    assert sheet._on_close is None


def test_standard_side_sheet_style_property_default():
    sheet = StandardSideSheet(Box())
    assert sheet.style == StandardSideSheetStyle()


def test_standard_side_sheet_style_property_custom():
    custom = StandardSideSheetStyle(width=320)
    sheet = StandardSideSheet(Box(), style=custom)
    assert sheet.style is custom


def test_standard_side_sheet_left_side():
    sheet = StandardSideSheet(Box(), side="left")
    assert sheet.side == "left"


def test_standard_side_sheet_stores_headline():
    sheet = StandardSideSheet(Box(), headline="Filters")
    assert sheet._headline == "Filters"


def test_standard_side_sheet_stores_on_close():
    def cb() -> None:
        pass

    sheet = StandardSideSheet(Box(), on_close=cb)
    assert sheet._on_close is cb


# ---------------------------------------------------------------------------
# StandardSideSheet.build() tests
# ---------------------------------------------------------------------------


def test_standard_side_sheet_build_returns_box():
    """build() returns a Box directly (no Collapsible wrapping)."""
    sheet = StandardSideSheet(Box(width=100, height=200))
    built = sheet.build()
    assert isinstance(built, Box)


def test_standard_side_sheet_build_no_header_when_none():
    """No header row is created when headline and on_close are both None."""
    from nuiitivet.layout.column import Column

    # Disable divider so Box.children[0] is the Column directly.
    from nuiitivet.material.styles.sheet_style import StandardSideSheetStyle

    sheet = StandardSideSheet(Box(), style=StandardSideSheetStyle(show_divider=False))
    built = sheet.build()
    assert isinstance(built, Box)
    # The body Column should contain only the content (no header Row).
    body_column = built.children[0]
    assert isinstance(body_column, Column)
    assert len(body_column.children) == 1


def test_standard_side_sheet_build_has_header_when_headline_given():
    """Header Row is present when headline is provided."""
    from nuiitivet.layout.column import Column
    from nuiitivet.layout.row import Row

    # Disable divider so Box.children[0] is the Column directly.
    from nuiitivet.material.styles.sheet_style import StandardSideSheetStyle

    sheet = StandardSideSheet(Box(), headline="Filters", style=StandardSideSheetStyle(show_divider=False))
    built = sheet.build()
    body_column = built.children[0]
    assert isinstance(body_column, Column)
    assert len(body_column.children) == 2
    assert isinstance(body_column.children[0], Row)


def test_standard_side_sheet_style_show_divider_default():
    """show_divider defaults to True."""
    assert StandardSideSheetStyle().show_divider is True


def test_standard_side_sheet_build_divider_right_side():
    """Right-side sheet: Divider appears as first child of the inner Row."""
    from nuiitivet.layout.row import Row as LayoutRow
    from nuiitivet.material.divider import VerticalDivider

    sheet = StandardSideSheet(Box(), side="right")
    built = sheet.build()
    inner = built.children[0]
    assert isinstance(inner, LayoutRow)
    assert isinstance(inner.children[0], VerticalDivider)


def test_standard_side_sheet_build_divider_left_side():
    """Left-side sheet: Divider appears as last child of the inner Row."""
    from nuiitivet.layout.row import Row as LayoutRow
    from nuiitivet.material.divider import VerticalDivider

    sheet = StandardSideSheet(Box(), side="left")
    built = sheet.build()
    inner = built.children[0]
    assert isinstance(inner, LayoutRow)
    assert isinstance(inner.children[-1], VerticalDivider)


def test_standard_side_sheet_build_no_divider_when_disabled():
    """When show_divider=False, Box.children[0] is not a Row with a Divider."""
    from nuiitivet.layout.column import Column

    sheet = StandardSideSheet(Box(), style=StandardSideSheetStyle(show_divider=False))
    built = sheet.build()
    assert isinstance(built.children[0], Column)


def test_standard_side_sheet_namespace_export():
    """StandardSideSheet is accessible via the nuiitivet.material namespace."""
    import nuiitivet.material as m

    assert m.StandardSideSheet is StandardSideSheet


def test_standard_side_sheet_style_namespace_export():
    """StandardSideSheetStyle is accessible via the nuiitivet.material namespace."""
    import nuiitivet.material as m

    assert m.StandardSideSheetStyle is StandardSideSheetStyle
