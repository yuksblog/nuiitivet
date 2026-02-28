"""Divider demo showing horizontal and vertical usage."""

from __future__ import annotations

from typing import List

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.spacer import Spacer
from nuiitivet.material import Divider, Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.styles.divider_style import DividerStyle
from nuiitivet.widgeting.widget import Widget


def _section_title(label: str) -> Text:
    return Text(label)


def _list_section() -> Column:
    """Horizontal Dividers inside a Column (list-style)."""
    items = ["Inbox", "Sent", "Drafts", "Trash"]
    children: List[Widget] = []
    for i, item in enumerate(items):
        children.append(
            Row(
                children=[Text(item)],
                padding=(12, 16, 12, 16),
            )
        )
        if i < len(items) - 1:
            children.append(Divider())

    return Column(
        children=children,
        cross_alignment="start",
    )


def _inset_section() -> Column:
    """Horizontal Dividers with inset_left (simulating list with leading icon space)."""
    items = ["Profile", "Settings", "Help", "Sign out"]
    children: List[Widget] = []
    for i, item in enumerate(items):
        children.append(
            Row(
                children=[
                    Spacer(width=40),
                    Text(item),
                ],
                padding=(12, 16, 12, 16),
            )
        )
        if i < len(items) - 1:
            children.append(Divider(style=DividerStyle(inset_left=56)))

    return Column(
        children=children,
        cross_alignment="start",
    )


def _row_section() -> Row:
    """Vertical Dividers inside a Row."""
    labels = ["Home", "Explore", "Favorites", "Account"]
    children: List[Widget] = []
    for i, label in enumerate(labels):
        children.append(
            Column(
                children=[Text(label)],
                padding=(8, 16, 8, 16),
                cross_alignment="center",
            )
        )
        if i < len(labels) - 1:
            children.append(Divider(orientation="vertical"))

    return Row(
        children=children,
        height=48,
        cross_alignment="center",
    )


def main() -> None:
    content = Column(
        children=[
            _section_title("Horizontal Divider – full width"),
            _list_section(),
            Divider(style=DividerStyle(thickness=8)),
            _section_title("Horizontal Divider – inset_left=56"),
            _inset_section(),
            Divider(style=DividerStyle(thickness=8)),
            _section_title("Vertical Divider in Row"),
            _row_section(),
        ],
        padding=24,
        gap=16,
    )

    app = MaterialApp(content=content)
    app.run()


if __name__ == "__main__":
    main()
