"""The app's own icon with ``App(icon=...)``.

A script run from the terminal shows the Python rocket in the Dock and on the
taskbar. ``icon=`` replaces it with the app's own image on every window the
app opens, the ones opened later too.

Interactions (run from a real terminal so the OS shows the icon):
    - Look at the Dock (macOS) or the taskbar button (Windows): the purple N,
      not the Python rocket.
    - "Open a second window" opens one more window; it carries the same icon.
"""

from __future__ import annotations

from pathlib import Path

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)
ICON = Path(__file__).parent / "assets" / "app_icon.png"


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.opened = nv.Observable(0)

    def _open_window(self) -> None:
        self.opened.value += 1
        nv.Window(
            content=lambda: nv.Text("Same icon here.", padding=24),
            title=f"Window {self.opened.value + 1}",
            width=320,
            height=160,
        ).open()

    def build(self):
        return nv.Column(
            children=[
                nv.Text("App icon", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text("Look at the Dock or the taskbar: the purple N is this app.", style=_MUTED),
                nv.Button("Open a second window", on_click=self._open_window),
                nv.Text(self.opened.map(lambda n: f"windows opened: {n}"), style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    app = nv.App(
        nv.Window(content=Screen, title="app_icon", width=480, height=240),
        icon=ICON,  # the Dock / taskbar / favicon image
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
