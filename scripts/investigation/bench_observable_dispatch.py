"""Benchmark the per-write cost of UI-thread dispatch (issue #538).

Marshalling a cross-thread ``Observable`` write onto the UI thread is now the
default. Every write therefore pays a thread test, where before ``dispatch_to_ui``
was opt-in and the flag short-circuited the test away for almost everyone.

This measures what that costs on the UI thread — the hot path, since a write
already on the UI thread is applied inline and the test is all it adds. Three
arms:

* ``opt-out``:     ``Observable(0, dispatch=False)`` — the flag short-circuits,
                   which is what every observable used to do.
* ``default``:     ``Observable(0)`` as shipped — ``is_ui_thread()``, a call.
* ``inline ident``: the same comparison written out at the call site, skipping
                   the function call. Not what ships, and measurably **not**
                   worth shipping: reaching across modules for
                   ``_ui_thread_ident`` costs more than the call it saves, so
                   the single definition of "the UI thread" is free.

Arms are interleaved round-robin so thermal drift hits all of them equally, and
the minimum of each is reported.

Run:  python scripts/investigation/bench_observable_dispatch.py [--writes N] [--rounds N]
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import timeit
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from nuiitivet.observable import runtime  # noqa: E402
from nuiitivet.observable.value import _ObservableValue  # noqa: E402
from nuiitivet.runtime import threading as nv_threading  # noqa: E402


class _InlineIdent(_ObservableValue):
    """``_ObservableValue`` with the UI-thread test inlined at the call site."""

    @property
    def value(self):
        return _ObservableValue.value.fget(self)

    @value.setter
    def value(self, v):
        if self._dispatch_to_ui and threading.get_ident() != nv_threading._ui_thread_ident:
            with self._lock:
                self._pending_value = v
                if not self._is_scheduled:
                    self._is_scheduled = True
                    runtime.clock.schedule_once(self._process_pending_update, 0)
            return
        self._apply(v)


def _build(cls, subscribers: int, dispatch: bool) -> _ObservableValue:
    obs = cls(0, dispatch=dispatch)
    for _ in range(subscribers):
        obs.subscribe(lambda v: None)
    return obs


def _measure(subscribers: int, writes: int, rounds: int) -> None:
    arms = {
        "opt-out (dispatch=False)": _build(_ObservableValue, subscribers, False),
        "default (is_ui_thread())": _build(_ObservableValue, subscribers, True),
        "inline ident (not shipped)": _build(_InlineIdent, subscribers, True),
    }
    # Distinct counters so no arm reuses another's values and hits the
    # equality short-circuit in ``_is_equal``.
    counters = {name: iter(range(writes * (rounds + 2))) for name in arms}
    times: Dict[str, List[float]] = {name: [] for name in arms}

    for _ in range(rounds):
        for name, obs in arms.items():
            times[name].append(
                timeit.timeit(
                    "o.value = next(c)",
                    globals={"o": obs, "c": counters[name], "next": next},
                    number=writes,
                )
            )

    baseline = min(times["opt-out (dispatch=False)"]) / writes * 1e9
    print(f"  subscribers={subscribers}")
    for name in arms:
        ns = min(times[name]) / writes * 1e9
        delta = ns - baseline
        pct = (ns / baseline - 1) * 100
        print(f"    {name:28s} {ns:7.1f} ns/write   {delta:+7.1f} ns  ({pct:+5.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writes", type=int, default=200_000, help="writes per timed round")
    parser.add_argument("--rounds", type=int, default=9, help="interleaved rounds per arm")
    args = parser.parse_args()

    print(f"python {sys.version.split()[0]} on {sys.platform}")
    print(f"{args.writes:,} writes x {args.rounds} rounds, minimum reported\n")
    for subscribers in (0, 1, 3):
        _measure(subscribers, args.writes, args.rounds)
        print()

    budget_ms = 16.6
    print(
        "A frame budget is "
        f"{budget_ms} ms at 60fps; multiply the delta by the observable writes "
        "your frame actually makes."
    )


if __name__ == "__main__":
    main()
