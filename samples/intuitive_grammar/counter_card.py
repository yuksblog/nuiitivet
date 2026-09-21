import nuiitivet.material as nv


class CounterCard(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def handle_add(self) -> None:
        self.count.value += 1
        if self.count.value % 10 == 0:
            print("Milestone reached!")

    def build(self) -> nv.Widget:
        return nv.Column(
            [
                nv.Text("Clicks", padding=12, width=200).modifier(nv.background("#BBDEFB") | nv.corner_radius(8)),
                nv.Row(
                    [
                        nv.Text(self.count.map(lambda n: f"{n} times"), width="wt"),
                        nv.Button("Add one", on_click=self.handle_add),
                    ],
                    gap=12,
                    width=200,
                    cross_alignment="center",
                ),
            ],
            gap=12,
            padding=20,
        )


def build_root() -> nv.Widget:
    return CounterCard()


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="The intuitive grammar", width=280, height=160))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
