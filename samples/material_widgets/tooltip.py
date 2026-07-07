"""Material Widgets - Tooltip and RichTooltip rendered inline."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=20,
            cross_alignment="start",
            children=[
                nv.Text("Tooltip (plain)"),
                nv.Tooltip("Save the current document"),
                nv.Text("RichTooltip"),
                nv.RichTooltip(
                    supporting_text="Saves your work and uploads it to the cloud.",
                    subhead="Save changes",
                    action_label="Learn more",
                    action_label_2="Dismiss",
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="Tooltip",
        width=440,
        height=320,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
