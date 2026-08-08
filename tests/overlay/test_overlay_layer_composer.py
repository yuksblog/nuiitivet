from __future__ import annotations

from nuiitivet.layout.stack import Stack
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.overlay_visual_state import MaterialOverlayLayerComposer
from nuiitivet.modifiers.passthrough_pointer import PassthroughPointerBox
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

    dialog = BasicDialog(title="Title", message="Body")
    overlay.show(dialog, passthrough=True)

    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    # A pass-through entry needs no blocking layer, so the composer's output is
    # the layer verbatim.
    assert built is sentinel
    assert_overlay_single_composition_context(composer.contexts, expected_content=dialog)


def test_overlay_stacks_its_blocking_layer_under_the_composed_content() -> None:
    sentinel = _SentinelWidget()
    composer = RecordingOverlayComposer(sentinel)
    overlay = Overlay(layer_composer=composer)

    overlay.show(BasicDialog(title="Title"), dismiss_on_outside_tap=True)

    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    assert isinstance(built, Stack)
    layers = built.children_snapshot()
    assert len(layers) == 2
    assert layers[-1] is sentinel, "content must be last so it is hit-tested first"


def test_overlay_makes_the_composed_backdrop_click_through() -> None:
    """The backdrop is decoration; the core, not the composer, says so."""
    sentinel = _SentinelWidget()
    backdrop = _SentinelWidget()
    composer = RecordingOverlayComposer(sentinel, backdrop_widget=backdrop)
    overlay = Overlay(layer_composer=composer)

    overlay.show(BasicDialog(title="Title"), backdrop=True, dismiss_on_outside_tap=True)

    entry = next(iter(overlay._entry_to_route.keys()))
    layers = entry.build_widget().children_snapshot()

    # backdrop (click-through) -> blocker -> content
    assert len(layers) == 3
    assert isinstance(layers[0], PassthroughPointerBox)
    assert layers[0].children_snapshot()[0] is backdrop
    assert layers[-1] is sentinel

    # A composer that paints a backdrop cannot break outside-tap dismissal by
    # omission: the wrapper declines every hit regardless of what it paints.
    assert layers[0].hit_test(0, 0) is None


def test_overlay_composition_context_carries_visual_facts_only() -> None:
    """The core/composer boundary is paint-only; input axes never cross it."""
    composer = RecordingOverlayComposer(_SentinelWidget())
    overlay = Overlay(layer_composer=composer)

    overlay.show(BasicDialog(title="Title"), backdrop=True, dismiss_on_outside_tap=True)

    context = composer.contexts[0]
    assert context.backdrop is True
    for removed in ("passthrough", "barrier_color", "barrier_dismissible", "on_barrier_click"):
        assert not hasattr(context, removed), f"{removed} must not cross the composer boundary"


def test_material_overlay_uses_material_layer_composer() -> None:
    overlay = MaterialOverlay(intents={})
    assert isinstance(overlay._layer_composer, MaterialOverlayLayerComposer)
