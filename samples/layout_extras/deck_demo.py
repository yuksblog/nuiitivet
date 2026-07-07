import nuiitivet.material as nv


class DeckDemo(nv.ComposableWidget):
    current_index: nv.Observable[int] = nv.Observable(0)

    def set_index(self, i: int) -> None:
        self.current_index.value = i

    def build(self) -> nv.Widget:

        menu = nv.Column(
            padding=8,
            gap=8,
            children=[
                nv.Button(
                    "Tab1",
                    on_click=lambda: self.set_index(0),
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Button(
                    "Tab2",
                    on_click=lambda: self.set_index(1),
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Button(
                    "Tab3",
                    on_click=lambda: self.set_index(2),
                    style=nv.ButtonStyle.filled(),
                ),
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
                    child=nv.Text("Tab 1 Content"),
                ).modifier(nv.background("#BBDEFB")),
                nv.Container(
                    alignment="center",
                    width="100%",
                    height="100%",
                    child=nv.Text("Tab 2 Content"),
                ).modifier(nv.background("#C8E6C9")),
                nv.Container(
                    alignment="center",
                    width="100%",
                    height="100%",
                    child=nv.Text("Tab 3 Content"),
                ).modifier(nv.background("#FFE0B2")),
            ],
        )

        demo = nv.Row(
            gap=12,
            width="100%",
            children=[menu, body],
        )

        return demo


def main(png: str = ""):

    app = nv.App(
        content=DeckDemo(),
        title="nv.Deck Demo",
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
