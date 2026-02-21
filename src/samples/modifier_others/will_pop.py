from dataclasses import dataclass

import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.text_fields import OutlinedTextField
from nuiitivet.modifiers import will_pop
from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.observable import Observable


@dataclass(frozen=True, slots=True)
class HomeIntent:
    pass


class HomeScreen(nv.ComposableWidget):
    def build(self):
        def _open_editor() -> None:
            Navigator.root().push(PageRoute(builder=lambda: EditScreen()))

        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    md.Text("Open editor, edit text, then try Esc or Back."),
                    FilledButton("Open editor", on_click=_open_editor),
                ],
                gap=14,
                cross_alignment="start",
            ),
        )


class EditScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.text = Observable("Hello")
        self._initial_text = str(self.text.value)

    def _is_dirty(self) -> bool:
        return str(self.text.value) != self._initial_text

    def _save(self) -> None:
        self._initial_text = str(self.text.value)

    def _try_pop(self) -> None:
        Navigator.root().pop()

    def _on_will_pop(self) -> bool:
        if not self._is_dirty():
            return True

        def _cancel() -> None:
            MaterialOverlay.root().close(None)

        def _discard() -> None:
            self._initial_text = str(self.text.value)
            MaterialOverlay.root().close(None)
            Navigator.root().pop()

        MaterialOverlay.root().dialog(
            AlertDialog(
                title="Discard changes?",
                message="You have unsaved changes.",
                actions=[
                    TextButton("Cancel", on_click=_cancel),
                    FilledButton("Discard", on_click=_discard),
                ],
            ),
            dismiss_on_outside_tap=False,
        )
        return False

    def build(self):
        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    md.Text("Edit text. Back/Esc asks confirmation when unsaved."),
                    OutlinedTextField.two_way(
                        self.text,
                        width=420,
                        height=52,
                        padding=10,
                    ),
                    nv.Row(
                        children=[
                            TextButton("Back", on_click=self._try_pop),
                            FilledButton("Save", on_click=self._save),
                        ],
                        gap=10,
                    ),
                ],
                gap=14,
                cross_alignment="start",
            ),
        ).modifier(will_pop(on_will_pop=self._on_will_pop))


def main(png: str = ""):
    app = md.MaterialApp.navigation(
        routes={
            HomeIntent: lambda _i: PageRoute(builder=HomeScreen),
        },
        initial_route=HomeIntent(),
        width=400,
        height=200,
        title_bar=nv.DefaultTitleBar(title="Will Pop Modifier"),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
