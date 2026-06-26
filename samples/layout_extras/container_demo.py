import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    widget = nv.Container(
        md.Button("Centered Content", style=md.ButtonStyle.filled()),
        width=250,
        height=200,
        alignment="center",
        padding=16,
    )

    app = md.App(content=widget, title="nv.Container Demo")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
