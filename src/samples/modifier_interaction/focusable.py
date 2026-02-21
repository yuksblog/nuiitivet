import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, focusable, border, corner_radius
from nuiitivet.observable import Observable


class FocusDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.is_focused = Observable(False)

    def _set_focused(self, focused: bool) -> None:
        self.is_focused.value = focused

    def build(self):
        border_color = self.is_focused.map(lambda f: "#2196F3" if f else "#00000000")

        return nv.Container(
            width=200,
            height=50,
            child=md.Text("Focus with Tab"),
            alignment="center",
        ).modifier(
            background("#E0E0E0")
            | corner_radius(8)
            | border(color=border_color, width=2)
            | focusable(on_focus_change=self._set_focused)
        )


def main(png: str = ""):
    content = nv.Column(
        children=[FocusDemo(), FocusDemo()],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Focusable Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
