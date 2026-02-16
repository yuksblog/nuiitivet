from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.widgeting.widget import Widget
from tests.helpers.layer_composer import (
    RecordingNavigationComposer,
    assert_navigation_transition_context_basic,
)


@dataclass(frozen=True, slots=True)
class _AnimatedTransitionSpec:
    pass


class _FlagWidget(Widget):
    def build(self) -> Widget:
        return self


def test_navigator_delegates_static_paint_to_layer_composer() -> None:
    spy = RecordingNavigationComposer()
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget)], layer_composer=spy)

    nav.paint(canvas=None, x=0, y=0, width=100, height=100)

    assert spy.static_paints == 1
    assert spy.transition_paints == 0


def test_navigator_delegates_transition_paint_to_layer_composer() -> None:
    spy = RecordingNavigationComposer()
    nav = Navigator(
        routes=[PageRoute(builder=_FlagWidget, transition_spec=_AnimatedTransitionSpec())],
        layer_composer=spy,
    )
    nav._app = object()  # type: ignore[attr-defined]

    nav.push(PageRoute(builder=_FlagWidget, transition_spec=_AnimatedTransitionSpec()))
    nav.paint(canvas=None, x=0, y=0, width=100, height=100)

    assert spy.transition_paints == 1
    assert spy.last_context is not None
    assert_navigation_transition_context_basic(spy.last_context)
