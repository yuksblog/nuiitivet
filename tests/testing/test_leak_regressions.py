"""Regression tests for the leaks the leak check found in our own widgets.

Each of these passed against a widget that was leaking, because nothing asserted
on it -- which is the whole argument for the check. They assert on the
observable's subscriber list rather than on behaviour: the leak *is* the
lingering reference, and every one of these widgets still behaves correctly
while leaking.
"""

from __future__ import annotations

from nuiitivet.layout.deck import Deck
from nuiitivet.material.selection_controls import Checkbox, RadioButton, Switch
from nuiitivet.material.text_fields import TextField
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def test_toggleable_releases_its_value_source_on_unmount():
    """``Toggleable.__init__`` subscribed bare, so every toggleable widget held
    its value source forever.

    ``Checkbox`` and ``Switch`` take an ``Observable`` the app owns, which is the
    outlives-the-widget case; ``RadioButton`` is driven by its group and only
    ever subscribes to its own descriptor observable, so it is covered by the
    same fix through ``Toggleable`` and asserted separately below.
    """
    for widget_type in (Checkbox, Switch):
        source = _ObservableValue(False)
        widget = widget_type(checked=source)
        with mount(widget) as host:
            host.layout(100, 100)
            assert source._subs, f"{widget_type.__name__} never subscribed"
        assert source._subs == [], f"{widget_type.__name__} leaked its subscription"


def test_radio_button_releases_its_internal_state_on_unmount():
    radio = RadioButton(value="a")
    with mount(radio) as host:
        host.layout(100, 100)
        state = radio._get_state_obj()
        assert state._subs
    assert state._subs == []


def test_toggleable_follows_the_observable_again_after_remount():
    source = _ObservableValue(False)
    box = Checkbox(checked=source)
    with mount(box) as host:
        host.layout(100, 100)
    source.value = True
    with mount(box) as host:
        host.layout(100, 100)
        assert box.state.checked is True  # picked up while it was detached
        source.value = False
        assert box.state.checked is False


def test_text_field_releases_its_animation_subscriptions_on_unmount():
    """Four bare ``Animatable.subscribe`` calls in ``__init__``. A running
    Animatable is held by the clock, so these kept the field alive too."""
    field = TextField(label="Name")
    with mount(field) as host:
        host.layout(200, 80)
        animatables = (
            field._label_progress,
            field._anim_indicator_width,
            field._anim_indicator_color,
            field._anim_label_color,
        )
        assert all(a._value._subs for a in animatables)
    assert all(a._value._subs == [] for a in animatables)


def test_text_field_repaints_on_animation_again_after_remount():
    field = TextField(label="Name")
    with mount(field) as host:
        host.layout(200, 80)
    with mount(field) as host:
        host.layout(200, 80)
        before = host.invalidate_count
        field._label_progress._value.value = 0.5
        assert host.invalidate_count > before


def test_deck_releases_the_index_observable_on_unmount():
    """``Deck.dispose()`` did this, and nothing ever called it: ``Widget`` has no
    dispose hook."""
    index = _ObservableValue(0)
    deck = Deck(children=[Text("A"), Text("B")], index=index)
    with mount(deck) as host:
        host.layout(200, 100)
        assert index._subs
    assert index._subs == []
