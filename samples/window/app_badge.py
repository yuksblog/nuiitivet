"""An unread count on the Dock / taskbar icon with ``app.badge``.

The app writes a count or a short text to ``app.badge``; the OS draws it on
the app's icon, where it shows while the window is in the background.

Interactions (run from a real terminal so the OS shows the badge):
    - "New message" adds one: the Dock icon (macOS) or the taskbar button
      (Windows) shows the count.
    - "Alert" shows "!" in place of the count.
    - "Mark all read" removes the badge.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.unread = nv.State(0)

    def _new_message(self) -> None:
        self.unread.value += 1
        nv.App.of(self).badge.value = self.unread.value  # a count

    def _alert(self) -> None:
        nv.App.of(self).badge.value = "!"  # a short text

    def _mark_all_read(self) -> None:
        self.unread.value = 0
        nv.App.of(self).badge.value = None  # no badge

    def build(self):
        return nv.Column(
            children=[
                nv.Text("App badge", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text("Look at the Dock or the taskbar: the icon carries the count.", style=_MUTED),
                nv.Row(
                    children=[
                        nv.Button("New message", on_click=self._new_message),
                        nv.Button("Alert", on_click=self._alert),
                        nv.Button("Mark all read", on_click=self._mark_all_read),
                    ],
                    gap=8,
                ),
                nv.Text(self.unread.map(lambda n: f"unread: {n}"), style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    app = nv.App(nv.Window(content=Screen, title="app_badge", width=520, height=240))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
