"""Plain dialog implementations.

These widgets provide minimal, design-system-agnostic implementations
for standard dialog intents.
"""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.overlay.intents import PlainDialogIntent, LoadingDialogIntent
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.theme.plain_theme import PlainColorRole
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import ensure_interaction_region
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.text_style import TextStyle
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class PlainDialog(ComposableWidget):
    """Plain implementation of an alert dialog."""

    def __init__(self, intent: PlainDialogIntent) -> None:
        super().__init__()
        self.intent = intent

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Box(
                background_color=PlainColorRole.SURFACE,
                border_color=PlainColorRole.OUTLINE,
                border_width=1,
                padding=24,
                child=Column(
                    gap=16,
                    children=[
                        Text(
                            self.intent.title,
                            style=TextStyle(
                                color=PlainColorRole.ON_SURFACE,
                            ),
                            type_scale=TypeScaleToken.from_size(20),
                        ),
                        Text(
                            self.intent.message,
                            style=TextStyle(
                                color=PlainColorRole.ON_SURFACE,
                            ),
                        ),
                        Row(
                            main_alignment="end",
                            children=[self._ok_button()],
                        ),
                    ],
                ),
            ),
        )

    def _ok_button(self) -> Widget:
        label = Box(padding=8, child=Text("OK", style=TextStyle(color=PlainColorRole.ON_SURFACE)))
        region = ensure_interaction_region(label)
        region.enable_click(on_click=lambda: Overlay.of(self).close())
        return region


class PlainLoadingDialog(ComposableWidget):
    """Plain implementation of a loading dialog."""

    def __init__(self, intent: LoadingDialogIntent) -> None:
        super().__init__()
        self.intent = intent

    def build(self) -> Widget:
        return Container(
            alignment="center",
            child=Box(
                background_color=PlainColorRole.SURFACE,
                border_color=PlainColorRole.OUTLINE,
                border_width=1,
                padding=24,
                child=Text(
                    self.intent.message,
                    style=TextStyle(
                        color=PlainColorRole.ON_SURFACE,
                    ),
                ),
            ),
        )
