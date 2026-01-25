"""Demo app to test Column and Row padding functionality."""

from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material import Text
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.material.theme.color_role import ColorRole


def main():
    """Show various padding configurations for Column and Row."""
    app = MaterialApp(
        content=FilledCard(
            child=Column(
                [
                    Text("Column and Row Padding Demo"),
                    FilledCard(
                        child=Column(
                            [Text("Column with padding=20"), Text("Second item"), Text("Third item")],
                            gap=5,
                            padding=20,
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.SURFACE_VARIANT),
                    ),
                    FilledCard(
                        child=Row(
                            [Text("Row"), Text("with"), Text("padding=15")],
                            gap=10,
                            padding=15,
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.SECONDARY_CONTAINER),
                    ),
                    FilledCard(
                        child=Column(
                            [
                                Text("Asymmetric padding:"),
                                Text("(left=5, top=10, right=15, bottom=20)"),
                            ],
                            padding=(5, 10, 15, 20),
                        ),
                        style=CardStyle.filled().copy_with(background=ColorRole.TERTIARY_CONTAINER),
                    ),
                    FilledCard(
                        child=Column(
                            [
                                Text("Nested: Row in Column, both with padding"),
                                Row(
                                    [FilledButton("Button 1"), FilledButton("Button 2")],
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
                    FilledCard(
                        child=Row(
                            [Text("No padding"), OutlinedButton("Button")],
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
