# Paint Cache

A frame's paint cost is the Python walk of the widget tree: every `paint()`
runs, computing what to draw and issuing Skia calls. Rasterisation is cheap
beside it; on a 1600-tile tree a frame measured about 28 ms, almost all of it
Python method-call overhead. That is what makes nuiitivet different from
Compose, browsers and Core Animation, where the walk is compiled and the
concern is GPU compositing. Every cache here exists to skip part of that walk.

Three caches cover three scopes. The first two are implemented; the third is
designed and verified in a prototype, and nothing designates a boundary today.

| Scope | What it skips | State |
| --- | --- | --- |
| A widget's own visuals | Re-rasterising one widget's background and shadow | implemented (`CachedPaintMixin`) |
| The whole frame | The walk, on a redraw whose content did not change | implemented (full-frame cache) |
| A subtree | The walk of clean subtrees, on a content change that is local | designed, not implemented (repaint boundary) |

## Own Visuals

A widget with heavy own visuals uses `CachedPaintMixin` to render its
background layers to an off-screen Skia surface and replay them. The cache is
discarded when `_paint_dependencies` change or a property setter or modifier
calls `invalidate_paint_cache()`; a widget that resolves a `ColorRole`
subscribes to the `ThemeManager` and invalidates on a theme change. Cached
layers never touch hit testing, which reads layout state (`layout_rect`,
`global_visual_rect`) and never `_last_rect`.

The cache is the widget's own: it invalidates on the widget's own property
changes and knows nothing about descendants. The subtree cache below is a
disjoint scope, so a descendant change never invalidates it.

## Whole Frame

A surface-loss redraw (window show, activation, resize, DPI change) must fill
the whole back buffer to keep the flip invariant of
[RENDERING_PIPELINE.md](RENDERING_PIPELINE.md), but the content it draws is
unchanged: the compositor discarded the buffer, the tree did not change. A
dev-overlay change is the same case, a hover highlight or a mark drawn over an
unchanged tree.

The GPU path (`draw_gpu_frame`) therefore keeps a full-frame cache: after each
real paint it snapshots the surface at device-pixel resolution into
`_gpu_frame_cache`, before the dev overlays go on. A later frame requested
with the tree still clean re-blits that snapshot 1:1 into the back buffer
instead of calling `root.paint()`, then paints the overlays fresh over it. The
whole buffer is filled, and baked-in transparency such as `CustomChrome`'s
rounded corners is reproduced exactly. The raster path does the same with
`_content_image`: the painted tree is kept as an image, and each display frame
composes the overlays over it (`_render_display_frame`).

`invalidate()` distinguishes two kinds of dirtiness so the loop knows when a
redraw is content-unchanged: `_dirty`, a frame was requested, and
`_paint_dirty`, the tree changed and must be re-painted. A content invalidation
(`invalidate()`, `content=True` by default) sets both; a surface-loss redraw and
the dev modes call `invalidate(content=False)`, setting only `_dirty`. Both
paths reuse the cached tree when `_paint_dirty` is clear and the cache matches
the current physical size, and otherwise paint in full, refresh the cache and
clear `_paint_dirty`.

A genuine content change still pays the full walk, however small the change.

## Subtree

Not implemented: nothing designates a cache boundary today. A localised
change, a hover, a caret, one animating widget, routes through
`Widget.invalidate()` → `App.invalidate(content=True)` → `_paint_dirty`, and
the next frame walks the whole tree. The goal is narrow:

> **Skip re-running Python `paint()` for subtrees that did not change.**

### The Mechanism

A container designated a **repaint boundary** caches its whole subtree,
background and descendants, into one offscreen artifact, and short-circuits
recursion when the subtree is clean by replaying the artifact instead of
walking its children. A localised change re-records only the spine from the
root to the changed widget, while every clean sibling boundary replays.

It is backend-agnostic: it lives in the widget paint layer that both the GPU
(`draw_gpu_frame`) and raster (`_render_snapshot`) paths drive, so both get
the short-circuit. A clean root still repaints the whole back buffer, composing
child artifacts, so the flip invariant holds directly.

### The Primitive: `SkPicture`, Not a Rasterised Surface

An `SkPicture` (`skia.PictureRecorder` → `canvas.drawPicture()`) is a recording
of draw commands, not a bitmap: recording captures the command sequence, and
replay re-executes it. It is the analogue of a GPU RenderNode or display list,
and it is the right primitive here for five reasons:

- **It caches the walk, not the pixels.** The expensive work is the Python
  walk that produces the command sequence. A stable subtree runs its Python
  `paint()` once, to record, and thereafter replays in C++ with no Python.
- **Cheap memory.** A 500×500 region is about 1 MB as a bitmap and a few KB as
  a command list, so many, and nested, boundaries are affordable.
- **Resolution-independent.** It records logical commands; the destination
  canvas matrix applies the device scale at replay, so one picture works at
  any DPI.
- **Nestable by reference.** A picture can contain `drawPicture(child)`. A
  parent boundary composites child pictures rather than baking their pixels,
  so a deep change re-records only the spine: cost is O(spine × direct
  children), never the full walk.
- **It does not clip to its recording bounds.** The cull rect is a hint, not a
  clip, so a child's shadow or focus ring that bleeds past the container is
  captured and replayed automatically.

What `SkPicture` does not save: rasterisation. Replay re-executes the
commands, so a blur is re-blurred each frame. A rasterised `SkSurface` would
skip that too, at the cost of memory and a resolution lock. The prototype
measured a fully clean picture-replay frame at about 1.4× a single full-frame
bitmap blit, because rasterising simple content from a picture is fast once
the walk is gone. So the bitmap tier buys little for typical content, and it
stays deferred until a rasterisation-heavy case, a large blur, demands a
second tier for a few very stable boundaries.

### Enablement Is Structural

The tempting rule, cache any subtree unchanged for N frames, is an outlier:
Compose creates layers from `graphicsLayer` and the clip, alpha, shadow and
scroll modifiers; Flutter from `RepaintBoundary`; Core Animation from every
`CALayer` with `shouldRasterize` as an opt-in; browsers retreated from
auto-promotion, the "layer explosion", to the declarative `will-change` hint.
None decides from frame history, and here a temporal rule misfires three
ways:

1. Under on-demand drawing a static tree already renders zero frames; frames
   exist only during interaction and animation. "Stable for N frames" enables
   only after an idle run, so a two-frame interaction never benefits, where a
   structural boundary helps from frame one.
2. Performance becomes history-dependent: the same tree in the same state
   performs differently by what happened before.
3. It cannot see semantics: a blinking caret is "unchanged for 3 frames", then
   enables and evicts in a loop.

One temporal rule stays, as a safety valve: a structurally chosen boundary
that invalidates on near-consecutive frames evicts its cache and re-arms once
stable. Recording every frame is worse than no cache, and this bounds a
boundary placed on an animating region.

### Where Boundaries Go

Coverage is not "every container is a boundary". Broad placement is
affordable with pictures, but a boundary earns its keep only where it
partitions the tree into independently changing regions. The high-value
pattern is **stable content viewed through a changing transform**:

- **Scroll**, and pan or zoom in a canvas app, are the same case: the content
  is unchanged and only the viewport transform moves. Caching the content and
  replaying it at the new transform avoids re-walking it every frame. This
  requires the viewport widget to replay at the new transform without
  invalidating the content cache; if scrolling routes through `invalidate()`
  and dirties the content, it re-records every frame and the safety valve
  evicts it. That transform-replay integration is the real work, not "make
  `Scrollable` a boundary".
- **A stable region beside a changing sibling** is the plain partial-repaint
  case: a stable panel replays while an animating sibling re-walks.

A clip alone marks a self-contained region and adds no cache value of its own.
Shadow and alpha get only the walk-skip, since replay re-runs the blur; they
are exactly where the deferred bitmap tier would pay.

Two tiers, as in Compose. Framework-automatic boundaries are effect-driven:
`Scrollable` (transform-replay) and `ModifierBox` from `.clip()` / `.shadow()`,
with no app cooperation. Developer-explicit: a `RepaintBoundary` widget or a
`.repaint_boundary()` modifier, which the app author places on subtrees they
know are stable. The explicit tier is the lowest-risk first step: no
automatic placement, no thrash detection.

### Invariants

1. **Flip.** A subtree-cached `root.paint()` still fills the whole back buffer.
2. **Raster / GPU parity.** Both paths run the same `paint()`, so a clean
   subtree either replays a picture that reproduces a full paint exactly or
   falls back to a normal paint; the two paths never diverge.
3. **The own-visual cache is untouched.** The subtree cache is a disjoint
   scope, a separate slot with separate invalidation, and never invalidates
   `CachedPaintMixin`'s cache on a descendant change.
4. **Conservative fallback.** A boundary that cannot prove its cache
   reproduces a full paint discards it and paints normally. A missed
   optimisation degrades to correct and slightly slower, never to wrong
   pixels.
5. **Outset bleed is captured.** A rasterised surface sized to the container
   would clip a child's shadow away; a picture does not clip to its recording
   bounds.

The residual correctness risk is a stale snapshot: a descendant change that
fails to invalidate an ancestor's subtree cache. Every paint-affecting path
routes through `Widget.invalidate()` (`Observable` and `Animatable`
notifications, theme changes, layout-driven repaints, the own-visual
`invalidate_paint_cache()`); the one direct `_paint_dirty = True` setter,
GL-context recreation, is a full repaint whose CPU-side artifacts stay valid.
An implementation re-audits this before trusting the cache.

### What the Prototype Verified

- Ancestor invalidation via `Widget.invalidate()`, dirtying only the subtree
  slot and stopping at the first already-dirty boundary, the paint-time
  short-circuit and the disjoint own-visual cache all behave as designed.
- Raster / GPU parity holds pixel for pixel under real Skia: a cached render
  of a localised change equals a full paint across sibling short-circuits,
  nested spines, a hover → press → focus sequence and a child shadow bleeding
  outside a `Column` boundary.
- On a 40×40-tile tree, invalidating one leaf per frame cost about 3 ms with
  row boundaries against about 28 ms for the full walk.

An implementation starts from one narrow target, `Scrollable` transform-replay
or the explicit `.repaint_boundary()` modifier, with the problem statement,
acceptance criteria and scope pinned before code. Broad container coverage,
a temporal enable rule and a bitmap primitive were each tried and replaced by
the design above.
