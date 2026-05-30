"""Material Widgets - Badge attached to icons."""

from __future__ import annotations

from nuiitivet.material import App, Icon, LargeBadge, SmallBadge, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def _cell(label: str, icon) -> Column:
    return Column(gap=8, cross_alignment="center", children=[icon, Text(label)])


def main(png_path: str = "") -> None:
    base = "notifications"
    content = Container(
        padding=24,
        child=Row(
            gap=32,
            cross_alignment="start",
            children=[
                _cell("None", Icon(base, size=32)),
                _cell("Small", Icon(base, size=32).modifier(SmallBadge().stick_modifier())),
                _cell("Large", Icon(base, size=32).modifier(LargeBadge("12").stick_modifier())),
                _cell("Overflow", Icon(base, size=32).modifier(LargeBadge("999+").stick_modifier())),
            ],
        ),
    )
    app = App(
        content=content,
        title="Badge",
        width=520,
        height=200,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
