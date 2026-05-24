"""Window Chrome - OS-managed decoration (default)."""

from nuiitivet.runtime.app import App
from nuiitivet.material import Text
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    app = App(
        content=Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Text("Hello, World!"),
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
