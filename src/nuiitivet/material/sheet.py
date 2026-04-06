"""Material Design 3 modal side sheet and bottom sheet widgets."""

from __future__ import annotations

import logging
from typing import Callable, Literal, Optional, Union

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.styles.sheet_style import BottomSheetStyle, SideSheetStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

_logger = logging.getLogger(__name__)


class SideSheet(ComposableWidget):
    """Modal side sheet container widget.

    Renders an M3-compliant header (optional Back button, Headline, Close button) above
    *content*.  Pass this widget to ``MaterialOverlay.side_sheet()``.

    The header layout is fixed by M3 spec::

        [ Back (optional) ]  [ Headline ]  [ Close ]

    Note:
        The Back button is visible only when *show_back_button* is truthy **and**
        *on_back* is not ``None``.  Providing ``show_back_button=True`` alone
        without *on_back* will silently suppress the button.

    Args:
        content: Widget to display below the header.
        headline: Header title text (str or Observable[str]). Required by M3.
        side: Edge the sheet slides in from (``"right"`` or ``"left"``).
            Defaults to ``"right"``.
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
        side: Literal["right", "left"] = "right",
        on_back: Optional[Callable[[], None]] = None,
        show_back_button: Union[bool, ReadOnlyObservableProtocol[bool]] = False,
        on_close: Optional[Callable[[], None]] = None,
        style: Optional[SideSheetStyle] = None,
    ) -> None:
        """Initialize SideSheet.

        Args:
            content: Widget to display below the header.
            headline: Header title text (str or Observable[str]).
            side: Edge the sheet slides in from. Defaults to ``"right"``.
            on_back: Callback for the Back icon button press.
            show_back_button: Back button visibility (bool or Observable[bool]).
                Defaults to ``False``. Rendered only when truthy **and** *on_back*
                is not ``None``.
            on_close: Callback for the Close icon button press.
            style: Container style. Defaults to :class:`SideSheetStyle`.
        """
        _style = style if style is not None else SideSheetStyle()
        super().__init__(height=_style.height)
        self._content = content
        self._headline = headline
        self.side = side
        self._on_back = on_back
        self._show_back_button = show_back_button
        self._on_close = on_close
        self._user_style = style

    @property
    def style(self) -> SideSheetStyle:
        """Return resolved sheet style."""
        return self._user_style if self._user_style is not None else SideSheetStyle()

    def _resolve_show_back(self) -> bool:
        if isinstance(self._show_back_button, ReadOnlyObservableProtocol):
            return bool(self._show_back_button.value)
        return bool(self._show_back_button)

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
                        style=TextStyle(font_size=22, color=ColorRole.ON_SURFACE_VARIANT),
                    ),
                    width="100%",
                    padding=(8, 0, 8, 0),
                ),
                # TODO(#38): when IOverlayAware is available, wire None → handle.close()
                IconButton("close", on_click=self._on_close),
            ],
            width="100%",
            height=72,
            padding=(4, 0, 4, 0),
            cross_alignment="center",
        )

        # Apply per-corner radius: round only the inner (away-from-edge) corners.
        cr = float(resolved_style.corner_radius)
        if self.side == "right":
            corner_radius = (cr, 0.0, 0.0, cr)  # tl, tr, br, bl
        else:
            corner_radius = (0.0, cr, cr, 0.0)  # tl, tr, br, bl

        return Box(
            Column(
                [header, self._content],
                width="100%",
            ),
            width=resolved_style.width,
            height=resolved_style.height,
            corner_radius=corner_radius,
            background_color=resolved_style.background_color,
            alignment="top-left",
        )


class BottomSheet(ComposableWidget):
    """Modal bottom sheet container widget.

    Renders an M3-compliant header (Headline, Close button) above *content*.
    Pass this widget to ``MaterialOverlay.bottom_sheet()``.

    The header layout is fixed by M3 spec::

        [ Headline ]  [ Close ]

    Args:
        content: Widget to display below the header.
        headline: Header title text (str or Observable[str]). Required by M3.
        on_close: Callback invoked when the Close icon button is pressed.
            If ``None``, the button will trigger ``IOverlayAware.close()``
            automatically once Issue #38 is resolved.
        style: Container size, background, and shape options.
            Defaults to :class:`BottomSheetStyle`.
    """

    def __init__(
        self,
        content: Widget,
        *,
        headline: Union[str, ReadOnlyObservableProtocol[str]],
        on_close: Optional[Callable[[], None]] = None,
        style: Optional[BottomSheetStyle] = None,
    ) -> None:
        """Initialize BottomSheet.

        Args:
            content: Widget to display below the header.
            headline: Header title text (str or Observable[str]).
            on_close: Callback for the Close icon button press.
            style: Container style. Defaults to :class:`BottomSheetStyle`.
        """
        _style = style if style is not None else BottomSheetStyle()
        super().__init__(width=_style.width)
        self._content = content
        self._headline = headline
        self._on_close = on_close
        self._user_style = style

    @property
    def style(self) -> BottomSheetStyle:
        """Return resolved sheet style."""
        return self._user_style if self._user_style is not None else BottomSheetStyle()

    def build(self) -> Widget:
        """Build the sheet: outer Box with header Row and content Column."""
        resolved_style = self.style

        header = Row(
            [
                Box(
                    Text(
                        self._headline,
                        style=TextStyle(font_size=22, color=ColorRole.ON_SURFACE_VARIANT),
                    ),
                    width="100%",
                    padding=(8, 0, 8, 0),
                ),
                # TODO(#38): when IOverlayAware is available, wire None → handle.close()
                IconButton("close", on_click=self._on_close),
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


__all__ = ["SideSheet", "BottomSheet"]
