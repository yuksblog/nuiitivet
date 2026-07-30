# Layout, sizing, spacing & modifiers

## The parameter principle

Size, alignment, and spacing are **parameters** of a widget, not separate wrapper
widgets. This is the deliberate difference from Flutter and the antidote to
nesting hell.

```python
# Correct
nv.Text("Hello", padding=12, width=200, alignment="center")

# Wrong (Flutter reflex): Padding(EdgeInsets.all(12), SizedBox(200, Text(...)))
```

Common parameters seen across widgets: `padding`, `width`, `height`, `gap`
(spacing between children of Row/Column), `alignment`, `cross_alignment`.

```python
nv.Column([a, b, c], gap=20, padding=20, cross_alignment="center")
nv.Row([x, y], gap=8, cross_alignment="center")
```

### padding tuple order — horizontal-first, NOT CSS

`padding` takes three forms:

- `int` → all four sides
- `(h, v)` → **horizontal** (left/right), then **vertical** (top/bottom)
- `(l, t, r, b)` → left, top, right, bottom

The 2-tuple is **horizontal-first**, the *opposite* of CSS's
`padding: <vertical> <horizontal>`. `padding=(16, 8)` = 16px left/right, 8px
top/bottom — do not carry over the CSS order. `None` means no padding.

## Alignment is positioning only — never sizing

Alignment answers *where to place* content in the remaining space. It does **not**
stretch or size anything — that is `width`/`height`/`Sizing`'s job. Do not bring
CSS flexbox habits here: there is no `stretch`, `fill`, `flex-start`, `flex-end`,
or `baseline`.

| Parameter | Valid values |
| --- | --- |
| `alignment` (single child) | `top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right` (and `start`/`center`/`end` on widgets like `Card`) |
| `main_alignment` (Row) | `start`, `center`, `end`, `space-between`, `space-around`, `space-evenly` |
| `main_alignment` (Column) | `start`, `center`, `end`, `space-between` |
| `cross_alignment` (Row/Column) | `start`, `center`, `end` |
| `origin` (`rotate`/`scale`) | same nine-point tokens (e.g. `top-left`, `bottom-center`), or an `(x, y)` tuple in local coords |

The **hyphen form is canonical** (`top-left`, `bottom-center`, ...). The
underscore form (`top_left`) is accepted as an alias for back-compat, but new
code should use hyphens. Unrecognized tokens emit a warning and fall back
rather than silently centering.

```python
# Wrong (CSS reflex): the alignment can't stretch the child to fill the cross axis
nv.Column([a, b], cross_alignment="stretch")

# Right: to fill, size the child; alignment only positions
nv.Column([a, b], cross_alignment="start")
a = nv.Text("x", width="100%")        # or width=nv.Sizing.flex()
```

Use `nv.CrossAligned(child, "center")` to override cross-axis position for one
child; its values are also `start`/`center`/`end` only.

## Sizing

Use `nv.Sizing` for flexible/auto sizing rather than hardcoding when a widget
should fill or hug its content: `nv.Sizing.auto()`, `nv.Sizing.fixed(n)`,
`nv.Sizing.flex()`, e.g. `width=nv.Sizing.flex()`.

## Adaptive layout with `on_size_changed`

To reflow on how much space a widget actually has, attach
`nv.on_size_changed(cb)` — it reports that widget's own measured `nv.Size`
(`.width` / `.height`) after every layout that changed it. There **is** a size
API; do not override `set_layout_rect` or any other layout hook to bridge size
into an Observable.

```python
class Panel(nv.ComposableWidget):
    def __init__(self) -> None:
        # Filling sizing: measure the space offered, not the content's size.
        super().__init__(width=nv.Sizing.flex(), height=nv.Sizing.flex())
        self._index = nv.Observable(0)                          # plain __init__

    def _on_size(self, size: nv.Size) -> None:
        self._index.value = 1 if size.width >= size.height else 0

    def build(self) -> nv.Widget:
        return nv.Deck(
            children=[portrait, landscape], index=self._index
        ).modifier(nv.on_size_changed(self._on_size))
```

- **No lifecycle override, no `Geometry`, no subscription.** The callback is
  attached to the widget itself (like `on_mount`, it adds no node to the tree),
  so the Observables it drives are created in a plain `__init__`.
- **It fires once with the first measurement**, so the callback alone seeds the
  state it drives. After that it fires only on an actual size change; a widget
  that merely moves is silent.
- **Give the Observable the value the initial size implies.** The first report
  arrives one frame after the first paint, so a mismatched seed shows one frame
  of the other layout (and animates); a matching seed de-dupes and is silent.
- **Measure something the parent sizes** (`flex` / `"100%"`), otherwise the
  widget measures its own content.
- **Don't resize the measured widget from its own callback** — that can
  oscillate. Change what is *inside* the measured box.
- This is also how to feed a **two-way** input such as
  `NavigationRail.expanded`, which its own menu button writes and so needs a
  plain mutable `Observable`.

The callback is dispatched between frames, never inside layout, so it may safely
mutate the tree; the effect lands on the next frame.

### When to use `Geometry` instead

`on_size_changed` tells a widget about its *own* size. Use `nv.Geometry` when the
widget that needs the size is a different one: **something nested at arbitrary
depth reacting to an ancestor's box**, without the widgets in between passing it
through.

```python
class Badge(nv.ComposableWidget):
    def on_mount(self) -> None:
        size = nv.Geometry.of(self).size                        # Observable[Size]
        self._label = size.map(lambda s: f"{s.width}px")
        super().on_mount()

nv.Geometry(Pane(), width="100%", height="100%")   # filling: defines the scope
```

- **Resolve in `on_mount`, not `__init__`.** `Geometry.of(self)` walks the
  ancestor chain, which does not exist yet in `__init__`.
- **Bind it; don't read `.value` in `build()`.** A `.value` read at build time is
  a one-time snapshot that never updates.
- **Nearest provider wins.** The app installs a root `Geometry` at the window, so
  a top-level read tracks the window.
- Measured during layout; a consumer that has to rebuild does so on the next
  frame.

## Dynamic lists

Three ways, in order of preference:

| Situation | Approach |
| --- | --- |
| Collection fixed at build time | plain list comprehension in `children=[...]` |
| Collection changes at runtime | `builder()` **(recommended)** |
| Prefer SwiftUI-like syntax | `ForEach(...)` inside `children` |

`Row`, `Column`, `Stack`, `Flow`, and `UniformFlow` expose a `builder()` class
method. Pass an **Observable** as the source to get automatic, region-scoped
regeneration:

```python
nv.Column.builder(
    self.items,                                   # a list, or an Observable for reactivity
    lambda item, index: nv.Text(item),            # (item, index) -> Widget
    gap=8,
    cross_alignment="center",
)
```

- `Deck` switches between children by `index` (give it an explicit `children`
  list; it does not take `builder()`): `nv.Deck(index=obs, children=[A(), B()])`.
- Wrap scrollable regions in `nv.VerticalScrollable(...)` / `nv.HorizontalScrollable(...)`.
- Grids: `nv.UniformFlow.builder(items, fn, columns=3, main_gap=8, cross_gap=8)`.

## Modifiers (decoration & behavior)

Attach decoration/behavior with `.modifier(...)`, composing several with `|` in a
single call — do not re-wrap the widget and do not chain `.modifier().modifier()`.

```python
nv.Button("OK").modifier(
    tooltip("Submit") | clickable(on_click) | background("#2196F3")
)
```

`padding`/`width` stay as **parameters**; modifiers are for things like
`background`, `corner_radius`, `clip`, `border`, `shadow`, `tooltip`, `clickable`,
`focusable`, `hoverable`, `opacity`, `translate`, `rotate`, `scale`, and popups.
(The corner-rounding modifier is `corner_radius`, **not** `radius`.)
