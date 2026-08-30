"""Small sample app demonstrating the Row demo from `my_app.py`.

This file provides a minimal `MyWidgetModel` and `MyWidget` App subclass
that exercise `Row`, `ForEach`, `Text` and `Button` to add/remove items
in a horizontal list.
"""

import logging
import sys
from typing import List, Optional

import nuiitivet.material as nv

_logger = logging.getLogger(__name__)


def _update_theme_seed(context, seed: str) -> None:
    current_mode = nv.Theme.of(context).mode
    if current_mode == "dark":
        nv.App.of(context).set_theme(nv.ThemeFactory.dark(seed))
    else:
        nv.App.of(context).set_theme(nv.ThemeFactory.light(seed))


def _toggle_theme_mode(context) -> None:
    # Default seed since we don't track it
    seed = "#6750A4"
    current_mode = nv.Theme.of(context).mode
    if current_mode == "light":
        nv.App.of(context).set_theme(nv.ThemeFactory.dark(seed))
    else:
        nv.App.of(context).set_theme(nv.ThemeFactory.light(seed))


class MyWidgetModel:
    """ViewModel for MyWidget — matches the demo in my_app.py.

    Provides separate observable lists for Column, Row and Grid demos with
    add/remove operations for each.
    """

    column_items: nv.Observable[List[str]] = nv.Observable([])
    row_items: nv.Observable[List[str]] = nv.Observable([])
    grid_items: nv.Observable[List[str]] = nv.Observable([])
    click_log: nv.Observable[str] = nv.Observable("")
    checkbox_state: nv.Observable[Optional[bool]] = nv.Observable(None)
    checkbox_state2: nv.Observable[Optional[bool]] = nv.Observable(None)

    def __init__(self) -> None:
        self._column_count: int = 0
        self._row_count: int = 0
        self._grid_count: int = 0
        self.column_items.value = ["CItem 1", "CItem 2"]
        self.row_items.value = []
        self.grid_items.value = []
        self.click_log.value = ""
        self.checkbox_state.value = None
        self.checkbox_state2.value = None

    def add_column_item(self) -> None:
        items = list(self.column_items.value) if getattr(self.column_items, "value", None) is not None else []
        self._column_count += 1
        items.append(f"CItem {self._column_count}")
        self.column_items.value = items

    def remove_column_item(self) -> None:
        items = list(self.column_items.value) if getattr(self.column_items, "value", None) is not None else []
        if not items:
            return
        items.pop()
        self.column_items.value = items

    def add_row_item(self) -> None:
        items = list(self.row_items.value) if getattr(self.row_items, "value", None) is not None else []
        self._row_count += 1
        items.append(f"RItem {self._row_count}")
        self.row_items.value = items

    def remove_row_item(self) -> None:
        items = list(self.row_items.value) if getattr(self.row_items, "value", None) is not None else []
        if not items:
            return
        items.pop()
        self.row_items.value = items

    def add_grid_item(self) -> None:
        items = list(self.grid_items.value) if getattr(self.grid_items, "value", None) is not None else []
        self._grid_count += 1
        items.append(f"GItem {self._grid_count}")
        self.grid_items.value = items

    def remove_grid_item(self) -> None:
        items = list(self.grid_items.value) if getattr(self.grid_items, "value", None) is not None else []
        if not items:
            return
        items.pop()
        self.grid_items.value = items

    def record_click(self, label: str) -> None:
        try:
            self.click_log.value = f"Clicked: {label}"
        except Exception:
            try:
                self.click_log._value = f"Clicked: {label}"
            except Exception:
                _logger.exception("Failed to record click in fallback path")


class MyWidget(nv.ComposableWidget):

    def __init__(self, model: MyWidgetModel):
        super().__init__()
        self.model = model
        self._icon_debugged = False

    def build(self):
        if self._icon_debugged:
            self._log_icon_debug()
            self._icon_debugged = False

        children = [
            nv.Row(
                [
                    nv.Button(
                        "Seed Purple",
                        on_click=lambda: _update_theme_seed(self, "#6750A4"),
                        style=nv.ButtonStyle.filled(),
                    ),
                    nv.Button(
                        "Seed Teal",
                        on_click=lambda: _update_theme_seed(self, "#00796B"),
                        style=nv.ButtonStyle.filled(),
                    ),
                    nv.Button(
                        "Seed Amber",
                        on_click=lambda: _update_theme_seed(self, "#FFC107"),
                        style=nv.ButtonStyle.filled(),
                    ),
                    nv.Button("Toggle Mode", on_click=lambda: _toggle_theme_mode(self), style=nv.ButtonStyle.filled()),
                ],
                gap=8,
                cross_alignment="center",
            ),
            nv.Card(
                nv.Row(
                    [
                        nv.Icon(nv.Symbols.home, size=24),
                        nv.Icon(nv.Symbols.search, size=24, style=nv.IconStyle(family="rounded")),
                        nv.Icon(nv.Symbols.menu, size=24, style=nv.IconStyle(family="sharp")),
                        nv.Icon(nv.Symbols.settings, size=24, style=nv.IconStyle(family="twotone")),
                    ],
                    gap=12,
                    cross_alignment="center",
                ),
                padding=8,
                style=nv.CardStyle.filled().copy_with(border_radius=8),
                alignment="center",
            ),
            nv.Card(
                nv.Row([nv.Text("Last click:"), nv.Text(self.model.click_log)], gap=8, cross_alignment="center"),
                padding=6,
                alignment="center",
            ),
            nv.Row(
                [
                    nv.Button(
                        "Record: A", on_click=lambda: self.model.record_click("A"), style=nv.ButtonStyle.elevated()
                    ),
                    nv.Button(
                        "Record: B", on_click=lambda: self.model.record_click("B"), style=nv.ButtonStyle.elevated()
                    ),
                    nv.Button("Clear", on_click=lambda: self.model.record_click(""), style=nv.ButtonStyle.outlined()),
                ],
                gap=8,
                cross_alignment="center",
            ),
            nv.Card(
                nv.Column(
                    [
                        nv.Text("Column demo:"),
                        nv.Row(
                            [
                                nv.Button(
                                    "Add (Column)",
                                    on_click=self.model.add_column_item,
                                    style=nv.ButtonStyle.elevated(),
                                ),
                                nv.Button(
                                    "Remove (Column)",
                                    on_click=self.model.remove_column_item,
                                    style=nv.ButtonStyle.outlined(),
                                ),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                        nv.VerticalScrollable(
                            nv.Column.builder(
                                self.model.column_items,
                                lambda item, idx: nv.Text(item),
                                gap=8,
                                cross_alignment="center",
                            ),
                            width=nv.Sizing.weight(),
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                    height=200,
                ),
                padding=8,
                style=nv.CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
            nv.Card(
                nv.Column(
                    [
                        nv.Text("Row demo:"),
                        nv.Row(
                            [
                                nv.Button("Add (Row)", on_click=self.model.add_row_item, style=nv.ButtonStyle.tonal()),
                                nv.Button(
                                    "Remove (Row)", on_click=self.model.remove_row_item, style=nv.ButtonStyle.text()
                                ),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                        nv.HorizontalScrollable(
                            nv.Row.builder(
                                self.model.row_items,
                                lambda item, idx: nv.Text(item),
                                gap=8,
                                cross_alignment="center",
                            ),
                            scrollbar_behavior=nv.ScrollbarBehavior(auto_hide=False),
                            height=50,
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                ),
                padding=8,
                style=nv.CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
            nv.Card(
                nv.Column(
                    [
                        nv.Text("Grid demo:"),
                        nv.UniformFlow.builder(
                            self.model.grid_items,
                            lambda item, idx: nv.Text(item),
                            columns=3,
                            main_gap=8,
                            cross_gap=8,
                        ),
                        nv.Row(
                            [
                                nv.Fab(nv.Symbols.add, on_click=self.model.add_grid_item),
                                nv.Button(
                                    "Remove (Grid)",
                                    on_click=self.model.remove_grid_item,
                                    style=nv.ButtonStyle.outlined(),
                                ),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                ),
                padding=8,
                style=nv.CardStyle.outlined().copy_with(border_radius=6),
                alignment="start",
            ).modifier(
                nv.shadow((nv.ColorRole.SHADOW, 0.12), blur=12.0, offset=(0, 6))
            ),  # Test that modifiers work on Cards
            nv.Card(
                nv.Column(
                    [
                        nv.Text("Checkbox demo:"),
                        nv.Row(
                            [
                                nv.Checkbox(checked=self.model.checkbox_state),
                                nv.Text(self.model.checkbox_state),
                            ],
                            gap=12,
                            cross_alignment="center",
                        ),
                        nv.Row(
                            [
                                nv.Checkbox(checked=self.model.checkbox_state2),
                                nv.Text(self.model.checkbox_state2),
                            ],
                            gap=12,
                            cross_alignment="center",
                        ),
                    ],
                    gap=8,
                    cross_alignment="start",
                ),
                padding=8,
                style=nv.CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
        ]

        root = nv.Column(children, padding=12, gap=12, cross_alignment="center")
        return root

    def _log_icon_debug(self) -> None:
        icon = nv.Icon(nv.Symbols.home, size=24)
        symbol_codepoint = icon._symbol_codepoint
        current_symbol = nv.Symbols.home
        debug_fields = {
            "icon_class": f"{nv.Icon.__module__}.{nv.Icon.__name__}",
            "symbol_name": current_symbol.name,
            "symbol_glyph": current_symbol.glyph(),
            "icon_resolved": symbol_codepoint,
            "icon_module": icon.__class__.__module__,
        }
        print("[my_widget debug]" + " ".join(f"{k}={v}" for k, v in debug_fields.items()), file=sys.stderr)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    model = MyWidgetModel()
    widget = MyWidget(model)

    app = nv.App(nv.Window(content=widget, title="MyWidget Demo"))
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("out_widget.png")
            print("Rendered out_widget.png")
        except Exception:
            print("Could not run app: missing interactive/render deps (pyglet/skia).")


if __name__ == "__main__":
    main()
