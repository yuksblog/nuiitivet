"""Window Chrome - OS-managed decoration (default)."""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Container(
        alignment="center",
        width="wt",
        height="wt",
        child=nv.Text("Hello, World!"),
    )


def main(png_path: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=build_root,
            title="My Application",
            width=400,
            height=240,
        ),
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
