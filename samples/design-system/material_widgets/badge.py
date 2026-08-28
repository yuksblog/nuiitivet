"""Material Widgets - Badge attached to icons."""

from __future__ import annotations

import nuiitivet.material as nv


def _cell(label: str, icon) -> nv.Column:
    return nv.Column(gap=8, cross_alignment="center", children=[icon, nv.Text(label)])


def main(png_path: str = "") -> None:
    base = "notifications"
    content = nv.Container(
        padding=24,
        child=nv.Row(
            gap=32,
            cross_alignment="start",
            children=[
                _cell("None", nv.Icon(base, size=32)),
                _cell("Small", nv.Icon(base, size=32).modifier(nv.SmallBadge().stick_modifier())),
                _cell("Large", nv.Icon(base, size=32).modifier(nv.LargeBadge("12").stick_modifier())),
                _cell("Overflow", nv.Icon(base, size=32).modifier(nv.LargeBadge("999+").stick_modifier())),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="Badge", width=520, height=200))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
