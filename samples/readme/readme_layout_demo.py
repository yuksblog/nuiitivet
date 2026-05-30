from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def build_layout_demo():
    return nv.Column(
        children=[
            md.Text("Title", padding=10),
            md.Text("Subtitle", padding=10),
            md.Text("Body", padding=10),
            nv.Row(
                children=[
                    md.Button("OK"),
                    md.Button("Cancel"),
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
    app = md.App(content=build_layout_demo(), title="Layout Demo")

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
