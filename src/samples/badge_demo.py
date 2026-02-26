"""Badge demo showing Small/Large badge attachment to icons."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Icon, LargeBadge, SmallBadge, Text
from nuiitivet.material.app import MaterialApp


def _badge_item(title: str, icon) -> Column:
    return Column(
        children=[Text(title), icon],
        gap=8,
        cross_alignment="center",
    )


def main() -> None:
    icon_base = "notifications"

    plain = Icon(icon_base, size=32)
    small = Icon(icon_base, size=32).modifier(SmallBadge().stick_modifier())
    large = Icon(icon_base, size=32).modifier(LargeBadge(12).stick_modifier())
    overflow = Icon(icon_base, size=32).modifier(LargeBadge(1200, max=999).stick_modifier())

    content = Column(
        children=[
            Text("Badge Demo"),
            Row(
                children=[
                    _badge_item("No badge", plain),
                    _badge_item("Small badge", small),
                    _badge_item("Large badge (12)", large),
                    _badge_item("Large badge (999+)", overflow),
                ],
                gap=24,
                cross_alignment="start",
            ),
        ],
        gap=16,
        padding=24,
        cross_alignment="start",
    )

    app = MaterialApp(content=content)
    app.run()


if __name__ == "__main__":
    main()
