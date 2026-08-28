"""Window Chrome - Borderless window (chrome=None)."""

import nuiitivet.material as nv

SKIP_WINDOW_FRAME = True


def main(png_path: str = "") -> None:
    app = nv.App(
        nv.Window(
            content=nv.Container(
                alignment="center",
                width="wt",
                height="wt",
                child=nv.Text("Borderless Window"),
            ),
            title="Borderless",
            chrome=None,
            width=400,
            height=240,
            background="#e3f2fd",
        ),
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
