"""Test Deck widget."""

from enum import IntEnum

from nuiitivet.layout.deck import Deck
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.observable.value import _ObservableValue


def test_deck_basic_creation():
    """Deck should create with default index."""
    deck = Deck(children=[Text("A"), Text("B"), Text("C")])
    assert deck.current_index == 0
    assert len(deck.children_snapshot()) == 3


def test_deck_with_explicit_index():
    """Deck should accept explicit index."""
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=1)
    assert deck.current_index == 1


def test_deck_set_index():
    """Deck should allow changing index with set_index."""
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=0)
    assert deck.current_index == 0

    deck.set_index(2)
    assert deck.current_index == 2


def test_deck_index_validation():
    """Deck should clamp invalid indices."""
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=10)
    assert deck.current_index == 2  # Clamped to max valid index

    deck2 = Deck(children=[Text("A"), Text("B"), Text("C")], index=-5)
    assert deck2.current_index == 0  # Clamped to min valid index


def test_deck_empty_children():
    """Deck should handle empty children list."""
    deck = Deck(children=[])
    assert deck.current_index == 0
    assert len(deck.children_snapshot()) == 0


def test_deck_single_child():
    """Deck should work with single child."""
    deck = Deck(children=[Text("A")])
    assert deck.current_index == 0
    assert len(deck.children_snapshot()) == 1


def test_deck_preferred_size_from_selected():
    """Deck preferred_size should come from selected child."""
    text_a = Text("Short")
    text_b = Text("Much longer text for sizing")
    deck = Deck(children=[text_a, text_b], index=0)

    size_0 = deck.preferred_size()
    deck.set_index(1)
    size_1 = deck.preferred_size()

    # Different children should have different sizes
    assert size_0 != size_1


def test_deck_with_padding():
    """Deck should respect padding."""
    deck = Deck(children=[Text("A")], padding=10)
    assert deck.padding == (10, 10, 10, 10)

    w, h = deck.preferred_size()
    deck_no_pad = Deck(children=[Text("A")], padding=0)
    w0, h0 = deck_no_pad.preferred_size()

    assert w == w0 + 20
    assert h == h0 + 20


def test_deck_with_observable_index():
    """Deck should work with Observable index."""
    index_obs = _ObservableValue(0)
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=index_obs)

    assert deck.current_index == 0

    # Change observable value
    index_obs.value = 2
    assert deck.current_index == 2


def test_deck_observable_subscription():
    """Deck should subscribe to Observable index changes."""
    index_obs = _ObservableValue(1)
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=index_obs)

    assert deck.current_index == 1

    # Changing observable should trigger update
    index_obs.value = 0
    assert deck.current_index == 0

    index_obs.value = 2
    assert deck.current_index == 2


def test_deck_observable_validation():
    """Deck should validate Observable index changes."""
    index_obs = _ObservableValue(0)
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=index_obs)

    # Set invalid index via observable
    index_obs.value = 10
    assert deck.current_index == 2  # Clamped to max

    index_obs.value = -5
    assert deck.current_index == 0  # Clamped to min


def test_deck_observable_cannot_set_index():
    """Deck should prevent set_index when using Observable."""
    index_obs = _ObservableValue(0)
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=index_obs)

    try:
        deck.set_index(1)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Observable" in str(e)


def test_deck_with_int_enum():
    """Deck should work with IntEnum index."""

    class Section(IntEnum):
        HOME = 0
        SEARCH = 1
        PROFILE = 2

    index_obs = _ObservableValue(Section.HOME)
    deck = Deck(children=[Text("Home"), Text("Search"), Text("Profile")], index=index_obs)

    assert deck.current_index == 0

    index_obs.value = Section.SEARCH
    assert deck.current_index == 1

    index_obs.value = Section.PROFILE
    assert deck.current_index == 2


def test_deck_layout_all_children():
    """Deck should layout all children (to preserve state)."""
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=0)

    # Layout the widget
    deck.layout(200, 200)

    # All children should be measured (have non-zero size)
    children = deck.children_snapshot()
    for child in children:
        w, h = child.preferred_size()
        assert w > 0
        assert h > 0


def test_deck_paint_only_selected():
    """Deck should only paint selected child."""
    # This is more of an integration test - verify that paint()
    # only calls paint on the selected child
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=1)

    # We can't easily mock canvas in unit tests, but we verify
    # that the selected index is correct
    assert deck.current_index == 1

    deck.set_index(2)
    assert deck.current_index == 2


def test_deck_dispose_cleanup():
    """Deck should clean up Observable subscription on dispose."""
    index_obs = _ObservableValue(0)
    deck = Deck(children=[Text("A"), Text("B"), Text("C")], index=index_obs)

    # Should have subscription
    assert deck._index_subscription is not None

    # Dispose should clean up
    deck.dispose()
    assert deck._index_subscription is None
