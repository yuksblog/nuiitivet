import nuiitivet as nv
import nuiitivet.material as md
import nuiitivet.modifiers as mod


def main(png: str = ""):
    # Even with many items, keep a 300px viewport and scroll within it.
    widget = nv.Container(
        height=300,
        child=nv.Column(
            children=[md.Text(f"Item {i}") for i in range(50)],
            gap=8,
            padding=16,
        ).modifier(mod.scrollable(axis="y", show_scrollbar=True)),
    )

    app = md.MaterialApp(content=widget, title_bar=nv.DefaultTitleBar(title="Scrollable List"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
