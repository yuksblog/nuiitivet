"""Dynamic list generation: ForEach (SwiftUI-like style).

Demonstrates the embedded ``children=[ForEach(...)]`` form. It behaves
identically to ``builder()`` at runtime but reads in a SwiftUI-like style.
"""

import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.layout.for_each import ForEach


def main(png: str = ""):
    tags = ["Python", "UI", "Framework", "Layout"]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=8,
        width=300,
        children=[
            ForEach(
                tags,
                lambda tag, index: md.Card(md.Text(tag, padding=8), style=md.CardStyle.outlined()),
            ),
        ],
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.App(content=root, title="Dynamic List: ForEach")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
