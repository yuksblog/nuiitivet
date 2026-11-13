"""Phase 1 State enhancements tests."""

from nuiitivet.observable import ComputedState, State


def test_dispatch_is_on_by_default():
    """A State marshals cross-thread writes unless told not to."""

    class Model:
        value = State(0)
        internal = State(0, dispatch=False)

    model = Model()

    assert model.value._dispatch_to_ui is True
    assert model.internal._dispatch_to_ui is False


def test_map_basic():
    """Test map transformation."""

    class Model:
        age = State(20)

    model = Model()
    is_adult = model.age.map(lambda x: x >= 18)

    # Check initial value
    assert is_adult.value is True

    # Change value
    model.age.value = 15
    assert is_adult.value is False

    model.age.value = 21
    assert is_adult.value is True


def test_computed_state_basic():
    """Test ComputedState with automatic dependency tracking."""

    class Model:
        price = State(100)
        quantity = State(2)

    model = Model()

    # Create computed with automatic tracking
    total = ComputedState(lambda: model.price.value * model.quantity.value)

    # Check initial value
    assert total.value == 200

    # Change price
    model.price.value = 150
    assert total.value == 300

    # Change quantity
    model.quantity.value = 3
    assert total.value == 450


def test_computed_with_subscription():
    """Test ComputedState notifications."""

    class Model:
        x = State(10)

    model = Model()

    computed = ComputedState(lambda: model.x.value * 2)

    values = []
    computed.subscribe(lambda v: values.append(v))

    model.x.value = 20
    model.x.value = 30

    # Should have received notifications
    assert 40 in values
    assert 60 in values


def test_map_inherits_the_dispatch_opt_out():
    """A derivation of a logic-layer State stays logic-layer.

    The opt-out is what has to propagate: re-enabling dispatch on the mapped
    value would start coalescing values the source was declared to deliver in
    full.
    """

    class Model:
        bound = State(10)
        internal = State(10, dispatch=False)

    model = Model()

    assert model.bound.map(lambda x: x * 2)._dispatch_to_ui is True
    assert model.internal.map(lambda x: x * 2)._dispatch_to_ui is False


def test_computed_dynamic_dependencies():
    """Test dynamic dependency tracking with conditional logic."""

    class Model:
        flag = State(True)
        a = State(10)
        b = State(20)

    model = Model()

    # Conditional computed
    result = ComputedState(lambda: model.a.value if model.flag.value else model.b.value)

    # Initially depends on flag and a
    assert result.value == 10

    # Change a (should update)
    model.a.value = 15
    assert result.value == 15

    # Switch to b
    model.flag.value = False
    assert result.value == 20

    # Change b (should update)
    model.b.value = 25
    assert result.value == 25

    # Change a (should NOT update - no longer dependent)
    old_value = result.value
    model.a.value = 100
    assert result.value == old_value  # Still 25


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
