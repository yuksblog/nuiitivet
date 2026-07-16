# Subtree Paint Cache (Issue #370, Part B) — Design Record

*Status: **PAUSED / not implemented.** This work was explored and prototyped in
depth; the prototype branch was **discarded** rather than merged (it delivered no
production behaviour — nothing designated a cache boundary — so landing it would
have added inert code). This document is the **design record and findings**, kept
so the reasoning is not lost. It does not describe shipped code. See §8 for why it
was paused and how to resume.*

The problem: eliminate the full `root.paint()` walk that a **localized** content
change (hover/press/focus, a caret, one animating widget) still pays, even when
the changed rectangle is a rounding error against the window. It is the follow-up
to the GPU **Full-Frame Paint Cache** (Issue #369, Part A), which only eliminated
the walk for *content-unchanged* surface-loss redraws.

---

## 1. The one insight that drives everything: the bottleneck is the Python walk

Every localized visual change routes through `Widget.invalidate()` →
`App.invalidate(content=True)` → `_paint_dirty = True`. On the next frame the
backend calls `app.root.paint(...)`, a **full Python walk of the widget tree**:
every widget's `paint()` runs, computing what to draw and issuing Skia calls.

**That Python walk — not rasterisation — is the dominant cost.** A prototype
benchmark on a 1600-tile tree measured ~28 ms per frame, almost all of it Python
method-call overhead; the actual Skia rasterisation is comparatively cheap.

This is what makes nuiitivet **different from Compose / browsers / Core
Animation**, where the tree walk is cheap (compiled) and the concern is GPU
compositing / rasterisation. Here the goal is narrow and specific:

> **Skip re-running Python `paint()` for subtrees that did not change.**

Every downstream decision — the cache primitive, what to cache, where — follows
from this. It is the headline, not a footnote.

## 2. The mechanism: a subtree paint cache

The abstraction mature toolkits converge on: a container designated a **repaint
boundary** caches its whole subtree (background + all descendants) into one
offscreen artifact and **short-circuits recursion when the subtree is clean** —
replaying the artifact instead of walking its children. A localized change then
re-records only the spine from the root to the changed widget, while every clean
sibling boundary replays.

It is **backend-agnostic**: it lives in the widget paint layer that both the GPU
(`draw_gpu_frame → root.paint()`) and raster (`_render_snapshot → root.paint()`)
paths drive, so both get the short-circuit for free. A clean root still repaints
the whole back buffer (compositing child artifacts), so the **flip invariant**
("never flip without drawing a full back buffer") holds directly.

## 3. The cache primitive: `SkPicture`, not a rasterized surface

**This is the crux, and the part most worth understanding.**

An `SkPicture` (via `skia.PictureRecorder` → `canvas.drawPicture()`) is a
**recording of draw commands** — drawRect / drawText / clip / transform /
drawPicture… — not a bitmap. Recording captures the command sequence; replay
re-executes it. It is the direct analogue of a GPU RenderNode / display list.

Why it is the right primitive **here specifically**:

- **It caches the walk, not the pixels.** The expensive work is the Python walk
  that *produces* the Skia command sequence. `SkPicture` captures that sequence,
  so a stable subtree runs its Python `paint()` **once** (record) and thereafter
  **replays in pure C++** with zero Python. This attacks the §1 bottleneck head-on.
- **Cheap memory.** A 500×500 region is ~1 MB as a bitmap but a few KB as a command
  list, so **many** (and nested) boundaries are affordable — the property that
  makes broad placement viable at all.
- **Resolution-independent.** It records logical commands; the destination canvas
  matrix applies device scale at replay. One picture works at any DPI (no
  device-scale bookkeeping).
- **Composable / nestable.** A picture can contain `drawPicture(child)` by
  *reference*. A parent boundary composites child boundary pictures rather than
  baking their pixels, so a deep change re-records only the spine (each level just
  re-composites child pictures) — cost is `O(spine × direct-children)`, never the
  exponential full walk. This makes it behave like Compose's RenderNode tree.
- **Does not clip to its recording bounds.** The recording cull rect is a *hint*,
  not a clip: draws outside it are still replayed. A child's shadow / focus ring
  that bleeds beyond the container is captured automatically (see §6).

What `SkPicture` does **not** save — important to hold clearly:

- **It does not skip rasterisation.** Replay re-executes the commands, so a blur is
  re-blurred and paths re-filled each frame. `SkPicture` saves "Python walk + Skia
  command construction", not pixel production.
- Therefore a **rasterized `SkSurface` (bitmap)** would additionally skip
  rasterisation — valuable for *rasterisation-heavy* content (big blurs) — at the
  cost of memory and resolution-lock. A **two-tier** scheme (picture everywhere;
  bitmap for a few rasterisation-heavy, very stable boundaries) is possible.

Prototype measurement of the two-tier question: a fully-clean frame replaying
pictures cost only **~1.4×** a single full-frame bitmap blit — because rasterising
simple content from a picture is fast once the walk is gone. So the bitmap tier
buys little for typical content; `SkPicture`-first is the right default, and the
bitmap tier stays deferred until a rasterisation-heavy case demands it.

> One-line takeaway: **`SkPicture` caches the walk; `SkSurface` also caches the
> pixels.** nuiitivet is walk-bound, so `SkPicture` captures the main win cheaply.
> In a GPU framework (walk is cheap) `SkPicture` would be far less compelling.

## 4. Enablement must be structural, not a temporal heuristic

The tempting design — auto-enable a cache for any subtree "unchanged for N frames"
— is an **industry outlier** and a poor fit here.

How mature toolkits actually decide what to cache:

| Toolkit | How a caching boundary is decided | Kind |
| --- | --- | --- |
| **Jetpack Compose** | Snapshot dependency-tracking scopes recomposition; `graphicsLayer` (and clip/alpha/shadow/scroll modifiers) create RenderNode layers | structural / effect-driven |
| **Flutter** | `RepaintBoundary` widget; framework auto-inserts at seams (e.g. `ListView` items); debug paint counters to *measure* value | structural / explicit |
| **Core Animation** | every `UIView` is a `CALayer` (always-on); `shouldRasterize` is explicit opt-in | structural / explicit |
| **Browsers / CSS** | compositor layers; auto-promotion caused "layer explosion" and retreated to the declarative `will-change` hint | declarative hint |

None enable caching from **frame history**. Enablement is decided by *where a
boundary sits* (structural), *what a node declares/uses* (effect/hint), or *what
state it depends on* (dependency tracking).

Why a temporal "stable for N frames" enable specifically mis-fires in nuiitivet:

1. **It optimises the wrong frames under on-demand drawing (#360).** A static tree
   already renders **zero** frames; frames exist only during interaction/animation.
   "Stable for N frames" only enables *after* an idle run, so a brief interaction
   (1–2 frames) never enables, and a structural boundary would help from frame 1.
2. **It makes performance history-dependent** and non-deterministic — the same
   tree in the same state performs differently depending on recent frames.
3. **It cannot see semantics** — "unchanged for 3 frames" ≠ "unchanged next frame"
   (a blinking caret enables then immediately evicts, in a loop).

**Keep one temporal rule, as a safety valve only:** a structurally-chosen boundary
that nonetheless invalidates on near-consecutive frames should **auto-evict** its
cache and re-arm once stable. This guards against a boundary placed on an
animating region (thrashing = record-every-frame, worse than no cache).

## 5. Where boundaries go (the coverage question)

Following Compose, there are two tiers. **Coverage is NOT "every container is a
boundary"** — with the compositional `SkPicture` design broad placement is
*affordable*, but boundaries still earn their keep only where they partition the
tree into independently-changing regions.

The unifying high-value pattern: **stable content viewed through a changing
transform.**

- **Scroll** (top target) and **pan / zoom** (photo/canvas apps) are the same
  pattern: the content is unchanged, only the viewport transform moves. Caching the
  content as a picture and **replaying it at the new transform** avoids re-walking
  it every frame. Caveat: this requires the scroll/viewport widget to **replay at
  the new transform without invalidating the content cache** — if scrolling routes
  through `invalidate()` and dirties the content, it re-records every frame
  (thrash → eviction → no benefit). This "transform-replay" integration is the real
  work, not merely "make Scrollable a boundary".
- **Generic "stable region while a sibling changes"** — the plain partial-repaint
  case; a stable panel replays while an animating sibling re-walks.

Weaker / marginal auto-targets:

- **Clip** alone is only a *marker* of a self-contained region, not a source of
  cache value; the photo/paint case's value comes from the **transform**, not the
  clip.
- **Shadow / Alpha**: with `SkPicture`, replay re-runs the blur, so these get only
  the walk-skip, not a rasterisation saving — **marginal**. These are exactly where
  the deferred bitmap (`SkSurface`) tier would pay.

Compose maps this to: **framework-automatic** boundaries are *effect-driven*
(clip / alpha / shadow / transform / scroll create layers), plus **developer-
explicit** (`graphicsLayer` / `RepaintBoundary`). The nuiitivet analogues:

- framework-automatic: **`Scrollable`** (transform-replay) and **`ModifierBox`**
  (from `.clip()` / `.shadow()`), automatic and invisible — no app cooperation.
- developer-explicit: a **`RepaintBoundary` widget or `.repaint_boundary()`
  modifier**. Lowest-risk, clearest value (the app author knows which subtrees are
  stable) — a reasonable *first* thing to ship, ahead of the automatic tier.

## 6. Correctness invariants (must hold in any implementation)

1. **Flip invariant.** A subtree-cached `root.paint()` still fills the whole back
   buffer, so "never flip without drawing" holds automatically.
2. **Raster / GPU parity.** Both paths run the same `paint()`, so a clean subtree
   either replays a picture that reproduces a full paint exactly, or conservatively
   falls back to a normal paint — the two paths never diverge.
3. **The existing `Box` own-visual cache must not degrade.** `CachedPaintMixin`
   caches a widget's *own* bg+shadow and invalidates only on the widget's *own*
   property changes. The subtree cache must be a **disjoint scope** (separate slot,
   separate invalidation) and never invalidate the own-visual cache on a descendant
   change.
4. **Conservative fallback.** Whenever a boundary cannot *prove* its cache
   reproduces a full paint, discard it and paint normally. A missed optimization
   degrades to "old, correct, slightly slower", never to wrong pixels.
5. **Descendant paint-outset bleed — dissolved by `SkPicture`.** A child's shadow /
   focus ring can extend outside the container rect. A rasterized surface sized to
   the container would *clip it away*; a picture does not clip to its recording
   bounds, so the bleed is captured and replayed automatically. (This is the
   correctness subtlety that got Part B split out of #369; the picture primitive
   removes it — verified in the prototype.)

**Invalidation universality (prerequisite).** The residual correctness risk is a
*stale snapshot*: a descendant change that failed to invalidate an ancestor's
subtree cache. A prototype audit confirmed **every** paint-affecting path routes
through `Widget.invalidate()` (Observable/Animatable notifications, theme changes,
layout-driven repaints, the own-visual `invalidate_paint_cache()` path). The one
direct `_paint_dirty=True` setter (GL-context recreation) is a full repaint whose
CPU-side artifacts stay content-valid, so it is safe. Re-audit before trusting the
cache in any resumed implementation.

## 7. Prototype findings (branch discarded, but verified)

A prototype implemented the full mechanism and **verified** the following before
being discarded. These facts are the real deliverable of this effort:

- **The mechanism works and is safe.** Ancestor-invalidation via `Widget.invalidate()`
  (dirtying only the subtree slot, early-stopping at the first already-dirty
  boundary), paint-time short-circuit, and the disjoint own-visual cache all
  behaved as designed.
- **Raster/GPU parity holds.** Real-Skia pixel-for-pixel tests: a cached render of a
  localized change was identical to a full paint, across sibling short-circuits,
  nested spines, an interaction (hover→press→focus) sequence, and a **shadow-bleed**
  case (child shadow extending outside a `Column` boundary).
- **`SkPicture` dissolves the outset-bleed problem** (§6.5) — confirmed empirically.
- **Benchmark: ~8–10× on a localized change.** On a 40×40 = 1600-tile / 40-row tree,
  invalidating one leaf per frame cost ~3 ms with row boundaries vs ~28 ms full
  walk. Two-tier signal: a fully-clean picture-replay frame cost ~1.4× a full-frame
  bitmap blit (§3).

**What the prototype got wrong (and the design churn to learn from):** it started
with (a) a *temporal* auto-enable heuristic, (b) a rasterized `SkSurface` primitive,
and (c) broad coverage by adding a mixin to six layout containers. All three were
later corrected to (a) **structural** enablement + eviction-as-safety-valve, (b)
**`SkPicture`**, and (c) **effect-driven / explicit** boundaries (§3–§5). The churn
is precisely why this was paused (§8): the design moved while code was already being
written.

## 8. Why paused, and how to resume

**Paused because** the *goal* was never pinned down — "which boundaries, how far" —
so the design churned (heuristic → structural, `SkSurface` → `SkPicture`, container
coverage → effect-driven) while implementation ran ahead of it. Rather than land
inert code (nothing designated a boundary, zero production effect) and repeat the
pattern of forcing partial work to "done", the branch was discarded and the
knowledge captured here.

**To resume, do not restart from the discarded branch.** Instead:

1. Pick **one narrow, high-value target** — the two strongest candidates:
   - **`Scrollable` transform-replay** (§5): the clearest win, but needs the
     "replay-at-new-transform-without-invalidating-content" integration.
   - **An explicit `.repaint_boundary()` modifier / widget** (§5): lowest risk,
     app-author-controlled, no automatic-placement or thrash-detection subtlety.
2. Before touching code, write a **one-paragraph problem statement + explicit
   acceptance criteria + scope boundary** for that one target. If they cannot be
   pinned down, do not start.
3. Reuse the verified design here: `SkPicture` primitive, structural enablement,
   disjoint own-visual scope, conservative fallback, the §6 invariants, and the
   real-Skia parity test approach.

Everything in §1–§6 is design knowledge that survives regardless of which target is
chosen; §7 records what a prototype already proved so it need not be re-discovered.
