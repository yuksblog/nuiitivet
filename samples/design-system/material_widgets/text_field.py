"""Material Widgets - TextField filled/outlined/error/multi-line."""

from __future__ import annotations

import nuiitivet.material as nv


def build_root() -> nv.Widget:
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
                nv.TextField.multiline(
                    value="Ships in two parts.\nThe second follows a week later.",
                    label="Notes",
                    max_lines=4,
                    width=320,
                ),
            ],
        ),
    )
    return content


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="TextField", width=440, height=460))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
