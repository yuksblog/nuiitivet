# Observable & Reactive Programming

本ドキュメントは `nuiitivet` の Observable とリアクティブ機構の内部設計をまとめます。
使い方のガイドは [docs/guide/observable.md](../guide/observable.md) を参照してください。

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

## 3. Thread safety: Explicit UI dispatch via method chaining

**Problem:** Worker threads updating observables can trigger UI updates from non-UI threads, causing crashes.

**Design decision:** **Default to fast (no dispatch), opt-in to safety via `.dispatch_to_ui()`**

```python
# UI layer (ViewModel) - explicit dispatch required
class ViewModel:
    items = Observable([])

    def __init__(self):
        self.items.dispatch_to_ui()  # Thread-safe for UI binding

    def load_async(self):
        def worker():
            result = fetch_data()
            self.items.value = result  # notify happens on UI thread
        threading.Thread(target=worker).start()

# Logic layer - default fast path
class DataProcessor:
    raw_data = Observable([])  # No dispatch = zero overhead

    def __init__(self):
        self.filtered = self.raw_data.map(lambda x: [i for i in x if i > 0])  # Fast by default
```

**Rationale for default-off:**

1. **Zero overhead for single-threaded apps** (most beginner use cases)
2. **Gradual learning curve**: Beginners ignore threading, intermediates learn `.dispatch_to_ui()` when needed
3. **Performance**: Logic-layer observable chains stay fast without UI thread hops
4. **Explicit intent**: UI-bound observables are clearly marked in code

**Implementation:**

- `.dispatch_to_ui()` is chainable on observable values and computed observables
- `_ObservableValue.__set__()` checks thread and uses `pyglet.clock.schedule_once()` to marshal notifications to UI thread when dispatch is enabled
- `batch()` automatically dispatches flush to UI thread if any observable in the batch has dispatch enabled
- Computed observables inherit dispatch setting via `CombineBuilder.dispatch_to_ui()` in method chains

**Constraints:**

- Compute functions execute on the triggering thread (may be worker thread)
- Only notifications are marshalled to UI thread
- Compute functions must NOT access UI-thread-only objects (widgets, UI state) - only observable values

## 4. Timing control: Debounce and throttle (Phase 2 complete)

**Problem:** High-frequency events (typing, mouse moves, API responses) can trigger excessive UI updates and expensive computations.

**Solution:** Observable timing operators that integrate with the UI event loop:

| Operator | Behavior | Use case |
| :--- | :--- | :--- |
| `.debounce(seconds)` | Emits only after `seconds` of silence | Search input, form validation |
| `.throttle(seconds)` | Emits first value immediately, then throttles to max 1 per `seconds` | Mouse tracking, scroll position |

**Design principles:**

1. **UI thread integration**: Use `pyglet.clock.schedule_once()` for timing to ensure thread safety
2. **Chainable operators**: Work seamlessly with `.map()`, `.combine()`, `.compute()`, `.dispatch_to_ui()`
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
# Debounce + map + dispatch
query.debounce(0.5).map(str.lower).dispatch_to_ui()

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
