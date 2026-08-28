"""Dynamic list generation: static list comprehension.

Demonstrates the simplest form — turning a fixed collection into widgets
inline with a list comprehension. Use this when the data does not change
after the layout is built.
"""

import nuiitivet.material as nv


def main(png: str = ""):
    tags = ["Python", "UI", "Framework", "Layout"]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=8,
        children=[nv.Card(nv.Text(tag, padding=8), style=nv.CardStyle.outlined()) for tag in tags],
        width=300,
    )

    root = nv.Container(alignment="center", child=widget)

    app = nv.App(nv.Window(content=root, title="Dynamic List: Static Comprehension"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
