# Observable: Patterns and Recipes

## ViewModel Pattern

Keep source state and derived state in a ViewModel, and keep rendering logic in the View.

This pattern makes responsibilities clear:

- The ViewModel owns state transitions and business logic.
- The View only renders and forwards user actions.
- Derived values (such as counts and flags) are centralized and reusable.

As a result, code becomes easier to test, reason about, and maintain.

```python
import nuiitivet.material as nv

class TodoViewModel:
    items = nv.Observable([])
    selected_item = nv.Observable(None)

    def __init__(self):
        self.item_count = self.items.map(lambda items: len(items))
        self.has_items = self.item_count.map(lambda count: count > 0)

    def add_item(self, text: str):
        with nv.batch():
            current = self.items.value
            self.items.value = current + [{"text": text, "done": False}]
```

In this structure, the View does not mutate low-level state directly.
It only invokes ViewModel methods, while rendering uses Observable-derived values.

```python
import nuiitivet.material as nv

class TodoView:
    def __init__(self, vm: TodoViewModel):
        self.vm = vm

    def build(self):
        return nv.Column(
            children=[
                nv.Text(self.vm.item_count.map(lambda c: f"Items: {c}")),
                nv.Button(
                    text="Add",
                    on_click=lambda: self.vm.add_item("New item")
                , style=nv.ButtonStyle.filled()),
            ]
        )
```

## Derived State Composition

Use derived state composition when one value should be computed from other observables.
This keeps calculation logic in one place and avoids duplicating the same formula across multiple views.
It also makes changes safer because you only update the derivation once.

```python
import nuiitivet.material as nv

class ShoppingCart:
    items = nv.Observable([])
    tax_rate = nv.Observable(0.1)

    def __init__(self):
        self.subtotal = self.items.map(
            lambda items: sum(item["price"] * item["qty"] for item in items)
        )
        self.total = nv.combine(self.subtotal, self.tax_rate).compute(
            lambda sub, rate: sub * (1 + rate)
        )
```

## Typed Values from Text Input

A text field's value is a string; your application's value usually is not.
Bind the text and derive the value from it — do not keep an `Observable[int]`
and write the text back into it. Two observables holding the same thing have to
be kept in step, and the field ends up reformatting itself under the user's
cursor.

```python
import nuiitivet.material as nv


def to_int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


class OrderForm:
    def __init__(self):
        self.qty_text = nv.Observable("1")      # the field writes into this
        self.qty = self.qty_text.map(to_int)    # the rest of the app reads this
```

Deriving never touches the text: `"007"` stays `"007"` in the field while `qty`
reads `7`.

### What text that will not convert becomes

`map()` converts every value the text takes, so text it cannot read becomes
`None` — something the rest of the app can act on:

```python
nv.Button("Order", disabled=self.qty.map(lambda n: n is None))
```

`filter()` instead passes only the values its predicate accepts, so one it
refuses leaves the previous result standing — including an empty field. Reach
for it when the value drives something that is worse blank than stale:

```python
self.results = self.query.filter(lambda q: len(q) >= 3, initial="").map(search)
```

See [Practical Controls](practical_controls.md) for both operators. The
predicate reads the text as it is, so a natural-looking `str.isdigit` refuses a
pasted `" 12 "` that `int()` would have read.

### Wiring the error state

Derive one `str | None` — `None` meaning nothing is wrong — and read both
`is_error` and `supporting_text` off it. Deriving each from the text separately
writes the same judgement twice, and the two can drift apart.

```python
import nuiitivet.material as nv


def arrival_error(text: str) -> str | None:
    if not text:
        return None
    arrival = nv.parse_date(text)
    if arrival is None:
        return "Invalid date"
    if arrival in BOOKED:        # a valid date can still be unacceptable
        return "Already booked"
    return None


class Booking:
    def __init__(self):
        self.arrival_text = nv.Observable("")
        self.arrival = self.arrival_text.map(nv.parse_date)
        self.error = self.arrival_text.map(arrival_error)

    def build(self):
        return nv.DockedDatePicker(
            value=self.arrival_text,
            supporting_text=self.error,
            is_error=self.error.map(lambda e: e is not None),
        )
```

`is_error` is separate from the message because it does something different: it
recolors the whole field. A field can be flagged without a message, and carry a
message without being flagged.

### Keeping unwanted text out

`input_filter` decides what may land in the field at all, before any of the
above. It runs on paste as well as typing, so `nv.digits_only()` turns a pasted
`"1,234"` into `"1234"` in the field itself — see
[TextField](../design-system/material_widgets.md#textfield).

It says what is *typeable*, not what is *valid*: `"1."` has to be typeable or
the decimal point could never be entered. Whether a finished value is
acceptable stays with the derivation above.

### Binding a derived value by mistake

A derived observable has no setter, so binding one as a field's `value` gives a
display-only field:

```python
nv.TextField(value=self.qty.map(str))   # renders, but cannot be typed into
```

Bind the observable you created, and derive from it — never the other way round.

---

## Next Steps

- [State Management Overview](index.md)
- [Concurrency: choosing a tool](../concurrency.md)
