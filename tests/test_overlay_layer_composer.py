from __future__ import annotations

from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.overlay_visual_state import MaterialOverlayLayerComposer
from nuiitivet.overlay import Overlay
from nuiitivet.widgeting.widget import Widget
from tests.helpers.layer_composer import RecordingOverlayComposer, assert_overlay_single_composition_context


class _SentinelWidget(Widget):
    def build(self) -> Widget:
        return self


def test_overlay_delegates_layer_composition_to_injected_composer() -> None:
    sentinel = _SentinelWidget()
    composer = RecordingOverlayComposer(sentinel)
    overlay = Overlay(layer_composer=composer)

    dialog = AlertDialog(title="Title", message="Body")
    overlay.show(dialog, dismiss_on_outside_tap=False)

    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    assert built is sentinel
    assert_overlay_single_composition_context(composer.contexts, expected_content=dialog)


def test_material_overlay_uses_material_layer_composer() -> None:
    overlay = MaterialOverlay(intents={})
    assert isinstance(overlay._layer_composer, MaterialOverlayLayerComposer)
