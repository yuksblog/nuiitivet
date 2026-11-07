"""Dynamic list generation: lazy() for a long list.

``Column.lazy`` holds a widget for the rows the scrollable shows and none for
the other rows; the ten thousand items below cost what a dozen do.
"""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    rows = [f"Row {i}" for i in range(10_000)]

    widget = nv.Container(
        height=300,
        child=nv.VerticalScrollable(
            child=nv.Column.lazy(
                rows,
                lambda row, index: nv.Text(row, padding=(16, 8)),  # built when the row scrolls into view
                gap=4,
            ),
        ),
    )
    return widget


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Dynamic List: lazy()", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
