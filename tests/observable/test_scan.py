"""``scan(fn, initial=...)`` — the operator for a value that depends on history.

Every other operator answers "what follows from the source's current value?".
``scan`` answers "what follows from all of them?", which is why these tests pin
what is folded and what is not: ``.value`` before the first emission, the order
the accumulator and the value reach ``fn``, and the construction-time value that
is deliberately left out.
"""

import gc
import time
import weakref

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.scanned import ScannedObservable
from nuiitivet.testing import HarnessClock


_WINDOW = 0.01


def _count(accumulated: int, _value: object) -> int:
    return accumulated + 1


class TestTheSeed:
    """``.value`` is defined from construction, and is exactly ``initial``."""

    def test_reports_initial_before_the_source_emits(self):
        source = Observable(5)

        total = source.scan(lambda acc, value: acc + value, initial=0)

        assert total.value == 0

    def test_the_construction_time_value_is_not_folded_in(self):
        """It never emitted, so counting it would count an emission that never happened."""
        source = Observable(5)

        counted = source.scan(_count, initial=0)

        assert counted.value == 0

        source.value = 6
        assert counted.value == 1

    def test_initial_is_required(self):
        source = Observable(1)

        with pytest.raises(TypeError):
            source.scan(_count)  # type: ignore[call-arg]

    def test_initial_is_keyword_only(self):
        source = Observable(1)

        with pytest.raises(TypeError):
            source.scan(_count, 0)  # type: ignore[misc]


class TestAccumulation:
    def test_the_accumulator_comes_first_and_the_value_second(self):
        source = Observable("a")
        joined = source.scan(lambda acc, value: f"{acc}{value}", initial="")

        source.value = "b"
        source.value = "c"

        assert joined.value == "bc"

    def test_every_emission_is_folded_and_published(self):
        source = Observable(0)
        total = source.scan(lambda acc, value: acc + value, initial=0)
        seen = []
        total.subscribe(seen.append)

        for value in (1, 2, 3):
            source.value = value

        assert seen == [1, 3, 6]
        assert total.value == 6

    def test_a_repeated_source_value_folds_once(self):
        """The source de-dupes before it notifies, and no wrapper second-guesses that."""
        source = Observable(0)
        counted = source.scan(_count, initial=0)

        source.value = 5
        source.value = 5

        assert counted.value == 1

    def test_a_fold_landing_on_the_same_accumulator_still_emits(self):
        """The fold ran, so the emission is real even where the value repeats."""
        source = Observable(0)
        capped = source.scan(lambda acc, value: max(acc, value), initial=0)
        seen = []
        capped.subscribe(seen.append)

        source.value = 3
        source.value = 1

        assert seen == [3, 3]

    def test_the_accumulator_may_be_a_different_type_from_the_source(self):
        source = Observable(0)
        history = source.scan(lambda acc, value: [*acc, value], initial=[])

        source.value = 1
        source.value = 2

        assert history.value == [1, 2]


class TestChaining:
    def test_scan_counts_the_emissions_of_a_debounced_source(
        self, nuiitivet_clock: HarnessClock
    ):
        """The case with no handler to hold an imperative counter."""
        source = Observable(0)
        debounced = source.debounce(_WINDOW)
        executed = debounced.scan(_count, initial=0)

        source.value = 1
        source.value = 2
        source.value = 3
        time.sleep(_WINDOW * 2)
        nuiitivet_clock.pump()

        assert source.value == 3
        assert executed.value == 1, "the thinned-out writes were counted"

    def test_scan_after_map(self):
        source = Observable(0)
        total = source.map(lambda value: value * 2).scan(lambda acc, value: acc + value, initial=0)

        source.value = 1
        source.value = 2

        assert total.value == 6

    def test_map_after_scan(self):
        source = Observable(0)
        label = source.scan(_count, initial=0).map(lambda n: f"{n}x")

        assert label.value == "0x"

        source.value = 1
        assert label.value == "1x"

    def test_scan_after_combine(self):
        price = Observable(100)
        qty = Observable(1)
        total = price.combine(qty).compute(lambda p, q: p * q)
        recomputes = total.scan(_count, initial=0)

        qty.value = 2
        price.value = 200

        assert recomputes.value == 2

    def test_scan_after_filter(self):
        source = Observable(0)
        passes = source.filter(lambda n: n % 2 == 0, initial=0).scan(_count, initial=0)

        source.value = 1
        source.value = 2
        source.value = 3
        source.value = 4

        assert passes.value == 2


class TestTheFoldIsNotADependency:
    """``fn`` is a pure function of the two values handed to it — nothing more."""

    def test_reading_an_observable_inside_fn_creates_no_edge(self):
        step = Observable(10)
        source = Observable(0)

        total = source.scan(lambda acc, _value: acc + step.value, initial=0)
        source.value = 1

        assert step._subs == [], "the fold's read was tracked as a dependency"
        assert total.value == 10

    def test_fn_does_not_register_with_an_enclosing_derivation(self):
        """Construction inside a ``compute`` must not leak the fold's reads to it."""
        step = Observable(10)
        source = Observable(0)
        held = []

        def compute_fn() -> int:
            total = source.scan(lambda acc, _value: acc + step.value, initial=0)
            held.append(total)
            return total.value

        computed = ComputedObservable(compute_fn)

        assert step not in computed._deps
        assert source not in computed._deps, "the source was registered instead of the wrapper"
        assert held[-1] in computed._deps


class TestLifetime:
    """Inherited from SourceSubscribingObservable — asserted, not reimplemented."""

    def test_the_source_does_not_hold_the_wrapper(self, collectable):
        source = Observable(0)
        wrapper = ScannedObservable(source, _count, initial=0)
        ref = weakref.ref(wrapper)
        assert len(source._subs) == 1

        del wrapper
        gc.collect()

        assert ref() is None
        assert source._subs == []

    def test_dispose_releases_the_source_and_stops_emission(self):
        source = Observable(0)
        wrapper = ScannedObservable(source, _count, initial=0)
        seen = []
        wrapper.subscribe(seen.append)

        wrapper.dispose()
        source.value = 5

        assert source._subs == []
        assert seen == []

    def test_dispose_is_idempotent(self):
        source = Observable(0)
        wrapper = ScannedObservable(source, _count, initial=0)

        wrapper.dispose()
        wrapper.dispose()

        assert source._subs == []

    def test_a_rebuilt_chain_starts_from_initial_again(self):
        """There is no re-seeding: the accumulator belongs to the observable."""
        source = Observable(0)
        counted = source.scan(_count, initial=0)

        source.value = 1
        assert counted.value == 1

        counted = source.scan(_count, initial=0)
        assert counted.value == 0

    def test_the_disposable_carries_the_chain(self, collectable):
        source = Observable(0)
        seen = []

        # The wrapper is never bound to a name, exactly as `self.bind(...)` leaves it.
        disposable = source.scan(_count, initial=0).subscribe(seen.append)
        gc.collect()

        source.value = 5

        assert seen == [1]
        disposable.dispose()


class TestBindingDirectlyIntoAWidget:
    """The headline rule — pass the observable in — must hold before the first fold."""

    @staticmethod
    def _screen(bound):
        from nuiitivet.layout.column import Column
        from nuiitivet.material.text import Text

        return lambda: Column(children=[Text(bound, key="readout")])

    def test_shows_the_seed_before_the_source_emits(self, nuiitivet_app):
        source = Observable(0)
        label = source.scan(_count, initial=0).map(lambda n: f"Executed: {n}")

        app = nuiitivet_app(self._screen(label), size=(800, 600))

        assert app.get(key="readout").text == "Executed: 0"

    def test_follows_the_accumulator(self, nuiitivet_app):
        source = Observable(0)
        label = source.scan(_count, initial=0).map(lambda n: f"Executed: {n}")

        app = nuiitivet_app(self._screen(label), size=(800, 600))

        source.value = 1
        app.settle()
        assert app.get(key="readout").text == "Executed: 1"

        source.value = 2
        app.settle()
        assert app.get(key="readout").text == "Executed: 2"
