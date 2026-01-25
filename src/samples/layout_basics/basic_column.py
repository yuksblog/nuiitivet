import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    content = nv.Column(
        children=[
            md.FilledTextField(label="Email"),
            md.FilledTextField(label="Password"),
            md.FilledButton("Login"),
        ],
        gap=16,
        padding=16,
    )

    app = md.MaterialApp(content=content, title_bar=nv.DefaultTitleBar(title="Basic nv.Column"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
