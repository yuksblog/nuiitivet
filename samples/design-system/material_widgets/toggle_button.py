"""Material Widgets - ToggleButton variants."""

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
                        nv.ToggleButton("Filled", icon="check", selected=True, style=nv.ToggleButtonStyle.filled()),
                        nv.ToggleButton("Filled", icon="check", selected=False, style=nv.ToggleButtonStyle.filled()),
                    ],
                ),
                nv.Row(
                    gap=12,
                    children=[
                        nv.ToggleButton(
                            "Outlined", icon="check", selected=True, style=nv.ToggleButtonStyle.outlined()
                        ),
                        nv.ToggleButton(
                            "Outlined", icon="check", selected=False, style=nv.ToggleButtonStyle.outlined()
                        ),
                    ],
                ),
                nv.Row(
                    gap=12,
                    children=[
                        nv.ToggleButton(
                            "Disabled", icon="check", selected=True, disabled=True, style=nv.ToggleButtonStyle.filled()
                        ),
                        nv.ToggleButton(
                            "Disabled",
                            icon="check",
                            selected=False,
                            disabled=True,
                            style=nv.ToggleButtonStyle.outlined(),
                        ),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="ToggleButton", width=560, height=260))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
