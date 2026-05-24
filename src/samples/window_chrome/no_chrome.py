"""Window Chrome - Borderless window (chrome=None)."""

from nuiitivet.runtime.app import App
from nuiitivet.material import Text
from nuiitivet.layout.container import Container

SKIP_WINDOW_FRAME = True


def main(png_path: str = "") -> None:
    app = App(
        content=Container(
            alignment="center",
            width="100%",
            height="100%",
            child=Text("Borderless Window"),
        ),
        title="Borderless",
        chrome=None,
        width=400,
        height=240,
        background="#e3f2fd",
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
