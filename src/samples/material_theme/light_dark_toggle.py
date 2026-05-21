"""Material Theme - Light / Dark Toggle.

Demonstrates real-time theme switching using from_seed_pair and ThemeModeIntent.
Click the toggle button to switch between light and dark mode.
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Button, Text, ThemeFactory
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable
from nuiitivet.theme.intents import ThemeModeIntent
from nuiitivet.widgeting.widget import ComposableWidget, Widget

light, dark = ThemeFactory.from_seed_pair("#6750A4")


class HomeScreen(ComposableWidget):
    _is_dark: bool = False
    _toggle_label: Observable[str] = Observable("Switch to Dark")

    def build(self) -> Widget:
        return Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Column(
                gap=16,
                children=[
                    Text("Theme Toggle"),
                    Button("Get Started", style=ButtonStyle.filled()),
                    Button("Learn More", style=ButtonStyle.outlined()),
                    Button(self._toggle_label, style=ButtonStyle.tonal(), on_click=self._on_toggle),
                ],
            ),
        )

    def _on_toggle(self) -> None:
        self._is_dark = not self._is_dark
        self._toggle_label.value = "Switch to Light" if self._is_dark else "Switch to Dark"
        next_theme = dark if self._is_dark else light
        App.of(self).dispatch(ThemeModeIntent(theme=next_theme))


def main() -> None:
    App(
        content=HomeScreen(),
        title_bar=nv.DefaultTitleBar(title="Light / Dark Toggle"),
        theme=light,
        width=400,
        height=320,
    ).run()


if __name__ == "__main__":
    main()
