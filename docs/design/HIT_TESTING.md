# Hit Testing

Which widget receives a pointer at a point. Two internal axes decide it for
every widget: **S**, whether the widget's own rectangle becomes the hit
target, and **C**, whether hit testing descends into its children.

## The `auto` Default

S resolves by one principle, *you can click what you can see*:

| Widget | S |
| --- | --- |
| Interactive (click, hover, focus, scroll, or overrides `on_pointer_event`) | catches its rect |
| Paints a visible surface (`Box` / `Container` background, border or shadow) | catches its rect |
| Transparent layout wrapper (`Container`, `Stack`, `Deck`, positioning wrappers) | defers to children |
| Non-interactive ink (`Text`, `Icon`, `Image`, `Divider`) | defers to children |

So a bare, non-painting, non-interactive layer lets clicks through to whatever
is behind it: a full-size alignment `Container` over a canvas passes the empty
area to the canvas while the toolbar inside it still catches. A layer meant to
block clicks paints a background, carries a handler, or takes
`block_pointer()`. A `Box` catches when it has a background, border or shadow;
the check is presence-based (a `border_width > 0` counts, alpha is not
resolved), so a deliberately invisible catcher carries a handler instead.

The hit region is always the rectangle, never per-pixel. A whole text block is
expected to be clickable, and per-pixel precision is impractical. This is SVG
`pointer-events: painted` and SwiftUI's painted-only default in spirit, but
bounding-box, not shape-aware, by choice.

S resolves to `none` / `painted` / `all` internally, and that tri-state is not
public: no string enum and no raw S API. The modifiers below each fix S and C
to name one posture.

## Opt-In Postures

Four intent-named modifiers deviate from `auto`. All route through one
wrapper, `HitParticipationBox`, configured by two booleans: `descend_children`
(C), which makes the box descend into the wrapped widget's own children so the
wrapped widget's S is governed by the box rather than by its `auto`
resolution, and `self_opaque` (S), passed straight to `_resolve_hit`.

| Modifier | C | S | Intent |
| --- | --- | --- | --- |
| `defer_pointer()` | on | off | self never catches; children do |
| `block_pointer()` | on | on | self catches its whole rect; children still work |
| `absorb_pointer()` | off | on | self catches its whole rect; children absorbed |
| `passthrough_pointer()` | off | off | whole subtree click-through |

`passthrough_pointer` is the both-off corner of the same box and backs the
`visible()` composition. Each modifier accepts a `bool` or `Observable[bool]`,
read and validated at construction or mount, never deferred to the first
click; while the condition is falsy the box falls back to `auto`.

The box lives in `nuiitivet.widgeting`, below the modifiers, and the overlay
builds its blocking and click-through layers from it directly. Borrowing the
modifiers instead would close an import cycle: `popup`, `tooltip` and
`context_menu` are overlay clients, so the modifiers already sit above the
overlay.

### Stacking

The modifiers wrap the widget as independent, nestable boxes evaluated
outermost-first (in `a | b`, `b` is outermost), and the outermost box's axes
dominate: its C decision says whether descent happens at all, and its S
decision resolves any point the descent leaves uncaught. A box with C off
(`absorb_pointer`, `passthrough_pointer`) stops descent, so a posture nested
inside it never runs; an outer `passthrough_pointer` therefore makes the
whole subtree click-through whatever is nested, the most-blocking modifier
wins. Two boxes that disagree only on S (`defer_pointer() | block_pointer()`)
resolve to the outermost. Stacking these on one widget is redundant; the rule
exists to keep the rare case well-defined.

## Implementation

All hit participation routes through one helper set on `WidgetKernel`:

- `_hit_test_children(x, y)`, the C axis: reverse Z-order descent. A child's
  `layout_rect` both gates the point and translates it into the child's space.
  A child with no rect or a zero-area one is neither gated nor translated; the
  point is handed down as is. That is what makes a size-less provider such as
  `ForEach` work: it reports `(0, 0)`, paints nothing and lifts its children
  into the parent's coordinate space, so it must never act as a bounds gate
  for a subtree it does not enclose.
- `_hit_self_opaque()` resolves S for `auto`. The base returns
  `_hit_is_interactive()`; `Box` widens it to a painted surface;
  `InteractionHostMixin` reports interactive.
- `_hit_is_interactive()` (`InputHubMixin`) is true when the widget overrides
  `on_pointer_event` / `on_scroll_event` or has a registered pointer or scroll
  hook.
- `_resolve_hit(x, y, *, child_hit, self_opaque)` combines C and S. A pure
  pass-through wrapper (`Deck`, the overlay positioning and passthrough layers)
  passes `self_opaque=False` so it never becomes the target; no wrapper keeps
  a hand-rolled `if hit is self` check.
