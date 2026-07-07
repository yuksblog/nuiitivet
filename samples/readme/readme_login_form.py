from __future__ import annotations
import nuiitivet.material as nv


def build_login_form():
    return nv.Column(
        [
            nv.TextField(
                value="",
                label="Username",
                width=300,
            ),
            nv.TextField(
                value="",
                label="Password",
                width=300,
            ),
            nv.Button(
                "Login",
                on_click=lambda: print("Login clicked"),
                width=300,
            ),
        ],
        gap=20,
        padding=20,
    )


def main(png: str = "") -> None:
    app = nv.App(content=build_login_form(), title="Login Form")

    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return

    app.run()


if __name__ == "__main__":
    main()
