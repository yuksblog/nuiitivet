# Basic API

## Creating a State

```python
import nuiitivet.material as nv

name = nv.State("Alice")
age = nv.State(20)
items = nv.State([])
```

## Getting and Setting Values

```python
current = age.value
age.value = 21
```

### Writing from a lambda

`age.value = 21` is a statement, and a Python lambda can only hold an
expression — so it cannot be used in a callback prop or a `subscribe` lambda.
`set()` is the same write in expression form:

```python
nv.Button("Increment", on_click=lambda: age.set(age.value + 1))
```

Use `.value =` wherever a statement fits; reach for `set()` only where one does
not. Both go through the identical write path, so equality de-duping, `compare`,
batching and thread dispatch behave the same either way.

## Subscribing and Unsubscribing

```python
subscription = age.subscribe(lambda value: print(value))
subscription.dispose()
```

Inside a widget, `self.bind(age.subscribe(...))` disposes the subscription when
the widget unmounts.

## Custom Comparison Function

By default, value equality uses `==`.

```python
count = nv.State(0)
```

You can customize comparison behavior when needed.

```python
always_notify = nv.State(0, compare=lambda a, b: False)

def compare_users(a, b):
    if a is None or b is None:
        return a is b
    return a.uid == b.uid

user = nv.State(None, compare=compare_users)
```

---

## Next Steps

- [Operators](operators.md)
- [State Management Overview](index.md)
