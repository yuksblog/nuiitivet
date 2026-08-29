"""System tray icon with ``App(tray=...)``.

The tray icon is declarative data registered on the App, like the menu bar:
a ``TrayIcon`` with a tooltip and a menu of ``MenuEntry`` entries. It is
installed while the app runs and removed when the app exits; whether the
platform actually showed it is readable from ``tray.installed``.

Interactions (run from a real terminal so the OS shows the icon):
    - Find the icon in the system tray (macOS: right side of the menu bar;
      without an ``icon=`` image it shows the tooltip text).
    - "Ping" bumps the counter in the window; its label live-updates in the
      native menu (Observable label).
    - "Muted" is checkable; the window readout follows it.
    - "Quit" exits the app — the same standard item as in a menu bar.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pings = nv.Observable(0)
        self.muted = nv.Observable(False)

    def tray(self) -> nv.TrayIcon:
        return nv.TrayIcon(
            tooltip="Nuiitivet Tray",
            menu=[
                nv.MenuEntry(
                    self.pings.map(lambda n: f"Ping ({n})"),
                    on_select=self._ping,
                ),
                nv.MenuEntry("Muted", on_select=lambda: None, checked=self.muted),
                nv.MenuEntry.separator(),
                nv.MenuEntry.quit(),
            ],
        )

    def _ping(self) -> None:
        self.pings.value += 1

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Tray icon", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.pings.map(lambda n: f"pings: {n}"), style=_MUTED),
                nv.Text(
                    self.muted.map(lambda m: f"muted: {'on' if m else 'off'}"),
                    style=_MUTED,
                ),
                nv.Text("Use the tray icon's menu; Quit exits the app.", style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    screen = Screen()
    app = nv.App(
        nv.Window(content=screen, title="tray_icon", width=480, height=240),
        tray=screen.tray(),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
