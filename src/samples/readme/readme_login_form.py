from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def build_login_form():
    return nv.Column(
        [
            md.TextField(
                value="",
                label="Username",
                width=300,
            ),
            md.TextField(
                value="",
                label="Password",
                width=300,
            ),
            md.Button(
                "Login",
                on_click=lambda: print("Login clicked"),
                width=300,
            ),
        ],
        gap=20,
        padding=20,
    )


def main(png: str = "") -> None:
    app = md.App(content=build_login_form(), title_bar=nv.DefaultTitleBar(title="Login Form"))

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
