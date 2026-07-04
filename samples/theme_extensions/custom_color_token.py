"""Theme Extensions - Light/Dark Widget.

Demonstrates how to extend ``AppBrandTheme`` to support light and dark modes.
``BrandCard`` is identical to the custom_widget.py example — the widget code
does not change at all.  Only the ``ThemeExtension`` values differ between the
two themes.

Run the app and click "Switch to Dark / Light" to toggle the theme at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from typing import Optional

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material import App, Button, Text, ThemeFactory
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.modifiers import background, corner_radius
from nuiitivet.observable import Observable
from nuiitivet.theme import ThemeExtension
from nuiitivet.theme.intents import ThemeModeIntent
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import ComposableWidget, Widget

# ---------------------------------------------------------------------------
# 1. ThemeExtension — same structure, different values per mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppBrandTheme:
    """Brand-specific design tokens for this application."""

    brand_surface: str
    brand_on_surface: str  # text color on top of brand_surface
    brand_accent: str

    def copy_with(self, **kwargs) -> ThemeExtension:
        """Return a copy with selected fields replaced."""
        return replace(self, **kwargs)


# ---------------------------------------------------------------------------
# 2. Two theme factories — light and dark
# ---------------------------------------------------------------------------


def make_light_theme() -> Theme:
    """Light variant: soft green surface, orange accent."""
    base = ThemeFactory.light("#1A6B3C")
    return Theme(
        mode=base.mode,
        extensions=[
            *base.extensions,
            AppBrandTheme(
                brand_surface="#E8F5E9",
                brand_on_surface="#1B2A1F",
                brand_accent="#FF6F00",
            ),
        ],
        name="app-brand-light",
    )


def make_dark_theme() -> Theme:
    """Dark variant: deep green surface, amber accent."""
    base = ThemeFactory.dark("#1A6B3C")
    return Theme(
        mode=base.mode,
        extensions=[
            *base.extensions,
            AppBrandTheme(
                brand_surface="#1B3A2A",
                brand_on_surface="#C8E6C9",
                brand_accent="#FFB300",
            ),
        ],
        name="app-brand-dark",
    )


_light = make_light_theme()
_dark = make_dark_theme()


# ---------------------------------------------------------------------------
# 3. Custom widget — unchanged from Use case 1
# ---------------------------------------------------------------------------


class BrandCard(ComposableWidget):
    """Reads brand colors from AppBrandTheme — same code as Use case 1."""

    def __init__(self, heading: str, content: str) -> None:
        super().__init__()
        self.heading = heading
        self.content = content
        self._theme_manager: Optional[ThemeManager] = None

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.runtime.app import AppScope

        scope = self.find_ancestor(AppScope)
        if scope is not None:
            self._theme_manager = scope.theme_manager
            self._theme_manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        if self._theme_manager is not None:
            self._theme_manager.unsubscribe(self._on_theme_change)
            self._theme_manager = None
        super().on_unmount()

    def _on_theme_change(self, _theme: Theme) -> None:
        self.rebuild()

    def build(self) -> Widget:
        brand = Theme.of(self).extension(AppBrandTheme)
        bg = brand.brand_surface if brand else "#1B3A2A"
        fg = brand.brand_on_surface if brand else "#C8E6C9"
        accent = brand.brand_accent if brand else "#FFB300"

        return Container(
            padding=16,
            child=Column(
                gap=8,
                children=[
                    Text(self.heading, style=TextStyle(color=accent), type_scale=TypeScaleToken.from_size(16)),
                    Text(self.content, style=TextStyle(color=fg), type_scale=TypeScaleToken.from_size(13)),
                ],
            ),
        ).modifier(background(bg) | corner_radius(12))


# ---------------------------------------------------------------------------
# 4. HomeScreen with a toggle button
# ---------------------------------------------------------------------------


class HomeScreen(ComposableWidget):
    _is_dark: bool = True
    _toggle_label: Observable[str] = Observable("Switch to Light")

    def build(self) -> Widget:
        return Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=16,
                children=[
                    BrandCard(
                        heading="Brand Card",
                        content="Colors come from AppBrandTheme.",
                    ),
                    Button(
                        self._toggle_label,
                        style=ButtonStyle.tonal(),
                        on_click=self._on_toggle,
                    ),
                ],
            ),
        )

    def _on_toggle(self) -> None:
        self._is_dark = not self._is_dark
        next_theme = _dark if self._is_dark else _light
        self._toggle_label.value = "Switch to Light" if self._is_dark else "Switch to Dark"
        App.of(self).dispatch(ThemeModeIntent(theme=next_theme))


def main(png_path: str = "") -> None:
    app = App(
        content=HomeScreen(),
        title="Theme Extensions - Light/Dark Widget",
        theme=_dark,
        width=400,
        height=280,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
