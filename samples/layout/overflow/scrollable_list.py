import nuiitivet.material as nv


def main(png: str = ""):
    # Even with many items, keep a 300px viewport and scroll within it.
    widget = nv.Container(
        height=300,
        child=nv.VerticalScrollable(
            child=nv.Column(
                children=[nv.Text(f"Item {i}") for i in range(50)],
                gap=8,
                padding=16,
            ),
        ),
    )

    app = nv.App(content=widget, title="Scrollable List", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
