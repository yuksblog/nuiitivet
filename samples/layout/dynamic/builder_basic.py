"""Dynamic list generation: builder() (recommended).

Demonstrates the ``builder()`` class method available on
Row / Column / Stack / Flow / UniformFlow. It materializes children from a
data collection via a ``(item, index) -> Widget`` builder function.
"""

import nuiitivet.material as nv


def main(png: str = ""):
    tags = ["Python", "UI", "Framework", "Layout"]

    widget = nv.Flow.builder(
        tags,
        lambda tag, index: nv.Card(nv.Text(tag, padding=8), style=nv.CardStyle.outlined()),
        main_gap=8,
        cross_gap=8,
        padding=8,
        width=300,
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="Dynamic List: builder()"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
