"""Navigator Demo.

This demo shows the minimal Navigator usage:
- A two-page stack
- push() to navigate forward
- pop() to navigate back

Run:
    uv run python -c "import sitecustomize; import samples.navigator_demo as m; m.main()"
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.modifiers import background
from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, TextButton
from nuiitivet.material import Text
from nuiitivet.widgeting.widget import ComposableWidget, Widget


@dataclass(frozen=True, slots=True)
class HomeIntent:
    pass


class HomePage(ComposableWidget):
    def build(self) -> Widget:
        def go_next() -> None:
            Navigator.of(self).push(PageRoute(builder=DetailsPage))

        return Container(
            padding=24,
            child=Column(
                gap=16,
                cross_alignment="start",
                children=[
                    Text("Navigator Demo"),
                    Text("This is the first page."),
                    FilledButton("Go to details", on_click=go_next),
                ],
            ),
        ).modifier(background("#E3F2FD"))


class DetailsPage(ComposableWidget):
    def build(self) -> Widget:
        def go_back() -> None:
            Navigator.of(self).pop()

        def push_more() -> None:
            Navigator.of(self).push(PageRoute(builder=DetailsPage))

        return Container(
            padding=24,
            child=Column(
                gap=16,
                cross_alignment="start",
                children=[
                    Text("Details"),
                    Text("This is the second page."),
                    TextButton("Back", on_click=go_back),
                    FilledButton("Push another details", on_click=push_more),
                ],
            ),
        ).modifier(background("#FFF3E0"))


def main() -> None:
    MaterialApp.navigation(
        routes={
            HomeIntent: lambda _i: PageRoute(builder=HomePage),
        },
        initial_route=HomeIntent(),
        width=480,
        height=360,
    ).run()


if __name__ == "__main__":
    main()
