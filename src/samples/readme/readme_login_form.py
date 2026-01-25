from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md

import argparse


def build_login_form():
    return nv.Column(
        [
            md.OutlinedTextField(
                value="",
                label="Username",
                width=300,
            ),
            md.OutlinedTextField(
                value="",
                label="Password",
                width=300,
            ),
            md.FilledButton(
                "Login",
                on_click=lambda: print("Login clicked"),
                width=300,
            ),
        ],
        gap=20,
        padding=20,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="README login form sample")
    parser.add_argument("--png", type=str, default="", help="Render to PNG instead of opening a window")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = md.MaterialApp(content=build_login_form(), title_bar=nv.DefaultTitleBar(title="Login Form"))

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
