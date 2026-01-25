from __future__ import annotations

import pytest
from nuiitivet.observable import Observable, batch


class PlainModel:
    count = Observable(0)
    name = Observable("init")


def test_ownerless_observable_immediate_notification():
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
        price = Observable(100)
        quantity = Observable(2)

    cart = Cart()

    computations = 0

    def compute_total():
        nonlocal computations
        computations += 1
        return cart.price.value * cart.quantity.value

    total = Observable.compute(compute_total)

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
        val = Observable(0)

    m = Model()
    stats = {"computations": 0}

    def compute():
        stats["computations"] += 1
        return m.val.value

    computed = Observable.compute(compute)
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
        val = Observable(0)

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


def test_multiple_computed_observables():
    """Test multiple ComputedObservables with dependencies."""

    class Model:
        a = Observable(1)
        b = Observable(2)

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

    c = Observable.compute(compute_c)
    d = Observable.compute(compute_d)
    e = Observable.compute(compute_e)

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


def test_computed_observable_equality_check():
    """Test that ComputedObservable doesn't notify if value hasn't changed."""

    class Model:
        flag = Observable(True)

    m = Model()
    notifications = []

    def compute_constant():
        _ = m.flag.value
        return 42

    computed = Observable.compute(compute_constant)
    computed.subscribe(lambda v: notifications.append(v))

    assert computed.value == 42
    assert len(notifications) == 0

    m.flag.value = False
    assert len(notifications) == 0
    assert computed.value == 42


def test_batch_size_limit():
    """Test that batch detects potential infinite loops via size limit."""

    class Model:
        val = Observable(0)

    m = Model()

    computeds = []
    for i in range(1005):

        def make_compute(index):
            return lambda: m.val.value + index

        computeds.append(Observable.compute(make_compute(i)))

    with pytest.raises(RuntimeError, match="Batch computed queue size limit exceeded"):
        with batch():
            m.val.value = 1


def test_nested_batch_deep():
    """Test deeply nested batch contexts."""

    class Model:
        val = Observable(0)

    m = Model()
    computations = 0

    def compute():
        nonlocal computations
        computations += 1
        return m.val.value

    computed = Observable.compute(compute)
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
        val = Observable(0)

    m = Model()
    computations = 0

    def compute():
        nonlocal computations
        computations += 1
        return m.val.value

    computed = Observable.compute(compute)
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
