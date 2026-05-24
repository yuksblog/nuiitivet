"""Window chrome configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from nuiitivet.widgeting.widget import Widget
    from nuiitivet.theme.types import ColorSpec

OSChromeVariant = Literal["default", "dialog", "tool", "borderless", "transparent"]

_VARIANT_DOC = (
    '"default": standard OS window, '
    '"dialog": no minimize/maximize, '
    '"tool": small title bar, '
    '"borderless": no OS decoration, '
    '"transparent": transparent background'
)


@dataclass
class Border:
    """Border specification for CustomChrome.

    Attributes:
        color: Border color (any ColorSpec accepted by the theme system).
        width: Border width in logical pixels.
    """

    color: "ColorSpec"
    width: float = 1.0


@dataclass
class OSChrome:
    """OS-managed window decoration.

    Maps *variant* directly to ``pyglet.window.Window.WINDOW_STYLE_*``.

    Args:
        variant: Window style. One of: "default", "dialog", "tool",
            "borderless", "transparent".
    """

    variant: OSChromeVariant = "default"


@dataclass
class CustomChrome:
    """Custom (app-drawn) window decoration.

    Always uses a borderless OS window (no OS title bar).
    Wraps *header* in :class:`~nuiitivet.runtime.title_bar.WindowDragArea`
    so the user can drag the window by the header.

    Args:
        header: Widget rendered as the window's title-bar area.
        corner_radius: Corner radius in logical pixels applied by the render
            layer. Content is clipped to a rounded rectangle; pixels outside
            the rounded corners are cleared to transparent. Note that true
            desktop-transparency in the corners requires platform-level window
            compositing support.
        border: Optional border drawn around the window edge inside the
            rounded-corner boundary.
    """

    header: "Widget"
    corner_radius: float = 0.0
    border: Optional[Border] = None
