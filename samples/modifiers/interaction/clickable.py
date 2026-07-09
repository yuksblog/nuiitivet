import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.Container(
                width=200,
                height=50,
                child=nv.Text("Click Me!"),
                alignment="center",
            ).modifier(
                nv.background("#4CAF50") | nv.corner_radius(8) | nv.clickable(on_click=lambda: print("Clicked!"))
            ),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(content=content, title="Clickable Modifier", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
