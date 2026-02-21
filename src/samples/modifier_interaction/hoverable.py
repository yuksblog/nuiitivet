import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, hoverable, corner_radius
from nuiitivet.observable import Observable


class HoverDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.is_hovered = Observable(False)

    def _set_hovered(self, hovered: bool) -> None:
        self.is_hovered.value = hovered

    def build(self):
        bg_color = self.is_hovered.map(lambda h: "#2196F3" if h else "#E0E0E0")

        return nv.Container(
            width=200,
            height=50,
            child=md.Text("Hover Me!"),
            alignment="center",
        ).modifier(background(bg_color) | corner_radius(8) | hoverable(on_hover_change=self._set_hovered))


def main(png: str = ""):
    content = nv.Column(
        children=[HoverDemo()],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Hoverable Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
