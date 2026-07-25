# Observable: Operators

## `.map(fn)`

Use `.map(fn)` to transform the value of a single Observable into another derived value.

```python
import nuiitivet.material as nv

age = nv.Observable(20)
is_adult = age.map(lambda x: x >= 18)

is_adult.subscribe(lambda v: print(f"Adult: {v}"))
age.value = 15  # Adult: False
age.value = 20  # Adult: True
```

## `.combine(other).compute(fn)`

Use this pattern when you need to compute a derived value from exactly two Observables.

```python
price = nv.Observable(100)
quantity = nv.Observable(2)
total = price.combine(quantity).compute(lambda p, q: p * q)
```

## `combine(a, b, ...).compute(fn)`

Use this form to combine three or more Observables in a single derived computation.

```python
import nuiitivet.material as nv

price = nv.Observable(100)
quantity = nv.Observable(2)
discount = nv.Observable(0.1)

total = nv.combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)
```

## `Observable.compute(fn)`

`Observable.compute(fn)` is useful for complex logic and conditional branches where dependencies may change dynamically.

```python
class Cart:
    def __init__(self):
        self.show_detail = nv.Observable(True)
        self.price = nv.Observable(100)
        self.quantity = nv.Observable(2)

        self.display = nv.Observable.compute(lambda: (
            f"¥{self.price.value * self.quantity.value:,}"
            if self.show_detail.value
            else "---"
        ))
```

## Operator Selection Guide

```python
# 1:1 transformation
is_adult = age.map(lambda x: x >= 18)

# 2 observables
subtotal = price.combine(quantity).compute(lambda p, q: p * q)

# 3+ observables
total = nv.combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)

# complex branching
display = nv.Observable.compute(lambda: (
    self.tax_included.value if self.show_tax.value
    else self.tax_excluded.value
))
```

## Keep Transformations Pure

The function you pass to `.map()` / `.compute()` should be a pure transformation:
derive a value from the observable inputs and return it, with no side effects.
These functions re-run whenever a dependency changes (and may be deferred to a
later frame), so side effects performed inside them — mutating other observables,
driving widgets — fire unpredictably.

Return the derived value and bind it where you need it (for example, pass the
resulting observable straight to a widget) instead of updating state from inside
the transform.

```python
# ❌ bad: the transform mutates a separate observable as a side effect
label = nv.Observable("")
nv.Text(label)

def update_label(c):
    label.value = f"Count: {c}"  # side effect, not a returned value

count.map(update_label)  # the mapped result is unused

# ✅ good: the transform returns a value; bind the widget to it
count_label = count.map(lambda c: f"Count: {c}")
nv.Text(count_label)
```

## Performance Note

- `.map()` and `.combine()` internally leverage compute-like mechanisms.
- Prefer explicit dependencies (`map`, `combine`) for readability.
- Use `Observable.compute()` for branching and complex dependency paths.

---

## Next Steps

- [Practical Controls](practical_controls.md)
- [Thread Safety](thread_safety.md)
- [State Management Overview](index.md)
