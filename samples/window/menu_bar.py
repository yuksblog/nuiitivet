"""Application menu bar with ``App(menu=...)``.

The menu is a declarative model registered on the App — not widgets in the
tree. It renders as a bar below the chrome, popups included; items carry
accelerators (displayed and registered from the same declaration), Observable
``enabled`` / ``checked`` state, nested submenus, and standard items like
``MenuEntry.quit()``.

Interactions:
    - Click File / Edit / View, or open a menu and switch with Left / Right.
    - "Save" is enabled only after "Open..." ran; Accel+S fires it without
      opening the menu.
    - View > Word Wrap is checkable; the readout follows it.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class State:
    """App-level state: the menu binds to it, so it is created once in main
    and survives hot reloads of the widget tree."""

    def __init__(self) -> None:
        self.log = nv.Observable("Pick something from the menu.")
        self.can_save = nv.Observable(False)
        self.word_wrap = nv.Observable(False)

    def open(self) -> None:
        self.can_save.value = True
        self.say("Opened; Save is now enabled.")

    def say(self, message: str) -> None:
        self.log.value = message


def _menu(state: State) -> nv.MenuBar:
    return nv.MenuBar(
        [
            nv.MenuEntry(
                "File",
                submenu=[
                    nv.MenuEntry("Open...", shortcut="Accel+O", on_select=state.open),
                    nv.MenuEntry(
                        "Save",
                        shortcut="Accel+S",
                        on_select=lambda: state.say("Saved."),
                        enabled=state.can_save,
                    ),
                    nv.MenuEntry.separator(),
                    nv.MenuEntry.quit(),
                ],
            ),
            nv.MenuEntry(
                "Edit",
                submenu=[
                    nv.MenuEntry("Undo", shortcut="Accel+Z", on_select=lambda: state.say("Undo.")),
                    nv.MenuEntry("Redo", shortcut="Accel+Shift+Z", on_select=lambda: state.say("Redo.")),
                    nv.MenuEntry.separator(),
                    nv.MenuEntry(
                        "Advanced",
                        submenu=[
                            nv.MenuEntry("Sort Lines", on_select=lambda: state.say("Sorted.")),
                        ],
                    ),
                ],
            ),
            nv.MenuEntry(
                "View",
                submenu=[
                    nv.MenuEntry(
                        "Word Wrap",
                        on_select=lambda: state.say(f"Word wrap: {state.word_wrap.value}"),
                        checked=state.word_wrap,
                    ),
                    nv.MenuEntry.full_screen(),
                ],
            ),
        ]
    )


class Screen(nv.ComposableWidget):
    def __init__(self, state: State) -> None:
        super().__init__()
        self.state = state

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Menu bar", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.state.log, style=_MUTED),
                nv.Text(self.state.word_wrap.map(lambda w: f"word wrap: {'on' if w else 'off'}"), style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    state = State()
    app = nv.App(
        nv.Window(content=lambda: Screen(state), title="menu_bar", width=560, height=320, menu=_menu(state))
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
