# Hit Testing

How nuiitivet decides which widget receives a pointer at a given point.

## The `auto` default

A widget's hit participation factors into two internal axes:

- **S — self surface**: does the widget's own rectangle become the hit target?
- **C — children**: does hit-testing descend into the widget's subtree?

The default resolves **S** as `auto` on one principle — *you can click what you
can see*:

| Widget | Behaviour |
|---|---|
| Interactive (click / hover / focus / scroll, or overrides `on_pointer_event`) | **catches** its rect |
| Paints a visible surface (`Box`/`Container` background, border, or shadow) | **catches** its rect |
| Transparent layout wrapper (`Container`, `Stack`, `Deck`, positioning wrappers) | **defers** to children |
| Non-interactive ink/line (`Text`, `Icon`, `Image`, `Divider`) | **defers** to children |

The hit region is always the widget's **rectangle** (bounding box), never
per-pixel. Modern users expect a whole text block to be clickable/selectable;
per-pixel precision is impractical. This mirrors SVG `pointer-events: painted`
and SwiftUI's painted-only default *in spirit*, but is deliberately
bounding-box, not shape-aware.

### The S tri-state is internal

S resolves to `none` / `painted` / `all` internally, but there is **no public
string enum and no raw S API**. The opt-in modifiers below build on the shared
helper and each fix S / C to name one posture; the tri-state itself is never
surfaced. The pass-behind (`translucent`) B axis remains a separate follow-up.

## Public opt-in modifiers (issue #449)

Four intent-named modifiers let a widget deviate from the `auto` default. All
route through one shared wrapper, `HitParticipationBox`
(`src/nuiitivet/modifiers/_hit_participation.py`), configured by two booleans:

- `descend_children` — the **C** axis. When set, the box descends into the
  *wrapped widget's own children* (`child._hit_test_children`), so the wrapped
  widget's **own surface (S)** is governed entirely by the box rather than by
  the widget's `auto` resolution. This is what lets `defer_pointer` suppress
  a painted widget's self-catch.
- `self_opaque` — the resolved **S** axis, passed straight to `_resolve_hit`.

| Modifier | `descend_children` (C) | `self_opaque` (S) | Intent |
|---|---|---|---|
| `defer_pointer()` | `True` | `False` | self never catches; children do |
| `block_pointer()` | `True` | `True` | self catches whole rect; children still work |
| `absorb_pointer()` | `False` | `True` | self catches whole rect; children absorbed |
| `passthrough_pointer()` | `False` | `False` | whole subtree click-through |

`passthrough_pointer` is the whole-subtree (both-off) corner of this same box and
backs the `visible()` composition. Each modifier accepts a `bool` /
`Observable[bool]`; the condition is read and validated at construction / mount,
never deferred to the first click. While the condition is falsy the box falls
back to the `auto` default.

### Stacking precedence

These modifiers wrap the widget as independent, nestable boxes evaluated
**outermost-first** (in a `a | b` chain, `b` is outermost). The outermost box's
axes dominate: its C decision determines whether descent happens at all, and its
S decision resolves any point the descent leaves uncaught. The outcome is
therefore deterministic:

- A box whose C axis is off (`absorb_pointer`, `passthrough_pointer`) stops
  descent, so any posture nested inside it never runs. Because `passthrough_pointer`
  also yields no target, an outer `passthrough_pointer` makes the whole subtree
  click-through regardless of what is nested — the most-blocking modifier wins.
- When two stacked boxes only disagree about the S axis (e.g.
  `defer_pointer() | block_pointer()`), the outermost box resolves S and wins
  the contested surface.

Stacking these on one widget is redundant in practice and discouraged; the rule
above exists to keep the rare case well-defined.

## Implementation

All hit participation routes through one shared helper on `WidgetKernel`:

- `_hit_test_children(x, y)` — the **C** axis (reverse Z-order descent).
- `_hit_self_opaque()` — resolves **S** for `auto`. Base returns
  `_hit_is_interactive()`; `Box` widens it to include a painted surface;
  `InteractionHostMixin` reports interactive.
- `_hit_is_interactive()` (`InputHubMixin`) — true when the widget overrides
  `on_pointer_event` / `on_scroll_event` or has a registered pointer/scroll hook.
- `_resolve_hit(x, y, *, child_hit, self_opaque)` — combines C and S. Pass
  `self_opaque=False` for pure pass-through wrappers (`Deck`, overlay
  positioning/passthrough layers) that must never become the hit target.

Because transparent wrappers now defer by default, the previously hand-rolled
`if hit is self` passthrough copies in `Deck`, the overlay positioning wrappers,
and the overlay modal navigator were removed — the behaviour emerges from the
default.

## ⚠️ Breaking change / Migration

Before this change, **every** widget caught pointers across its whole bounding
box. Now a bare, non-painting, non-interactive layer **lets clicks pass
through to whatever is behind it**. This fixes the common overlay bug where a
full-size alignment `Container` over a canvas swallowed every click:

```python
nv.Stack([
    canvas,                        # now clickable across its whole area
    nv.Container(                  # transparent alignment box -> defers
        toolbar, width="wt", height="wt", alignment="bottom-center",
    ),
])
```

This regresses **silently at click time** (a click that used to be absorbed now
passes through). Audit overlapping layouts for either symptom:

- **A background-less layer was relied on to *block* clicks.** Give it a
  background (real scrims already paint one), attach a click handler, or use the
  forthcoming `block_pointer` modifier. Note: a layer with a click handler is
  interactive and still catches — only *non-interactive, invisible* occluders
  changed.
- **A deliberately transparent `Box` must still catch** (e.g. an invisible hit
  target). A `Box` catches when it has a background/border/shadow; the check is
  **presence-based** (a `border_width > 0` counts; alpha is not resolved). A
  fully transparent catcher should carry an explicit handler instead.
