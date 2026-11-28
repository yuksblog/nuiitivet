from __future__ import annotations

import contextvars
import gc
import weakref

import pytest
from nuiitivet.observable import State, batch


class PlainModel:
    count = State(0)
    name = State("init")


def test_ownerless_state_immediate_notification():
    model = PlainModel()
    notifications = []

    obs_count = model.count
    obs_count.subscribe(lambda v: notifications.append(f"count:{v}"))

    model.count.value = 1
    assert notifications == ["count:1"]

    model.count.value = 2
    assert notifications == ["count:1", "count:2"]


def test_batch_defers_computed_recalculation():
    class Cart:
        price = State(100)
        quantity = State(2)

    cart = Cart()

    computations = 0

    def compute_total():
        nonlocal computations
        computations += 1
        return cart.price.value * cart.quantity.value

    total = State.compute(compute_total)

    assert total.value == 200
    assert computations == 1

    cart.price.value = 150
    assert total.value == 300
    assert computations == 2

    cart.quantity.value = 3
    assert total.value == 450
    assert computations == 3

    with batch():
        cart.price.value = 200
        assert total.value == 450
        assert computations == 3

        cart.quantity.value = 4
        assert total.value == 450
        assert computations == 3

    assert total.value == 800
    assert computations == 4


def test_nested_batch():
    class Model:
        val = State(0)

    m = Model()
    stats = {"computations": 0}

    def compute():
        stats["computations"] += 1
        return m.val.value

    computed = State.compute(compute)
    assert stats["computations"] == 1

    with batch():
        m.val.value = 1
        with batch():
            m.val.value = 2
            assert stats["computations"] == 1
        assert stats["computations"] == 1

        m.val.value = 3
        assert stats["computations"] == 1

    assert stats["computations"] == 2
    assert computed.value == 3


def test_batch_exception_safety():
    class Model:
        val = State(0)

    m = Model()

    try:
        with batch():
            m.val.value = 1
            raise ValueError("oops")
    except ValueError:
        pass

    with batch():
        m.val.value = 2

    assert m.val.value == 2


def test_multiple_computed_states():
    """Test multiple ComputedStates with dependencies."""

    class Model:
        a = State(1)
        b = State(2)

    m = Model()
    computations = {"c": 0, "d": 0, "e": 0}

    def compute_c():
        computations["c"] += 1
        return m.a.value + m.b.value

    def compute_d():
        computations["d"] += 1
        return m.a.value * 2

    def compute_e():
        computations["e"] += 1
        return m.a.value + m.b.value + 1

    c = State.compute(compute_c)
    d = State.compute(compute_d)
    e = State.compute(compute_e)

    assert computations == {"c": 1, "d": 1, "e": 1}

    m.a.value = 10
    assert computations == {"c": 2, "d": 2, "e": 2}

    m.b.value = 20
    assert computations == {"c": 3, "d": 2, "e": 3}

    with batch():
        m.a.value = 100
        m.b.value = 200
        assert computations == {"c": 3, "d": 2, "e": 3}

    assert computations == {"c": 4, "d": 3, "e": 4}
    assert c.value == 300
    assert d.value == 200
    assert e.value == 301


def test_computed_state_equality_check():
    """Test that ComputedState doesn't notify if value hasn't changed."""

    class Model:
        flag = State(True)

    m = Model()
    notifications = []

    def compute_constant():
        _ = m.flag.value
        return 42

    computed = State.compute(compute_constant)
    computed.subscribe(lambda v: notifications.append(v))

    assert computed.value == 42
    assert len(notifications) == 0

    m.flag.value = False
    assert len(notifications) == 0
    assert computed.value == 42


def test_batch_size_limit():
    """Test that batch detects potential infinite loops via size limit."""

    class Model:
        val = State(0)

    m = Model()

    computeds = []
    for i in range(1005):

        def make_compute(index):
            return lambda: m.val.value + index

        computeds.append(State.compute(make_compute(i)))

    with pytest.raises(RuntimeError, match="Batch computed queue size limit exceeded"):
        with batch():
            m.val.value = 1


def test_nested_batch_deep():
    """Test deeply nested batch contexts."""

    class Model:
        val = State(0)

    m = Model()
    computations = 0

    def compute():
        nonlocal computations
        computations += 1
        return m.val.value

    computed = State.compute(compute)
    assert computations == 1

    with batch():
        m.val.value = 1
        with batch():
            m.val.value = 2
            with batch():
                m.val.value = 3
                assert computations == 1
            assert computations == 1
        assert computations == 1

    assert computations == 2
    assert computed.value == 3


def test_batch_exception_no_flush():
    """Test that batch doesn't flush if exception occurs."""

    class Model:
        val = State(0)

    m = Model()
    computations = 0

    def compute():
        nonlocal computations
        computations += 1
        return m.val.value

    computed = State.compute(compute)
    assert computations == 1
    assert computed.value == 0

    try:
        with batch():
            m.val.value = 1
            assert computations == 1
            raise ValueError("error")
    except ValueError:
        pass

    assert computations == 1
    assert computed.value == 0

    assert m.val.value == 1


def test_a_context_copied_inside_a_batch_recomputes_at_once_after_the_exit():
    count = State(0)
    label = count.map(lambda n: f"count={n}")

    with batch():
        copied = contextvars.copy_context()

    copied.run(count.set, 1)

    assert label.value == "count=1"


def test_a_context_copied_inside_a_batch_keeps_no_state_it_writes_after_the_exit():
    with batch():
        copied = contextvars.copy_context()

    state = State(0)
    copied.run(state.set, 1)
    ref = weakref.ref(state)
    del state
    gc.collect()

    assert ref() is None


def test_a_batch_opened_in_a_copied_context_defers_nothing_for_another_copy():
    count = State(0)
    label = count.map(lambda n: f"count={n}")

    with batch():
        first = contextvars.copy_context()
        second = contextvars.copy_context()

    seen: list[str] = []

    def write_from_second_inside_a_batch_of_first() -> None:
        with batch():
            second.run(count.set, 1)
            seen.append(label.value)

    first.run(write_from_second_inside_a_batch_of_first)

    assert seen == ["count=1"]


def test_a_write_made_during_the_flush_is_deferred_to_the_same_flush():
    a = State(0)
    b = State(0)
    d = a.map(lambda v: v * 10)
    seen: list[tuple[int, int]] = []

    def compute_e() -> int:
        seen.append((b.value, d.value))
        return b.value + d.value

    e = State.compute(compute_e)
    d.subscribe(lambda v: b.set(v + 1))
    seen.clear()

    with batch():
        a.value = 1

    assert seen == [(11, 10)]
    assert e.value == 21
