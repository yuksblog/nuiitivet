import nuiitivet as nv
import nuiitivet.material as md


def main(png: str = ""):
    widget = md.FilledCard(
        width=200,  # 幅を 200px に固定
        height=100,  # 高さを 100px に固定
        child=md.Text("Fixed Size Box"),
        padding=16,
        alignment="center",
    )

    # Wrap in center container for better visibility
    root = nv.Container(alignment="center", child=widget)

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="Fixed Size"), width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
