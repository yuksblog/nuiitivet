# Concurrency: choosing a tool

Work that takes time — a search, a file read, a long import — must not run on
the UI thread, or the window stops painting until it finishes. Its result must
not reach a widget from the thread that produced it either.

Both halves already have answers, and none of them involve writing marshalling
code by hand. Find your situation below.

## Which tool

| Your situation | Reach for | Read |
| --- | --- | --- |
| A value derived from another, asynchronously — the `map` whose transform takes time. A `SearchBar` that searches as you type | `switch_map` | [Async State](state-management/async_state.md) |
| I/O in an event handler, and the screen just waits for it | an `async` handler, awaiting the call — no thread involved | |
| Heavy work in an event handler, and the screen just waits for it | an `async` handler, `await asyncio.to_thread(...)` — a thread, but the runtime owns it | [Thread Safety](state-management/thread_safety.md#short-work-await-it-instead-of-managing-a-thread) |
| The same heavy work, but it should report progress and be cancellable | a hand-written worker thread | [Background Work](state-management/background_work.md) |
| Values arriving faster than the screen needs them | `debounce()` / `throttle()` | [Practical Controls](state-management/practical_controls.md) |
| Getting a worker's result onto the UI thread | nothing — an observable write is marshalled for you | [Thread Safety](state-management/thread_safety.md) |
| A consumer that must see every intermediate value, not the newest | `dispatch=False` | [Thread Safety](state-management/thread_safety.md#opting-out-dispatchfalse) |
| Testing an `async` handler | `await app.idle()`, `await app.wait_for(...)` | [Testing async flows](testing/async.md) |
| Testing a write that came from a worker thread | `app.settle()` | [Thread Safety](state-management/thread_safety.md#testing) |
