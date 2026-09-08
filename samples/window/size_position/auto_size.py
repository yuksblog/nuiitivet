"""Window sizing - "auto" sizes the window to fit its content."""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Container(
        child=nv.Text("Auto Sized Window"),
        padding=50,
    )


def main(png: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=build_root,
            width="auto",
            height="auto",
        ),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
