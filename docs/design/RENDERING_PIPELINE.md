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
* **Dedicated Scopes**: Core Widgets like `ForEach` and `MaterialContainer` have dedicated scopes to isolate list items or decorative content.
* **Dependency Tracking**: Scope metadata records `_layout_dependencies` and `_paint_dependencies` for each child, ensuring proper routing of binding invalidations.
* **Batching**: Binding and scope recomposition queues are flushed together, and unmounted Widgets are rebuilt immediately.

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
    * **Forbidden**: Issuing draw commands or state changes with side effects (except for storing layout results).

2. **`_layout_rect` Property**
    * Holds the relative position and size `(x, y, w, h)` as seen from the parent Widget, calculated during `layout()`.
    * The `paint()` method reads this value to perform rendering.

3. **`mark_needs_layout()` Method**
    * Called when a property affecting layout (e.g., `width`, `padding`, addition/removal of children) is changed.
    * Sets its own `_needs_layout` flag and propagates it recursively to the parent Widget.
    * This ensures that only necessary parts of the tree are re-laid out in the next frame.

### Layout Cache & Profiling

* **Sizing Cache**: `parse_sizing()` is memoized, so repeated width/height literals are converted to `Sizing` objects without additional allocations.
* **Layout Engine Cache**: `LayoutEngine` caches preferred sizes, internal rects, and child placement results. Cache keys include padding, border width, container `_layout_cache_token`, child tokens, etc.
* **Invalidation**: Widgets that change padding or border width increment their `_layout_cache_token` to invalidate the cache.
* **Profiling**: Using `enable_layout_cache_profiling()`, developers can inspect hit rates to optimize complex trees.

### Lifecycle Integration

The `App` main loop processes tasks in the following order:

1. **Layout Pass**: Calls `layout()` on the root Widget (only if `_needs_layout` is True).
    * At this stage, sizes, positions, and scroll metrics for all Widgets are finalized.
    * This guarantees the accuracy of scrollbar visibility and hit-testing.

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

### Paint Cache Reuse

* **CachedPaintMixin**: Widgets performing heavy rendering use `CachedPaintMixin` to render background layers to an off-screen Skia surface.
* **Cache Invalidation**: Caches are discarded if `_paint_dependencies` change, or if property setters or Modifiers call `invalidate_paint_cache()`.
* **Hit Testing**: Cached layers do not affect hit-testing; `_last_rect` remains the single source of truth.
* **Theme Awareness**: Widgets referencing ColorRoles are responsible for subscribing to the `ThemeManager` and invalidating the cache upon theme changes.
