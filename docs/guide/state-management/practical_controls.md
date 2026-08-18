# Observable: Practical Controls

## `batch()`

Use `batch()` to group related updates and avoid redundant recalculations.

This is especially useful when multiple source observables affect the same derived value.

```python
import nuiitivet.material as nv

price = nv.Observable(100)
quantity = nv.Observable(2)
total = price.combine(quantity).compute(lambda p, q: p * q)

with nv.batch():
    price.value = 200
    quantity.value = 3
```

Inside UI event handlers, batching is commonly applied automatically.

## `debounce()`

Use `debounce()` when you want to run logic only after input has settled for a period of time.

```python
import nuiitivet.material as nv

query = nv.Observable("")
debounced_query = query.debounce(0.5)
debounced_query.subscribe(lambda q: print(f"search: {q}"))
```

Typical use cases are search boxes, validation, and autosave.

## `throttle()`

Use `throttle()` when you need periodic sampling for high-frequency updates.

```python
mouse_x = nv.Observable(0)
throttled_x = mouse_x.throttle(0.1)
throttled_x.subscribe(lambda x: print(f"x={x}"))
```

Typical use cases are scrolling, pointer movement, resize handling, and real-time streams.

## `debounce` vs `throttle`

| Feature | debounce | throttle |
| ------ | ---------- | ---------- |
| First change | Wait | Execute immediately |
| Continuous changes | Keep waiting | Execute periodically |
| Last change | Always execute | Depends on timing |
| Execution count | Minimized | Regular |

## `filter()`

Use `filter()` when only some of the source's values should reach the UI.
`initial` is required: it is what the observable reports until a value passes.

```python
amount = nv.Observable(0)
last_valid = amount.filter(lambda n: n > 0, initial=0)

nv.Text(last_valid.map(str))
```

Values the predicate rejects change nothing — no notification, and `.value` keeps
reporting the last one that passed. At construction the source's current value is
tested too, so `initial` shows only when nothing has passed.

The predicate must be a pure function of the value it is handed. Reading another
observable inside it does not create a dependency, so the filter will not re-run
when that observable changes — use `combine()` for that.

## Binding into a widget

A `debounce()` / `throttle()` / `filter()` result holds the value it last emitted,
so pass it into a widget the same way you would any other observable:

```python
nv.Text(query.debounce(0.5))
```

Until the first emission it reports its seed — for `debounce`, the value the
source had when the chain was built, which is what you see until the input first
settles; `throttle` emits on the first change, so it moves right away; `filter`
reports `initial` until something passes.

## Chaining

```python
formatted_query = (
    query
    .debounce(0.5)
    .map(lambda q: q.strip().lower())
)

position_display = (
    mouse_x
    .throttle(0.1)
    .combine(mouse_y.throttle(0.1))
    .compute(lambda x, y: f"({x}, {y})")
)

long_enough_query = (
    query
    .map(lambda q: q.strip())
    .filter(lambda q: len(q) >= 3, initial="")
)
```

---

## Next Steps

- [Thread Safety](thread_safety.md)
- [State Management Overview](index.md)
