import nuiitivet as nv
import nuiitivet.material as md


class CollapsibleDemo(nv.ComposableWidget):
    opened: nv.Observable[bool] = nv.Observable(True)

    def toggle(self) -> None:
        self.opened.value = not self.opened.value

    def build(self) -> nv.Widget:
        details = nv.Collapsible(
            md.Card(
                nv.Column(
                    padding=16,
                    gap=8,
                    children=[
                        md.Text("Format: PDF / EPUB / HTML"),
                        md.Text("Size: 4.2 MB"),
                        md.Text("License: MIT"),
                    ],
                ),
            ),
            opened=self.opened,
        )

        return nv.Column(
            padding=16,
            gap=12,
            width="100%",
            children=[
                md.Button("Show Details", on_click=self.toggle),
                details,
            ],
        )


def main(png: str = "") -> None:
    app = md.App(
        content=CollapsibleDemo(),
        title="nv.Collapsible Demo",
        width=320,
        height=220,
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
