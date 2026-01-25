import nuiitivet as nv
import nuiitivet.material as md
import nuiitivet.modifiers as mod


class DeckDemo(nv.ComposableWidget):
    current_index: nv.Observable[int] = nv.Observable(0)

    def set_index(self, i: int) -> None:
        self.current_index.value = i

    def build(self) -> nv.Widget:

        menu = nv.Column(
            padding=8,
            gap=8,
            children=[
                md.FilledButton("Tab1", on_click=lambda: self.set_index(0)),
                md.FilledButton("Tab2", on_click=lambda: self.set_index(1)),
                md.FilledButton("Tab3", on_click=lambda: self.set_index(2)),
            ],
        )

        body = nv.Deck(
            index=self.current_index,
            width="100%",
            height="100%",
            children=[
                nv.Container(
                    alignment="center",
                    width="100%",
                    height="100%",
                    child=md.Text("Tab 1 Content"),
                ).modifier(mod.background("#BBDEFB")),
                nv.Container(
                    alignment="center",
                    width="100%",
                    height="100%",
                    child=md.Text("Tab 2 Content"),
                ).modifier(mod.background("#C8E6C9")),
                nv.Container(
                    alignment="center",
                    width="100%",
                    height="100%",
                    child=md.Text("Tab 3 Content"),
                ).modifier(mod.background("#FFE0B2")),
            ],
        )

        demo = nv.Row(
            gap=12,
            width="100%",
            children=[menu, body],
        )

        return demo


def main(png: str = ""):

    app = md.MaterialApp(
        content=DeckDemo(),
        title_bar=nv.DefaultTitleBar(title="nv.Deck Demo"),
        width=520,
        height=300,
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
