"""Material Theme - Dark Mode.

Demonstrates dark mode using the same seed color as the light theme.
"""

from __future__ import annotations

import nuiitivet.material as nv


class HomeScreen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Material App"),
                    nv.Button("Get Started", style=nv.ButtonStyle.filled()),
                    nv.Button("Learn More", style=nv.ButtonStyle.outlined()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = nv.App(
        nv.Window(content=HomeScreen(), title="Dark Mode", width=400, height=280),
        theme=nv.ThemeFactory.dark("#00639B"),
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
