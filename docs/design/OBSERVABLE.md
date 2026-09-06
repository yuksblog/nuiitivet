# Observable & Reactive Programming

This document summarizes the internal design of the Observable and reactive system in `nuiitivet`.
For a usage guide, see [docs/guide/state-management/index.md](../guide/state-management/index.md).

See also:

- [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md)
- [THREADING_MODEL.md](THREADING_MODEL.md)
- [PROGRAMMING_PARADIMS.md](PROGRAMMING_PARADIMS.md)

**How this document is arranged.** §1–§2 are the core model and its threading
rule. §3 is the operator surface as a whole. §4 is the contract every
source-wrapping operator obeys, stated once; §5 gives each such operator only
what the contract does not already say. Adding an operator should therefore touch
§3.2's table and one subsection of §5 — and §4 only if it genuinely changes a
rule shared by all wrappers. §6 is what binding an observable to a widget means,
and §7 is what happens when any callback in the graph raises.

## 1. Core model

- Observable descriptors are **ownerless**: they emit immediate notifications in any layer (domain models, services, widgets) without relying on framework mixins or hidden hooks.
- A global `batch()` context (backed by `contextvars`) unifies batching semantics. It supports nesting, records dirty `_ObservableValue` instances, and queues ComputedObservables so they recompute exactly once when the outermost batch exits. This delivers glitch-free updates even when multiple observables change within a single handler.
- The UI layer automatically wraps pointer/key/focus dispatch in `batch()`, so widget authors simply mutate state inside event handlers. Business logic stays explicit: `with batch():` clusters related updates only when needed, keeping the learning cost low.
- Binding updates flow through `_queue_binding_invalidation()` and flush alongside scope recompositions before paint. The binding queue and the batching context complement each other: batch reduces redundant recompute work, while the queue ensures widget invalidations happen once per frame.

## 2. Threading: UI dispatch by default, with an explicit opt-out

**Problem:** worker threads updating observables can trigger UI updates from non-UI threads, causing crashes.

**Design decision: default to safe** (marshal to the UI thread), opt out with `dispatch=False`.

```python
# UI layer (ViewModel) - nothing to enable
class ViewModel:
    items = Observable([])

    def load_async(self):
        def worker():
            result = fetch_data()
            self.items.value = result  # notify happens on the UI thread
        threading.Thread(target=worker).start()

# Logic layer - opt out where no widget will ever bind
class DataProcessor:
    raw_data = Observable([], dispatch=False)

    def __init__(self):
        # Inherits the opt-out: a derivation of a logic-layer value stays one.
        self.filtered = self.raw_data.map(lambda x: [i for i in x if i > 0])
```

**Rationale for default-on:**

1. **The unsafe case must not be the quiet one.** Forgetting to dispatch would produce a crash or silent tree corruption whose cause is nowhere near the symptom. Forgetting `dispatch=False` costs some coalescing on a value nothing renders.
2. **Cost is small and bounded.** The per-write work is one integer comparison against a cached UI-thread ident (~75 ns, ~9.5% of a write).
3. **The opt-out carries real information.** `dispatch=False` states "no widget binds to this, and every intermediate value matters" — which the absence of a call could not say.

**Implementation:**

- `_ObservableValue`, `Observable` and `ComputedObservable` take `dispatch: bool = True`
- The thread test is `nuiitivet.runtime.threading.is_ui_thread()` — a cached-ident comparison, and the single definition of "the UI thread" for both this and `assert_ui_thread()`
- The setter marshals through the installed clock (`runtime.clock.schedule_once(..., 0)`), coalescing to one scheduled flush per tick
- `batch()` dispatches its flush to the UI thread if any observable in the batch dispatches
- `map()` propagates the **opt-out**; `combine(...).compute(...)` dispatches unless every source opted out, and takes an explicit `dispatch=` to override
- Wrappers make no dispatch decision of their own; §4.4 states why, and the one exception

**Constraints:**

- Compute functions execute on the triggering thread (may be a worker thread)
- Only notifications are marshalled to the UI thread
- Compute functions must NOT access UI-thread-only objects (widgets, UI state) — only observable values
- A marshalled write is asynchronous and coalesced: the writer reads back the old value until the next tick, and intermediate values are dropped

## 3. Operators

### 3.1 Principles

The framework provides a minimal, unified API for reactive transformations inspired by ReactiveProperty (WPF) and Signals (Solid.js).

- **Unified syntax**: all reactive operations use method chaining for consistency
- **Explicit over implicit**: dependencies are clear in simple cases (`.map()`, `.combine()`), automatic tracking handles complex cases (`.compute()`)
- **Minimal API surface**: only essential operators, to reduce learning cost and API confusion
- **Gradual learning curve**: beginners start with `.map()`, advance to `.combine()`, master `.compute()` for complex scenarios

**Operators deliberately absent:**

- **`combine_latest`**: redundant with `.combine().compute()`
- **`select` / `where`**: second names for `map` and `filter`
- **`zip` / `merge`**: no in-tree case needs them

**The bar for adding one.** Minimal surface is the default, so an operator earns
its place by removing a hazard rather than by saving keystrokes — by making a
class of silent, intermittent bug unwritable.

### 3.2 Catalog

| Operator | Kind | Use case | Example |
| :--- | :--- | :--- | :--- |
| `.map(fn)` | derives | 1:1 transformation | `age.map(lambda x: x >= 18)` |
| `.combine(other)` | derives | Explicit multi-source composition (method form) | `price.combine(qty).compute(lambda p, q: p * q)` |
| `combine(a, b, ...)` | derives | Explicit multi-source composition (function form, 3+ sources) | `combine(price, qty, discount).compute(lambda p, q, d: ...)` |
| `Observable.compute(fn)` | derives | Automatic dependency tracking for complex logic | `Observable.compute(lambda: self.a.value if self.flag.value else self.b.value)` |
| `.debounce(seconds)` | wraps | Emit only after `seconds` of silence (§5.1) | `query.debounce(0.3)` |
| `.throttle(seconds)` | wraps | Emit on the leading edge, then at most once per `seconds` (§5.1) | `position.throttle(0.1)` |
| `.filter(pred, initial=...)` | wraps | Emit only values passing `pred` (§5.2) | `amount.filter(lambda n: n > 0, initial=0)` |
| `.switch_map(fn, initial=...)` | wraps | Asynchronous `map`; the newest run's result wins (§5.3) | `query.switch_map(search, initial=SearchOutcome())` |
| `.scan(fn, initial=...)` | wraps | Fold every emission into a running accumulator (§5.4) | `clicks.debounce(0.5).scan(lambda n, _: n + 1, initial=0)` |

### 3.3 Two kinds: deriving and wrapping

The **Kind** column above is the load-bearing distinction in this document.

**Deriving** operators — `map`, `combine`, `compute` — answer "what is `.value`
right now?" with a function of their sources. They hold no state and keep nothing
subscribed; the tracking context re-collects their dependencies on every
recompute.

**Wrapping** operators stay subscribed to their source for as long as they live
— either shaping *when* or *whether* its values are republished (`debounce`,
`throttle`, `filter`), or publishing values of their own that depend on more than
the source's current one (`switch_map`, `scan`). That subscription is what makes
lifetime, value semantics and threading real questions rather than trivial ones. §4 answers them
once for all wrappers; §5 covers what each operator adds on top.

**Implementation strategy (deriving):**

- `.map()` and `.combine()` internally use `Observable.compute()` for automatic dependency tracking
- Signals pattern with global `_tracking_context` (via `contextvars`) captures `.value` access during compute functions
- Dynamic dependency re-collection on every recompute handles conditional logic correctly
- Full integration with `batch()` prevents redundant computations

## 4. The wrapper contract

Everything in this section applies to every source-wrapping operator. An operator
in §5 states only where it adds to these rules; where it is silent, these rules
hold unchanged.

### 4.1 Lifetime

A wrapper's subscription to its source is a reference edge, and pointing it the
wrong way makes the whole chain uncollectable.

**Rule 1 — the source must not keep the wrapper alive.** `source.subscribe(self._on_x)`
stores a *bound method*, which strongly references the wrapper. The source then
outlives the wrapper and keeps it, and everything it holds, reachable forever.
Wrappers therefore subscribe through a **weak reference to `self`**, the shape
`ComputedObservable` uses for its dependency edges.

**Rule 2 — a wrapper lives exactly as long as something holds it.** Either the
object itself, or the `Disposable` that `subscribe()` returns, whose closure holds
the wrapper. This is what makes the framework's own convention correct without
further thought:

```python
self.bind(self.query.debounce(0.3).subscribe(self._on_query))
```

`bind()` retains the `Disposable`, which retains the chain; unmount disposes it,
and the chain is collectable once the widget is. Dropping the `Disposable` on the
floor drops the chain with it — the same rule `compute` and `map` already follow:
**a derived observable nobody holds does not exist.**

**Rule 3 — teardown releases the source and disarms the clock.** `dispose()` is
idempotent, unschedules every callback the wrapper may have armed, and runs from
`__del__` as a backstop. A wrapper with a timer already armed survives until it
fires — the clock holds the bound callback — so a pending emit completes rather
than vanishing mid-flight.

**Corollary — `Disposable.dispose()` drops its closure.** That closure holds the
observable, the subscriber, and every wrapper between them, so retaining it after
disposal would pin the whole chain for as long as the `Disposable` lives — for a
widget's `bind()` list, until the widget itself is collected. Disposal installs a
no-op in its place; the leak check is unaffected because it only reads
`_dispose_fn` on subscriptions that are still undisposed.

**Consequence for the leak check.** `testing/_leaks.py` exempts the observable
graph's own edges from leak reporting. It recognises them by an explicit mark
(`mark_internal_subscription`) rather than by inferring an owner from the
callback, because under Rule 1 there is no owner left to infer.

### 4.2 Value semantics

**A wrapper holds the value it last emitted.** `.value` is not a live read of the
source; it is what this observable last published, seeded when the wrapper is
constructed. `_emit_to_subscribers()` stores the value before notifying, so a
subscriber reading back through the wrapper sees what it was handed.

```python
d = q.debounce(0.3)     # d.value == q.value  (seeded at construction)
q.value = "abc"         # d.value unchanged — still the seed
# 0.3 s later           # d.value == "abc"
nv.Text(d)              # binds correctly, no map() needed
```

**Why, given that shaping could have lived on the notification path alone.** If
`.value` read through to the source, `nv.Text(q.debounce(0.3))` would render
whatever the source holds at build time — with no error and no warning, the UI
working while silently ignoring the operator that was asked for. The workaround
would not read as one either: `.map(str)` looks like type conversion, so nothing
in the code would say "this is what makes debounce take effect". Read-through
also makes `.value` mean two different things depending on the object: "this
observable's current value" on `Observable` / `ComputedObservable`, but "some
*other* observable's current value" on a wrapper.

**Before the first emission, a wrapper reports its seed.** What the seed is
belongs to each operator (§5), because it is the one part of value semantics they
do not agree on.

**Cost.** "Thin the notifications but read the true current value on demand"
(throttle as a sampler) is not expressible through the operator. No in-tree case
needs it; `wrapper._source.value` is there if one appears.

### 4.3 Dependency tracking

**A derivation depends on the wrapper, not on what the wrapper reads.** If a
wrapper's inner read of its source registered that *source* with the tracking
context, a derivation would hold two edges — one shaped, one raw — and the raw one
fires first and unconditionally, bypassing the shaping entirely:
`q.debounce(0.3).map(f)` would recompute on the keystroke rather than 0.3 s after
it. `SourceSubscribingObservable.value` therefore registers itself and evaluates
`_current_value()` with tracking suppressed; the seed read in `__init__` is
untracked for the same reason, so building a wrapper inside a `compute()` does
not hand that computation an edge to the wrapper's source.

A user callback a wrapper invokes — `filter`'s predicate, for instance — runs
untracked for the same reason: reading another observable inside it creates no
edge, and that dependency belongs in `combine`.

### 4.4 Dispatch

**Wrappers have no `dispatch` flag, because the decision belongs to whoever
writes a value.** Nothing writes to a wrapper: it re-publishes what its source
notified it of, and that notification already arrived on the thread the source
chose — the UI thread if the source dispatches, the writing thread if it opted
out. A wrapper emits right there, inheriting the source's decision without making
one.

**The exception is a wrapper that emits from a worker it started itself** —
`switch_map` (§5.3), and only that one. There is no arrival thread to inherit, so
it marshals unconditionally: every result goes through the clock, with no thread
test, because `fn` never runs on the UI thread anyway.

It cannot honour a source's `dispatch=False`. That opt-out promises a
notification synchronous with the write, and the answer does not exist yet when
the write happens. Emitting from the worker instead would also break superseding:
two runs can each pass the "am I still current?" test before either emits, and
routing both through the clock is what collapses them to one emission of the
newest. The alternative, emitting under the lock, runs subscriber code with the
lock held.

### 4.5 Operator parity

**A wrapper offers the same operators as any other observable**, so a chain never
dead-ends on the operator it just used. `_ObservableValue`, `ComputedObservable`
and `SourceSubscribingObservable` each define the full set from §3.2.

Not a shared mixin: the first two propagate the `dispatch=False` opt-out into what
they build and a wrapper has none to propagate (§4.4), so the bodies only look
alike. `tests/observable/test_operator_parity.py` asserts the three stay equal.

### 4.6 Implementation

- `SourceSubscribingObservable` (`observable/wrapper.py`) owns every rule in this section; operators subclass it and implement `_seed`, `_on_source_changed` and `_clock_callbacks`
- It takes **two type parameters**, `[TIn, TOut]`. An operator that hands the source's own values on subclasses `ShapingObservable[T]`, which fixes the two together and seeds from the source — correct **because** the types agree. `switch_map` and `scan` are the operators where they differ, and therefore the ones whose seed cannot come from the source at all
- `_seed()` sets `_held_value`; `_emit_to_subscribers()` updates it; the default `_current_value()` returns it. A subclass that must report something other than what it emitted overrides `_current_value()`, and the tracking suppression in `value` keeps that read from registering the source (§4.3)
- Clock callbacks are matched by **equality**, so `dispose()` can unschedule a callback that was never armed at no cost
- `wrapper._untracked(fn)` is how a wrapper runs its own reads and its user callbacks with tracking suppressed
- The pytest plugin arms `track_subscriptions` around every test and holds each `Disposable` strongly by design, so a test that asserts on *collection* must disarm it first (see `tests/observable/test_wrapper_lifecycle.py`)

## 5. The wrapping operators

### 5.1 Timing: debounce and throttle

**Problem:** high-frequency events (typing, mouse moves, API responses) trigger
excessive UI updates and expensive computations.

| Operator | Behavior | Use case |
| :--- | :--- | :--- |
| `.debounce(seconds)` | Emits only after `seconds` of silence | Search input, form validation |
| `.throttle(seconds)` | Emits the first value immediately, then at most one per `seconds` | Mouse tracking, scroll position |

**Design decisions:**

- **Debounce for settling, throttle for sampling.** Most UI event filtering wants the trailing edge (typing, window resize); mouse moves and scrolling want periodic samples instead, which is why both exist rather than one
- **Timing is explicit.** The seconds parameter puts the performance trade-off in the code rather than in a default
- **The clock, not a thread.** Timers go through the installed clock (`pyglet.clock` in production), so they fire on the UI thread and integrate with the event loop. Debounce cancels and re-arms on each new value; throttle emits on the leading edge and samples afterwards

**Seeds:** `debounce` reports the source's construction-time value until the input
first settles. `throttle` emits on the leading edge, so its first change moves it
immediately.

**Implementation:**

- `DebouncedObservable` and `ThrottledObservable` (`observable/timed.py`) hold only the latest pending value; timer cancellation happens in `dispose()` (§4.1 Rule 3)
- Testing uses `MockClock` with epsilon tolerance for deterministic timing assertions

### 5.2 Value gating: filter

**Problem:** some of a source's values must not reach the UI — an amount that has
not validated yet, a selection that is sometimes empty. `map` cannot express
this: it must return something for every input, so the rejected value still
arrives, merely transformed.

**Solution:** `.filter(pred, initial=...)` updates only when `pred` accepts the
source's value. `.value` is the last value that passed, or `initial` if none has.

```python
valid = amount.filter(lambda n: n > 0, initial=0)
nv.Text(valid.map(str))   # never shows a rejected amount
```

**The seed is required**, keyword-only and without a default. Every other
operator derives `.value` from its source; `filter` alone cannot, because the
predicate may reject everything the source ever produces. The caller therefore
states what the UI shows until the first value passes. Two alternatives were not
chosen:

- **Pass the source through until the first pass.** It displays a value the
  predicate rejected, which is the one outcome the operator exists to prevent,
  and it is the read-through §4.2 rules out
- **Report `Optional[T]`.** Every downstream `.map()` grows a `None` check, and
  the seed answers the same question without changing the type

**Semantics:**

- **The seed is tested too.** At construction the source's current value runs
  through `pred` and is kept if it passes, so `initial` means strictly "nothing
  has passed", not "nothing has arrived yet"
- **A rejected value changes nothing**: no emission, and `.value` keeps reporting
  the last value that passed
- **`None` is an ordinary value.** "Nothing has passed" is carried by the seed
  rather than by the value, so no sentinel is needed and a legitimate `None`
  passes like any other value
- **No equality check of its own.** `_ObservableValue` de-dupes before it
  notifies, and no wrapper second-guesses that
- **`pred` is a pure function of the value it is handed**, run untracked (§4.3)

**Implementation:**

- `FilteredObservable` (`observable/filtered.py`) subclasses `ShapingObservable`,
  so §4 is inherited rather than restated
- The seed is its only departure from the base: `__init__` replaces `_held_value`
  with `initial` unless the source's construction-time value passes `pred`

### 5.3 Asynchronous mapping: switch_map

**Problem:** deriving a value from a function that takes time to answer.
`map` runs its function synchronously on the triggering thread — the UI thread in
a `debounce` chain — so I/O in it blocks the window, and with two calls in flight
the slower-but-older one lands last and wins. Writing it by hand means a per-run
`threading.Event` protocol whose failure modes are silent: a reused `Event` that
gets `clear()`ed lets a superseded worker resume, and an unguarded `except` /
`finally` lets a stale run write over a live one. That is the hazard §3.1
requires an operator to remove.

**Solution:** `.switch_map(fn, initial=...)` runs `fn` off the UI thread and
delivers only the newest run's result.

```python
self.results = self.query.debounce(0.3).switch_map(self._search, initial=SearchOutcome())
```

**`switch_map` is `map`**, and the rest follows:

- a run starts **only** because the source's value changed
- a run is discarded **only** because the source's value changed again
- a run produces **exactly one** value

**What it cannot express**, which stays a hand-written worker
(`samples/state-management/background_work.py`):

| Shape | Why it is not a mapping |
| :--- | :--- |
| Started by a button | A click changes no input. A Retry button is the sharp case: the value is unchanged, so de-duplication means nothing fires |
| Reports progress as it runs | A mapping produces one value, not a stream |
| Stopped by an explicit Cancel | "The user wants this to stop" is not an input |
| Accumulates onto the previous value | A mapping depends on its input alone; an append also depends on the value it replaces, which superseding cannot order. Accumulating the *results* is `scan` over the output (§5.4) |

Two things are not criteria: the amount of data returned (items *and* a total
*and* facets is one answer) and the weight of the work (a thread is started
either way).

**The seed is required**, keyword-only and without a default, as in §5.2 — but
meaning "**no run has landed yet**" rather than "nothing has passed", because
**no run starts at construction**: building a ViewModel must not fire I/O.

**Failure is a value.** `fn` catches what the UI must render and returns it in
the app's own result type, so one value decides both the error and the items it
replaces. The return stays a plain observable whose only read surface is
`.value`. An exception that escapes `fn` is a bug, not a result: logged through
`exception_once`, delivered to nobody.

A companion `results.error: Observable[Exception | None]` was rejected. It does
not survive `.map()`, so a binding built from the result cannot see it; it needs
its own supersede test, clearing rule and batching; and it decides only the error,
never the accompanying value, leaving a failed run's error above the previous
run's rows. Adding it later would be purely additive.

**`CancelToken` is cooperative and optional.** Python cannot interrupt a thread,
so superseding discards the result and the worker still runs to completion. A run
that checks the token can return early instead; one that blocks in a single call
never gets the chance. It is still the second positional parameter of every `fn`,
because a signature cannot be widened later without breaking every existing one.
Against a hand-rolled `threading.Event` it removes the ways to misuse one: no
`clear()`, one token per run.

**Semantics:**

- **A superseded run's result never lands, from any path.** The test is identity
  against the live token at delivery, not a flag read earlier, so a result
  returned from `fn`'s own `except` or `finally` is discarded like any other
- **`.value` is the last landed result**; a superseded run does not change it
- **`dispose()` supersedes whatever is in flight**
- **Results are marshalled to the UI thread** before publication (§4.4)
- **`fn` is synchronous.** `async def` is not accepted; accepting both behind one
  name would mean two supersede implementations. The event-loop story is
  `ASYNCIO_INTEGRATION.md`, and widening the accepted type later is additive

**Implementation:**

- `SwitchMappedObservable` (`observable/switched.py`) subclasses
  `SourceSubscribingObservable[TIn, TOut]` rather than `ShapingObservable` — it is
  the operator whose two type parameters differ (§4.6)
- Each run gets a fresh `CancelToken` and a daemon thread named
  `switch_map:<fn qualname>`; the name lets tests join workers instead of sleeping
- Delivery stages the result under a lock only if the delivering token is still
  current, then schedules `_flush` on the clock; `_flush` re-reads the stage, so a
  result superseded in between is still dropped
- `exception_once` is keyed on the function's qualname, so two `switch_map`s
  cannot de-duplicate each other's bug into silence

### 5.4 Accumulation: scan

**Purpose:** a value that follows from every emission rather than from the
source's current one — how many times something fired, a running total, a list
appended to.

The scope is accumulation over **an operator's output**. `Observable` is mutable
state, so accumulating a user action is one line in the handler
(`self.count.value += 1`) and needs no operator at all. `debounce`, `throttle` and
`switch_map` publish because time passed or a run landed, so there is no handler
to hold that line and `subscribe` becomes the only way in — an empty `Observable`
beside the write that fills it, plus a `Disposable` that must be held or the value
silently stops moving.

```python
self.debounced = self.raw_count.debounce(0.5)
self.executed = self.debounced.scan(lambda n, _: n + 1, initial=0)
```

**API:** `.scan(fn, initial=...)` folds `fn(accumulator, value)` over every
emission, and the accumulator is this observable's value.

- **The seed is required**, keyword-only and without a default, as in §5.2 and
  §5.3 — here meaning "the source has emitted nothing"
- **The construction-time value is not folded in.** It has not been emitted, and
  folding it would start a counter at 1 and count a debounce window that never
  settled
- **One emission out per emission in.** Nothing is dropped: a fold landing on the
  accumulator it already held still emits, because the fold ran
- **No equality check of its own.** `_ObservableValue` de-dupes before it
  notifies, so a repeated source value folds once
- **The accumulator never re-seeds.** It belongs to this observable rather than to
  the chain: a rebuilt chain is a new observable that starts from `initial` again
- **`fn` is a pure function of the two values handed to it**, run untracked (§4.3)
- **A raising `fn` leaves the accumulator as it stood**: logged, nothing emitted
  (§7)

`fold` was rejected as the name: it states a terminal result, and what is
published here is every intermediate accumulator. `accumulate` matches
`itertools` at the cost of length. §3.1 keeps second names out, and `scan` is not
one — no existing operator accumulates.

**Implementation:** `ScannedObservable` (`observable/scanned.py`) subclasses
`SourceSubscribingObservable[TIn, TAcc]` rather than `ShapingObservable`, because
its two type parameters differ: `_seed` returns `initial` without reading the
source (§4.6). The rest is the wrapper contract in §4, unchanged.

## 6. Binding an observable to a widget: the value cell

Every input widget holds a value somewhere. Passing an observable to its
constructor **substitutes that storage cell** — it does not describe a direction
of flow. `Toggleable` states the rule in code:

```python
def _get_state_obj(self):
    if self._state_external is not None:
        return self._state_external
    return self._state_internal
```

Both the read path and the write path go through `_get_state_obj()`, and only
one of the two cells is ever live. With a single cell there is no second copy to
keep in sync and no direction to choose: the user's edit lands wherever the
widget's value lives, which is the caller's observable when the caller supplied
one. Two-way binding is therefore a consequence of the structure, not a mode
that gets selected. `Checkbox`, `Switch`, `RadioButton`, `RadioGroup` and the
sliders all behave this way without any of them implementing "two-way binding".

Three consequences follow, and they are what makes the rule worth stating:

- **A widget must not keep its own copy alongside an external observable.** Two
  cells make a direction expressible, and any direction chosen is then wrong
  half the time. Where a widget's internal representation is richer than what
  the caller's observable can hold, the widget mirrors instead of substituting,
  and the mirror has to be justified and documented — see the state-management
  section of [TEXT_EDITING.md](TEXT_EDITING.md), which is currently the only
  such case.
- **A read-only observable is display-only**, because there is nothing to write
  to. This is what a computed or mapped value is, and it is how a caller asks
  for display without an edit path.
- **The distinction is enforced at runtime, not by the type checker.** Whether a
  source is writable is decided by `isinstance(value, ObservableProtocol)`,
  which separates the two protocols by the presence of `set`. A static overload
  cannot express it: both arms take the same argument and return the same
  widget, so there is nothing for the checker to discriminate on.

  This is why **no operator may hand back a read-only static type over a
  runtime-writable object**. Such an operator produces a source that the caller
  has declared display-only and that a widget then writes to anyway, and no
  runtime check can catch it because there is nothing to check. `changes()` was
  exactly that — it returned `self` under a `ReadOnlyObservableProtocol` return
  type — and was removed rather than repaired: `subscribe()` already delivers
  changes and nothing else, so the operator had no second meaning to fall back
  on. Should a genuine read-only view be wanted later, it has to be a real
  wrapper object, so that the runtime agrees with the type.

### 6.1 When the caller's type is not the widget's input type

A text field edits `str`. Applications want dates, amounts, quantities. This
looks like the one case §6 cannot serve: there is no single cell, because the
two sides hold different types.

**The answer is not a mirror but an inversion. The text is the cell; the typed
value is derived from it.**

```python
self.arrival_text = nv.Observable("")            # the cell, bound to the field
self.arrival = self.arrival_text.map(parse_date)  # derived, read-only
```

A widget's value type therefore follows its **primary input mechanism**, not the
type the application finds most convenient. `DockedDatePicker` binds `str`
because it can be typed into; `DatePicker`, the inline calendar, binds
`date | None` because it cannot. These are the same rule, not an inconsistency.

Three things rule out keeping the typed value as the cell:

- **The mirror exception does not stretch this far.** TEXT_EDITING.md's mirror
  is a *total* enrichment: text plus selection contains the text, so the two
  always agree about the value. A conversion is **partial** — `"06/1"` is not a
  date. A widget mirroring across a partial map has to invent a policy for the
  gap, and needs an error cell to express it. It is then the sole writer of that
  cell, so an application that wants to report a business-level error ("already
  booked") has to write to it too, and the two-writer problem reappears one
  level up. The gap is not a defect to be handled; it is the normal state of a
  field someone is typing into.

- **An observable-side conversion operator cannot see the commit.** Whether a
  value is finished is a widget event — Enter, or focus leaving. An Observable
  is not told about either, so an operator-shaped conversion has no choice but
  to convert on every keystroke, which is the behaviour it was introduced to
  avoid. Commit-time work belongs on `on_submit` / `on_focus_change`, which is
  where the widget's own value already lives.

- **Derivation loses nothing.** `filter().map()` holds the last valid value,
  `map()` alone reports the invalid state, `debounce()` composes into the same
  chain, and the error message is one more `map()` of the same text — one
  writer, no disagreement possible. The widget contributes nothing that the
  chain does not already express.

This is a consequence of reactivity being **observable-driven**. In a
rebuild-driven framework an application influences a widget by supplying values
that are read during rebuild, so a date field can accept a validity predicate
and a set of error strings and the application never needs to own a cell —
Flutter's `InputDatePickerFormField` is built exactly that way. Here the cell
*is* the influence path. Handing the application the cell is therefore not one
option among several; it is the only way to give it control at all.

## 7. Failure semantics

§5.3 states the rule for `switch_map`: **failure the UI must render is a value,
not an exception.** `fn` catches what it can handle and returns it in the app's
own result type, and an exception that escapes is a bug rather than a result.
That rule is not specific to asynchronous work. It is the whole of this
section, generalized to every callback the graph runs.

**So an exception reaching the framework is always a bug**, never an outcome to
publish. And a bug needs a place to be reported. It cannot be *raised*, because
there is no caller who could handle it: a derivation re-runs because something
changed, and "something" is a clock callback marshalling a worker's write, a
`debounce` timer, or an unrelated handler three widgets away. None of them wrote
the broken function. Raising there only decides, by which thread happened to be
passing, whose stack the failure lands on — the undefined behaviour this section
replaces (#562).

**Every such bug is therefore logged and contained**, through
`exception_once_per_exc`, keyed by the failure's own type and innermost frame.
Two different broken derivations are reported separately; one that keeps failing
every keystroke stays a single line. The compute function's *name* cannot do
that job: every `.map()` shares one `compute_fn` closure inside
`ComputedObservable.map`, so keying on it would collapse unrelated bugs into the
first one reported. `switch_map` keys on the qualname instead because there the
user's own `fn` is what runs.

**Containment is per callback, and what the observable holds is the previous
value:**

| What raises | Where it is caught | What `.value` reports afterwards |
| :--- | :--- | :--- |
| a derivation (`map`, `combine().compute`, `Observable.compute`) | `ComputedObservable._recompute` | the previous value — no emission, so subscribers see nothing |
| a `filter` predicate | `FilteredObservable._passes` | the last value that *passed* — the tested value counts as not passing |
| a `switch_map` function | `SwitchMappedObservable._run` (§5.3) | the last landed result — the failed run publishes nothing |
| a `scan` function | `ScannedObservable._on_source_changed` (§5.4) | the accumulator as it stood — the failed fold publishes nothing |
| a subscriber | `_notify.notify_all` | unaffected; the remaining subscribers are still notified |

Keeping the previous value is chosen over propagating a sentinel, which would
leak into every consumer and into every operator downstream of one. The cost is
stated plainly rather than hidden: **a failed derivation is silently stale**, and
the log line is the only signal. That is the same trade `filter` already makes
for a value the predicate rejects.

**A failed derivation is retried.** Its dependency edges are torn down before
each run and re-armed after it, *whether or not it succeeded* — so the next
change to a source runs it again, and a transiently broken derivation recovers
on its own. Leaving the edges down would be worse than the original bug: one log
line, and then an observable frozen for the rest of the process. The one case
that cannot recover is a run that raised before reading anything, which has no
source to recover from.

**The subscriber guard is per callback, not one `try` around the loop.** A
single `try` would relocate the truncation rather than remove it: the first
raising subscriber would still stop every one registered after it, which is what
makes the symptom "a binding that sometimes does not update" — registration
order decides who breaks. The loop also re-reads the value per callback, because
a subscriber may write back to the observable notifying it (§6's cell, where an
application normalizes what a text field produced), and the subscribers after it
must be handed what that write left behind.

**The graph's own subscriptions are exempt.** A computed's dependency edges and
a wrapper's edge to its source are tagged `mark_internal_subscription` (§4.1),
and an exception on one of them re-raises rather than being logged. Such an
exception is not a broken subscriber but the framework's own signal — the batch
queue's infinite-loop detector reaches the notify loop through exactly this path,
and swallowing it would turn a loud protection into a silent one. Every internal
edge that runs application code guards it at its own site instead, which is also
where the log can name what actually broke.

**Implementation:**

- `observable/_notify.py` holds the one notify loop, used by `_ObservableValue`,
  `ComputedObservable` (both the direct and the marshalled path) and
  `SourceSubscribingObservable`
- `ComputedObservable._recompute` records success in a sentinel-typed local and
  assigns `_value` only on success, so "keep the previous value" is the absence
  of a write rather than a restore
- Equality failure after a recompute is a separate, older guard
  (`computed_value_eq_exc`): a `__eq__` that raises is treated as "not equal",
  which emits rather than suppresses
