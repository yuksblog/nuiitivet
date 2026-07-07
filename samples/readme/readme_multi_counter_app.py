from __future__ import annotations
import nuiitivet.material as nv


class MultiCounterApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count_a = nv.Observable(0)
        self.count_b = nv.Observable(0)
        self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)

    def increment_a(self) -> None:
        self.count_a.value += 1

    def increment_b(self) -> None:
        self.count_b.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Row(
                    [
                        nv.Text(self.count_a),
                        nv.Button("+", on_click=self.increment_a),
                    ],
                    gap=12,
                ),
                nv.Row(
                    [
                        nv.Text(self.count_b),
                        nv.Button("+", on_click=self.increment_b),
                    ],
                    gap=12,
                ),
                nv.Text(self.total),
            ],
            gap=16,
            padding=20,
        )


def main(png: str = "") -> None:
    app_widget = MultiCounterApp()
    if png:
        app_widget.count_a.value = 3
        app_widget.count_b.value = 5
    app = nv.App(
        content=app_widget,
        title="Multi Counter Demo",
        width=250,
    )

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
