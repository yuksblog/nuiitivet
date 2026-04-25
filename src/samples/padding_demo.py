"""Demo app to test Column and Row padding functionality."""

from nuiitivet.material import App
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import Card
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material import Text
from nuiitivet.material.buttons import Button
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material import ButtonStyle


def main():
    """Show various padding configurations for Column and Row."""
    app = App(
        content=Card(
            child=Column(
                [
                    Text("Column and Row Padding Demo"),
                    Card(
                        child=Column(
                            [Text("Column with padding=20"), Text("Second item"), Text("Third item")],
                            gap=5,
                            padding=20,
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.SURFACE_VARIANT),
                    ),
                    Card(
                        child=Row(
                            [Text("Row"), Text("with"), Text("padding=15")],
                            gap=10,
                            padding=15,
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.SECONDARY_CONTAINER),
                    ),
                    Card(
                        child=Column(
                            [
                                Text("Asymmetric padding:"),
                                Text("(left=5, top=10, right=15, bottom=20)"),
                            ],
                            padding=(5, 10, 15, 20),
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.TERTIARY_CONTAINER),
                    ),
                    Card(
                        child=Column(
                            [
                                Text("Nested: Row in Column, both with padding"),
                                Row(
                                    [
                                        Button("Button 1", style=ButtonStyle.filled()),
                                        Button("Button 2", style=ButtonStyle.filled()),
                                    ],
                                    gap=10,
                                    padding=10,
                                ),
                            ],
                            gap=10,
                            padding=15,
                        ),
                        style=CardStyle.filled().copy_with(
                            background=ColorRole.SURFACE,
                            border_width=2,
                        ),
                    ),
                    Card(
                        child=Row(
                            [Text("No padding"), Button("Button", style=ButtonStyle.outlined())],
                            gap=10,
                            padding=0,
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.ERROR_CONTAINER),
                    ),
                ],
                gap=20,
                padding=30,
            ),
        ),
    )
    app.run()


if __name__ == "__main__":
    main()
