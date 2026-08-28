from __future__ import annotations
import nuiitivet.material as nv


class CounterApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def increment(self) -> None:
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),
                nv.Button(
                    "Increment",
                    on_click=self.increment,
                ),
            ],
            gap=20,
            padding=20,
        )


def main(png: str = "") -> None:
    app_widget = CounterApp()
    if png:
        app_widget.count.value = 3
    app = nv.App(nv.Window(content=app_widget, title="Counter Demo", width=250))

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
