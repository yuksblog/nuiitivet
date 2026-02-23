---
layout: default
---

# Observable: Operators

## `.map(fn)`

Use `.map(fn)` to transform the value of a single Observable into another derived value.

```python
from nuiitivet.observable import Observable

age = Observable(20)
is_adult = age.map(lambda x: x >= 18)

is_adult.subscribe(lambda v: print(f"Adult: {v}"))
age.value = 15  # Adult: False
age.value = 20  # Adult: True
```

## `.combine(other).compute(fn)`

Use this pattern when you need to compute a derived value from exactly two Observables.

```python
price = Observable(100)
quantity = Observable(2)
total = price.combine(quantity).compute(lambda p, q: p * q)
```

## `combine(a, b, ...).compute(fn)`

Use this form to combine three or more Observables in a single derived computation.

```python
from nuiitivet.observable import Observable, combine

price = Observable(100)
quantity = Observable(2)
discount = Observable(0.1)

total = combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)
```

## `Observable.compute(fn)`

`Observable.compute(fn)` is useful for complex logic and conditional branches where dependencies may change dynamically.

```python
class Cart:
    def __init__(self):
        self.show_detail = Observable(True)
        self.price = Observable(100)
        self.quantity = Observable(2)

        self.display = Observable.compute(lambda: (
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
total = combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)

# complex branching
display = Observable.compute(lambda: (
    self.tax_included.value if self.show_tax.value
    else self.tax_excluded.value
))
```

## Performance Note

- `.map()` and `.combine()` internally leverage compute-like mechanisms.
- Prefer explicit dependencies (`map`, `combine`) for readability.
- Use `Observable.compute()` for branching and complex dependency paths.

---

## Next Steps

- [Practical Controls](practical-controls.md)
- [Thread Safety](thread-safety.md)
- [State Management Overview](../observable.md)
