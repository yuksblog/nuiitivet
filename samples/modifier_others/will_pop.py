import nuiitivet.material as nv


class HomeScreen(nv.ComposableWidget):
    def build(self):
        def _open_editor() -> None:
            nv.Navigator.root().push(EditScreen())

        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    nv.Text("Open editor, edit text, then try Esc or Back."),
                    nv.Button("Open editor", on_click=_open_editor, style=nv.ButtonStyle.filled()),
                ],
                gap=14,
                cross_alignment="start",
            ),
        )


class EditScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.text = nv.Observable("Hello")
        self._initial_text = str(self.text.value)

    def _is_dirty(self) -> bool:
        return str(self.text.value) != self._initial_text

    def _save(self) -> None:
        self._initial_text = str(self.text.value)

    async def _on_will_pop(self) -> bool:
        if not self._is_dirty():
            return True

        result = await nv.Overlay.root().dialog(
            nv.BasicDialog(
                title="Discard changes?",
                message="You have unsaved changes.",
                actions=[
                    nv.Button("Cancel", on_click=lambda: nv.Overlay.root().close(False), style=nv.ButtonStyle.text()),
                    nv.Button("Discard", on_click=lambda: nv.Overlay.root().close(True), style=nv.ButtonStyle.filled()),
                ],
            ),
            dismiss_on_outside_tap=False,
        )
        return bool(result.value)

    def build(self):
        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    nv.Text("Edit text. Back/Esc asks confirmation when unsaved."),
                    nv.TextField.two_way(
                        self.text,
                        width=420,
                        height=52,
                        padding=10,
                    ),
                    nv.Row(
                        children=[
                            nv.Button("Back", on_click=lambda: nv.Navigator.root().pop(), style=nv.ButtonStyle.text()),
                            nv.Button("Save", on_click=self._save, style=nv.ButtonStyle.filled()),
                        ],
                        gap=10,
                    ),
                ],
                gap=14,
                cross_alignment="start",
            ),
        ).modifier(nv.will_pop(on_will_pop=self._on_will_pop))


def main(png: str = ""):
    app = nv.App(
        HomeScreen(),
        width=400,
        height=200,
        title="Will Pop Modifier",
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
