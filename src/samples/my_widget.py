"""Small sample app demonstrating the Row demo from `my_app.py`.

This file provides a minimal `MyWidgetModel` and `MyWidget` App subclass
that exercise `Row`, `ForEach`, `Text` and `Button` to add/remove items
in a horizontal list.
"""

import logging
import sys
from typing import List, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Checkbox, Icon, Text
from nuiitivet.material.styles import IconStyle
from nuiitivet.observable import Observable
from nuiitivet.scrolling import ScrollDirection
from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroller import Scroller
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.material.symbols import Symbols
from nuiitivet.material.buttons import (
    ElevatedButton,
    FilledButton,
    FilledTonalButton,
    FloatingActionButton,
    OutlinedButton,
    TextButton,
)
from nuiitivet.theme import manager as theme_manager
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.scrollbar import ScrollbarBehavior
from nuiitivet.material.theme.material_theme import MaterialTheme


_logger = logging.getLogger(__name__)


def _update_theme_seed(seed: str) -> None:
    mode = theme_manager.current.mode
    if mode == "dark":
        theme_manager.set_theme(MaterialTheme.dark(seed))
    else:
        theme_manager.set_theme(MaterialTheme.light(seed))


def _toggle_theme_mode() -> None:
    mode = theme_manager.current.mode
    # Default seed since we don't track it
    seed = "#6750A4"
    if mode == "light":
        theme_manager.set_theme(MaterialTheme.dark(seed))
    else:
        theme_manager.set_theme(MaterialTheme.light(seed))


class MyWidgetModel:
    """ViewModel for MyWidget — matches the demo in my_app.py.

    Provides separate observable lists for Column, Row and Grid demos with
    add/remove operations for each.
    """

    column_items: Observable[List[str]] = Observable([])
    row_items: Observable[List[str]] = Observable([])
    grid_items: Observable[List[str]] = Observable([])
    click_log: Observable[str] = Observable("")
    checkbox_state: Observable[Optional[bool]] = Observable(None)
    checkbox_state2: Observable[Optional[bool]] = Observable(None)

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
                exception_once(
                    _logger,
                    "my_widget_record_click_fallback_exc",
                    "Failed to record click in fallback path",
                )


class MyWidget(ComposableWidget):

    def __init__(self, model: MyWidgetModel):
        super().__init__()
        self.model = model
        self._icon_debugged = False

    def build(self):
        if self._icon_debugged:
            self._log_icon_debug()
            self._icon_debugged = False

        children = [
            Row(
                [
                    FilledButton("Seed Purple", on_click=lambda: _update_theme_seed("#6750A4")),
                    FilledButton("Seed Teal", on_click=lambda: _update_theme_seed("#00796B")),
                    FilledButton("Seed Amber", on_click=lambda: _update_theme_seed("#FFC107")),
                    FilledButton(
                        "Toggle Mode",
                        on_click=_toggle_theme_mode,
                    ),
                ],
                gap=8,
                cross_alignment="center",
            ),
            FilledCard(
                Row(
                    [
                        Icon(Symbols.home, size=24),
                        Icon(Symbols.search, size=24, style=IconStyle(family="rounded")),
                        Icon(Symbols.menu, size=24, style=IconStyle(family="sharp")),
                        Icon(Symbols.settings, size=24, style=IconStyle(family="twotone")),
                    ],
                    gap=12,
                    cross_alignment="center",
                ),
                padding=8,
                style=CardStyle.filled().copy_with(border_radius=8),
                alignment="center",
            ),
            FilledCard(
                Row([Text("Last click:"), Text(self.model.click_log)], gap=8, cross_alignment="center"),
                padding=6,
                alignment="center",
            ),
            Row(
                [
                    ElevatedButton("Record: A", on_click=lambda: self.model.record_click("A")),
                    ElevatedButton("Record: B", on_click=lambda: self.model.record_click("B")),
                    OutlinedButton("Clear", on_click=lambda: self.model.record_click("")),
                ],
                gap=8,
                cross_alignment="center",
            ),
            FilledCard(
                Column(
                    [
                        Text("Column demo:"),
                        Row(
                            [
                                ElevatedButton("Add (Column)", on_click=self.model.add_column_item),
                                OutlinedButton("Remove (Column)", on_click=self.model.remove_column_item),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                        Scroller(
                            Column.builder(
                                self.model.column_items,
                                lambda item, idx: Text(item),
                                gap=8,
                                cross_alignment="center",
                            ),
                            width=Sizing.flex(),
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                    height=200,
                ),
                padding=8,
                style=CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
            FilledCard(
                Column(
                    [
                        Text("Row demo:"),
                        Row(
                            [
                                FilledTonalButton("Add (Row)", on_click=self.model.add_row_item),
                                TextButton("Remove (Row)", on_click=self.model.remove_row_item),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                        Scroller(
                            Row.builder(
                                self.model.row_items,
                                lambda item, idx: Text(item),
                                gap=8,
                                cross_alignment="center",
                            ),
                            scrollbar=ScrollbarBehavior(auto_hide=False),
                            direction=ScrollDirection.HORIZONTAL,
                            height=50,
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                ),
                padding=8,
                style=CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
            FilledCard(
                Column(
                    [
                        Text("Grid demo:"),
                        Flow.builder(
                            self.model.grid_items,
                            lambda item, idx: Text(item),
                            uniform=True,
                            columns=3,
                            main_gap=8,
                            cross_gap=8,
                        ),
                        Row(
                            [
                                FloatingActionButton(Symbols.add, on_click=self.model.add_grid_item),
                                OutlinedButton("Remove (Grid)", on_click=self.model.remove_grid_item),
                            ],
                            gap=8,
                            cross_alignment="center",
                        ),
                    ],
                    gap=6,
                    cross_alignment="start",
                ),
                padding=8,
                style=CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
            FilledCard(
                Column(
                    [
                        Text("Checkbox demo:"),
                        Row(
                            [
                                Checkbox(checked=self.model.checkbox_state),
                                Text(self.model.checkbox_state),
                            ],
                            gap=12,
                            cross_alignment="center",
                        ),
                        Row(
                            [
                                Checkbox(checked=self.model.checkbox_state2),
                                Text(self.model.checkbox_state2),
                            ],
                            gap=12,
                            cross_alignment="center",
                        ),
                    ],
                    gap=8,
                    cross_alignment="start",
                ),
                padding=8,
                style=CardStyle.filled().copy_with(border_radius=6),
                alignment="start",
            ),
        ]

        root = Column(children, padding=12, gap=12, cross_alignment="center")
        return root

    def _log_icon_debug(self) -> None:
        icon = Icon(Symbols.home, size=24)
        symbol_codepoint = icon._symbol_codepoint
        current_symbol = Symbols.home
        debug_fields = {
            "icon_class": f"{Icon.__module__}.{Icon.__name__}",
            "symbol_name": current_symbol.name,
            "symbol_glyph": current_symbol.glyph(),
            "icon_resolved": symbol_codepoint,
            "icon_module": icon.__class__.__module__,
        }
        print("[my_widget debug]" + " ".join(f"{k}={v}" for k, v in debug_fields.items()), file=sys.stderr)


if __name__ == "__main__":
    model = MyWidgetModel()
    widget = MyWidget(model)
    import nuiitivet as nv

    app = MaterialApp(
        content=widget,
        # width=750,
        # height=850,
        title_bar=nv.DefaultTitleBar(title="MyWidget Demo"),
    )
    try:
        app.run()
    except Exception:
        try:
            app.render_to_png("out_widget.png")
            print("Rendered out_widget.png")
        except Exception:
            print("Could not run app: missing interactive/render deps (pyglet/skia).")
