"""Dynamic list generation: static list comprehension.

Demonstrates the simplest form — turning a fixed collection into widgets
inline with a list comprehension. Use this when the data does not change
after the layout is built.
"""

import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    tags = ["Python", "UI", "Framework", "Layout"]

    widget = nv.Flow(
        main_gap=8,
        cross_gap=8,
        padding=8,
        children=[md.Card(md.Text(tag, padding=8), style=md.CardStyle.outlined()) for tag in tags],
        width=300,
    )

    root = nv.Container(alignment="center", child=widget)

    app = md.App(content=root, title="Dynamic List: Static Comprehension")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
