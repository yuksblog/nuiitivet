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

## Adaptive layout with `Geometry`

To reflow on how much space a region actually has, read `nv.Geometry` — it
measures its own box and publishes it to its subtree as an `Observable[Size]`
(`.width` / `.height`). There **is** a reactive size API; do not override
`set_layout_rect` or any other layout hook to bridge size into an Observable.

```python
class Panel(nv.ComposableWidget):
    def on_mount(self) -> None:
        size = nv.Geometry.of(self).size                       # Observable[Size]
        self._index = size.map(lambda s: 1 if s.width >= s.height else 0)
        super().on_mount()

    def build(self) -> nv.Widget:
        return nv.Deck(children=[portrait, landscape], index=self._index)
```

- **Resolve in `on_mount`, not `__init__`.** `Geometry.of(self)` walks the
  ancestor chain, which does not exist yet in `__init__`. Deriving there also
  builds the mapped Observable once; `build()` only references it.
- **Bind it; don't read `.value` in `build()`.** Same rule as any Observable —
  a `.value` read at build time is a one-time snapshot that never updates.
- **For a side effect rather than a binding, use `self.observe(size, cb)`.** It
  applies the current value immediately, subscribes, and disposes on unmount.
  Do not hand-roll `subscribe()` plus an `on_unmount` override. This is also how
  to feed a **two-way** input such as `NavigationRail.expanded`, which its own
  menu button writes and so needs a plain mutable `Observable`, not a `.map`.
- **Nearest provider wins.** The app installs a root `Geometry` at the window, so
  a top-level read tracks the window. To scope to a region instead, wrap it in a
  **filling** `Geometry`: `nv.Geometry(Panel(), width="100%", height="100%")`.

The size is published on the frame after layout — one frame of latency, never
re-entrant mid-layout.

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
