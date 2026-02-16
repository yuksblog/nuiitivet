from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nuiitivet.navigation.layer_composer import NavigationLayerCompositionContext
from nuiitivet.overlay.layer_composer import OverlayLayerCompositionContext
from nuiitivet.widgeting.widget import Widget


@dataclass(slots=True)
class RecordingNavigationComposer:
    static_paints: int = 0
    transition_paints: int = 0
    last_context: NavigationLayerCompositionContext | None = None

    def paint_static(self, *, canvas: Any, widget: Widget, x: int, y: int, width: int, height: int) -> None:
        self.static_paints += 1

    def paint_transition(self, context: NavigationLayerCompositionContext) -> None:
        self.transition_paints += 1
        self.last_context = context


@dataclass(slots=True)
class RecordingOverlayComposer:
    result_widget: Widget
    contexts: list[OverlayLayerCompositionContext] = field(default_factory=list)

    def compose(self, context: OverlayLayerCompositionContext) -> Widget:
        self.contexts.append(context)
        return self.result_widget


def assert_navigation_transition_context_basic(context: NavigationLayerCompositionContext) -> None:
    assert context.kind == "push"
    assert 0.0 <= context.progress <= 1.0
    assert context.from_phase.value == "exit"
    assert context.to_phase.value == "enter"


def assert_overlay_single_composition_context(
    contexts: list[OverlayLayerCompositionContext],
    *,
    expected_content: Widget,
) -> None:
    assert len(contexts) == 1
    assert contexts[0].content is expected_content
