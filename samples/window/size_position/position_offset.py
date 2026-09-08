"""Window position - alignment with an offset and a screen index."""

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Positioned Window")


def main(png: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=build_root,
            width=400,
            height=300,
            window_position=nv.WindowPosition.alignment(
                alignment="top-right",
                offset=(-20, 20),  # 20 pixels left, 20 pixels down from top-right corner
                screen_index=0,    # Primary monitor
            ),
        ),
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
