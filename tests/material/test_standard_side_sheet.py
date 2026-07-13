"""Tests for StandardSideSheet widget."""

from typing import Optional

import pytest

from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row as LayoutRow
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.divider import VerticalDivider
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL
from nuiitivet.material.sheet import StandardSideSheet
from nuiitivet.material.styles.sheet_style import StandardSideSheetStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import PointerInputNode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _container(built: Widget) -> Box:
    """Return the sheet container Box inside the built Collapsible."""
    assert isinstance(built, Collapsible)
    child = built.children[0]
    assert isinstance(child, Box)
    return child


def _find_close_button(built: Widget) -> Optional[IconButton]:
    """Return the header close IconButton, or None when it is not rendered."""
    if isinstance(built, IconButton):
        return built
    for child in built.children:
        found = _find_close_button(child)
        if found is not None:
            return found
    return None


def _press(button: IconButton) -> None:
    """Fire the button's click callbacks as a real press would."""
    node = button.get_node(PointerInputNode)
    assert isinstance(node, PointerInputNode)
    for callback in node._click_callbacks:
        callback()


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
    assert sheet._on_close_click is None
    assert sheet._opened is True


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


def test_standard_side_sheet_stores_on_close_click():
    def cb() -> None:
        pass

    sheet = StandardSideSheet(Box(), on_close_click=cb)
    assert sheet._on_close_click is cb


# ---------------------------------------------------------------------------
# Embedded Collapsible tests
# ---------------------------------------------------------------------------


def test_standard_side_sheet_build_returns_collapsible():
    """build() wraps the sheet container in a Collapsible."""
    built = StandardSideSheet(Box(width=100, height=200)).build()
    assert isinstance(built, Collapsible)
    assert isinstance(built.children[0], Box)


def test_standard_side_sheet_collapsible_axis_is_horizontal():
    built = StandardSideSheet(Box()).build()
    assert isinstance(built, Collapsible)
    assert built._axis == "horizontal"


def test_standard_side_sheet_right_side_anchors_to_end():
    """A right-docked sheet keeps its right edge pinned while collapsing."""
    built = StandardSideSheet(Box(), side="right").build()
    assert isinstance(built, Collapsible)
    assert built._align == ("end", "start")


def test_standard_side_sheet_left_side_anchors_to_start():
    """A left-docked sheet keeps its left edge pinned while collapsing."""
    built = StandardSideSheet(Box(), side="left").build()
    assert isinstance(built, Collapsible)
    assert built._align == ("start", "start")


def test_standard_side_sheet_uses_expressive_spatial_motion():
    """Motion is the M3 expressive default and is not part of the public API."""
    built = StandardSideSheet(Box()).build()
    assert isinstance(built, Collapsible)
    assert built._motion_in is EXPRESSIVE_DEFAULT_SPATIAL
    assert built._motion_out is EXPRESSIVE_DEFAULT_SPATIAL


def test_standard_side_sheet_collapsible_present_for_literal_opened():
    """The Collapsible is inserted even when opened is a literal True."""
    assert isinstance(StandardSideSheet(Box(), opened=True).build(), Collapsible)


def test_standard_side_sheet_forwards_opened_observable():
    opened = Observable(False)
    built = StandardSideSheet(Box(), opened=opened).build()
    assert isinstance(built, Collapsible)
    assert built._opened is opened


def test_standard_side_sheet_closed_snaps_without_animation():
    """opened=False snaps the width to zero on the first measure."""
    built = StandardSideSheet(Box(width=100, height=200), opened=False).build()
    width, _ = built.preferred_size()
    assert width == 0


def test_standard_side_sheet_opened_measures_style_width():
    """opened=True snaps to the style width on the first measure."""
    built = StandardSideSheet(Box(width=100, height=200), opened=True).build()
    width, _ = built.preferred_size()
    assert width == StandardSideSheetStyle().width


# ---------------------------------------------------------------------------
# Close button visibility and press behavior
# ---------------------------------------------------------------------------


def test_close_button_writable_opened_without_callback_closes():
    """Writable opened, no callback: button shown, press writes opened=False."""
    opened = Observable(True)
    button = _find_close_button(StandardSideSheet(Box(), opened=opened).build())
    assert button is not None

    _press(button)
    assert opened.value is False


def test_close_button_writable_opened_with_callback_does_not_auto_close():
    """Writable opened + callback: the callback replaces the auto-close."""
    opened = Observable(True)
    calls: list[int] = []
    sheet = StandardSideSheet(Box(), opened=opened, on_close_click=lambda: calls.append(1))
    button = _find_close_button(sheet.build())
    assert button is not None

    _press(button)
    assert calls == [1]
    assert opened.value is True


def test_close_button_hidden_for_literal_opened_without_callback():
    """Literal opened, no callback: a press would have nothing to do, so no button."""
    assert _find_close_button(StandardSideSheet(Box(), opened=True).build()) is None


def test_close_button_shown_for_literal_opened_with_callback():
    """Literal opened + callback: button shown, press invokes the callback."""
    calls: list[int] = []
    sheet = StandardSideSheet(Box(), opened=True, on_close_click=lambda: calls.append(1))
    button = _find_close_button(sheet.build())
    assert button is not None

    _press(button)
    assert calls == [1]


# ---------------------------------------------------------------------------
# StandardSideSheet.build() structure tests
# ---------------------------------------------------------------------------


def test_standard_side_sheet_build_no_header_when_none():
    """No header row is created when headline and close button are both absent."""
    # Disable the divider so the container's child is the body Column directly.
    sheet = StandardSideSheet(Box(), style=StandardSideSheetStyle(show_divider=False))
    body_column = _container(sheet.build()).children[0]
    assert isinstance(body_column, Column)
    # Only the content, no header Row.
    assert len(body_column.children) == 1


def test_standard_side_sheet_build_has_header_when_headline_given():
    """Header Row is present when headline is provided."""
    sheet = StandardSideSheet(Box(), headline="Filters", style=StandardSideSheetStyle(show_divider=False))
    body_column = _container(sheet.build()).children[0]
    assert isinstance(body_column, Column)
    assert len(body_column.children) == 2
    assert isinstance(body_column.children[0], LayoutRow)


def test_standard_side_sheet_build_has_header_when_only_close_button():
    """Header Row is present when the close button alone is rendered."""
    sheet = StandardSideSheet(
        Box(),
        opened=Observable(True),
        style=StandardSideSheetStyle(show_divider=False),
    )
    body_column = _container(sheet.build()).children[0]
    assert isinstance(body_column, Column)
    assert len(body_column.children) == 2


def test_standard_side_sheet_style_show_divider_default():
    """show_divider defaults to True."""
    assert StandardSideSheetStyle().show_divider is True


def test_standard_side_sheet_build_divider_right_side():
    """Right-side sheet: Divider appears as first child of the inner Row."""
    inner = _container(StandardSideSheet(Box(), side="right").build()).children[0]
    assert isinstance(inner, LayoutRow)
    assert isinstance(inner.children[0], VerticalDivider)


def test_standard_side_sheet_build_divider_left_side():
    """Left-side sheet: Divider appears as last child of the inner Row."""
    inner = _container(StandardSideSheet(Box(), side="left").build()).children[0]
    assert isinstance(inner, LayoutRow)
    assert isinstance(inner.children[-1], VerticalDivider)


def test_standard_side_sheet_build_no_divider_when_disabled():
    """When show_divider=False, the container's child is the body Column."""
    sheet = StandardSideSheet(Box(), style=StandardSideSheetStyle(show_divider=False))
    assert isinstance(_container(sheet.build()).children[0], Column)


# ---------------------------------------------------------------------------
# Height resolution tests
# ---------------------------------------------------------------------------


def _layout_in_row(sheet: StandardSideSheet, width: int = 800, height: int = 600) -> tuple[int, int, int, int]:
    """Mount and lay the sheet out beside a filler widget; return its rect.

    Mounting is required: a composable only builds its subtree on mount, so an
    unmounted sheet would leave the inner widgets without a layout rect.
    """
    from nuiitivet.runtime.app import App

    row = LayoutRow([Box(width="100%", height="100%"), sheet], width=width, height=height)
    app = App(content=row, width=width, height=height)
    app.root.mount(app)
    app.root.layout(width, height)
    rect = sheet.layout_rect
    assert rect is not None
    return rect


def _built_container(sheet: StandardSideSheet) -> Box:
    """Return the container Box of the mounted (laid-out) subtree."""
    built = sheet._built
    assert built is not None
    return _container(built)


@pytest.mark.parametrize("show_divider", [True, False])
def test_standard_side_sheet_fills_parent_height(show_divider: bool):
    """The default height="100%" fills the parent regardless of the divider.

    The divider is a flex widget whose preferred height matches the available
    height, which used to be the only reason the sheet appeared full-height.
    """
    sheet = StandardSideSheet(
        Box(width=100, height=100),
        headline="Filters",
        style=StandardSideSheetStyle(show_divider=show_divider),
    )
    assert _layout_in_row(sheet)[3] == 600


@pytest.mark.parametrize("show_divider", [True, False])
def test_standard_side_sheet_fixed_style_height(show_divider: bool):
    """A fixed style height wins over both the content and the available height."""
    sheet = StandardSideSheet(
        Box(width=100, height=100),
        headline="Filters",
        style=StandardSideSheetStyle(height=300, show_divider=show_divider),
    )
    assert _layout_in_row(sheet)[3] == 300


@pytest.mark.parametrize("show_divider", [True, False])
def test_standard_side_sheet_content_is_top_aligned(show_divider: bool):
    """The body starts at the top of a full-height container, not centered."""
    sheet = StandardSideSheet(
        Box(width=100, height=100),
        headline="Filters",
        style=StandardSideSheetStyle(show_divider=show_divider),
    )
    _layout_in_row(sheet)
    body = _built_container(sheet).children[0]
    rect = body.layout_rect
    assert rect is not None
    assert rect[1] == 0


def test_standard_side_sheet_content_can_fill_height():
    """Content declaring a flex height gets the space left over by the header."""
    content = Box(width=100, height="100%")
    sheet = StandardSideSheet(content, headline="Filters")
    _layout_in_row(sheet)
    rect = content.layout_rect
    assert rect is not None
    # 600px container minus the 72px header row.
    assert rect[3] == 600 - 72


def test_standard_side_sheet_auto_content_keeps_natural_height():
    """Content without a height stays at its natural height."""
    content = Box(width=100, height=100)
    sheet = StandardSideSheet(content, headline="Filters")
    _layout_in_row(sheet)
    rect = content.layout_rect
    assert rect is not None
    assert rect[3] == 100


def test_standard_side_sheet_width_sizing_stays_auto():
    """The node width must stay auto: the open/close animation drives it."""
    sheet = StandardSideSheet(Box(width=100, height=100))
    assert sheet.width_sizing.kind == "auto"


def test_standard_side_sheet_namespace_export():
    """StandardSideSheet is accessible via the nuiitivet.material namespace."""
    import nuiitivet.material as m

    assert m.StandardSideSheet is StandardSideSheet


def test_standard_side_sheet_style_namespace_export():
    """StandardSideSheetStyle is accessible via the nuiitivet.material namespace."""
    import nuiitivet.material as m

    assert m.StandardSideSheetStyle is StandardSideSheetStyle
