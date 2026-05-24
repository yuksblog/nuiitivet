import nuiitivet.material as md


def main(png: str = ""):
    widget = md.Card(
        width="100%",
        child=md.Text("Full Width Box"),
        padding=16,
        alignment="center",
    )

    app = md.App(content=widget, title="Full Width Box", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
