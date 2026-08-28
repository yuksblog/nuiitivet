"""Dynamic list generation: ForEach (SwiftUI-like style).

Demonstrates the embedded ``children=[ForEach(...)]`` form. It behaves
identically to ``builder()`` at runtime but reads in a SwiftUI-like style.
"""

import nuiitivet.material as nv


def main(png: str = ""):
    tags = ["Python", "UI", "Framework", "Layout"]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=8,
        width=300,
        children=[
            nv.ForEach(
                tags,
                lambda tag, index: nv.Card(nv.Text(tag, padding=8), style=nv.CardStyle.outlined()),
            ),
        ],
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="Dynamic List: ForEach"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
