import nuiitivet.material as nv


def main(png: str = ""):
    content = nv.Column(
        children=[
            nv.TextField(label="Email"),
            nv.TextField(label="Password"),
            nv.Button("Login", style=nv.ButtonStyle.filled()),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="Basic nv.Column", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
