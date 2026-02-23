---
layout: default
---

# Observable: Practical Controls

## `batch()`

Use `batch()` to group related updates and avoid redundant recalculations.

This is especially useful when multiple source observables affect the same derived value.

```python
from nuiitivet.observable import Observable, batch

price = Observable(100)
quantity = Observable(2)
total = price.combine(quantity).compute(lambda p, q: p * q)

with batch():
    price.value = 200
    quantity.value = 3
```

Inside UI event handlers, batching is commonly applied automatically.

## `debounce()`

Use `debounce()` when you want to run logic only after input has settled for a period of time.

```python
from nuiitivet.observable import Observable

query = Observable("")
debounced_query = query.debounce(0.5)
debounced_query.subscribe(lambda q: print(f"search: {q}"))
```

Typical use cases are search boxes, validation, and autosave.

## `throttle()`

Use `throttle()` when you need periodic sampling for high-frequency updates.

```python
mouse_x = Observable(0)
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

## Chaining

```python
formatted_query = (
    query
    .debounce(0.5)
    .map(lambda q: q.strip().lower())
    .dispatch_to_ui()
)

position_display = (
    mouse_x
    .throttle(0.1)
    .combine(mouse_y.throttle(0.1))
    .compute(lambda x, y: f"({x}, {y})")
)
```

---

## Next Steps

- [Thread Safety](thread-safety.md)
- [Patterns and Recipes](patterns-and-recipes.md)
- [State Management Overview](../observable.md)
