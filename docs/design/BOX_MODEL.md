# Box Model (Single Source of Truth)

This document defines the framework's box model vocabulary and the rules that connect:

- layout (allocated sizes),
- padding (content rect),
- hit testing (interactive bounds),
- and visual overflow (outsets).

The goal is to keep these rules consistent across widgets, layout containers, and modifiers.

## Terminology

A widget is painted with an **allocated rect**:

- **allocated rect**: `(x, y, width, height)` passed from the parent to `paint()`.

From the allocated rect, the widget derives a **content rect**:

- **padding**: the widget's inner insets.
- **content rect**: the allocated rect minus padding.

Separately, a widget may report **outsets**:

- **outsets**: paint-only expansion (e.g. shadow, focus ring) that may extend beyond the allocated rect.

## Rect Relationships

Allocated and content rect:

```text
allocated rect
┌───────────────────────────┐
│ padding                   │
│  ┌─────────────────────┐  │
│  │ content rect        │  │
│  └─────────────────────┘  │
└───────────────────────────┘
```

Outsets (visual overflow):

```text
visual bounds (allocated + outsets)
┌──────────────────────────────────┐
│  allocated rect                  │
│  ┌────────────────────────────┐  │
│  │ padding                    │  │
│  │  ┌──────────────────────┐  │  │
│  │  │ content rect         │  │  │
│  │  └──────────────────────┘  │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

## Padding Semantics

`Widget.padding` always means: **allocated rect → content rect**.

Why it can look like "outer spacing" for leaf widgets:

- A leaf widget often draws its meaningful visuals inside the content rect.
- If the leaf's padding is large and the leaf draws no background, that padding area can be visually empty.
- Hit testing (by default) can still include the full allocated rect, so the padding area can be interactive.

For M3-style components:

- Treat the M3 "component" as the widget's content.
- M3 internal spacing (e.g. button label insets) should be modeled as *component-internal layout*, not as `Widget.padding`.

## Hit Testing: Interactive Bounds

The framework distinguishes:

- **interactive bounds**: what can receive pointer events (hit test).
- **visual bounds**: what may be drawn (including overflow).

### Default rule

Default hit testing uses the **allocated rect**.

Rationale:

- For interactive controls (buttons, toggles), users expect padding to be part of the touch target.
- Using the content rect as the hit target tends to create "visible but not clickable" padding.

### Viewport/clip exception

## Viewport / Clip: Visible Region

To avoid ad-hoc exceptions, the framework treats "viewport" and "clip" as the same concept:
a widget (or modifier) may define a **visible region** that constrains its subtree.

Definitions:

- **visible region**: the region where descendants are allowed to be visible and interactive.
- **effective visible region**: the intersection of all ancestor visible regions.

Rules:

- **Hit testing**: descendants must not receive pointer events outside the effective visible region.
- **Drawing**: descendants should not be visible outside the effective visible region when clipping is enabled.

Rationale:

- It should not be possible to interact with content outside what is visible.
- This makes `ScrollViewport`, `Clip`, and future `Mask` / `ClipPath` consistent without special-casing.

Examples:

- A scroll viewport clamps hit-testing to its viewport rect.
- A Clip modifier clamps both drawing and hit-testing to its clip shape/rect.

Notes:

- The default remains: if no visible region is defined, the allocated rect is the interactive bound.
- This rule is about *subtree constraints*. It does not change the meaning of padding/content/outsets.

## Outsets: Visual Overflow Only

Outsets are **not** part of layout and **not** part of hit testing.

Outsets exist to:

- avoid clipping artifacts when using paint caches,
- allow natural shadows, focus rings, and overlays to extend beyond the allocated rect.

Consequences:

- Visual effects can overlap neighboring widgets.
- Spacing rules (`gap`, `spacing`, padding conventions) should be used when overlap is undesirable.

## Visual Overlap: Operational Guidance

Decision (2025-12-21): visual overlap is **allowed by default**.

Rationale:

- Outsets are paint-only, and we avoid coupling layout/hit testing to visual effects.
- Many UIs accept shadows and focus rings overlapping adjacent visuals.

When overlap is undesirable:

- Prefer adding layout space (e.g. `gap` or parent `padding`) between interactive components.
- Prefer explicit clipping at the appropriate boundary (e.g. a card surface, a scroll viewport).
  - Clipping is a visible-region concern; do not "fix" overlap by changing hit test bounds.

What not to do:

- Do not treat outsets as layout spacing.
- Do not expand hit testing to match outsets.

## Design Notes

- Layout containers decide the allocated rect.
- Widgets decide how to use padding to produce a content rect.
- Modifiers may introduce visual overflow, but should not silently change layout semantics.
