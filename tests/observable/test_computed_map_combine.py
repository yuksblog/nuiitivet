"""Test ComputedState .map() and .combine() methods."""

from nuiitivet.observable import State


def test_computed_map():
    """Test that ComputedState supports .map()"""

    class Model:
        price = State(100)
        quantity = State(2)

    model = Model()

    # Create computed State
    subtotal = model.price.combine(model.quantity).compute(lambda p, q: p * q)

    # Chain .map() on computed
    formatted = subtotal.map(lambda st: f"¥{st:,}")

    # Check initial value
    assert formatted.value == "¥200"

    # Update and verify
    model.price.value = 150
    assert formatted.value == "¥300"

    model.quantity.value = 3
    assert formatted.value == "¥450"


def test_computed_combine():
    """Test that ComputedState supports .combine()"""

    class Model:
        a = State(10)
        b = State(20)
        c = State(30)

    model = Model()

    # Create computed State
    sum_ab = model.a.combine(model.b).compute(lambda a, b: a + b)

    # Combine computed with another State
    sum_abc = sum_ab.combine(model.c).compute(lambda ab, c: ab + c)

    # Check initial value
    assert sum_abc.value == 60  # 10 + 20 + 30

    # Update and verify
    model.a.value = 15
    assert sum_abc.value == 65  # 15 + 20 + 30

    model.c.value = 40
    assert sum_abc.value == 75  # 15 + 20 + 40


def test_computed_map_chain():
    """Test chaining multiple .map() on computed States"""

    class Model:
        value = State(5)

    model = Model()

    # Create computed and chain multiple maps
    computed = State.compute(lambda: model.value.value * 2)
    doubled = computed.map(lambda x: x * 2)
    formatted = doubled.map(lambda x: f"Result: {x}")

    # Check initial value
    assert formatted.value == "Result: 20"  # 5 * 2 * 2

    # Update and verify
    model.value.value = 10
    assert formatted.value == "Result: 40"  # 10 * 2 * 2
