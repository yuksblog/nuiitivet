# Dynamically Generating a List from Data

Screens often need to render a collection of items — tags, cards, list rows —
whose contents come from data rather than being written out one by one.
NuiiTivet offers three ways to do this, from the simplest static form to a
fully reactive one.

## Static: List Comprehension

When the data is fixed at build time, a plain Python list comprehension is all
you need. Each item is turned into a widget inline:

```python
import nuiitivet as nv
import nuiitivet.material as md

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow(
    main_gap=8,
    cross_gap=8,
    children=[
        md.Card(md.Text(tag), style=md.CardStyle.outlined()) for tag in tags
    ],
)
```

This is the right choice when the collection does not change after the layout is
built. If the list can change at runtime and you want the layout to update
automatically, use `builder()` instead.

## `builder()` (Recommended)

`Row`, `Column`, `Stack`, `Flow`, and `UniformFlow` all expose a `builder()`
class method that materializes children from a data collection:

```python
Row.builder(items, fn, ...)
```

- `items`: the source data collection — a plain list, or an **observable** for
  reactive updates.
- `fn`: a builder function with the signature `(item, index) -> Widget`, called
  once per item.

```python
import nuiitivet as nv
import nuiitivet.material as md

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow.builder(
    tags,
    lambda tag, index: md.Card(md.Text(tag), style=md.CardStyle.outlined()),
    main_gap=8,
    cross_gap=8,
)
```

`builder()` reads naturally: `Row.builder(items, ...)` says "a Row builds its
children from items", which matches the mental model of the widget owning its
own children. This is why it is the recommended approach for general use.

> **Note:** `Deck` does **not** support `builder()`. `Deck` switches between
> children by `index` rather than laying them all out, so it has no `builder()`
> method. Use it with an explicit list of children instead.

### Reactive Regeneration with an Observable

The essential value of `builder()` shows when you pass an **observable** as
`items`. The layout then subscribes to it and regenerates automatically whenever
the collection changes — and only the affected regions are invalidated, not the
whole layout:

```python
import nuiitivet as nv
import nuiitivet.material as md

class TagList:
    def __init__(self):
        self.tags = nv.Observable(["Python", "UI"])

    def build(self):
        return nv.Flow.builder(
            self.tags,
            lambda tag, index: md.Card(md.Text(tag), style=md.CardStyle.outlined()),
            main_gap=8,
            cross_gap=8,
        )

    def add(self, tag: str) -> None:
        # Reassigning .value pushes the change; the Flow regenerates its cards.
        self.tags.value = [*self.tags.value, tag]
```

With a static list you would have to rebuild and re-render the layout yourself.
With an observable, `builder()` keeps the children in sync with the data for you.

## `ForEach` (SwiftUI-like Style)

If you prefer a SwiftUI-style declaration, `ForEach` provides the same dynamic
generation as an embedded element inside a normal `children` list:

```python
import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.layout.for_each import ForEach

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow(
    main_gap=8,
    cross_gap=8,
    children=[
        ForEach(
            tags,
            lambda tag, index: md.Card(md.Text(tag), style=md.CardStyle.outlined()),
        ),
    ],
)
```

`ForEach` accepts the same `items` (including observables) and `(item, index) ->
Widget` builder, so it behaves identically to `builder()` at runtime.

> **Caveat:** written as `children=[ForEach(...)]`, it visually reads as a
> dynamic array nested inside another array, which can clash with the mental
> model of a flat child list. For that reason `builder()` is recommended for
> general use, with `ForEach` offered for those who prefer the SwiftUI-like
> expression.

## When to Use Which

| Situation | Approach |
| --- | --- |
| Collection is fixed at build time | List comprehension |
| Collection changes at runtime (dynamic) | `builder()` (recommended) |
| You prefer a SwiftUI-like declaration | `ForEach` |
