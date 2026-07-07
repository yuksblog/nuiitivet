"""Material Widgets - Button style variants."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=12,
            cross_alignment="start",
            children=[
                nv.Row(
                    gap=12,
                    children=[
                        nv.Button("Filled", style=nv.ButtonStyle.filled()),
                        nv.Button("Tonal", style=nv.ButtonStyle.tonal()),
                        nv.Button("Elevated", style=nv.ButtonStyle.elevated()),
                    ],
                ),
                nv.Row(
                    gap=12,
                    children=[
                        nv.Button("Outlined", style=nv.ButtonStyle.outlined()),
                        nv.Button("Text", style=nv.ButtonStyle.text()),
                    ],
                ),
                nv.Row(
                    gap=12,
                    children=[
                        nv.Button("With icon", icon="add", style=nv.ButtonStyle.filled()),
                        nv.Button("Disabled", style=nv.ButtonStyle.filled(), disabled=True),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="Button",
        width=560,
        height=260,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
