from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md

import argparse


def build_layout_demo():
    return nv.Column(
        children=[
            md.Text("Title", padding=10),
            md.Text("Subtitle", padding=10),
            md.Text("Body", padding=10),
            nv.Row(
                children=[
                    md.FilledButton("OK"),
                    md.TextButton("Cancel"),
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="README layout demo sample")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = md.MaterialApp(content=build_layout_demo(), title_bar=nv.DefaultTitleBar(title="Layout Demo"))

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
