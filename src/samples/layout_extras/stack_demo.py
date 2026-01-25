import nuiitivet as nv
import nuiitivet.material as md
import nuiitivet.modifiers as mod
from nuiitivet.material.styles.card_style import CardStyle


def main(png: str = ""):
    widget = nv.Stack(
        width=200,
        height=200,
        alignment="center",  # デフォルトの配置位置
        children=[
            # 1. 背景（奥）
            md.FilledCard(
                md.Text(""),
                width="100%",
                height="100%",
            ).modifier(mod.background("#BBDEFB")),
            md.FilledCard(
                md.Text(""),
                width="80%",
                height="80%",
            ).modifier(mod.background("#90CAF9")),
            md.FilledCard(
                md.Text("Overlay md.Text"),
                width="60%",
                height="60%",
                alignment="center",
            ).modifier(mod.background("#64B5F6")),
        ],
    )

    root = md.FilledCard(
        widget,
        alignment="center",
        style=CardStyle(background=None, border_radius=0),
    )

    app = md.MaterialApp(content=root, title_bar=nv.DefaultTitleBar(title="nv.Stack Demo"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
