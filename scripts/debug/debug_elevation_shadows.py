"""Eyeball every widget whose shadow comes from the MD3 elevation table.

Card, Menu, Dialog, DatePicker, Tooltip and FAB all route through
``md3_elevation_to_shadow``, so a change to that table changes all of them at
once. This puts them on one screen, over a plain surface, next to a row of bare
cards at levels 1-5 for reference.

Run:  python -m nuiitivet.dev run scripts/debug/debug_elevation_shadows.py
"""

from __future__ import annotations

import nuiitivet.material as nv


class ElevationGallery(nv.ComposableWidget):
    """Every elevation-bearing surface, on one screen."""

    def __init__(self) -> None:
        super().__init__()
        self.menu_open = nv.Observable(False)
        self.arrival = nv.Observable("")

    def build(self) -> nv.Widget:
        return nv.VerticalScrollable(
            nv.Column(
                gap=28,
                padding=32,
                children=[
                    nv.Text("MD3 elevation levels", type_scale=nv.TypeScaleToken.from_size(18)),
                    self._level_row(),
                    nv.HorizontalDivider(),
                    nv.Text("Components", type_scale=nv.TypeScaleToken.from_size(18)),
                    self._component_row(),
                    nv.HorizontalDivider(),
                    nv.Text("Tooltips", type_scale=nv.TypeScaleToken.from_size(18)),
                    # Placed directly rather than triggered by hover: the point
                    # is the shadow, and the dev bridge cannot hover.
                    nv.Row(
                        gap=24,
                        children=[
                            nv.Tooltip("Plain tooltip, level 0 -- flat by spec"),
                            nv.RichTooltip(
                                "A rich tooltip container also sits at level 2.",
                                subhead="Rich tooltip",
                                width=260,
                            ),
                        ],
                    ),
                    nv.HorizontalDivider(),
                    nv.Text("Date picker", type_scale=nv.TypeScaleToken.from_size(18)),
                    nv.DockedDatePicker(value=self.arrival, label="Arrival"),
                ],
            )
        )

    def _level_row(self) -> nv.Widget:
        """Bare cards at every level, so the steps are comparable side by side."""
        return nv.Row(
            gap=24,
            children=[
                nv.Card(
                    nv.Text(f"level {level}", padding=12),
                    width=120,
                    height=70,
                    style=nv.CardStyle.elevated().copy_with(elevation=level),
                )
                for level in range(1, 6)
            ],
        )

    def _component_row(self) -> nv.Widget:
        return nv.Row(
            gap=24,
            children=[
                nv.Button("Dialog", on_click=self._open_dialog, style=nv.ButtonStyle.filled()),
                nv.Button("Snackbar", on_click=self._open_snackbar),
                nv.Button("Tooltip me").modifier(nv.tooltip("A tooltip sits at level 2")),
                nv.Button("Menu", on_click=self._toggle_menu).modifier(
                    nv.popup(
                        nv.Menu(
                            [
                                nv.MenuItem("Cut"),
                                nv.MenuItem("Copy"),
                                nv.MenuItem("Paste"),
                            ]
                        ),
                        is_open=self.menu_open,
                    )
                ),
                nv.Fab(icon="add", on_click=self._open_snackbar),
            ],
        )

    def _toggle_menu(self) -> None:
        self.menu_open.value = not self.menu_open.value

    def _open_snackbar(self) -> None:
        nv.Overlay.of(self).snackbar("Snackbar sits at level 3")

    async def _open_dialog(self) -> None:
        await nv.Overlay.of(self).dialog(
            nv.BasicDialog(
                title="Dialog",
                message="A dialog container sits at level 3.",
            )
        )


def build_root() -> nv.Widget:
    return ElevationGallery()


def main(png: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="Elevation shadows", width=980, height=720))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else "")
