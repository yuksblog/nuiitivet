"""Regression tests: MaterialNavigator must render Material page transitions.

See issue #399. ``MaterialNavigator`` created directly via ``intents`` / ``routes``
(not only the implicit navigator that ``MaterialApp`` wires up) fell back to the
core ``_DefaultNavigationLayerComposer``, which composites both routes at full
opacity. The transition therefore never animated — every frame painted the same
pixels regardless of progress.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

import nuiitivet.material as nv
from nuiitivet.material.navigation_visual_state import MaterialNavigationLayerComposer
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.rendering.skia import skia_module

_HAS_SKIA = skia_module.get_skia(raise_if_missing=False) is not None


@dataclass(frozen=True)
class _ScreenIntent:
    depth: int


class _Screen(nv.ComposableWidget):
    def __init__(self, depth: int) -> None:
        super().__init__()
        self.depth = depth

    def build(self) -> nv.Widget:
        color = "#FF0000" if self.depth == 0 else "#0000FF"
        return nv.Box(
            background_color=color,
            width=nv.Sizing.weight(1),
            height=nv.Sizing.weight(1),
            child=nv.Text(f"depth {self.depth}"),
        )


class _DummyApp:
    def invalidate(self, immediate: bool = False, content: bool = True) -> None:
        del immediate, content


def _material_intents_nav() -> MaterialNavigator:
    nav = nv.Navigator.intents(
        initial_route=_ScreenIntent(depth=0),
        routes={_ScreenIntent: lambda intent: _Screen(depth=intent.depth)},
    )
    assert isinstance(nav, MaterialNavigator)
    return nav


def test_intents_navigator_defaults_to_material_composer() -> None:
    nav = _material_intents_nav()
    assert isinstance(nav._layer_composer, MaterialNavigationLayerComposer)  # type: ignore[attr-defined]


def test_widget_navigator_defaults_to_material_composer() -> None:
    nav = MaterialNavigator(_Screen(depth=0))
    assert isinstance(nav._layer_composer, MaterialNavigationLayerComposer)  # type: ignore[attr-defined]


def test_explicit_composer_is_respected() -> None:
    composer = MaterialNavigationLayerComposer()
    nav = MaterialNavigator(_Screen(depth=0), layer_composer=composer)
    assert nav._layer_composer is composer  # type: ignore[attr-defined]


@pytest.mark.skipif(not _HAS_SKIA, reason="skia backend not available")
def test_push_transition_pixels_vary_with_progress() -> None:
    from nuiitivet.rendering.skia import make_raster_surface

    width, height = 200, 160
    nav = _material_intents_nav()
    nv.Navigator.set_root(nav)
    nav.mount(_DummyApp())
    nav.layout(width, height)
    nav.push(_ScreenIntent(depth=1))
    nav.layout(width, height)

    assert nav._transition is not None  # type: ignore[attr-defined]

    def _pixel_hash(progress: float) -> str:
        nav._transition.progress = progress  # type: ignore[union-attr]
        surface = make_raster_surface(width, height)
        canvas = surface.getCanvas()
        canvas.clear(0xFFFFFFFF)
        nav.paint(canvas, 0, 0, width, height)
        data = surface.makeImageSnapshot().encodeToData()
        return hashlib.sha1(bytes(data)).hexdigest()

    hashes = {p: _pixel_hash(p) for p in (0.0, 0.5, 1.0)}
    # A rendered fade means each progress step produces distinct pixels.
    assert len(set(hashes.values())) == 3, f"transition did not animate: {hashes}"
