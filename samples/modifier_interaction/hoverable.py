import nuiitivet.material as nv


class HoverDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.is_hovered = nv.Observable(False)

    def _set_hovered(self, hovered: bool) -> None:
        self.is_hovered.value = hovered

    def build(self):
        bg_color = self.is_hovered.map(lambda h: "#2196F3" if h else "#E0E0E0")

        return nv.Container(
            width=200,
            height=50,
            child=nv.Text("Hover Me!"),
            alignment="center",
        ).modifier(nv.background(bg_color) | nv.corner_radius(8) | nv.hoverable(on_hover_change=self._set_hovered))


def main(png: str = ""):
    content = nv.Column(
        children=[HoverDemo()],
        gap=16,
        padding=16,
    )

    app = nv.App(content=content, title="Hoverable Modifier")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
