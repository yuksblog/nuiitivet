import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, will_pop, clickable, corner_radius
from nuiitivet.observable import Observable


class WillPopDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.can_pop = Observable(False)

    def _toggle_can_pop(self) -> None:
        self.can_pop.value = not self.can_pop.value

    def build(self):
        bg_color = self.can_pop.map(lambda c: "#4CAF50" if c else "#F44336")
        text = self.can_pop.map(lambda c: "Can Pop: True" if c else "Can Pop: False")

        return nv.Container(
            width=200,
            height=50,
            child=md.Text(text),
            alignment="center",
        ).modifier(
            background(bg_color)
            | corner_radius(8)
            | clickable(on_click=self._toggle_can_pop)
            | will_pop(on_will_pop=lambda: self.can_pop.value)
        )


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.Text("Click the button to toggle pop permission."),
            md.Text("Then try to close the window or press Esc."),
            WillPopDemo(),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Will Pop Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
