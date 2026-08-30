"""Material Theme - Light / Dark Toggle.

Demonstrates real-time theme switching using from_seed_pair and
``App.of(...).set_theme``. Click the toggle button to switch between light
and dark mode.
"""

from __future__ import annotations

import nuiitivet.material as nv

light, dark = nv.ThemeFactory.from_seed_pair("#6750A4")


class HomeScreen(nv.ComposableWidget):
    _is_dark: bool = False
    _toggle_label: nv.Observable[str] = nv.Observable("Switch to Dark")

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Theme Toggle"),
                    nv.Button("Get Started", style=nv.ButtonStyle.filled()),
                    nv.Button("Learn More", style=nv.ButtonStyle.outlined()),
                    nv.Button(self._toggle_label, style=nv.ButtonStyle.tonal(), on_click=self._on_toggle),
                ],
            ),
        )

    def _on_toggle(self) -> None:
        self._is_dark = not self._is_dark
        self._toggle_label.value = "Switch to Light" if self._is_dark else "Switch to Dark"
        next_theme = dark if self._is_dark else light
        nv.App.of(self).set_theme(next_theme)


def main() -> None:
    nv.App(nv.Window(content=HomeScreen(), title="Light / Dark Toggle", width=400, height=320), theme=light).run()


if __name__ == "__main__":
    main()
