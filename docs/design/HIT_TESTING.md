# Hit Testing

How nuiitivet decides which widget receives a pointer at a given point.

## The `auto` default (paper / glass model)

A widget's hit participation factors into two internal axes:

- **S — self surface**: does the widget's own rectangle become the hit target?
- **C — children**: does hit-testing descend into the widget's subtree?

The default resolves **S** as `auto`, following a "paper / glass" intuition —
*you can click what you can see*:

| Widget | Behaviour | Metaphor |
|---|---|---|
| Interactive (click / hover / focus / scroll, or overrides `on_pointer_event`) | **catches** its rect | button |
| Paints a visible surface (`Box`/`Container` background, border, or shadow) | **catches** its rect | opaque paper |
| Transparent layout wrapper (`Container`, `Stack`, `Deck`, positioning wrappers) | **defers** to children | glass |
| Non-interactive ink/line (`Text`, `Icon`, `Image`, `Divider`) | **defers** to children | print on glass |

The hit region is always the widget's **rectangle** (bounding box), never
per-pixel. Modern users expect a whole text block to be clickable/selectable;
per-pixel precision is impractical. This mirrors SVG `pointer-events: painted`
and SwiftUI's painted-only default *in spirit*, but is deliberately
bounding-box, not shape-aware.

### The S tri-state is internal

S resolves to `none` / `painted` / `all` internally, but there is **no public
string enum and no raw S API**. Public opt-in modifiers
(`defer_to_children` / `block_behind` / `absorb_from_children`) and the
pass-behind (`translucent`) axis are separate follow-ups that build on the
shared helper introduced here.

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
        toolbar, width="100%", height="100%", alignment="bottom-center",
    ),
])
```

This regresses **silently at click time** (a click that used to be absorbed now
passes through). Audit overlapping layouts for either symptom:

- **A background-less layer was relied on to *block* clicks.** Give it a
  background (real scrims already paint one), attach a click handler, or use the
  forthcoming `block_behind` modifier. Note: a layer with a click handler is
  interactive and still catches — only *non-interactive, invisible* occluders
  changed.
- **A deliberately transparent `Box` must still catch** (e.g. an invisible hit
  target). A `Box` catches when it has a background/border/shadow; the check is
  **presence-based** (a `border_width > 0` counts; alpha is not resolved). A
  fully transparent catcher should carry an explicit handler instead.
