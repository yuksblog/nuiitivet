"""Material Theme - Form Factor.

Demonstrates how ``form_factor`` sets the component sizes. ``"mobile"`` is the
MD3 baseline; the default is ``"desktop"``.
"""

from __future__ import annotations

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Container(
        alignment="center",
        width="wt",
        height="wt",
        child=nv.Row(
            gap=12,
            cross_alignment="center",
            children=[
                nv.TextField("Ada", label="Name", style=nv.TextFieldStyle.outlined()),
                nv.Checkbox(checked=True),
                nv.Button("Save", style=nv.ButtonStyle.filled()),
            ],
        ),
    )


def main(png_path: str = "") -> None:
    app = nv.App(
        nv.Window(content=build_root, title="Form Factor", width=440, height=140),
        # use this: "desktop" (default), "mobile" or a FormFactor
        theme=nv.ThemeFactory.light("#6750A4", form_factor="mobile"),
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
