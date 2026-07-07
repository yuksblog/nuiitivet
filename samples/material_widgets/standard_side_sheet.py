"""Material Widgets - StandardSideSheet with Collapsible open/close."""

from __future__ import annotations

import nuiitivet.material as nv


class StandardSideSheetDemo(nv.ComposableWidget):
    """Demo: main content area beside an openable StandardSideSheet."""

    opened: nv.Observable[bool] = nv.Observable(True)

    def toggle(self) -> None:
        self.opened.value = not self.opened.value

    def build(self) -> nv.Widget:
        sheet = nv.Collapsible(
            nv.StandardSideSheet(
                nv.Column(
                    padding=16,
                    gap=12,
                    width="100%",
                    children=[
                        nv.Text("Option A"),
                        nv.Text("Option B"),
                        nv.Text("Option C"),
                    ],
                ),
                headline="Filters",
                on_close=self.toggle,
            ),
            opened=self.opened,
            axis="horizontal",
            alignment="top_right",
        )

        body = nv.Box(
            nv.Column(
                padding=20,
                gap=12,
                children=[
                    nv.Text("StandardSideSheet demo"),
                    nv.Text("The sheet slides in from the right."),
                    nv.Button("Toggle sheet", on_click=self.toggle),
                ],
            ),
            background_color=nv.ColorRole.SURFACE,
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )

        return nv.Row(
            [body, sheet],
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )


def main(png_path: str = "") -> None:
    app = nv.App(
        content=StandardSideSheetDemo(),
        title="StandardSideSheet",
        width=600,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
