"""Window position - centered on screen with the alignment-string shorthand."""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Positioned Window")


def main(png: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=build_root,
            width=400,
            height=300,
            window_position="center",
        ),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
