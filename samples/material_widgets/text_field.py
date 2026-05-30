"""Material Widgets - TextField filled/outlined/error."""

from __future__ import annotations

from nuiitivet.material import App, TextField, TextFieldStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                TextField(
                    value="",
                    label="Username",
                    leading_icon="person",
                    width=320,
                ),
                TextField(
                    value="",
                    label="Password",
                    leading_icon="lock",
                    obscure_text=True,
                    width=320,
                    style=TextFieldStyle.outlined(),
                ),
                TextField(
                    value="invalid@",
                    label="Email",
                    supporting_text="Invalid email address",
                    is_error=True,
                    width=320,
                    style=TextFieldStyle.outlined(),
                ),
            ],
        ),
    )
    app = App(
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
