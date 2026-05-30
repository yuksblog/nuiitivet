"""Phase 1 Observable enhancements tests."""

from nuiitivet.observable import ComputedObservable, Observable


def test_dispatch_to_ui_basic():
    """Test basic dispatch_to_ui functionality."""

    class Model:
        value = Observable(0)

    model = Model()
    obs = model.value.dispatch_to_ui()

    # Should return self for chaining
    assert obs is model.value

    # Verify flag is set
    assert model.value._dispatch_to_ui is True


def test_map_basic():
    """Test map transformation."""

    class Model:
        age = Observable(20)

    model = Model()
    is_adult = model.age.map(lambda x: x >= 18)

    # Check initial value
    assert is_adult.value is True

    # Change value
    model.age.value = 15
    assert is_adult.value is False

    model.age.value = 21
    assert is_adult.value is True


def test_computed_observable_basic():
    """Test ComputedObservable with automatic dependency tracking."""

    class Model:
        price = Observable(100)
        quantity = Observable(2)

    model = Model()

    # Create computed with automatic tracking
    total = ComputedObservable(lambda: model.price.value * model.quantity.value)

    # Check initial value
    assert total.value == 200

    # Change price
    model.price.value = 150
    assert total.value == 300

    # Change quantity
    model.quantity.value = 3
    assert total.value == 450


def test_computed_with_subscription():
    """Test ComputedObservable notifications."""

    class Model:
        x = Observable(10)

    model = Model()

    computed = ComputedObservable(lambda: model.x.value * 2)

    values = []
    computed.subscribe(lambda v: values.append(v))

    model.x.value = 20
    model.x.value = 30

    # Should have received notifications
    assert 40 in values
    assert 60 in values


def test_map_dispatch_inheritance():
    """Test that map inherits dispatch_to_ui from source."""

    class Model:
        value = Observable(10)

    model = Model()

    # Enable dispatch on source
    model.value.dispatch_to_ui()

    # Map should inherit dispatch flag
    doubled = model.value.map(lambda x: x * 2)
    assert doubled._dispatch_to_ui is True


def test_computed_dynamic_dependencies():
    """Test dynamic dependency tracking with conditional logic."""

    class Model:
        flag = Observable(True)
        a = Observable(10)
        b = Observable(20)

    model = Model()

    # Conditional computed
    result = ComputedObservable(lambda: model.a.value if model.flag.value else model.b.value)

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
