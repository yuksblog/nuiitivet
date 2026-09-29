# Observable and Reactive Programming

An `Observable` is a value that notifies when it changes. It is ownerless: a
domain model, a service or a widget holds one and it emits without a
framework mixin or a hidden hook. The thread rules it lives under are in
[CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md), and the paradigms it serves in
[PROGRAMMING_PARADIMS.md](PROGRAMMING_PARADIMS.md).

## 1. Core Model

A global `batch()` context, backed by `contextvars`, unifies batching. It
nests, records the dirty `_ObservableValue`s and queues the computed
observables so that each recomputes exactly once when the outermost batch
exits, which makes an update glitch-free when several observables change in
one handler. The UI layer wraps pointer, key and focus dispatch in `batch()`,
so a widget author mutates state in a handler and gets the batch for free;
business logic writes `with batch():` only where it clusters updates.

Binding updates flow through `_queue_binding_invalidation()` and flush with
the scope recompositions before paint. The two mechanisms complement each
other: the batch removes redundant recomputes, the queue makes a widget
invalidate once per frame.

## 2. Threading: Dispatch by Default, Opt Out Explicitly

A worker thread that writes an observable would otherwise notify widgets from
a non-UI thread. So a write from another thread marshals its notification onto
the UI thread by default, and `dispatch=False` opts a value out. Default-on
was chosen for three reasons:

1. **The unsafe case must not be the quiet one.** Forgetting to dispatch
   would produce a crash or silent tree corruption whose cause is nowhere near
   the symptom; forgetting `dispatch=False` costs some coalescing on a value
   nothing renders.
2. **The cost is small and bounded**: one integer comparison against a cached
   UI-thread ident per write, about 75 ns, a tenth of a write.
3. **The opt-out carries information.** `dispatch=False` states "no widget
   binds to this, and every intermediate value matters", which the absence
   of a call could not say.

`_ObservableValue`, `Observable` and `ComputedObservable` take
`dispatch: bool = True`. The thread test is
`runtime.threading.is_ui_thread()`, the one definition of the UI thread. The
setter marshals through the installed clock (`runtime.clock.schedule_once(...,
0)`), coalescing to one flush per tick; `batch()` dispatches its flush to the
UI thread if any observable in it dispatches. `map()` propagates the opt-out;
`combine(...).compute(...)` dispatches unless every source opted out, and
takes an explicit `dispatch=` to override. A wrapper makes no dispatch
decision of its own (§4.4).

A compute function runs on the triggering thread, which may be a worker;
only the notification is marshalled, so a compute function reads observable
values and never a widget. A marshalled write is asynchronous and coalesced:
the writer reads back the old value until the next tick, and intermediate
values are dropped.

## 3. Operators

The operator set is minimal and uniform, in the spirit of ReactiveProperty
and Signals: every operation is a method chain, dependencies are explicit
where a case is simple (`map`, `combine`) and tracked automatically where it
is not (`compute`), and a reader learns `map` first and `compute` last.

Operators left out: `combine_latest`, redundant with `combine().compute()`;
`select` / `where`, second names for `map` and `filter`; `zip` / `merge`, with
no in-tree case. An operator earns its place by removing a hazard, by making a
class of silent, intermittent bug unwritable, never by saving keystrokes.

### 3.1 Two Kinds: Deriving and Wrapping

This distinction is the load-bearing one in this document.

**Deriving** operators, `map`, `combine` and `compute`, answer "what is
`.value` right now?" with a function of their sources. They hold no state and
keep nothing subscribed: `map` and `combine` are built on `compute`, whose
tracking context (`_tracking_context`, a `contextvars` value) captures every
`.value` read during the function and re-collects the dependencies on every
recompute, so a conditional read is tracked correctly and `batch()` folds
redundant recomputes.

**Wrapping** operators stay subscribed to their source for as long as they
live, either shaping when or whether its values are republished (`debounce`,
`throttle`, `filter`) or publishing values of their own that depend on more
than the source's current one (`switch_map`, `scan`). That subscription is
what makes lifetime, value semantics and threading real questions. §4
answers them once for all wrappers; §5 covers what each operator adds.

## 4. The Wrapper Contract

Everything here applies to every source-wrapping operator. An operator in §5
states only where it adds to these rules.

### 4.1 Lifetime

A wrapper's subscription to its source is a reference edge, and pointing it
the wrong way makes the whole chain uncollectable.

**The source must not keep the wrapper alive.** `source.subscribe(self._on_x)`
stores a bound method, which strongly references the wrapper; the source then
outlives the wrapper and keeps everything it holds reachable. Wrappers
subscribe through a weak reference to `self`, the shape `ComputedObservable`
uses for its dependency edges.

**A wrapper lives exactly as long as something holds it**: the object itself,
or the `Disposable` that `subscribe()` returns, whose closure holds the
wrapper. This is what makes the framework's convention correct without
further thought:

```python
self.bind(self.query.debounce(0.3).subscribe(self._on_query))
```

`bind()` retains the `Disposable`, which retains the chain; unmount disposes
it, and the chain is collectable once the widget is. Dropping the
`Disposable` drops the chain, the rule `compute` and `map` already follow: a
derived observable nobody holds does not exist.

**Teardown releases the source and disarms the clock.** `dispose()` is
idempotent, unschedules every callback the wrapper may have armed, and runs
from `__del__` as a backstop. A wrapper with a timer already armed survives
until it fires, since the clock holds the bound callback, so a pending emit
completes rather than vanishing mid-flight.

`Disposable.dispose()` drops its closure, which holds the observable, the
subscriber and every wrapper between them; retaining it after disposal would
pin the chain for as long as the `Disposable` lives, for a widget's `bind()`
list until the widget itself is collected. Disposal installs a no-op in its
place. The leak check in `testing/_leaks.py` exempts the graph's own edges,
recognised by an explicit `mark_internal_subscription` rather than by
inferring an owner from the callback, because under the first rule there is
no owner left to infer.

### 4.2 Value Semantics

**A wrapper holds the value it last emitted.** `.value` is not a live read of
the source; it is what this observable last published, seeded at
construction. `_emit_to_subscribers()` stores the value before notifying, so a
subscriber reading back through the wrapper sees what it was handed.

```python
d = q.debounce(0.3)     # d.value == q.value  (seeded at construction)
q.value = "abc"         # d.value unchanged: still the seed
# 0.3 s later           # d.value == "abc"
nv.Text(d)              # binds correctly, no map() needed
```

Reading through to the source was rejected. `nv.Text(q.debounce(0.3))` would
then render whatever the source holds at build time, with no error and no
warning, the UI working while silently ignoring the operator asked for; the
workaround, `.map(str)`, reads as type conversion, so nothing in the code
would say "this is what makes debounce take effect". Read-through also makes
`.value` mean "this observable's value" on an `Observable` and "some other
observable's value" on a wrapper.

Before the first emission a wrapper reports its seed, and what the seed is
belongs to each operator (§5), the one part of value semantics they do not
share. The cost: "thin the notifications but read the true current value on
demand", throttle as a sampler, is not expressible through the operator; no
in-tree case needs it, and `wrapper._source.value` is there if one appears.

### 4.3 Dependency Tracking

**A derivation depends on the wrapper, not on what the wrapper reads.** If a
wrapper's inner read of its source registered that source with the tracking
context, a derivation would hold two edges, one shaped and one raw, and the
raw one fires first and unconditionally, bypassing the shaping:
`q.debounce(0.3).map(f)` would recompute on the keystroke. So
`SourceSubscribingObservable.value` registers itself and evaluates
`_current_value()` with tracking suppressed, and the seed read in `__init__`
is untracked for the same reason, so building a wrapper inside a `compute()`
hands that computation no edge to the wrapper's source. A user callback a
wrapper invokes, `filter`'s predicate, runs untracked too: reading another
observable inside it creates no edge, and that dependency belongs in
`combine`.

### 4.4 Dispatch

**Wrappers have no `dispatch` flag, because the decision belongs to whoever
writes a value.** Nothing writes to a wrapper: it re-publishes what its source
notified it of, and that notification already arrived on the thread the
source chose. A wrapper emits right there, inheriting the decision.

The exception is a wrapper that emits from a worker it started itself,
`switch_map` and only that one. There is no arrival thread to inherit, so it
marshals unconditionally through the clock, with no thread test, because
`fn` never runs on the UI thread. It cannot honour a source's
`dispatch=False`: that opt-out promises a notification synchronous with the
write, and the answer does not exist yet when the write happens. Emitting
from the worker would also break superseding, since two runs can each pass
the "am I still current?" test before either emits, and routing both through
the clock is what collapses them to one emission of the newest; emitting
under the lock would run subscriber code with the lock held.

### 4.5 Operator Parity

A wrapper offers the same operators as any other observable, so a chain never
dead-ends on the operator it just used: `_ObservableValue`,
`ComputedObservable` and `SourceSubscribingObservable` each define the full
set. Not through a shared mixin, because the first two propagate the
`dispatch=False` opt-out into what they build and a wrapper has none to
propagate; `tests/observable/test_operator_parity.py` asserts the three stay
equal.

### 4.6 Implementation

`SourceSubscribingObservable` (`observable/wrapper.py`) owns every rule in
this section; an operator subclasses it and implements `_seed`,
`_on_source_changed` and `_clock_callbacks`. It takes two type parameters,
`[TIn, TOut]`. An operator that hands the source's own values on subclasses
`ShapingObservable[T]`, which fixes the two together and seeds from the
source, correct because the types agree; `switch_map` and `scan` are the
operators where they differ, and therefore the ones whose seed cannot come
from the source. `_seed()` sets `_held_value`, `_emit_to_subscribers()`
updates it, and the default `_current_value()` returns it. Clock callbacks
are matched by equality, so `dispose()` can unschedule a callback that was
never armed at no cost. `_untracked(fn)` runs a wrapper's own reads and its
user callbacks with tracking suppressed. The pytest plugin arms
`track_subscriptions` around every test and holds each `Disposable`
strongly, so a test that asserts on collection disarms it first.

## 5. The Wrapping Operators

### 5.1 Timing: `debounce` and `throttle`

Typing, pointer moves and a stream of API responses change a source faster
than the UI and the recomputations behind it are worth running. Two
operators thin them because they thin differently: most input wants the
trailing edge, once it has settled (typing, a window resize), while pointer
moves and scrolling want periodic samples of something that never settles.

- `seconds` has no default. The window is a trade-off the app makes, and a
  default would hide it in the framework.
- The seed differs by operator: `debounce` reports the source's
  construction-time value until the input first settles; `throttle` emits on
  the leading edge, so its first change moves it immediately.
- Emissions arrive on the UI thread, because the timers go through the
  installed clock rather than a thread of their own, so nothing needs
  marshalling and a test installs a deterministic clock instead of sleeping.

`DebouncedObservable` and `ThrottledObservable` (`observable/timed.py`) hold
only the latest pending value and disarm their timer in `dispose()`.

### 5.2 Value Gating: `filter`

Some of a source's values must not reach the UI: an amount that has not
validated yet, a selection that is sometimes empty. `map` cannot express
this, since it must return something for every input, so the rejected value
still arrives, merely transformed. `filter` updates only when the predicate
accepts the value, and `.value` is the last value that passed.

- The seed (`initial`) is required, keyword-only, without a default. Every
  other operator derives `.value` from its source; `filter` alone cannot,
  because the predicate may reject everything the source ever produces, so
  the caller states what the UI shows until the first value passes.
- The seed is tested too: at construction the source's current value runs
  through the predicate and is kept if it passes, so `initial` means
  strictly "nothing has passed", not "nothing has arrived yet".
- `None` is an ordinary value. "Nothing has passed" is carried by the seed
  rather than by the value, so no sentinel is needed.
- No equality check of its own: `_ObservableValue` de-dupes before it
  notifies, and no wrapper second-guesses that.

Two alternatives to the seed were rejected. Passing the source through until
the first pass displays a value the predicate rejected, the one outcome the
operator exists to prevent, and is the read-through §4.2 rules out. Reporting
`Optional[T]` grows a `None` check on every downstream `map`, where the seed
answers the same question without changing the type.

`FilteredObservable` (`observable/filtered.py`) is a `ShapingObservable`
whose `__init__` replaces `_held_value` with `initial` unless the source's
construction-time value passes.

### 5.3 Asynchronous Mapping: `switch_map`

A value derived from a function that takes time to answer. `map` runs its
function synchronously on the triggering thread, the UI thread in a
`debounce` chain, so I/O in it blocks the window, and with two calls in
flight the slower-but-older one lands last and wins. Written by hand, the
per-run `threading.Event` protocol fails silently: a reused `Event` that gets
`clear()`ed lets a superseded worker resume, and an unguarded `except` /
`finally` lets a stale run write over a live one. That is the hazard §3
requires an operator to remove.

`switch_map` is `map`, and its scope follows: a run starts only because the
source's value changed, is discarded only because it changed again, and
produces exactly one value. What that cannot express stays a hand-written
worker:

| Shape | Why it is not a mapping |
| :--- | :--- |
| Started by a button | A click changes no input; a Retry button is the sharp case, since an unchanged value de-duplicates and nothing fires. |
| Reports progress as it runs | A mapping produces one value, not a stream. |
| Stopped by an explicit Cancel | "The user wants this to stop" is not an input. |
| Accumulates onto the previous value | A mapping depends on its input alone; an append also depends on the value it replaces, which superseding cannot order. Accumulating the results is `scan` over the output. |

The amount of data returned and the weight of the work are not criteria: a
thread is started either way.

- The seed is required, as in §5.2, but means "no run has landed yet",
  because no run starts at construction: building a ViewModel must not fire
  I/O.
- Failure is a value. `fn` catches what the UI must render and returns it in
  the app's own result type, so one value decides both the error and the
  items it replaces, and the result stays a plain observable whose only read
  surface is `.value`. An exception that escapes `fn` is a bug: logged
  through `exception_once`, delivered to nobody.
- `CancelToken` is cooperative and optional. Python cannot interrupt a
  thread, so superseding discards the result and the worker runs to
  completion; a run that checks the token can return early, and one that
  blocks in a single call never gets the chance. It is still the second
  positional parameter of every `fn`, because a signature cannot be widened
  later without breaking every existing one, and against a hand-rolled
  `threading.Event` it removes the ways to misuse one: no `clear()`, one
  token per run.
- A superseded run's result never lands, from any path. The test is identity
  against the live token at delivery, not a flag read earlier, so a result
  returned from `fn`'s own `except` or `finally` is discarded like any other.
- `.value` is the last landed result; `dispose()` supersedes whatever is in
  flight; results are marshalled to the UI thread (§4.4).
- `fn` is synchronous. Accepting `async def` behind the same name would mean
  two supersede implementations; widening later is additive.

A companion `results.error` observable was rejected: it does not survive
`.map()`, so a binding built from the result cannot see it; it needs its own
supersede test, clearing rule and batching; and it decides only the error,
never the accompanying value, leaving a failed run's error above the previous
run's rows.

`SwitchMappedObservable` (`observable/switched.py`) subclasses
`SourceSubscribingObservable[TIn, TOut]`. Each run gets a fresh `CancelToken`
and a daemon thread named `switch_map:<fn qualname>`, so a test joins workers
instead of sleeping. Delivery stages the result under a lock only if the
delivering token is still current, then schedules `_flush` on the clock, and
`_flush` re-reads the stage, so a result superseded in between is still
dropped. `exception_once` is keyed on the function's qualname, so two
`switch_map`s cannot de-duplicate each other's bug into silence.

### 5.4 Accumulation: `scan`

A value that follows from every emission rather than from the source's
current one: how many times something fired, a running total, a list
appended to. The scope is accumulation over an operator's output. An
`Observable` is mutable state, so accumulating a user action is one line in
the handler; `debounce`, `throttle` and `switch_map` publish because time
passed or a run landed, so there is no handler to hold that line, and without
`scan` the only way in is `subscribe`: an empty `Observable` beside the write
that fills it, plus a `Disposable` that must be held or the value silently
stops moving.

- The seed is required, as in §5.2 and §5.3, meaning "the source has emitted
  nothing". The construction-time value is not folded in: it has not been
  emitted, and folding it would start a counter at 1 and count a debounce
  window that never settled.
- One emission out per emission in. A fold landing on the accumulator it
  already held still emits, because the fold ran; a repeated source value
  folds once, since `_ObservableValue` de-dupes before it notifies.
- The accumulator never re-seeds. It belongs to this observable rather than
  to the chain: a rebuilt chain is a new observable that starts from `initial`
  again.
- `fn` is a pure function of the two values handed to it, run untracked
  (§4.3); a raising `fn` leaves the accumulator as it stood (§7).

`fold` was rejected as the name: it states a terminal result, and what is
published here is every intermediate accumulator. `accumulate` matches
`itertools` at the cost of length. `scan` is not a second name, since no
existing operator accumulates.

`ScannedObservable` (`observable/scanned.py`) subclasses
`SourceSubscribingObservable[TIn, TAcc]`; `_seed` returns `initial` without
reading the source.

## 6. Binding an Observable to a Widget: the Value Cell

Every input widget holds a value somewhere. Passing an observable to its
constructor **substitutes that storage cell**; it does not describe a
direction of flow. `Toggleable` states the rule in code:

```python
def _get_state_obj(self):
    if self._state_external is not None:
        return self._state_external
    return self._state_internal
```

Both the read path and the write path go through `_get_state_obj()`, and only
one of the two cells is ever live. With a single cell there is no second copy
to keep in sync and no direction to choose: the user's edit lands wherever the
widget's value lives, which is the caller's observable when the caller
supplied one. Two-way binding is a consequence of the structure, not a mode;
`Checkbox`, `Switch`, `RadioButton`, `RadioGroup` and the sliders all behave
this way without implementing it.

Three consequences follow:

- **A widget does not keep its own copy alongside an external observable.**
  Two cells make a direction expressible, and any direction chosen is wrong
  half the time. Where a widget's internal representation is richer than what
  the caller's observable can hold, the widget mirrors instead of
  substituting, and the mirror is justified in
  [TEXT_EDITING.md](TEXT_EDITING.md), the one such case.
- **A read-only observable is display-only**, because there is nothing to
  write to. That is what a computed or mapped value is, and it is how a caller
  asks for display without an edit path.
- **The distinction is enforced at runtime, not by the type checker.**
  Whether a source is writable is decided by
  `isinstance(value, ObservableProtocol)`, which separates the two protocols
  by the presence of `set`. A static overload cannot express it: both arms
  take the same argument and return the same widget, so there is nothing for
  the checker to discriminate on. That is why no operator may hand back a
  read-only static type over a runtime-writable object: it would produce a
  source the caller declared display-only that a widget then writes to, and
  no runtime check could catch it. A genuine read-only view has to be a real
  wrapper object, so that the runtime agrees with the type.

### 6.1 When the Caller's Type Is Not the Widget's Input Type

A text field edits `str`; applications want dates, amounts, quantities. This
looks like the one case §6 cannot serve, since the two sides hold different
types. The answer is not a mirror but an inversion: **the text is the cell;
the typed value is derived from it.**

```python
self.arrival_text = nv.Observable("")            # the cell, bound to the field
self.arrival = self.arrival_text.map(parse_date)  # derived, read-only
```

A widget's value type therefore follows its primary input mechanism, not the
type the application finds most convenient. `DockedDatePicker` binds `str`
because it can be typed into; `DatePicker`, the inline calendar, binds
`date | None` because it cannot. Three things rule out keeping the typed
value as the cell:

- **The mirror exception does not stretch this far.** The text-editing
  mirror is a total enrichment: text plus selection contains the text, so the
  two always agree about the value. A conversion is partial, `"06/1"` is not
  a date. A widget mirroring across a partial map has to invent a policy for
  the gap, and needs an error cell to express it; it is then the sole writer
  of that cell, so an application that wants to report a business-level
  error ("already booked") has to write to it too, and the two-writer problem
  reappears one level up. The gap is not a defect; it is the normal state of
  a field someone is typing into.
- **An observable-side conversion operator cannot see the commit.** Whether
  a value is finished is a widget event, Enter or focus leaving, that an
  `Observable` is not told about, so an operator-shaped conversion has to
  convert on every keystroke, the behaviour it was introduced to avoid.
  Commit-time work belongs on `on_submit` / `on_focus_change`, where the
  widget's own value already lives.
- **Derivation loses nothing.** `filter().map()` holds the last valid value,
  `map()` alone reports the invalid state, `debounce()` composes into the
  same chain, and the error message is one more `map()` of the same text:
  one writer, no disagreement possible.

This follows from reactivity being observable-driven. In a rebuild-driven
framework an application influences a widget by supplying values read during
rebuild, so a date field can accept a validity predicate and a set of error
strings and the application never owns a cell; Flutter's
`InputDatePickerFormField` is built that way. Here the cell is the influence
path, so handing the application the cell is the only way to give it control.

## 7. Failure Semantics

§5.3 states the rule for `switch_map`: failure the UI must render is a value,
not an exception. That rule holds for every callback the graph runs. **An
exception reaching the framework is always a bug**, never an outcome to
publish, and it cannot be raised, because there is no caller who could handle
it: a derivation re-runs because something changed, and "something" is a
clock callback marshalling a worker's write, a `debounce` timer, or an
unrelated handler three widgets away. Raising there decides only, by which
thread happened to be passing, whose stack the failure lands on.

**Every such bug is logged and contained**, through
`exception_once_per_exc`, keyed by the failure's own type and innermost
frame, so two broken derivations are reported separately and one that keeps
failing every keystroke stays a single line. The compute function's name
cannot do that job: every `.map()` shares one `compute_fn` closure inside
`ComputedObservable.map`, so keying on it would collapse unrelated bugs into
the first one reported. `switch_map` keys on the qualname because there the
user's own `fn` is what runs.

Containment is per callback, and what the observable holds is the previous
value:

| What raises | Where it is caught | What `.value` reports afterwards |
| :--- | :--- | :--- |
| a derivation (`map`, `combine().compute`, `Observable.compute`) | `ComputedObservable._recompute` | the previous value; no emission |
| a `filter` predicate | `FilteredObservable._passes` | the last value that passed; the tested value counts as not passing |
| a `switch_map` function | `SwitchMappedObservable._run` | the last landed result; the failed run publishes nothing |
| a `scan` function | `ScannedObservable._on_source_changed` | the accumulator as it stood; the failed fold publishes nothing |
| a subscriber | `_notify.notify_all` | unaffected; the remaining subscribers are still notified |

Keeping the previous value was chosen over propagating a sentinel, which would
leak into every consumer and every operator downstream. The cost is stated
plainly: a failed derivation is silently stale, and the log line is the only
signal, the trade `filter` already makes for a rejected value.

**A failed derivation is retried.** Its dependency edges are torn down before
each run and re-armed after it whether or not it succeeded, so the next change
to a source runs it again and a transiently broken derivation recovers on its
own. Leaving the edges down would be worse than the original bug: one log
line, then an observable frozen for the rest of the process. The one case
that cannot recover is a run that raised before reading anything, which has
no source to recover from.

**The subscriber guard is per callback, not one `try` around the loop.** A
single `try` would relocate the truncation: the first raising subscriber
would still stop every one registered after it, which is what makes the
symptom "a binding that sometimes does not update", with registration order
deciding who breaks. The loop also re-reads the value per callback, because a
subscriber may write back to the observable notifying it (§6's cell, where an
application normalises what a text field produced), and the subscribers after
it must be handed what that write left behind.

**The graph's own subscriptions are exempt.** A computed's dependency edges
and a wrapper's edge to its source are tagged `mark_internal_subscription`
(§4.1), and an exception on one of them re-raises rather than being logged.
Such an exception is the framework's own signal, not a broken subscriber: the
batch queue's infinite-loop detector reaches the notify loop through exactly
this path, and swallowing it would turn a loud protection into a silent one.
Every internal edge that runs application code guards it at its own site,
where the log can name what broke.

`observable/_notify.py` holds the one notify loop, used by
`_ObservableValue`, `ComputedObservable` on both the direct and the
marshalled path, and `SourceSubscribingObservable`.
`ComputedObservable._recompute` records success in a sentinel-typed local and
assigns `_value` only on success, so "keep the previous value" is the absence
of a write rather than a restore. An equality check that raises after a
recompute (`computed_value_eq_exc`) is treated as "not equal", which emits
rather than suppresses.
