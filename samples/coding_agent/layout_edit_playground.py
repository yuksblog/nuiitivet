"""A page to try layout edit mode on: spacing to drag, presets to pick.

Press Ctrl+Shift+E (Cmd+Shift+E on macOS), click a widget, and press W to
reach its column. The spacing handles change the padding and the gap; the
bar over a selected button, toggle, FAB, chip, text field, card or text
holds its presets.
"""

from __future__ import annotations

import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            padding=8,
            cross_alignment="start",
            children=[
                nv.Text("Layout edit playground", type_scale=nv.TypeScale.HEADLINE_SMALL),
                nv.Text("Drag a spacing handle, or click a button for its bar.", type_scale=nv.TypeScale.BODY_MEDIUM),
                nv.Row(
                    gap=12,
                    children=[
                        nv.Button("Filled", style=nv.ButtonStyle.filled()),
                        nv.Button("Tonal", style=nv.ButtonStyle.tonal("m"), padding=12),
                        nv.Button("Outlined", style=nv.ButtonStyle.outlined()),
                    ],
                ),
                nv.Row(
                    gap=12,
                    children=[
                        nv.ToggleButton("Toggle", style=nv.ToggleButtonStyle.outlined()),
                        nv.Fab("add"),
                        nv.AssistChip(label="Assist"),
                    ],
                ),
                nv.TextField(label="Field", style=nv.TextFieldStyle.outlined()),
                nv.Card(
                    nv.Text("A card that sizes to its text", type_scale=nv.TypeScale.TITLE_MEDIUM),
                    padding=(16, 12),
                    style=nv.CardStyle.filled(),
                ),
                nv.Card(
                    nv.Text("A card 300 wide", type_scale=nv.TypeScale.TITLE_MEDIUM),
                    width=300,
                    padding=(16, 12),
                    style=nv.CardStyle.outlined(),
                ),
            ],
        ),
    )


def main() -> None:
    nv.App(nv.Window(content=build_root, title="Layout edit playground", width=520, height=500)).run()


if __name__ == "__main__":
    main()
