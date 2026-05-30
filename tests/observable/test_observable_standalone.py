from nuiitivet.observable import Observable


def test_observable_standalone_init():
    """Test Observable when instantiated inside a function or method (standalone)."""
    obs = Observable(10)

    assert obs.value == 10

    # Test updating value
    obs.value = 20
    assert obs.value == 20

    # Test subscription
    param = []
    obs.subscribe(lambda v: param.append(v))

    obs.value = 30
    assert param == [30]


def test_observable_instance_attribute():
    """Test Observable when assigned to an instance attribute in __init__."""

    class MyComponent:
        def __init__(self):
            self.count = Observable(0)

    c = MyComponent()

    # Should be able to access .value directly on the observable instance
    assert c.count.value == 0

    c.count.value = 1
    assert c.count.value == 1

    # Verify it's actually an Observable instance, not the wrapper logic from descriptor
    assert isinstance(c.count, Observable)


def test_observable_descriptor_behavior_still_works():
    """Test that existing descriptor functionality allows works as expected."""

    class MyComponent:
        count = Observable(100)

    c1 = MyComponent()
    c2 = MyComponent()

    # Each instance should have independent values
    assert c1.count.value == 100
    assert c2.count.value == 100

    c1.count.value = 101
    assert c1.count.value == 101
    assert c2.count.value == 100  # Should not change

    # Descriptor access returns the inner _ObservableValue, not the Observable instance itself
    # (Note: depending on implementation, Observable is now an _ObservableValue subclass,
    # but the descriptor protocol returns the *instance-specific* storage)

    # Let's verify details if needed, but mainly behavior is what matters.
    # The 'count' attribute on class is the descriptor (Observable instance).
    assert isinstance(MyComponent.count, Observable)

    # The 'count' attribute on instance is the _ObservableValue (storage)
    # The _ensure method returns an _ObservableValue.
    # Since Observable now inherits _ObservableValue, checking types might be tricky if we don't check identity.
    # The key is that c1.count is NOT MyComponent.count
    assert c1.count is not MyComponent.count
    assert c1.count is not c2.count
