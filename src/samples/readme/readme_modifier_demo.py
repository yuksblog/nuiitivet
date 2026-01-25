from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md
import nuiitivet.modifiers as mod
from nuiitivet.material.styles.text_style import TextStyle

import argparse


def build_modifier_demo():
    text1 = md.Text("Hello", padding=12).modifier(mod.background("#FF5722"))
    text2 = md.Text(
        "Rounded Box",
        padding=12,
        style=TextStyle(color="white"),
    ).modifier(mod.background("#2196F3") | mod.corner_radius(8))

    return nv.Column(
        children=[
            text1,
            text2,
        ],
        gap=12,
        padding=20,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="README modifier demo sample")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = md.MaterialApp(content=build_modifier_demo(), title_bar=nv.DefaultTitleBar(title="Modifier Demo"))

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
