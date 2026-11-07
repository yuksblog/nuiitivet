# Dynamic Children

Screens often need to render a collection of items — tags, cards, list rows —
whose contents come from data rather than being written out one by one.
Nuiitivet offers several ways to do this, from the simplest static form to a
fully reactive one.

## Static: List Comprehension

When the data is fixed at build time, a plain Python list comprehension is all
you need. Each item is turned into a widget inline:

```python
import nuiitivet.material as nv

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow(
    main_gap=8,
    cross_gap=8,
    children=[
        nv.Card(nv.Text(tag), style=nv.CardStyle.outlined()) for tag in tags
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
nv.Row.builder(items, fn, ...)
```

- `items`: the source data collection — a plain list, or an **observable** for
  reactive updates.
- `fn`: a builder function with the signature `(item, index) -> Widget`, called
  once per item.

```python
import nuiitivet.material as nv

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow.builder(
    tags,
    lambda tag, index: nv.Card(nv.Text(tag), style=nv.CardStyle.outlined()),
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
import nuiitivet.material as nv

class TagList:
    def __init__(self):
        self.tags = nv.Observable(["Python", "UI"])

    def build(self):
        return nv.Flow.builder(
            self.tags,
            lambda tag, index: nv.Card(nv.Text(tag), style=nv.CardStyle.outlined()),
            main_gap=8,
            cross_gap=8,
        )

    def add(self, tag: str) -> None:
        # Reassigning .value pushes the change; the Flow regenerates its cards.
        self.tags.value = [*self.tags.value, tag]
```

With a static list you would have to rebuild and re-render the layout yourself.
With an observable, `builder()` keeps the children in sync with the data for you.

The Flow matches cards to tags by position. Inserting a tag at the front then
rebuilds every card. Pass `key_fn=lambda tag, index: tag` to match by tag. The
existing cards then stay.

## `lazy()` for a Long List

`Column.lazy()`, `Row.lazy()` and `UniformFlow.lazy()` take the same `items`
and builder as `builder()`, but build only the items the scrollable shows,
plus the next few ahead of the scroll while the app has nothing else to do:

```python
import nuiitivet.material as nv

rows = [f"Row {i}" for i in range(10_000)]

nv.Container(
    height=300,
    child=nv.VerticalScrollable(
        child=nv.Column.lazy(
            rows,
            lambda row, index: nv.Text(row, padding=(16, 8)),  # built as the row nears the view
            gap=4,
        ),
    ),
)
```

Every row gets the height of the first one. A taller row overlaps the next.
Pass `item_height=` (`item_width=` on a `Row`) when the first row is not
typical. `UniformFlow.lazy()` takes its row height from `aspect_ratio`, else
from the first item.

A row that scrolls well out of view is thrown away. It is built again from
the builder when it scrolls back in. A checkbox the user ticked inside the
row is unticked by then. Keep such state in the item data.

The lazy Column is as wide as the scrollable. `cross_alignment` places each row
inside that width. Outside a scrollable it builds only the rows that fit its
height. The rest are not drawn, where a plain `Column` would overflow.

## `ForEach` (SwiftUI-like Style)

If you prefer a SwiftUI-style declaration, `ForEach` provides the same dynamic
generation as an embedded element inside a normal `children` list:

```python
import nuiitivet.material as nv

tags = ["Python", "UI", "Framework", "Layout"]

nv.Flow(
    main_gap=8,
    cross_gap=8,
    children=[
        nv.ForEach(
            tags,
            lambda tag, index: nv.Card(nv.Text(tag), style=nv.CardStyle.outlined()),
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
| Collection is long: thousands of rows in a scrollable | `lazy()` |
| You prefer a SwiftUI-like declaration | `ForEach` |
