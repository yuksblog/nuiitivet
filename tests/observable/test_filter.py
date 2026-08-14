"""``filter(pred, initial=...)`` — the operator OBSERVABLE.md §2 once rejected.

The objection was that a filtered observable has no defined ``.value`` before
anything passes. The seed answers it, so these tests pin what ``.value`` reports
at every point: before the first pass, after one, and after a value the predicate
rejected.
"""

import gc
import weakref
from typing import Optional

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.filtered import FilteredObservable


def _is_positive(value: int) -> bool:
    return value > 0


class TestTheSeed:
    """``.value`` is defined from construction — that is the whole point."""

    def test_reports_initial_when_the_source_does_not_pass(self):
        source = Observable(-5)

        filtered = source.filter(_is_positive, initial=0)

        assert filtered.value == 0

    def test_reports_the_source_when_it_already_passes(self):
        """``initial`` means "nothing has passed", not "nothing has arrived"."""
        source = Observable(7)

        filtered = source.filter(_is_positive, initial=0)

        assert filtered.value == 7

    def test_initial_is_required(self):
        source = Observable(1)

        with pytest.raises(TypeError):
            source.filter(_is_positive)  # type: ignore[call-arg]

    def test_initial_is_keyword_only(self):
        source = Observable(1)

        with pytest.raises(TypeError):
            source.filter(_is_positive, 0)  # type: ignore[misc]


class TestEmission:
    def test_a_passing_value_is_emitted_and_held(self):
        source = Observable(0)
        filtered = source.filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        source.value = 3

        assert seen == [3]
        assert filtered.value == 3

    def test_a_rejected_value_emits_nothing_and_changes_nothing(self):
        source = Observable(0)
        filtered = source.filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        source.value = 3
        source.value = -1

        assert seen == [3], "the rejected value was published"
        assert filtered.value == 3, "the rejected value became .value"

    def test_only_the_passing_values_come_through_in_order(self):
        source = Observable(0)
        filtered = source.filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        for value in (1, -1, 2, -2, 3):
            source.value = value

        assert seen == [1, 2, 3]

    def test_a_repeated_passing_value_is_not_re_emitted(self):
        """No equality check of our own: the source already de-duped it."""
        source = Observable(0)
        filtered = source.filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        source.value = 5
        source.value = 5

        assert seen == [5]


class TestNoneIsAnOrdinaryValue:
    """"Nothing has passed" is carried by the seed, never by ``None``."""

    def test_none_can_pass_the_predicate(self):
        source: Observable[Optional[str]] = Observable("a")
        filtered = source.filter(lambda v: v is None or v.startswith("k"), initial="seed")
        seen = []
        filtered.subscribe(seen.append)

        source.value = None

        assert seen == [None]
        assert filtered.value is None

    def test_a_none_seed_survives_until_something_passes(self):
        source: Observable[Optional[int]] = Observable(1)
        filtered = source.filter(lambda v: v is not None and v > 10, initial=None)

        assert filtered.value is None

        source.value = 2
        assert filtered.value is None

        source.value = 42
        assert filtered.value == 42

    def test_a_source_holding_none_is_tested_at_construction(self):
        source: Observable[Optional[str]] = Observable(None)
        filtered = source.filter(lambda v: v is None, initial="seed")

        assert filtered.value is None


class TestChaining:
    def test_map_after_filter_sees_only_passing_values(self):
        source = Observable(0)
        doubled = source.filter(_is_positive, initial=0).map(lambda v: v * 2)

        assert doubled.value == 0

        source.value = -4
        assert doubled.value == 0, "a rejected value reached the map"

        source.value = 4
        assert doubled.value == 8

    def test_filter_after_map(self):
        source = Observable(0)
        filtered = source.map(lambda v: v * 2).filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        source.value = -1
        source.value = 3

        assert seen == [6]
        assert filtered.value == 6

    def test_filter_after_combine(self):
        price = Observable(100)
        qty = Observable(0)
        total = price.combine(qty).compute(lambda p, q: p * q)
        filtered = total.filter(_is_positive, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        qty.value = 2

        assert seen == [200]
        assert filtered.value == 200

    def test_a_filtered_observable_can_be_filtered_again(self):
        source = Observable(0)
        filtered = source.filter(_is_positive, initial=0).map(lambda v: v).filter(lambda v: v % 2 == 0, initial=0)
        seen = []
        filtered.subscribe(seen.append)

        source.value = 3
        source.value = 4

        assert seen == [4]


class TestPredicateIsNotADependency:
    """``pred`` is a pure function of the value handed to it — nothing more."""

    def test_reading_an_observable_inside_pred_creates_no_edge(self):
        threshold = Observable(10)
        source = Observable(0)

        filtered = source.filter(lambda v: v > threshold.value, initial=-1)

        assert threshold._subs == [], "pred's read was tracked as a dependency"
        assert filtered.value == -1

    def test_pred_does_not_register_with_an_enclosing_derivation(self):
        """Construction inside a ``compute`` must not leak pred's reads to it."""
        threshold = Observable(10)
        source = Observable(0)
        held = []

        def compute_fn() -> int:
            filtered = source.filter(lambda v: v > threshold.value, initial=-1)
            held.append(filtered)
            return filtered.value

        computed = ComputedObservable(compute_fn)

        assert threshold not in computed._deps
        assert source not in computed._deps, "the source was registered instead of the wrapper"
        assert held[-1] in computed._deps


class TestLifetime:
    """Inherited from SourceSubscribingObservable — asserted, not reimplemented."""

    def test_the_source_does_not_hold_the_wrapper(self, collectable):
        source = Observable(0)
        wrapper = FilteredObservable(source, _is_positive, initial=0)
        ref = weakref.ref(wrapper)
        assert len(source._subs) == 1

        del wrapper
        gc.collect()

        assert ref() is None
        assert source._subs == []

    def test_dispose_releases_the_source_and_stops_emission(self):
        source = Observable(0)
        wrapper = FilteredObservable(source, _is_positive, initial=0)
        seen = []
        wrapper.subscribe(seen.append)

        wrapper.dispose()
        source.value = 5

        assert source._subs == []
        assert seen == []

    def test_dispose_is_idempotent(self):
        source = Observable(0)
        wrapper = FilteredObservable(source, _is_positive, initial=0)

        wrapper.dispose()
        wrapper.dispose()

        assert source._subs == []

    def test_the_disposable_carries_the_chain(self, collectable):
        source = Observable(0)
        seen = []

        # The wrapper is never bound to a name, exactly as `self.bind(...)` leaves it.
        disposable = source.filter(_is_positive, initial=0).subscribe(seen.append)
        gc.collect()

        source.value = 5

        assert seen == [5]
        disposable.dispose()


class TestBindingDirectlyIntoAWidget:
    """The headline rule — pass the observable in — must hold before the first pass."""

    @staticmethod
    def _screen(bound):
        from nuiitivet.layout.column import Column
        from nuiitivet.material.text import Text
        from nuiitivet.modifiers.keyed import keyed

        return lambda: Column(children=[Text(bound).modifier(keyed("readout"))])

    def test_shows_the_seed_before_anything_passes(self, nuiitivet_app):
        source = Observable("")
        filtered = source.filter(lambda v: len(v) >= 3, initial="(none)")

        source.value = "ab"  # rejected, and the widget must not show it

        app = nuiitivet_app(self._screen(filtered), size=(800, 600))
        assert app.get(key="readout").text == "(none)", "a rejected value reached the widget"

    def test_follows_the_first_passing_value(self, nuiitivet_app):
        source = Observable("")
        filtered = source.filter(lambda v: len(v) >= 3, initial="(none)")

        app = nuiitivet_app(self._screen(filtered), size=(800, 600))

        source.value = "abc"
        app.settle()
        assert app.get(key="readout").text == "abc"

        source.value = "ab"
        app.settle()
        assert app.get(key="readout").text == "abc", "the rejected value reached the widget"
