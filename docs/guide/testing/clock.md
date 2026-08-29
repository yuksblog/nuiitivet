# Testing outside the harness

The pytest plugin installs a [`HarnessClock`](index.md#the-harness-clock) around
every test, and `settle()` / `pump()` are how a test plays the callbacks it
queued. This page is for the case where the plugin is not in play — a test suite
that does not use it, or a test whose subject *is* a clock — and you have to
control delivery yourself.

The indirection point is `nv.Clocks.set()`, not pyglet: nuiitivet schedules
every deferred notification through the installed clock, and the backend
installs pyglet's at startup. Anything satisfying the `nv.Clock` protocol can
take its place.

```python
import threading
from typing import List, Tuple

import nuiitivet.material as nv


class ManualClock:
    """Queue scheduled callbacks and run them on demand.

    Structurally an `nv.Clock` — the protocol a clock has to satisfy.
    """

    def __init__(self) -> None:
        self._pending: List[Tuple[float, nv.ClockCallback]] = []

    def schedule_once(self, fn: nv.ClockCallback, delay: float) -> None:
        self.unschedule(fn)
        self._pending.append((delay, fn))

    def schedule_interval(self, fn: nv.ClockCallback, interval: float) -> None:
        self._pending.append((interval, fn))

    def unschedule(self, fn: nv.ClockCallback) -> None:
        # Compare by equality, not `is`: `obj.method` is a fresh object on
        # every access, so identity never matches and timers leak.
        self._pending = [entry for entry in self._pending if entry[1] != fn]

    def tick(self, dt: float = 0.0) -> None:
        pending, self._pending = self._pending, []
        for _, fn in pending:
            fn(dt)


def test_worker_update_reaches_subscribers():
    previous = nv.Clocks.get()
    manual = ManualClock()
    nv.Clocks.set(manual)
    try:
        vm = CsvPreview()
        received = []
        vm.rows.subscribe(received.append)

        thread = threading.Thread(target=lambda: vm.load("data.csv"))
        thread.start()
        thread.join()

        assert received == []  # still queued
        manual.tick()
        assert received == [expected]
    finally:
        nv.Clocks.set(previous)
```

Read the current clock with `nv.Clocks.get()` at the moment you need it, and
never keep the returned reference around: the backend installs its own clock
during `App.run()`, so a reference saved earlier still points at the startup
fallback.

Two rules for a hand-rolled clock:

- **Match callbacks by equality (`==`), never by `is` or `id()`.** This is what
  `pyglet.clock` does, and nuiitivet relies on it — `unschedule(self._emit)`
  has to cancel a timer armed with `self._emit`, even though each attribute
  access produces a distinct bound-method object.
- **Prefer running callbacks synchronously on the thread that ticks the clock.**
  The fallback clock delivers on its own servicing thread, so subscribers must
  not touch widgets, and assertions have to wait on real time.

Restore the previous clock afterwards, or later tests inherit yours.

---

## Next Steps

- [Testing Overview](index.md)
- [Observable: Thread Safety](../state-management/thread_safety.md)
