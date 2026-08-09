"""Theme Extensions - Light/Dark Widget.

Demonstrates how to extend ``AppBrandTheme`` to support light and dark modes.
``BrandCard`` is identical to the custom_widget.py example — the widget code
does not change at all.  Only the ``ThemeExtension`` values differ between the
two themes.

Run the app and click "Switch to Dark / Light" to toggle the theme at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import nuiitivet.material as nv

# ---------------------------------------------------------------------------
# 1. ThemeExtension — same structure, different values per mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppBrandTheme:
    """Brand-specific design tokens for this application."""

    brand_surface: str
    brand_on_surface: str  # text color on top of brand_surface
    brand_accent: str

    def copy_with(self, **kwargs) -> nv.ThemeExtension:
        """Return a copy with selected fields replaced."""
        return replace(self, **kwargs)


# ---------------------------------------------------------------------------
# 2. Two theme factories — light and dark
# ---------------------------------------------------------------------------


def make_light_theme() -> nv.Theme:
    """Light variant: soft green surface, orange accent."""
    base = nv.ThemeFactory.light("#1A6B3C")
    return nv.Theme(
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


def make_dark_theme() -> nv.Theme:
    """Dark variant: deep green surface, amber accent."""
    base = nv.ThemeFactory.dark("#1A6B3C")
    return nv.Theme(
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


class BrandCard(nv.ComposableWidget):
    """Reads brand colors from AppBrandTheme — same code as Use case 1."""

    def __init__(self, heading: str, content: str) -> None:
        super().__init__()
        self.heading = heading
        self.content = content

    def build(self) -> nv.Widget:
        brand = nv.Theme.of(self).extension(AppBrandTheme)
        bg = brand.brand_surface if brand else "#1B3A2A"
        fg = brand.brand_on_surface if brand else "#C8E6C9"
        accent = brand.brand_accent if brand else "#FFB300"

        return nv.Container(
            padding=16,
            child=nv.Column(
                gap=8,
                children=[
                    nv.Text(self.heading, style=nv.TextStyle(color=accent), type_scale=nv.TypeScaleToken.from_size(16)),
                    nv.Text(self.content, style=nv.TextStyle(color=fg), type_scale=nv.TypeScaleToken.from_size(13)),
                ],
            ),
        ).modifier(nv.background(bg) | nv.corner_radius(12))


# ---------------------------------------------------------------------------
# 4. HomeScreen with a toggle button
# ---------------------------------------------------------------------------


class HomeScreen(nv.ComposableWidget):
    _is_dark: bool = True
    _toggle_label: nv.Observable[str] = nv.Observable("Switch to Light")

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    BrandCard(
                        heading="Brand Card",
                        content="Colors come from AppBrandTheme.",
                    ),
                    nv.Button(
                        self._toggle_label,
                        style=nv.ButtonStyle.tonal(),
                        on_click=self._on_toggle,
                    ),
                ],
            ),
        )

    def _on_toggle(self) -> None:
        self._is_dark = not self._is_dark
        next_theme = _dark if self._is_dark else _light
        self._toggle_label.value = "Switch to Light" if self._is_dark else "Switch to Dark"
        nv.App.of(self).dispatch(nv.ThemeModeIntent(theme=next_theme))


def main(png_path: str = "") -> None:
    app = nv.App(
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
