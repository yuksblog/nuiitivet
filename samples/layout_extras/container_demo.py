import nuiitivet.material as nv


def main(png: str = ""):
    widget = nv.Container(
        nv.Button("Centered Content", style=nv.ButtonStyle.filled()),
        width=250,
        height=200,
        alignment="center",
        padding=16,
    )

    app = nv.App(content=widget, title="nv.Container Demo")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
