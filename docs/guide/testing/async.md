# Testing async flows

An `async def` handler — a fetch, an awaited dialog, a debounced search — needs a
running event loop and something that knows when its work is finished. Both come
from the harness. Write the test as `async def` and it runs on a real loop, with
no `pytest-asyncio` needed:

```python
async def test_loading(nuiitivet_app):
    screen = ItemsScreen(api=FakeApi())
    app = nuiitivet_app(screen, size=(800, 600))

    app.click(key="load")
    await app.idle()

    assert screen.items.value == ["a", "b"]
```

## Two rules

Everything on this page follows from them.

**1. Never sleep a fixed amount. Wait for a condition.** The harness runs in real
time, so `await asyncio.sleep(0.3)` is a bet on how fast the machine is. It wins
on your laptop and loses on a busy CI runner, and when it loses the failure
points at the assertion rather than at the sleep.

`await asyncio.sleep(0)` looks exempt and is not: it is *one turn* of the loop,
which is enough for a one-hop task and not for a flow whose task starts another.
The number of turns needed is an implementation detail of the code you are
testing, which is exactly what a test should not encode.

**2. If a test needs to wait more than about a second of real time, it is an E2E
test.** Mock the slow thing, or drive the real app through the dev bridge.

## `idle()` — drain what is already in motion

```python
app.click(key="save")
await app.idle()
assert screen.saved.value is True
```

`idle()` pumps the clock, settles the tree and lets pending tasks run until the
loop has nothing left it can do on its own. Use it after an action whose effects
are already under way.

It returns in two situations that surprise people the first time, both on
purpose:

- **with a dialog open.** A handler sitting on `await overlay.confirm(...)` is an
  app *at rest*, waiting for input only your test can supply. Waiting for that
  handler to finish would hang every dialog test.
- **with an animation still running.** A spinner's timer never stops firing, so
  "no timer fired recently" can never be the signal. Waiting for an animation to
  *end* is waiting for a future event — that is `wait_for`.

`idle()` does not wait out a timer either. A debounce, a tooltip delay, or a
mocked call that sleeps are all future events.

## `wait_for()` — wait for an outcome

Whenever a delay is involved:

```python
app.type("hello", key="search")
await app.wait_for(key="results")           # a node appeared
await app.wait_for(key="spinner", present=False)   # ... and one went away
await app.wait_for(lambda: vm.items.value)  # or any predicate at all
```

The delay never appears in the test, so changing a debounce from 0.3 s to 0.5 s
breaks nothing.

Conditions come in two shapes. The tree vocabulary is the dev bridge's, one for
one — `key`, `label`, `text`, `present` — so what you learned writing E2E works
here. The **predicate** form is for everything the tree cannot express, which
includes the assertion this guide otherwise pushes you towards: the `Observable`
your screen is driven by.

`timeout` defaults to one second. To change it for a whole suite:

```toml
[tool.nuiitivet.testing]
wait_timeout = 2.0
```

A timeout raises `WaitTimeoutError`, and the message names what was still
outstanding in *both* queues — armed clock callbacks and pending tasks — plus the
identities that do exist, when the condition was a tree query.

## An awaited dialog, end to end

```python
async def test_delete_asks_first(nuiitivet_app):
    screen = ItemScreen()
    app = nuiitivet_app(screen, size=(800, 600))

    app.click(key="delete")
    await app.idle()                    # returns with the dialog up
    assert app.get(label="Delete this item?")

    app.click(label="Cancel")
    await app.idle()                    # the handler resumes and finishes
    assert screen.deleted.value is False
```

## What fails, and how

**A handler that raised.** In production the framework contains an exception in a
user callback and carries on — one broken handler must not kill the frame. Under
the harness that containment would mean a handler which raised on line one reads
as one that worked, so `idle()` and `wait_for()` re-raise it, with the original
traceback.

**A handler that could not be scheduled.** Calling an async handler from a
*synchronous* test raises `UnschedulableAsyncWork`: there is no loop, so the
handler never ran, and the assertion after it would have been meaningless. The
fix is in the message — make the test `async def`.

**Work you started and never waited for.** If a test ends with a task still in
flight that no `idle()` or `wait_for()` ever observed, the harness warns and
names it. A forgotten `await app.idle()` makes a positive assertion fail loudly,
but `assert app.query(key="error") is None` passes for entirely the wrong reason;
the warning is what catches that one.

## Tasks are never your problem

You do not create them, cancel them or count them. The framework reports the work
it starts — async handlers, `Navigator.pop()`, an overlay dismissal gated on
`will_pop`, back-button handling — and the harness waits on exactly that set.

The one gap: a handler that calls `asyncio.create_task()` itself, fire and
forget, is outside it. Such a task is *listed* in a timeout diagnostic rather
than waited on, so what is missed stays visible. If you need to await one, hold
it and await it directly.
