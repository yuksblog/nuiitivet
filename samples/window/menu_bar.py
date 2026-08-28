"""Application menu bar with ``App(menu=...)``.

The menu is a declarative model registered on the App — not widgets in the
tree. It renders as a bar below the chrome, popups included; items carry
accelerators (displayed and registered from the same declaration), Observable
``enabled`` / ``checked`` state, nested submenus, and standard items like
``MenuBarItem.quit()``.

Interactions:
    - Click File / Edit / View, or open a menu and switch with Left / Right.
    - "Save" is enabled only after "Open..." ran; Accel+S fires it without
      opening the menu.
    - View > Word Wrap is checkable; the readout follows it.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.log = nv.Observable("Pick something from the menu.")
        self.can_save = nv.Observable(False)
        self.word_wrap = nv.Observable(False)

    def menu(self) -> nv.MenuBar:
        return nv.MenuBar(
            [
                nv.MenuBarItem(
                    "File",
                    submenu=[
                        nv.MenuBarItem("Open...", shortcut="Accel+O", on_select=self._open),
                        nv.MenuBarItem(
                            "Save",
                            shortcut="Accel+S",
                            on_select=lambda: self._say("Saved."),
                            enabled=self.can_save,
                        ),
                        nv.MenuBarItem.separator(),
                        nv.MenuBarItem.quit(),
                    ],
                ),
                nv.MenuBarItem(
                    "Edit",
                    submenu=[
                        nv.MenuBarItem("Undo", shortcut="Accel+Z", on_select=lambda: self._say("Undo.")),
                        nv.MenuBarItem("Redo", shortcut="Accel+Shift+Z", on_select=lambda: self._say("Redo.")),
                        nv.MenuBarItem.separator(),
                        nv.MenuBarItem(
                            "Advanced",
                            submenu=[
                                nv.MenuBarItem("Sort Lines", on_select=lambda: self._say("Sorted.")),
                            ],
                        ),
                    ],
                ),
                nv.MenuBarItem(
                    "View",
                    submenu=[
                        nv.MenuBarItem(
                            "Word Wrap",
                            on_select=lambda: self._say(f"Word wrap: {self.word_wrap.value}"),
                            checked=self.word_wrap,
                        ),
                        nv.MenuBarItem.full_screen(),
                    ],
                ),
            ]
        )

    def _open(self) -> None:
        self.can_save.value = True
        self._say("Opened; Save is now enabled.")

    def _say(self, message: str) -> None:
        self.log.value = message

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Menu bar", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.log, style=_MUTED),
                nv.Text(self.word_wrap.map(lambda w: f"word wrap: {'on' if w else 'off'}"), style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    screen = Screen()
    app = nv.App(nv.Window(content=screen, title="menu_bar", width=560, height=320, menu=screen.menu()))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
