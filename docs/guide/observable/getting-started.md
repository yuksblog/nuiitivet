---
layout: default
---

# Observable: Getting Started

Observables are the foundation of reactive state management in nuiitivet.
They let you model values that notify subscribers when updated.

## Quick Start

### Basic Usage

The most intuitive way to define Observables is inside `__init__`, like normal instance fields.

```python
import nuiitivet as nv

class Counter:
    def __init__(self):
        self.count = nv.Observable(0)
        self.double_count = self.count.map(lambda c: c * 2)

counter = Counter()
counter.count.subscribe(lambda value: print(f"Count: {value}"))
counter.count.value = 1  # -> "Count: 1"
```

### Integration with UI

```python
import nuiitivet as nv
from nuiitivet import material

class CounterApp:
    def __init__(self):
        self.count = nv.Observable(0)

    def build(self):
        return nv.Column(
            children=[
                material.Text(text=self.count.map(lambda c: f"Count: {c}")),
                material.FilledButton(
                    text="Increment",
                    on_click=lambda: self.increment()
                )
            ]
        )

    def increment(self):
        self.count.value += 1
```

## Core Concepts

### What is an Observable?

An Observable is a value you can observe. When it changes, all subscribers are notified.

**Features:**

- ✅ Intuitive usage (close to normal variables)
- ✅ Automatic change notifications
- ✅ Automatic cleanup to reduce memory leak risk
- ✅ Efficient grouped updates with `batch()`

### Class Attributes (Advanced)

You can also define an Observable as a class attribute (descriptor pattern).

```python
from nuiitivet.observable import Observable

class Model:
    value = Observable(0)

x = Model()
y = Model()

x.value.value = 10
y.value.value = 20  # independent per instance
```

**Benefits:**

- Better debugging: descriptors can know their field name.
- Lazy backing storage: useful for large optional state sets.

**Limitations:**

- Computed state (e.g. `.map()`) is usually better defined in `__init__`.
- Mixed style can scatter state definitions.

For most cases, start with instance attributes in `__init__`.

---

## Next Steps

- [Basic API](basic-api.md)
- [Operators](operators.md)
- [State Management Overview](../observable.md)
