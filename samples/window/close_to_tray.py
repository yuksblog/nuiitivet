"""A tray-resident app: close-to-tray with the full recipe.

Three independent declarations make an app resident — each line keeps its
meaning if the others are removed:

- ``exit_policy=EXPLICIT``: only Quit exits the app.
- ``Window(close_action=...)``: the close button hides instead of closing —
  bound to ``tray.installed`` so it falls back to closing when no tray icon
  is actually showing (nothing to summon the app back from).
- ``App(tray=...)``: the tray icon itself, with ``dock_visibility="auto"``
  so on macOS the Dock icon disappears while the window is hidden.

Interactions (run from a real terminal so the OS shows the icon):
    - Close the window with the OS close button: it hides, the app stays in
      the tray (macOS: the Dock icon disappears too).
    - Tray menu "Open" summons the window back — state intact.
    - Tray menu "Quit" is the only way to exit.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.notes = nv.Observable("")

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Close to tray", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(
                    "Close this window: it hides to the tray. "
                    "Type something first — it survives the round trip.",
                    style=_MUTED,
                ),
                nv.TextField(value=self.notes, label="Scratch note"),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    screen = Screen()
    window: nv.Window  # assigned below; the tray menu closure resolves it lazily
    tray = nv.TrayIcon(
        tooltip="Close to Tray",
        dock_visibility="auto",
        menu=[
            nv.MenuEntry("Open", on_select=lambda: window.show()),
            nv.MenuEntry.separator(),
            nv.MenuEntry.quit(),
        ],
    )
    window = nv.Window(
        content=screen,
        title="close_to_tray",
        width=480,
        height=240,
        close_action=tray.installed.map(lambda ok: "hide" if ok else "close"),
    )
    app = nv.App(window, tray=tray, exit_policy=nv.ExitPolicy.EXPLICIT)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
