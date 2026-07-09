"""Window Chrome - OS-managed decoration (default)."""

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    app = nv.App(
        content=nv.Container(
            alignment="center",
            width="100%",
            height="100%",
            child=nv.Text("Hello, World!"),
        ),
        title="My Application",
        width=400,
        height=240,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
