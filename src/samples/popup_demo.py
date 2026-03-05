"""modeless()/light_dismiss() Modifier Demo

Shows the main usage patterns for modeless()/light_dismiss() modifiers:

1. Internal state  - click the anchor to toggle; outside tap to dismiss
2. External state  - open/close driven by Observable[bool] + button
3. Alignment       - four placements (bottom-left, bottom-right,
                     top-left, top-right)
4. Transition      - enter/exit animation via MaterialTransitions.dialog()
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Icon, Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, OutlinedButton
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.modifiers import light_dismiss, modeless
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import ComposableWidget, Widget


# ---------------------------------------------------------------------------
# Helper: simple popup menu content
# ---------------------------------------------------------------------------


def _menu_item(label: str, on_click=None) -> Widget:
    box = Box(
        child=Text(label, style=TextStyle(font_size=14)),
        padding=12,
        width="100%",
    )
    if on_click is not None:
        from nuiitivet.modifiers import clickable

        box = box.modifier(clickable(on_click=on_click))
    return box


def _popup_menu(*items: tuple[str, ...]) -> Widget:
    """A styled panel containing menu items."""
    children = [_menu_item(label) for label in items]
    return Box(
        child=Column(children=children, gap=0, cross_alignment="start"),
        padding=4,
        width=180,
        background_color=(255, 255, 255, 255),
        corner_radius=8.0,
        shadow_blur=16.0,
        shadow_color=(0, 0, 0, 60),
    )


def _section_label(text: str) -> Widget:
    return Text(text, style=TextStyle(font_size=11, color=(100, 100, 100, 255)))


# ---------------------------------------------------------------------------
# Section 1: Internal state (click-to-toggle)
# ---------------------------------------------------------------------------


class _InternalStateDemo(ComposableWidget):
    is_open: Observable[bool] = Observable(False)

    def build(self) -> Widget:
        from nuiitivet.modifiers import clickable

        def toggle() -> None:
            self.is_open.value = not self.is_open.value

        anchor = (
            FilledButton("Menu")
            .modifier(clickable(on_click=toggle))
            .modifier(
                modeless(
                    _popup_menu("Profile", "Settings", "Help", "Sign out"),
                    is_open=self.is_open,
                    alignment="bottom-left",
                    anchor="top-left",
                    offset=(0.0, 4.0),
                )
            )
        )

        return Column(
            children=[
                _section_label("1. Internal state - click anchor to open/close"),
                anchor,
            ],
            gap=8,
            cross_alignment="start",
        )


# ---------------------------------------------------------------------------
# Section 2: External Observable state
# ---------------------------------------------------------------------------


class _ExternalStateDemo(ComposableWidget):
    is_open: Observable[bool] = Observable(False)

    def build(self) -> Widget:
        def open_popup() -> None:
            self.is_open.value = True

        def close_popup() -> None:
            self.is_open.value = False

        anchor = Box(
            child=Row(
                children=[
                    Icon("more_vert", size=24),
                    Text("Anchor", style=TextStyle(font_size=14)),
                ],
                gap=4,
                cross_alignment="center",
            ),
            padding=(8, 12),
            background_color=(230, 234, 240, 255),
            corner_radius=8.0,
        ).modifier(
            modeless(
                _popup_menu("Option A", "Option B", "Option C"),
                is_open=self.is_open,
                alignment="bottom-left",
                anchor="top-left",
                offset=(0.0, 4.0),
            )
        )

        return Column(
            children=[
                _section_label("2. External Observable - buttons control open/close"),
                Row(
                    children=[
                        anchor,
                        FilledButton("Open", on_click=open_popup),
                        OutlinedButton("Close", on_click=close_popup),
                    ],
                    gap=8,
                    cross_alignment="center",
                ),
            ],
            gap=8,
            cross_alignment="start",
        )


# ---------------------------------------------------------------------------
# Section 3: Alignment variants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Section 3: Alignment variants
# ---------------------------------------------------------------------------


class _AlignmentDemo(ComposableWidget):
    is_open_bl: Observable[bool] = Observable(False)
    is_open_br: Observable[bool] = Observable(False)
    is_open_tl: Observable[bool] = Observable(False)
    is_open_tr: Observable[bool] = Observable(False)

    def build(self) -> Widget:
        from nuiitivet.modifiers import clickable

        def _anchor(label: str, alignment: str, anchor_pt: str, is_open: Observable[bool]) -> Widget:
            def toggle() -> None:
                is_open.value = not is_open.value

            return (
                Box(
                    child=Text(label, style=TextStyle(font_size=12)),
                    padding=8,
                    background_color=(210, 225, 250, 255),
                    corner_radius=6.0,
                )
                .modifier(clickable(on_click=toggle))
                .modifier(
                    modeless(
                        _popup_menu("Item 1", "Item 2", "Item 3"),
                        is_open=is_open,
                        alignment=alignment,
                        anchor=anchor_pt,
                        offset=(0.0, 4.0),
                    )
                )
            )

        row = Row(
            children=[
                _anchor("bottom-left", "bottom-left", "top-left", self.is_open_bl),
                _anchor("bottom-right", "bottom-right", "top-right", self.is_open_br),
                _anchor("top-left", "top-left", "bottom-left", self.is_open_tl),
                _anchor("top-right", "top-right", "bottom-right", self.is_open_tr),
            ],
            gap=8,
            cross_alignment="center",
        )

        return Column(
            children=[
                _section_label("3. Alignment variants - click each anchor"),
                row,
            ],
            gap=8,
            cross_alignment="start",
        )


# ---------------------------------------------------------------------------
# Section 4: With transition
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Section 4: With transition
# ---------------------------------------------------------------------------


class _TransitionDemo(ComposableWidget):
    is_open: Observable[bool] = Observable(False)

    def build(self) -> Widget:
        from nuiitivet.modifiers import clickable

        def toggle() -> None:
            self.is_open.value = not self.is_open.value

        anchor = OutlinedButton("Open with animation", on_click=toggle).modifier(
            modeless(
                _popup_menu("Cut", "Copy", "Paste", "Select all"),
                is_open=self.is_open,
                alignment="top-left",
                anchor="bottom-left",
                transition_spec=MaterialTransitions.dialog(),
            )
        )

        return Column(
            children=[
                _section_label("4. Transition - MaterialTransitions.dialog()"),
                anchor,
            ],
            gap=8,
            cross_alignment="start",
        )


class _BehaviorComparisonDemo(ComposableWidget):
    modeless_open: Observable[bool] = Observable(False)
    light_open: Observable[bool] = Observable(False)
    modeless_close_clicks: Observable[int] = Observable(0)
    light_close_clicks: Observable[int] = Observable(0)

    def build(self) -> Widget:
        def _open_modeless() -> None:
            self.modeless_open.value = True

        def _open_light_dismiss() -> None:
            self.light_open.value = True

        def _inc_modeless_close_clicks() -> None:
            self.modeless_close_clicks.value = int(self.modeless_close_clicks.value) + 1
            self.modeless_open.value = False

        def _inc_light_close_clicks() -> None:
            self.light_close_clicks.value = int(self.light_close_clicks.value) + 1
            self.light_open.value = False

        modeless_anchor = FilledButton("Open modeless", on_click=_open_modeless).modifier(
            modeless(
                _popup_menu("Modeless menu", "Background is clickable"),
                is_open=self.modeless_open,
                alignment="bottom-left",
                anchor="top-left",
                offset=(0.0, 4.0),
            )
        )

        light_anchor = FilledButton("Open light_dismiss", on_click=_open_light_dismiss).modifier(
            light_dismiss(
                _popup_menu("Light dismiss menu", "Outside tap closes"),
                is_open=self.light_open,
                alignment="bottom-left",
                anchor="top-left",
                offset=(0.0, 4.0),
            )
        )

        modeless_row = Row(
            children=[
                modeless_anchor,
                OutlinedButton("Close button behind", on_click=_inc_modeless_close_clicks),
                Text(self.modeless_close_clicks.map(lambda v: f"button clicks: {v}")),
            ],
            gap=8,
            cross_alignment="center",
        )

        light_row = Row(
            children=[
                light_anchor,
                OutlinedButton("Close button behind", on_click=_inc_light_close_clicks),
                Text(self.light_close_clicks.map(lambda v: f"button clicks: {v}")),
            ],
            gap=8,
            cross_alignment="center",
        )

        return Column(
            children=[
                _section_label("5. Behavior check - modeless vs light_dismiss"),
                Text("modeless: behind button remains clickable while open."),
                modeless_row,
                Text("light_dismiss: first outside tap closes overlay and blocks behind button."),
                light_row,
            ],
            gap=8,
            cross_alignment="start",
        )


# ---------------------------------------------------------------------------
# Top-level layout
# ---------------------------------------------------------------------------


def _build_content() -> Widget:
    return Column(
        children=[
            Text("modeless()/light_dismiss() Modifier Demo", style=TextStyle(font_size=20)),
            _InternalStateDemo(),
            _ExternalStateDemo(),
            _AlignmentDemo(),
            _TransitionDemo(),
            _BehaviorComparisonDemo(),
        ],
        gap=32,
        padding=32,
        cross_alignment="start",
    )


def main() -> None:
    app = MaterialApp(content=_build_content())
    app.run()


if __name__ == "__main__":
    main()
