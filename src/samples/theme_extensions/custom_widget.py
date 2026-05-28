"""Theme Extensions - Custom Widget.

Demonstrates how to create a ThemeExtension and use it inside a custom widget.
The ``AppBrandTheme`` extension stores brand-specific colors that are not part
of Material Design.  ``BrandCard`` reads those colors via ``theme.extension()``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import App, Text, ThemeFactory
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.modifiers import background, corner_radius
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import ComposableWidget, Widget

# ---------------------------------------------------------------------------
# 1. Define a custom ThemeExtension
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppBrandTheme:
    """Brand-specific design tokens for this application.

    This extension coexists alongside ``MaterialThemeData`` in the same
    ``Theme.extensions`` list.
    """

    brand_primary: str = "#1A6B3C"
    brand_on_primary: str = "#FFFFFF"
    brand_surface: str = "#E8F5E9"
    brand_accent: str = "#FF6F00"

    def copy_with(self, **kwargs) -> "AppBrandTheme":
        """Return a copy with selected fields replaced."""
        return replace(self, **kwargs)


# ---------------------------------------------------------------------------
# 2. Build the Theme (Material + AppBrandTheme coexist)
# ---------------------------------------------------------------------------


def make_theme() -> Theme:
    """Create a theme that contains both Material and brand extensions."""
    base = ThemeFactory.light("#1A6B3C")
    # Append the brand extension to the existing extensions list
    return Theme(
        mode=base.mode,
        extensions=[*base.extensions, AppBrandTheme()],
        name="app-brand-light",
    )


# ---------------------------------------------------------------------------
# 3. Custom widget that reads from AppBrandTheme
# ---------------------------------------------------------------------------


class BrandCard(ComposableWidget):
    """A card-like widget styled with brand colors from ``AppBrandTheme``."""

    def __init__(self, heading: str, content: str) -> None:
        super().__init__()
        self.heading = heading
        self.content = content

    def build(self) -> Widget:
        brand = Theme.of(self).extension(AppBrandTheme)
        bg = brand.brand_surface if brand else "#E8F5E9"
        accent = brand.brand_accent if brand else "#FF6F00"

        return Container(
            padding=16,
            child=Column(
                gap=8,
                children=[
                    Text(self.heading, style=TextStyle(color=accent, font_size=16)),
                    Text(self.content, style=TextStyle(font_size=13)),
                ],
            ),
        ).modifier(background(bg) | corner_radius(12))


class HomeScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=16,
                children=[
                    BrandCard(
                        heading="Welcome",
                        content="This card uses AppBrandTheme colors.",
                    ),
                    BrandCard(
                        heading="Feature",
                        content="Multiple extensions can coexist in one Theme.",
                    ),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = App(
        content=HomeScreen(),
        title="Theme Extensions - Custom Widget",
        theme=make_theme(),
        width=400,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
