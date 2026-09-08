"""One shared menu command acting on whichever pane is focused.

A shared "Save" entry must save the document the user is working in. The app
owns an ``active`` Observable: each pane writes it when it gains focus, and
the entry's ``on_select`` reads it. The entry's label binds to the same
observable, so the menu itself shows which document the command will hit.

Interactions:
    - Click into either editor, then File > Save (or Accel+S): the log names
      the focused pane's document.
    - Refocus the other pane and open File again: the Save label followed.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Document:
    """One pane's document: a name and its editable text."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.text = nv.Observable("")


class State:
    """App-level state: the shared Save entry reads ``active`` instead of
    hard-wiring a document; each pane writes it on focus."""

    def __init__(self) -> None:
        self.notes = Document("notes.txt")
        self.draft = Document("draft.txt")
        self.active = nv.Observable(self.notes)
        self.log = nv.Observable("Click into a pane, then File > Save (or Accel+S).")

    def save(self) -> None:
        document = self.active.value
        self.log.value = f"Saved {document.name} ({len(document.text.value)} characters)."


def _menu(state: State) -> nv.MenuBar:
    return nv.MenuBar(
        [
            nv.MenuEntry(
                "File",
                submenu=[
                    nv.MenuEntry(
                        state.active.map(lambda d: f"Save {d.name}"),
                        shortcut="Accel+S",
                        on_select=state.save,
                    ),
                    nv.MenuEntry.separator(),
                    nv.MenuEntry.quit(),
                ],
            ),
        ]
    )


class Pane(nv.ComposableWidget):
    def __init__(self, state: State, document: Document) -> None:
        super().__init__()
        self.state = state
        self.document = document

    def build(self) -> nv.Widget:
        return nv.TextField(
            value=self.document.text,
            label=self.document.name,
            on_focus_change=self._on_focus_change,
        )

    def _on_focus_change(self, focused: bool, source: nv.FocusSource) -> None:
        if focused:
            self.state.active.value = self.document


class Screen(nv.ComposableWidget):
    def __init__(self, state: State) -> None:
        super().__init__()
        self.state = state

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[
                nv.Row(
                    children=[
                        Pane(self.state, self.state.notes),
                        Pane(self.state, self.state.draft),
                    ],
                    gap=12,
                ),
                nv.Text(self.state.log, style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    state = State()
    app = nv.App(
        nv.Window(
            content=lambda: Screen(state),
            title="menu_bar_active_pane",
            width=560,
            height=240,
            menu=_menu(state),
        )
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
