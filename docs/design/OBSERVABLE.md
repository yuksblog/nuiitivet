# Observable & Reactive Programming

This document summarizes the internal design of the Observable and reactive system in `nuiitivet`.
For a usage guide, see [docs/guide/state-management/index.md](../guide/state-management/index.md).

See also:

- [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md)
- [THREADING_MODEL.md](THREADING_MODEL.md)
- [PROGRAMMING_PARADIMS.md](PROGRAMMING_PARADIMS.md)

## 1. Core design: Ownerless observables with unified batching

- Observable descriptors are now **ownerless**: they emit immediate notifications in any layer (domain models, services, widgets) without relying on framework mixins or hidden hooks.
- A global `batch()` context (backed by `contextvars`) unifies batching semantics. It supports nesting, records dirty `_ObservableValue` instances, and queues ComputedObservables so they recompute exactly once when the outermost batch exits. This delivers glitch-free updates even when multiple observables change within a single handler.
- The UI layer automatically wraps pointer/key/focus dispatch in `batch()`, so widget authors simply mutate state inside event handlers. Business logic stays explicit: `with batch():` clusters related updates only when needed, keeping the learning cost low.
- Binding updates continue to flow through `_queue_binding_invalidation()` and flush alongside scope recompositions before paint. The binding queue and the batching context complement each other: batch reduces redundant recompute work, while the queue ensures widget invalidations happen once per frame.

## 2. Method-chained reactive operators (Phase 1 complete)

The framework provides a minimal, unified API for reactive transformations inspired by ReactiveProperty (WPF) and Signals (Solid.js).

**Design principles:**

- **Unified syntax**: All reactive operations use method chaining for consistency
- **Explicit over implicit**: Dependencies are clear in simple cases (`.map()`, `.combine()`), automatic tracking handles complex cases (`.compute()`)
- **Minimal API surface**: Only essential operators to reduce learning cost and API confusion
- **Gradual learning curve**: Beginners start with `.map()`, advance to `.combine()`, master `.compute()` for complex scenarios

**Implemented operators:**

| Operator | Use case | Example |
| :--- | :--- | :--- |
| `.map(fn)` | 1:1 transformation | `age.map(lambda x: x >= 18)` |
| `.combine(other)` | Explicit multi-source composition (method form) | `price.combine(qty).compute(lambda p, q: p * q)` |
| `combine(a, b, ...)` | Explicit multi-source composition (function form, 3+ sources) | `combine(price, qty, discount).compute(lambda p, q, d: ...)` |
| `Observable.compute(fn)` | Automatic dependency tracking for complex logic | `Observable.compute(lambda: self.a.value if self.flag.value else self.b.value)` |

**Why this API over Rx-style operators:**

- **No `combine_latest`**: Redundant with `.combine().compute()`
- **No `select` / `where`**: Aliases cause confusion
- **No `zip` / `merge`**: Low usage frequency in UI frameworks
- **No `filter`**: Initial value semantics are problematic for UI binding

**Implementation strategy:**

- `.map()` and `.combine()` internally use `Observable.compute()` for automatic dependency tracking
- Signals pattern with global `_tracking_context` (via `contextvars`) captures `.value` access during compute functions
- Dynamic dependency re-collection on every recompute handles conditional logic correctly
- Full integration with `batch()` system prevents redundant computations

## 3. Thread safety: UI dispatch by default, with an explicit opt-out

**Problem:** Worker threads updating observables can trigger UI updates from non-UI threads, causing crashes.

**Design decision:** **Default to safe (marshal to the UI thread), opt out with `dispatch=False`** (#538)

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

1. **The unsafe case must not be the quiet one.** Under default-off, forgetting a single call produced a crash or silent tree corruption whose cause was nowhere near the symptom. Under default-on, forgetting `dispatch=False` costs some coalescing on a value nothing renders.
2. **Cost is small and bounded.** The added per-write work is one integer comparison against a cached UI-thread ident (~75 ns, ~9.5% of a write). `threading.current_thread()` was the expensive part and is gone.
3. **The opt-out carries real information.** `dispatch=False` states "no widget binds to this, and every intermediate value matters" — which the reader could not previously infer from the absence of a call.

**Reversal of the original decision.** This section first argued for default-off on zero-overhead and gradual-learning grounds. Both survive in weaker form: the overhead it avoided is now measured and small, and the learning curve it protected was in practice a trap, since the failure mode appears only under threading, only sometimes, and never at the line that caused it.

**Implementation:**

- `_ObservableValue`, `Observable` and `ComputedObservable` take `dispatch: bool = True`
- The thread test is `nuiitivet.runtime.threading.is_ui_thread()` — a cached-ident comparison, and the single definition of "the UI thread" for both this and `assert_ui_thread()`
- The setter marshals through the installed clock (`runtime.clock.schedule_once(..., 0)`), coalescing to one scheduled flush per tick
- `batch()` dispatches its flush to the UI thread if any observable in the batch dispatches
- `map()` propagates the **opt-out**; `combine(...).compute(...)` dispatches unless every source opted out, and takes an explicit `dispatch=` to override

**Constraints:**

- Compute functions execute on the triggering thread (may be a worker thread)
- Only notifications are marshalled to the UI thread
- Compute functions must NOT access UI-thread-only objects (widgets, UI state) - only observable values
- A marshalled write is asynchronous and coalesced: the writer reads back the old value until the next tick, and intermediate values are dropped

## 4. Timing control: Debounce and throttle (Phase 2 complete)

**Problem:** High-frequency events (typing, mouse moves, API responses) can trigger excessive UI updates and expensive computations.

**Solution:** Observable timing operators that integrate with the UI event loop:

| Operator | Behavior | Use case |
| :--- | :--- | :--- |
| `.debounce(seconds)` | Emits only after `seconds` of silence | Search input, form validation |
| `.throttle(seconds)` | Emits first value immediately, then throttles to max 1 per `seconds` | Mouse tracking, scroll position |

**Design principles:**

1. **UI thread integration**: Use `pyglet.clock.schedule_once()` for timing to ensure thread safety
2. **Chainable operators**: Work seamlessly with `.map()`, `.combine()`, `.compute()`
3. **Cancellation semantics**:
   - Debounce: Each new value cancels pending timer and starts fresh delay
   - Throttle: First value emits immediately, subsequent values sampled at intervals
4. **Memory efficiency**: Only hold reference to latest value, cancel timers on unsubscribe

**Implementation:**

```python
# Debounce example: Search input
class SearchBox:
    query = Observable("")

    def __init__(self):
        # Delay search until user stops typing for 0.5s
        self.query.debounce(0.5).subscribe(lambda q: perform_search(q))

# Throttle example: Mouse tracking
class MouseTracker:
    position = Observable((0, 0))

    def __init__(self):
        # Update UI at most once per 0.1s
        self.position.throttle(0.1).subscribe(lambda pos: update_tooltip(pos))
```

**Integration with other operators:**

```python
# Debounce + map
query.debounce(0.5).map(str.lower)

# Throttle + combine + compute
mouse_pos.throttle(0.1).combine(viewport).compute(lambda pos, vp: is_inside(pos, vp))
```

**Rationale:**

1. **Debounce default**: Most UI event filtering needs debounce (typing, window resize)
2. **Throttle for sampling**: Mouse moves and scroll need periodic sampling, not trailing edge
3. **Explicit timing**: Seconds parameter makes performance impact visible in code
4. **Framework integration**: `pyglet.clock` ensures timers run on correct thread and integrate with event loop

**Implementation details:**

- `DebouncedObservable` and `ThrottledObservable` classes wrap upstream observable
- Both support full observable protocol: `.map()`, `.subscribe()`, chaining
- Timer cancellation happens in `__set__()` to prevent memory leaks
- Testing uses `MockClock` with epsilon tolerance for deterministic timing assertions
