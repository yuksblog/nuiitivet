import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.layout.scroller import Scroller


def main(png: str = ""):
    # Even with many items, keep a 300px viewport and scroll within it.
    widget = nv.Container(
        height=300,
        child=Scroller(
            child=nv.Column(
                children=[md.Text(f"Item {i}") for i in range(50)],
                gap=8,
                padding=16,
            ),
            direction="vertical",
            scrollbar_enabled=True,
        ),
    )

    app = md.App(content=widget, title="Scrollable List", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
