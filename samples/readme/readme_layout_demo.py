from __future__ import annotations
import nuiitivet.material as nv


def build_layout_demo():
    return nv.Column(
        children=[
            nv.Text("Title", padding=10),
            nv.Text("Subtitle", padding=10),
            nv.Text("Body", padding=10),
            nv.Row(
                children=[
                    nv.Button("OK"),
                    nv.Button("Cancel"),
                ],
                gap=12,
                main_alignment="end",
                cross_alignment="center",
            ),
        ],
        gap=16,
        padding=20,
        cross_alignment="start",
    )


def main(png: str = "") -> None:
    app = nv.App(content=build_layout_demo(), title="Layout Demo")

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
