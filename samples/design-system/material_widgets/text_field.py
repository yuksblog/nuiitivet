"""Material Widgets - TextField filled/outlined/error."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.TextField(
                    value="",
                    label="Username",
                    leading_icon="person",
                    on_submit=lambda value: print(f"Submitted: {value}"),
                    width=320,
                ),
                nv.TextField(
                    value="",
                    label="Password",
                    leading_icon="lock",
                    obscure_text=True,
                    width=320,
                    style=nv.TextFieldStyle.outlined(),
                ),
                nv.TextField(
                    value="invalid@",
                    label="Email",
                    supporting_text="Invalid email address",
                    is_error=True,
                    width=320,
                    style=nv.TextFieldStyle.outlined(),
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="TextField",
        width=440,
        height=360,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
