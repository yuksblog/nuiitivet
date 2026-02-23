---
layout: default
---

# Observable: Basic API

## Creating an Observable

```python
from nuiitivet.observable import Observable

name = Observable("Alice")
age = Observable(20)
items = Observable([])
```

## Getting and Setting Values

```python
current = age.value
age.value = 21
```

## Subscribing and Unsubscribing

```python
subscription = age.subscribe(lambda value: print(value))
subscription.unsubscribe()
```

In most UI cases, cleanup is handled automatically by the framework lifecycle.

## Custom Comparison Function

By default, value equality uses `==`.

```python
count = Observable(0)
```

You can customize comparison behavior when needed.

```python
always_notify = Observable(0, compare=lambda a, b: False)

def compare_users(a, b):
    if a is None or b is None:
        return a is b
    return a.id == b.id

user = Observable(None, compare=compare_users)
```

---

## Next Steps

- [Operators](operators.md)
- [Practical Controls](practical-controls.md)
- [State Management Overview](../observable.md)
