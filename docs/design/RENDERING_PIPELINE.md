# Rendering Pipeline Architecture

The rendering pipeline of this framework is composed of three primary phases: **Build**, **Layout**, and **Paint**. Each phase has clearly separated responsibilities, and by adopting a **Layout-first Architecture**, the framework guarantees that all geometric information is finalized before rendering occurs.

## 1. Build Phase

*Status: Implemented (WidgetBuilder, ScopedFragment)*

The phase where the Widget tree is constructed and incremental updates are performed in response to state changes.

* **Responsibilities**:
  * Generate the actual Widget instance tree from declarative Widget definitions.
  * Detect changes in `Observable`s and perform "Recomposition" only for the affected scopes (`ScopedFragment`).
  * At this stage, parent-child relationships and Widget properties are determined, but specific sizes and positions remain undecided.

### Scoped Rendering Optimization

* **Fine-grained Updates**: Dynamic child elements are wrapped using `render_scope` blocks to prevent the regeneration of high-cost Widgets when a parent is rebuilt.
* **Dedicated Scopes**: Core Widgets like `ForEach` and `Card` have dedicated scopes to isolate list items or decorative content.
* **Dependency Tracking**: Scope metadata records `_layout_dependencies` and `_paint_dependencies` for each child, ensuring proper routing of binding invalidations.
* **Idempotent Recomposition**: A scope is rebuilt only when it is new, unbuilt, or explicitly invalidated (tracked via `_dirty_scopes`); merely re-running the host's `build()` does **not** rebuild un-invalidated scopes. See [Widget Optimization › Recompose Scope API](WIDGET_ARCHITECTURE.md#1-recompose-scope-api).
* **Batching**: Binding and scope recomposition queues are flushed together. For an unmounted host there is no pending frame to await, so invalidating a scope flushes its rebuild synchronously rather than deferring it.

## 2. Layout Phase

*Status: Implemented (Layout-first Architecture)*

The phase where the size and position of each Widget are determined. This phase is guaranteed to execute before the Paint phase.

### The Layout Protocol

All `Widget`s adhere to the following protocol:

1. **`layout(width, height)` Method**
    * Called by the parent Widget, passing the available size (constraints).
    * **Responsibilities**:
        1. Determine its own size (based on `preferred_size` and `Sizing` settings).
        2. If child Widgets exist, call their `layout()` to determine their sizes and positions.
        3. Store calculation results (own size, child relative positions) in `_layout_rect`.
        4. Clear the `_needs_layout` flag.
    * **Forbidden**: Issuing draw commands, or any state change that other consumers can observe from within the same layout pass. An `Observable` write is the canonical violation: it propagates synchronously, so a sibling measured *before* the write and painted *after* it sees two different values inside one frame — a torn frame. Whether tearing strikes depends on sibling order within the pass, which app authors cannot reason about; the writer is the only party that knows it is inside `layout()`, so the rule binds the writer.
    * **Permitted side effects** — these do not make anything observable mid-pass:
        1. Storing layout results: `_layout_rect`, and plain synchronous fields that paint, hit-testing, and other post-layout consumers read (e.g. the recorded scroll metrics).
        2. Requesting a frame: `invalidate()` / `mark_needs_layout()` alter no measurement; scheduling work discovered during measurement is unavoidable.
        3. Queueing a deferred publish or callback (`widgeting.widget_size_change`). The app flushes that queue between frames — at the start of the next frame, before its build flush — which is the sanctioned way to make a measured result reactive: `Geometry`'s size and the scroll metrics publish to their `Observable`s through it. Reactive consumers therefore see a measurement one frame after the layout that produced it, and never a torn mix of old and new.

2. **`preferred_size()` Method**
    * Reports the Widget's intrinsic size so the parent can allocate room during `layout()`.
    * **Forbidden (measure purity)**: `preferred_size()` must be free of side effects, the same constraint that applies to `layout()`. In particular, measuring a mounted composable must **not** call `build()` and unmount/rebuild the live subtree — doing so discards focus, scroll position, animation state, and pointer capture, and cancels in-progress gestures. Measurement reads the existing subtree only.
    * **Required (constraint monotonicity)**: measurement must behave greedily with respect to its max constraints: shrinking a constraint down to (but not below) the measured result must not change the result. Text wrapping, min/max clamping, and every other fit-then-report strategy satisfy this naturally; what it rules out is a result computed as a *function* of the constraint while staying strictly inside it (e.g. "half the available width"). The measure cache relies on this to reuse a measurement across a constraint animation.

3. **`_layout_rect` Property**
    * Holds the relative position and size `(x, y, w, h)` as seen from the parent Widget, calculated during `layout()`.
    * The `paint()` method reads this value to perform rendering.

4. **`mark_needs_layout()` Method**
    * Called when a property affecting layout (e.g., `width`, `padding`, addition/removal of children) is changed.
    * Sets its own `_needs_layout` flag and propagates it recursively to the parent Widget.
    * This ensures that only necessary parts of the tree are re-laid out in the next frame.

### Layout Cache & Profiling

* **Sizing Cache**: `parse_sizing()` is memoized, so repeated width/height literals are converted to `Sizing` objects without additional allocations.
* **Layout Engine Cache**: `LayoutEngine` caches preferred sizes, internal rects, and child placement results. Cache keys include padding, border width, container `_layout_cache_token`, child tokens, etc.
* **Measure Cache**: `layout.measure.preferred_size()` memoizes each widget's measurement, keyed on the max constraints it was asked about (`_measure_cache`). `mark_needs_layout()` drops the widget's cache, and its upward propagation drops every ancestor's — so any change routed through the normal invalidation path (content, style, theme, children) re-measures exactly the dirtied path while untouched siblings stay O(1). Constraint monotonicity (above) additionally lets a cached result answer a *shrunk* constraint it still fits, which is what keeps a width animation from re-measuring the static subtrees beside it.
* **Arrange Skip**: `Row`/`Column` skip a child's `layout()` recursion entirely when the child is clean (`needs_layout` is false) and its allocated size is unchanged — position is applied via `set_layout_rect` and is not an input to `layout()`. Together with the measure cache this makes a frame's layout cost proportional to what changed, not to the tree size.
* **Invalidation**: Widgets that change padding or border width increment their `_layout_cache_token` to invalidate the cache.
* **Profiling**: Using `enable_layout_cache_profiling()`, developers can inspect hit rates to optimize complex trees.

### Lifecycle Integration

The `App` main loop processes each frame in the following order:

1. **Queue Flush**: Runs the deferred publishes and size-change callbacks the *previous* frame's layout queued (see Permitted side effects above), then flushes bindings and scope recompositions — so an `Observable` written here is picked up by this frame's build.
2. **Layout Pass**: Calls `layout()` on the root Widget (only if `_needs_layout` is True).
    * Sizes, positions, and scroll metrics for all Widgets are **recorded** at this stage, in `_layout_rect` and plain synchronous fields. Paint and hit-testing read those records — that is what guarantees scrollbar visibility and hit-testing accuracy within the same frame.
    * Recording is distinct from publishing: the `Observable` publish of a recorded measurement rides the queue and lands at the start of the next frame. Layout finalizes the frame's geometry without making any of it observable mid-pass.
3. **Paint Pass**: Draws from the recorded layout results.

## 3. Paint Phase

*Status: Implemented (Skia integration)*

The phase where actual drawing to the screen is performed based on the finalized layout information.

* **Responsibilities**:
  * Render itself and its child Widgets using the `_layout_rect` calculated during `layout()`.
  * Issue drawing commands to the Skia canvas.
  * Apply clipping and coordinate transformations (`save`, `translate`, `restore`).
* **Constraints**:
  * Calculating sizes or changing placements is forbidden at this stage.
  * `paint()` is a pure consumer and must not modify layout results.
* **Culling**: A multi-child container (`Column`, `Row`, `Flow`, `UniformFlow`, `Grid`) reads the canvas clip once per paint and skips any child whose visual bounds -- layout rect plus `paint_outsets()` -- end more than a small slack outside it. A scrolled list therefore pays paint cost for the rows in the viewport, not for the whole content. A culled child still receives its `last_rect`; only its subtree's paint code is not run. Without a readable clip (no canvas, or a stand-in) every child is painted. See [BOX_MODEL.md](BOX_MODEL.md) for what this asks of a widget that draws outside its rect.

### Paint Cache Reuse

* **CachedPaintMixin**: Widgets performing heavy rendering use `CachedPaintMixin` to render background layers to an off-screen Skia surface.
* **Cache Invalidation**: Caches are discarded if `_paint_dependencies` change, or if property setters or Modifiers call `invalidate_paint_cache()`.
* **Hit Testing**: Cached layers do not affect hit-testing, which reads layout state (`layout_rect`, `global_visual_rect`), never `_last_rect`.
* **Theme Awareness**: Widgets referencing ColorRoles are responsible for subscribing to the `ThemeManager` and invalidating the cache upon theme changes.

## 4. Frame Scheduling

*Status: Implemented (on-demand drawing)*

The framework draws **on demand**. A frame is produced only when something has invalidated the tree; an idle window — nothing animating, no interaction — draws **zero frames per second**, so a static screen costs no CPU or battery.

### Invalidation Drives Frames

Every visual state change routes to a redraw request:

* `Widget.invalidate()` → `App.invalidate()` → `ResponsiveEventLoop.request_draw()` sets `_draw_pending`.
* Most state changes reach `invalidate()` indirectly: `Observable` and `Animatable` properties notify subscribers, and those subscriptions call `invalidate()`. This is why interaction modules (hover/press/focus, scrolling, slider drag, overlay transitions, animations) contain few or no explicit `invalidate()` calls — the observable graph carries the signal. Scroll offset, for example, is an `Observable`; the scrollable subscribes and invalidates on change.
* Animations tick on the UI clock (`runtime.clock`, installed as the event loop's clock). Each tick updates an `Animatable` value → subscriber `invalidate()` → one frame. When the animation completes it unschedules itself, the clock goes idle, and the loop returns to zero frames.

### `draw_fps` is an Upper Bound, not a Mandate

`App.run(draw_fps=...)` (and `set_draw_fps`) configure an **upper-bound throttle**, never a mandate to draw:

* `draw_fps=None` (the default): pure on-demand. Draw as soon as a request arrives.
* `draw_fps=N`: still only draws when something invalidated, but coalesces requests so no more than `N` frames per second are produced.

`ResponsiveEventLoop._should_draw()` returns `False` whenever `_draw_pending` is clear, regardless of cadence. `_compute_sleep_timeout()` correspondingly refuses to wake the loop for a cadence deadline when nothing is pending — otherwise an idle app would spin at `draw_fps` doing nothing.

### The Flip Invariant

The GPU and raster backends both present via a double-buffered `window.flip()` (buffer swap). After a swap, the contents of the new back buffer are **undefined**. The rendering loop upholds a single invariant:

> **Never flip without drawing.** A frame is always a full repaint of the back buffer followed by a flip; the loop never presents a buffer it did not just draw.

On-demand drawing satisfies this trivially: when the tree is clean the loop draws *nothing and flips nothing*, so the front buffer keeps showing the last complete frame. The historical belief that "the GPU must redraw every frame" conflated this invariant with a fixed cadence — but redrawing every frame was never required, only *not flipping stale buffers*.

Surface-loss paths that can leave an undefined front buffer (window show, activation, resize, DPI change) explicitly `invalidate()` so the next frame repaints from scratch rather than relying on retained buffer contents.

### GPU Full-Frame Paint Cache

A surface-loss redraw must fill the whole back buffer (to uphold the flip invariant), but the *content* it draws is unchanged — the tree did not change, the compositor merely discarded our buffer. Re-walking the entire widget tree in Python just to reproduce the same pixels is wasteful; on a large tree that walk dominates frame cost.

The GPU path (`draw_gpu_frame`) therefore keeps a **full-frame cache**: after each real paint it snapshots the surface at physical (device-pixel) resolution into `app._gpu_frame_cache`. When a later frame is requested with the tree still clean, it re-blits that snapshot 1:1 into the back buffer instead of calling `root.paint()`. This fills the whole buffer (flip invariant preserved) and reproduces any baked-in transparency (e.g. `CustomChrome` rounded corners) exactly. It mirrors what the raster path achieves with `_last_image`.

To know when a redraw is content-unchanged, `invalidate()` distinguishes two kinds of dirtiness:

* `_dirty` — "a frame was requested" (drives the on-demand loop).
* `_paint_dirty` — "the widget tree changed and must be re-painted".

Content invalidations (`invalidate()`, default `content=True`) set both; surface-loss redraws (window show/activation) call `invalidate(content=False)`, setting only `_dirty`. `draw_gpu_frame` re-blits the cache when `_paint_dirty` is clear and the cached snapshot matches the current physical size, and otherwise does a full paint that refreshes the cache and clears `_paint_dirty`. A genuine content change still pays a full `root.paint()` walk — eliminating *that* cost for partial updates (subtree/dirty-region caching) is tracked separately.
