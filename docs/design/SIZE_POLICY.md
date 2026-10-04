# Size Policy

A widget's size has two halves. Layout gives it an **allocated rect**: the
parent decides it from the widget's `width` / `height` sizing. Paint decides
how the widget fits its content into that rect. Hit testing on the rect is in
[BOX_MODEL.md](BOX_MODEL.md).

The framework forbids no sizing. Every widget accepts `fixed`, `auto` and
`weight` on both axes, a `Checkbox` with `width="wt"` included. Sensible
defaults stand in for restrictions.

## Layout: the Allocated Rect

### Weight Is a Share of the Leftover Space

`weight` is a share of the space left over on an axis, in the spirit of WPF
star (`*`) sizing. The rule for an axis:

1. `fixed` and `auto` children are given the space they ask for.
2. Whatever remains is split among the `weight` children in proportion to
   their weights.

Two consequences follow:

- **A lone weight child fills the axis, whatever its weight.** With no weight
  sibling to share with, it receives the entire remainder, so `"wt"` and
  `"wt2"` are identical for an only child. This holds in `Row`, `Column`,
  `Grid`, `Stack` and for overlay-presented content: a `Stack` child overlaps
  its siblings rather than sharing an axis with them, so it is always the sole
  claimant, and the same is true of overlay content.
- **A weight is not a fraction of the parent.** `Row([a, b])` with `a="wt"`
  and `b="wt3"` gives `a` a quarter of the row and `b` three quarters. The
  weights are normalised against each other, not against a fixed total; a
  `fixed` sibling changes what the remainder is, not the ratio between `a`
  and `b`.

A genuine fraction of the parent is written as a number (`height=300`); there
is no fraction-of-parent spec. `"50%"` raises `ValueError`. Accepting it as a
weight with the `%` discarded was rejected, because it reads as a fraction of
the parent and a weight is not one.

### Which Size Dimensions Are Constructor Parameters

Whether a Material widget exposes a size dimension as a public constructor
parameter is decided per axis, not per widget, by one test:

1. **MD3 leaves the axis open** → a constructor parameter, named by its degree
   of freedom: `width` or `length` for one independently variable axis,
   `size` for two axes that vary together (1:1). It lives on the constructor,
   never inside `style`.
2. **MD3 fixes the axis** (a spec token or a size variant) → no parameter;
   customisation goes through `style`.

Examples of each branch:

- open on both axes (`Box`, `Row`, `Card`, `Text`): `width`, `height`
- open on one axis: `Button.width`, `TextField.width`, `NavigationRail.width`;
  the other axis is a token (button height by size variant,
  `TextFieldStyle.container_height`, `MenuStyle.item_height`) and lives in
  style
- main axis only, named `length`: `Slider`, `VerticalScrollbar`; the cross
  axis is a track or thickness token
- uniform: `Icon.size`, `CircularProgressIndicator.size`
- fixed on both: `Checkbox` / `RadioButton` / `Switch` (a fixed graphic in a
  box the form factor decides, adjustable via `*Style.default_touch_target`), `IconButton`
  / `Fab` (a square of the container height), the badges: no size parameter

The rule curates the public surface only. Reaching into `WidgetKernel`'s
`width_sizing` / `height_sizing` still works, as an unsupported escape hatch.
Clamping or ignoring the value there was rejected: it would be runtime
enforcement, and leaving the hatch open costs nothing.

`size` / `length` / `width` say how each axis is meant to vary, where a
generic `width` / `height` everywhere would not. `Icon` keeps a numeric `size`
because MD3 defines several optical icon sizes (20/24/40/48dp), so the axis is
open; coupling it to the `Text` type scale through an ambient mechanism was
rejected in [TYPOGRAPHY.md](TYPOGRAPHY.md), and composite widgets pick
optical sizes internally.

### Composable Wrappers Are Transparent to Layout Metadata

For the layout metadata a parent reads from a child — `width_sizing` /
`height_sizing` and the alignment hints `layout_align` / `cross_align` — a
`ComposableWidget` resolves each value by one rule:

> **A declared value wins; an undeclared one is derived from the widget that
> `build()` returned.**

So extracting a subtree into a composable does not change how the tree lays
out.

- Sizing tracks declaration explicitly: an explicit `"auto"` is a declaration
  and pins the intrinsic size, the opt-out from derivation. For the alignment
  hints, `None` is "undeclared".
- Before `build()` has run (pre-mount intrinsic measurement), the wrapper
  reports its own defaults; `preferred_size` measures the built subtree
  directly, so intrinsic sizes stay correct.
- Scope fragments (`render_scope`) never declare metadata of their own, so
  they are always fully transparent.

## Paint: Content Inside the Rect

Once the allocated rect is known, the widget fits its content into it by a
**content mode** (`fit`). `contain` scales the content to the largest size
that fits while preserving aspect ratio; `none` draws it at its intrinsic
size, centred, however large the rect. `cover` and `fill` exist for `Image`.
Where the content does not fill the rect, `content_alignment` places it,
centred by default. `Image` exposes `fit`; `Checkbox`, `RadioButton` and
`Icon` do not, and behave as if set by an internal default.

| Widget | Default `fit` | Behaviour |
| --- | --- | --- |
| `Checkbox`, `RadioButton` | `contain` | The graphic scales with the rect. |
| `Icon`, `Image` | `contain` | Vector and bitmap content is resized freely. |
| `Button`, `IconButton`, `Fab` | container | Fills the rect and aligns its label and icon inside. |

`Checkbox` defaults to `contain` where most frameworks pin the graphic to a
fixed size. A user who writes `width="wt"` or `width=100` means to resize the
widget, and that intent is honoured over the design guardrail; the guardrail
is the default `width`, which is fixed at the standard size. `contain` also
matches `Icon` and `Image`, so there is one rule to learn, and vector
rendering keeps the graphic crisp at any size.
