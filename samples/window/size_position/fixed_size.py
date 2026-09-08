"""Window sizing - fixed pixel width and height."""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Fixed Size Window")


def main(png: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=build_root,
            width=800,
            height=600,
        ),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
