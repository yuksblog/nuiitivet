import nuiitivet.material as nv


class DeckDemo(nv.ComposableWidget):
    current_index: nv.Observable[int] = nv.Observable(0)

    def build(self) -> nv.Widget:

        menu = nv.Column(
            padding=8,
            gap=8,
            children=[
                nv.Button(
                    "Tab1",
                    # ``set`` writes the Observable from inside a lambda, where
                    # ``current_index.value = 0`` would not be allowed.
                    on_click=lambda: self.current_index.set(0),
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Button(
                    "Tab2",
                    on_click=lambda: self.current_index.set(1),
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Button(
                    "Tab3",
                    on_click=lambda: self.current_index.set(2),
                    style=nv.ButtonStyle.filled(),
                ),
            ],
        )

        body = nv.Deck(
            index=self.current_index,
            width="wt",
            height="wt",
            children=[
                nv.Container(
                    alignment="center",
                    width="wt",
                    height="wt",
                    child=nv.Text("Tab 1 Content"),
                ).modifier(nv.background("#BBDEFB")),
                nv.Container(
                    alignment="center",
                    width="wt",
                    height="wt",
                    child=nv.Text("Tab 2 Content"),
                ).modifier(nv.background("#C8E6C9")),
                nv.Container(
                    alignment="center",
                    width="wt",
                    height="wt",
                    child=nv.Text("Tab 3 Content"),
                ).modifier(nv.background("#FFE0B2")),
            ],
        )

        demo = nv.Row(
            gap=12,
            width="wt",
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
