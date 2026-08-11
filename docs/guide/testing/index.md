# Testing

`nuiitivet` ships a pytest plugin that makes a test suite behave predictably:
each test runs isolated from every other test, and scheduled timers fire on the
test thread only when the test asks. It activates automatically on install —
no `conftest.py` boilerplate — the moment `nuiitivet` is importable in the
environment pytest runs in.

On top of that environment sit the two objects you write tests against:

| Level | Unit of test | Entry point |
| --- | --- | --- |
| Unit | one widget | [`mount()`](widgets.md) |
| Integration | a screen: state, tree, input | [`AppHarness`](screens.md) |
| E2E | the running process | [the dev bridge](../ai_pair_programming/dev_bridge_mcp.md) |

Targeting is by `key` at every level and the action verbs are the dev bridge's,
one for one, so what you learn at any level carries to the others. This page
covers the environment underneath all three.

## Why the isolation exists

The framework keeps process-global state: pending widget invalidations, the
theme reader stack, the once-per-process log de-duplication, and — most
importantly — `runtime.clock`, which schedules every delayed callback in the
framework (`debounce`, tooltip delays, overlay auto-dismiss, cross-thread
`dispatch_to_ui`).

Without the plugin, two things go wrong, and both have the same expensive
signature — **the test that fails is not the test that is wrong**:

- A test that touches process-global state and dies mid-way leaves it corrupted
  for every later test in the session. Whether an unrelated test passes then
  depends on collection order, and the failure moves when you reorder or filter
  the suite with `-k`.
- With no backend running, the fallback clock fires scheduled callbacks on
  `threading.Timer` threads at wall-clock time. A widget that arms a delayed
  callback and is never torn down leaves that timer live; it fires in the
  middle of some later test, mutating widget state off the UI thread.

The plugin ends both: around every test it installs a fresh
[`HarnessClock`](#the-harness-clock) and resets the framework's process-global
state. Disabling it re-opens both failure modes — do it only for a test that
genuinely needs the real clock, and know what you are trading away.

## The harness clock

`HarnessClock` holds every scheduled callback in a queue and fires it only when
the test **pumps** — on the test thread, deterministically, never on a timer
thread.

```python
def test_deferred_reset_fires_on_the_next_frame(nuiitivet_clock):
    widget.pointer_leave()            # schedules a next-frame reset
    nuiitivet_clock.pump_immediate()    # play it, on the test thread
    assert widget.state.value == "idle"
```

The `nuiitivet_clock` fixture returns the installed clock, typed. Two pumps
exist because `delay == 0` is a different request:

- `pump_immediate()` fires **zero-delay one-shots only**. In this framework
  `schedule_once(fn, 0)` means "not on this call stack" — a marshal to the UI
  thread, or a deferral to the next frame. A synchronous test can honour that:
  the pump call *is* the next stack.
- `pump()` fires **everything already due**. A delayed callback is a genuine
  wait, and it becomes due only when real time has genuinely passed — there is
  no `advance()`; the clock runs in real time.

`due_now` and `next_deadline` (seconds until the earliest callback is due,
`None` when nothing is armed) let a test wait exactly as long as needed:

```python
def test_debounce_delivers_after_its_delay(nuiitivet_clock):
    field.text.value = "hel"
    time.sleep(nuiitivet_clock.next_deadline)
    nuiitivet_clock.pump()
    assert search.calls == 1
```

## Do not assert the absence of a timed effect

A synchronous test never pumps a delayed callback, so this passes whether the
debounce works or was deleted outright:

```python
field.text.value = "hel"
assert search.calls == 0    # debounce not elapsed — or debounce broken
```

Assert the **presence** of the effect after making time pass (as in the
example above) instead. Two mechanisms back this rule up:

- By default, a test that ends with callbacks **due and never pumped** gets a
  `NuiitivetClockWarning` naming each callback and where it was scheduled.
- `@pytest.mark.nuiitivet(clock="strict")` **fails** the test if any callback
  was armed and never fired. Callbacks the code under test explicitly
  `unschedule`d are exempt — a debounce that re-arms by cancelling its
  predecessor is behaving correctly. A green strict test looks like the
  debounce example above: arm, elapse, pump, assert.

## Configuration

Everything above is on by default, for every test, with nothing to set up.
Configuration exists only to *deviate* from that default, per test, through
one marker: `@pytest.mark.nuiitivet(...)`. It takes two keyword arguments.

### `clock=` — which clock the test runs on

**`clock="harness"` (the default).** The test gets a fresh `HarnessClock`:
scheduled callbacks fire only when the test pumps. This is what every example
above assumes.

**`clock="strict"`.** Same harness clock, plus a check at the end of the test:
if any callback was armed and never fired, the test **fails** instead of
merely warning. Turn it on for a test whose *subject* is a timed effect — a
debounce, an auto-dismiss — where "the callback never ran" must not pass
silently. See [the strict example](#do-not-assert-the-absence-of-a-timed-effect)
for what a passing strict test looks like.

**`clock="real"`.** The plugin installs nothing and leaves whatever clock is
already in place — with no backend running, that is the fallback clock, which
fires callbacks on **background threads** at wall-clock time. This buys
nothing except fidelity to the no-harness world, and it re-opens the race the
harness exists to close: an assertion can now run *while* a timer fires on
another thread. Reach for it only when a test is genuinely *about* real timer
threads — testing a clock implementation itself, or thread interaction. If
you only want a delayed callback to actually run, you do not need this:
sleep and `pump()` instead.

### `isolate=` — whether the process-global resets run

**`isolate=True` (the default).** Around the test, the plugin resets the
framework's process-global state — pending invalidations, the theme reader
stack, the log-once registry, and so on — so the test neither inherits an
earlier test's leftovers nor leaks its own.

**`isolate=False`.** Those resets are skipped: the test sees whatever state
earlier tests left behind, and whatever it corrupts stays corrupted for every
test after it. There is almost no good reason to want this in an app suite;
it exists for tests that examine the framework's global state across test
boundaries on purpose. If a test only *reads* some global, the default
already works — opting out is never required for that.

### Combining and scoping

The two arguments are independent and combine freely. Stacked markers merge
their keyword arguments (nearest to the function wins per key), so a
file-wide `pytestmark` and a per-test marker compose:

```python
pytestmark = pytest.mark.nuiitivet(clock="strict")   # whole file is strict

@pytest.mark.nuiitivet(isolate=False)                # this test: strict AND unisolated
def test_cross_test_bookkeeping():
    ...
```

Suite-wide defaults live in `pyproject.toml`, overridden per test by the
marker:

```toml
[tool.nuiitivet.testing]
clock = "harness"    # "harness" (default) | "strict" | "real"
isolate = true
```

## Async tests

A bare `async def` test just runs — no `pytest-asyncio`, no marker, no
configuration:

```python
async def test_fetch_updates_the_model(nuiitivet_clock):
    await model.refresh()
    assert model.items
```

The plugin creates a fresh event loop for the test, runs the coroutine to
completion on it, and closes the loop afterwards. Any task the test left
pending is cancelled before the loop closes, so a forgotten background task
cannot warn (or fire) outside its test. The loop runs in **real time** — the
[harness clock](#the-harness-clock) controls the framework's scheduled
callbacks, not asyncio's.

If your suite already uses a dedicated async plugin, nothing changes:

- A test marked `@pytest.mark.asyncio` runs under **pytest-asyncio** whenever
  that plugin is installed — including its auto mode, which marks every async
  test for you.
- A test marked `@pytest.mark.anyio` runs under **anyio** whenever that plugin
  is installed.

The plugin stands aside only when the marked-for plugin is *actually there*.
A marker without its plugin — say `@pytest.mark.asyncio` left behind after
dropping the dependency — is orphaned; standing aside for it would defer to
nobody and the test would silently never run. Orphaned tests run on the
plugin's own loop instead, and their markers are registered so
`--strict-markers` stays quiet.

One behavioural consequence: with pytest-asyncio installed in strict mode, an
*unmarked* `async def` test used to be collected and skipped with a warning.
Now it runs, on the plugin's loop.

## Concurrency

Tests must run **one at a time in one thread**. Plain pytest does that, and
`pytest-xdist` preserves it — `-n 4` parallelises across worker *processes*.
Thread-parallel plugins (`pytest-parallel` and similar) are refused with an
error: everything above is process-global, so concurrent tests in one process
would race on it. This is a property of the framework, not of the plugin.
