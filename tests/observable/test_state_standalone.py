from nuiitivet.observable import State


def test_state_standalone_init():
    """Test State when instantiated inside a function or method (standalone)."""
    obs = State(10)

    assert obs.value == 10

    # Test updating value
    obs.value = 20
    assert obs.value == 20

    # Test subscription
    param = []
    obs.subscribe(lambda v: param.append(v))

    obs.value = 30
    assert param == [30]


def test_state_instance_attribute():
    """Test State when assigned to an instance attribute in __init__."""

    class MyComponent:
        def __init__(self):
            self.count = State(0)

    c = MyComponent()

    # Should be able to access .value directly on the State instance
    assert c.count.value == 0

    c.count.value = 1
    assert c.count.value == 1

    # Verify it's actually a State instance, not the wrapper logic from descriptor
    assert isinstance(c.count, State)


def test_state_descriptor_behavior_still_works():
    """Test that existing descriptor functionality allows works as expected."""

    class MyComponent:
        count = State(100)

    c1 = MyComponent()
    c2 = MyComponent()

    # Each instance should have independent values
    assert c1.count.value == 100
    assert c2.count.value == 100

    c1.count.value = 101
    assert c1.count.value == 101
    assert c2.count.value == 100  # Should not change

    # Descriptor access returns the inner _StateValue, not the State instance itself
    # (Note: depending on implementation, State is now a _StateValue subclass,
    # but the descriptor protocol returns the *instance-specific* storage)

    # Let's verify details if needed, but mainly behavior is what matters.
    # The 'count' attribute on class is the descriptor (State instance).
    assert isinstance(MyComponent.count, State)

    # The 'count' attribute on instance is the _StateValue (storage)
    # The _ensure method returns a _StateValue.
    # Since State now inherits _StateValue, checking types might be tricky if we don't check identity.
    # The key is that c1.count is NOT MyComponent.count
    assert c1.count is not MyComponent.count
    assert c1.count is not c2.count
