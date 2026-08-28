"""Window Chrome - Custom (app-drawn) decoration."""

import nuiitivet.material as nv

SKIP_WINDOW_FRAME = True


def main(png_path: str = "") -> None:
    header = nv.Row(
        children=[
            nv.Text("My App", style=nv.TextStyle(color="#ffffff"), type_scale=nv.TypeScaleToken.from_size(14)),
        ],
        cross_alignment="center",
        width="wt",
        height=40,
        padding=(12, 0),
    ).modifier(nv.background("#1a237e"))

    app = nv.App(
        nv.Window(
            content=nv.Container(
                alignment="center",
                width="wt",
                height="wt",
                child=nv.Text("Custom Chrome"),
            ),
            title="My App",
            chrome=nv.CustomChrome(
                header=header,
                corner_radius=8,
            ),
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
