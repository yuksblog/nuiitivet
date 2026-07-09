"""Material Design 3 modal side sheet and bottom sheet widgets."""

from __future__ import annotations

import logging
from typing import Callable, Literal, Optional, Union

from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.divider import VerticalDivider
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL
from nuiitivet.material.styles.sheet_style import BottomSheetStyle, SideSheetStyle, StandardSideSheetStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable.protocols import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.overlay import OverlayAware
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

_logger = logging.getLogger(__name__)


class SideSheet(ComposableWidget, OverlayAware[None]):
    """Modal side sheet container widget.

    Renders an M3-compliant header (optional Back button, Headline, Close button) above
    *content*.  Pass this widget to ``MaterialOverlay.side_sheet()``.

    The header layout is fixed by M3 spec::

        [ Back (optional) ]  [ Headline ]  [ Close ]

    Note:
        The Back button is visible only when *show_back_button* is truthy **and**
        *on_back* is not ``None``.  Providing ``show_back_button=True`` alone
        without *on_back* will silently suppress the button.

    The Close button always dismisses the sheet through the overlay's unified
    dismissal pipeline. To intercept the close (for unsaved changes, etc.),
    attach a ``will_pop`` modifier::

        overlay.side_sheet(
            SideSheet(content, headline="Settings")
            .modifier(will_pop(on_will_pop=lambda: not has_unsaved_changes))
        )

    The slide-in edge and corner rounding are owned by
    ``MaterialOverlay.side_sheet(sheet, side=...)``, not by this widget.

    Args:
        content: Widget to display below the header.
        headline: Header title text (str or Observable[str]). Required by M3.
        on_back: Callback invoked when the Back icon button is pressed.
            Back button visibility is controlled separately by *show_back_button*.
        show_back_button: Whether to show the Back icon button.
            Accepts ``bool`` or ``Observable[bool]`` for dynamic toggling
            (e.g. driven by in-sheet navigation state). Defaults to ``False``.
            The button is only rendered when this is truthy **and** *on_back* is
            not ``None``.
        style: Container style. Defaults to :class:`SideSheetStyle`.
    """

    def __init__(
        self,
        content: Widget,
        *,
        headline: Union[str, ReadOnlyObservableProtocol[str]],
        on_back: Optional[Callable[[], None]] = None,
        show_back_button: Union[bool, ReadOnlyObservableProtocol[bool]] = False,
        style: Optional[SideSheetStyle] = None,
    ) -> None:
        """Initialize SideSheet.

        Args:
            content: Widget to display below the header.
            headline: Header title text (str or Observable[str]).
            on_back: Callback for the Back icon button press.
            show_back_button: Back button visibility (bool or Observable[bool]).
                Defaults to ``False``. Rendered only when truthy **and** *on_back*
                is not ``None``.
            style: Container style. Defaults to :class:`SideSheetStyle`.
        """
        _style = style if style is not None else SideSheetStyle()
        super().__init__(width=_style.width, height=_style.height)
        self._content = content
        self._headline = headline
        self._on_back = on_back
        self._show_back_button = show_back_button
        self._user_style = style

    @property
    def style(self) -> SideSheetStyle:
        """Return resolved sheet style."""
        return self._user_style if self._user_style is not None else SideSheetStyle()

    def _resolve_show_back(self) -> bool:
        if isinstance(self._show_back_button, ReadOnlyObservableProtocol):
            return bool(self._show_back_button.value)
        return bool(self._show_back_button)

    def _on_close_click(self) -> None:
        """Close button handler: route through overlay's unified dismissal pipeline."""
        if self._overlay_handle is None:
            return
        self.overlay_handle.request_close(None)

    def on_mount(self) -> None:
        """Mount and subscribe to show_back_button observable if provided."""
        super().on_mount()
        if isinstance(self._show_back_button, ReadOnlyObservableProtocol):
            sub = self._show_back_button.subscribe(lambda _: self.rebuild())
            self.bind(sub)

    def build(self) -> Widget:
        """Build the sheet: outer Box with header Row and content Column."""
        resolved_style = self.style

        # Header row: [Back slot] [Headline (flex)] [Close]
        # The back-button slot is always reserved (same width as IconButton default)
        # so the headline stays at a consistent horizontal position regardless of
        # whether the back button is visible.
        _BACK_SIZE = 40  # matches IconButton default size

        if self._resolve_show_back() and self._on_back is not None:
            back_slot: Widget = IconButton("arrow_back", on_click=self._on_back)
        else:
            back_slot = Box(width=_BACK_SIZE, height=_BACK_SIZE)

        header = Row(
            [
                back_slot,
                Box(
                    Text(
                        self._headline,
                        style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT),
                        type_scale=TypeScaleToken.from_size(22),
                    ),
                    width="100%",
                    padding=(8, 0, 8, 0),
                ),
                IconButton("close", on_click=self._on_close_click if self._overlay_handle is not None else None),
            ],
            width="100%",
            height=72,
            padding=(4, 0, 4, 0),
            cross_alignment="center",
        )

        # Corner rounding is applied by ``MaterialOverlay.side_sheet()`` via the
        # ``corner_radius`` modifier (it depends on the slide-in edge, which this
        # widget does not know).  The container itself is square.
        return Box(
            Column(
                [header, self._content],
                width="100%",
            ),
            width=resolved_style.width,
            height=resolved_style.height,
            background_color=resolved_style.background_color,
            alignment="top-left",
        )


class BottomSheet(ComposableWidget, OverlayAware[None]):
    """Modal bottom sheet container widget.

    Renders an M3-compliant header (Headline, Close button) above *content*.
    Pass this widget to ``MaterialOverlay.bottom_sheet()``.

    The header layout is fixed by M3 spec::

        [ Headline ]  [ Close ]

    The Close button always dismisses the sheet through the overlay's unified
    dismissal pipeline. To intercept the close (for unsaved changes, etc.),
    attach a ``will_pop`` modifier.

    Args:
        content: Widget to display below the header.
        headline: Header title text (str or Observable[str]). Required by M3.
        style: Container size, background, and shape options.
            Defaults to :class:`BottomSheetStyle`.
    """

    def __init__(
        self,
        content: Widget,
        *,
        headline: Union[str, ReadOnlyObservableProtocol[str]],
        style: Optional[BottomSheetStyle] = None,
    ) -> None:
        """Initialize BottomSheet.

        Args:
            content: Widget to display below the header.
            headline: Header title text (str or Observable[str]).
            style: Container style. Defaults to :class:`BottomSheetStyle`.
        """
        _style = style if style is not None else BottomSheetStyle()
        super().__init__(width=_style.width)
        self._content = content
        self._headline = headline
        self._user_style = style

    @property
    def style(self) -> BottomSheetStyle:
        """Return resolved sheet style."""
        return self._user_style if self._user_style is not None else BottomSheetStyle()

    def _on_close_click(self) -> None:
        """Close button handler: route through overlay's unified dismissal pipeline."""
        if self._overlay_handle is None:
            return
        self.overlay_handle.request_close(None)

    def build(self) -> Widget:
        """Build the sheet: outer Box with header Row and content Column."""
        resolved_style = self.style

        header = Row(
            [
                Box(
                    Text(
                        self._headline,
                        style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT),
                        type_scale=TypeScaleToken.from_size(22),
                    ),
                    width="100%",
                    padding=(8, 0, 8, 0),
                ),
                IconButton("close", on_click=self._on_close_click if self._overlay_handle is not None else None),
            ],
            width="100%",
            height=72,
            padding=(4, 0, 4, 0),
            cross_alignment="center",
        )

        # Round only the top corners.
        cr = float(resolved_style.corner_radius)
        corner_radius = (cr, cr, 0.0, 0.0)  # tl, tr, br, bl

        return Box(
            Column(
                [header, self._content],
                width="100%",
            ),
            width=resolved_style.width,
            height=resolved_style.height,
            corner_radius=corner_radius,
            background_color=resolved_style.background_color,
        )


class StandardSideSheet(ComposableWidget):
    """Material Design 3 standard (docked) side sheet.

    A standard side sheet is a permanent part of the layout, sitting beside
    the main content.  It owns its open/close animation: the sheet stays
    mounted while its allocated width animates between the style width and
    zero::

        opened: Observable[bool] = Observable(True)

        Row([
            main_content,
            StandardSideSheet(panel_content, headline="Filters", opened=opened),
        ])

    Toggling the sheet is a plain write to *opened*
    (``opened.value = not opened.value``).  Conditionally rendering the sheet
    instead would unmount it and skip the animation.

    The close icon button is rendered when the sheet can act on a press, i.e.
    when *opened* is a writable observable, when *on_close_click* is given, or
    both.  With a literal ``bool`` *opened* and no callback there is nothing a
    press could do, so no button is shown.

    Args:
        content: Widget to display inside the sheet.
        opened: ``bool`` or writable ``Observable[bool]`` driving the
            expand/collapse animation.  Defaults to ``True``.
        on_close_click: Callback invoked when the close icon button is
            pressed.  **Supplying it disables the default auto-close**: the
            sheet no longer writes ``opened.value = False`` and updating
            *opened* becomes the caller's responsibility.  This is the
            interception point for confirm-before-close flows.
        headline: Optional header title text (``str`` or
            ``Observable[str]``).  When provided, an M3-compliant header row
            is rendered above *content*.
        side: Edge the sheet is attached to (``"right"`` or ``"left"``).
            Defaults to ``"right"``.  The collapse anchor is derived from it.
        style: Container style.  Defaults to :class:`StandardSideSheetStyle`.
    """

    def __init__(
        self,
        content: Widget,
        *,
        opened: Union[bool, ObservableProtocol[bool]] = True,
        on_close_click: Optional[Callable[[], None]] = None,
        headline: Optional[Union[str, ReadOnlyObservableProtocol[str]]] = None,
        side: Literal["right", "left"] = "right",
        style: Optional[StandardSideSheetStyle] = None,
    ) -> None:
        """Initialize StandardSideSheet.

        Args:
            content: Widget to display inside the sheet.
            opened: ``bool`` or writable ``Observable[bool]``.  Defaults to
                ``True``.
            on_close_click: Callback for the close icon button.  Supplying it
                disables the default ``opened.value = False`` auto-close.
            headline: Optional header title (str or Observable[str]).
            side: Attachment edge (``"right"`` or ``"left"``).
                Defaults to ``"right"``.
            style: Container style.  Defaults to :class:`StandardSideSheetStyle`.
        """
        super().__init__()
        self._content = content
        self._opened = opened
        self._on_close_click = on_close_click
        self._headline = headline
        self.side = side
        self._user_style = style

    @property
    def style(self) -> StandardSideSheetStyle:
        """Return the resolved sheet style."""
        return self._user_style if self._user_style is not None else StandardSideSheetStyle()

    def _can_auto_close(self) -> bool:
        """Return whether *opened* is writable, i.e. the sheet can close itself."""
        return isinstance(self._opened, ObservableProtocol)

    def _show_close_button(self) -> bool:
        return self._on_close_click is not None or self._can_auto_close()

    def _handle_close_click(self) -> None:
        """Close button handler: the callback replaces the default auto-close."""
        if self._on_close_click is not None:
            self._on_close_click()
            return
        if isinstance(self._opened, ObservableProtocol):
            self._opened.value = False

    def on_mount(self) -> None:
        """Mount and subscribe to headline observable if provided."""
        super().on_mount()
        if isinstance(self._headline, ReadOnlyObservableProtocol):
            sub = self._headline.subscribe(lambda _: self.rebuild())
            self.bind(sub)

    def build(self) -> Widget:
        """Build the sheet: a Collapsible wrapping the sheet container Box."""
        resolved_style = self.style

        # Optionally build the header row (headline + close button).
        body_parts: list[Widget] = []
        show_close = self._show_close_button()
        if self._headline is not None or show_close:
            header_children: list[Widget] = []
            if self._headline is not None:
                header_children.append(
                    Box(
                        Text(
                            self._headline,
                            style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT),
                            type_scale=TypeScaleToken.from_size(22),
                        ),
                        width=Sizing.flex(1),
                        padding=(8, 0, 8, 0),
                    )
                )
            if show_close:
                header_children.append(IconButton("close", on_click=self._handle_close_click))
            body_parts.append(
                Row(
                    header_children,
                    width="100%",
                    height=72,
                    padding=(4, 0, 4, 0),
                    cross_alignment="center",
                )
            )
        body_parts.append(self._content)

        content_col = Column(body_parts, width=Sizing.flex(1))

        # Optionally add a vertical Divider on the edge facing the main content.
        if resolved_style.show_divider:
            divider = VerticalDivider()
            if self.side == "right":
                inner: Widget = Row([divider, content_col], width="100%", height="100%")
            else:
                inner = Row([content_col, divider], width="100%", height="100%")
        else:
            inner = content_col

        container = Box(
            inner,
            width=resolved_style.width,
            height=resolved_style.height,
            background_color=resolved_style.background_color,
        )

        # The collapse anchor is the edge the sheet is docked to: the child is
        # laid out at its natural width while the allocated rect shrinks, so
        # the docked edge must stay pinned.
        alignment = ("end", "start") if self.side == "right" else ("start", "start")
        return Collapsible(
            container,
            opened=self._opened,
            axis="horizontal",
            alignment=alignment,
            motion=EXPRESSIVE_DEFAULT_SPATIAL,
        )


__all__ = ["SideSheet", "BottomSheet", "StandardSideSheet"]
