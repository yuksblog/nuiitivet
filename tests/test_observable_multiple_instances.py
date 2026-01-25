"""Test that Observable works correctly with multiple instances."""

from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget


def test_observable_multiple_instances():
    """Each instance should have independent Observable values."""

    class CounterWidget(ComposableWidget):
        count = Observable(0)

        def build(self):
            return None

    # Create multiple instances
    counter1 = CounterWidget()
    counter2 = CounterWidget()
    counter3 = CounterWidget()

    # Each instance should start with default value (0)
    assert counter1.count.value == 0
    assert counter2.count.value == 0
    assert counter3.count.value == 0

    # Modify counter1
    counter1.count.value = 10
    assert counter1.count.value == 10
    assert counter2.count.value == 0  # counter2 should be unaffected
    assert counter3.count.value == 0  # counter3 should be unaffected

    # Modify counter2
    counter2.count.value = 20
    assert counter1.count.value == 10  # counter1 should remain unchanged
    assert counter2.count.value == 20
    assert counter3.count.value == 0  # counter3 should be unaffected

    # Modify counter3
    counter3.count.value = 30
    assert counter1.count.value == 10
    assert counter2.count.value == 20
    assert counter3.count.value == 30


def test_observable_subscriptions_per_instance():
    """Subscriptions should be independent per instance."""

    class CounterWidget(ComposableWidget):
        count = Observable(0)

        def build(self):
            return None

    counter1 = CounterWidget()
    counter2 = CounterWidget()

    # Track notifications for each counter
    notifications1 = []
    notifications2 = []

    counter1.count.subscribe(lambda v: notifications1.append(v))
    counter2.count.subscribe(lambda v: notifications2.append(v))

    # Update counter1
    counter1.count.value = 10
    assert notifications1 == [10]
    assert notifications2 == []  # counter2 subscribers should not be notified

    # Update counter2
    counter2.count.value = 20
    assert notifications1 == [10]  # counter1 subscribers should not be notified again
    assert notifications2 == [20]


def test_observable_in_row_builder_scenario():
    """Test Observable with Row.builder() scenario - multiple instances from same class."""

    class ItemWidget(ComposableWidget):
        value = Observable("")

        def __init__(self, initial: str):
            super().__init__()
            self.value.value = initial

        def build(self):
            return None

    # Simulate creating multiple widgets (like Row.builder would do)
    items = [ItemWidget(f"Item {i}") for i in range(5)]

    # Verify each instance has independent value
    for i, item in enumerate(items):
        assert item.value.value == f"Item {i}"

    # Modify one instance
    items[2].value.value = "Modified"

    # Verify only that instance changed
    assert items[0].value.value == "Item 0"
    assert items[1].value.value == "Item 1"
    assert items[2].value.value == "Modified"
    assert items[3].value.value == "Item 3"
    assert items[4].value.value == "Item 4"
