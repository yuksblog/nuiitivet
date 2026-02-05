# Widget Architecture & Mixin Design

The `Widget` class in `nuiitivet` adopts a **Cooperative Multiple Inheritance** pattern, combining multiple Mixins. Each Mixin is responsible for a specific functionality (lifecycle, layout, input, etc.) following the Single Responsibility Principle.

See also: [WIDGET_INTERNAL_STATE_ACCESS.md](WIDGET_INTERNAL_STATE_ACCESS.md)

## Internal State Access

Internal state ownership is defined by mixin responsibility. Access underscore-prefixed fields only within the owning module.
Across module boundaries, use the public accessors documented in [WIDGET_INTERNAL_STATE_ACCESS.md](WIDGET_INTERNAL_STATE_ACCESS.md).

## Widget vs ComposableWidget

Generally, application developers use `ComposableWidget` to construct the build tree. On the other hand, advanced users creating low-level leaf widgets use `Widget`.

- `Widget`
  - Used for creating leaf widgets that focus on `layout()`, `paint()`, and `hit_test()` without depending on `build()`.
  - Child management is handled by `children` (or a specialized store), and it does not return a subtree from build.
  - Examples: Low-level drawing widgets, input/layout primitives.

- `ComposableWidget`
  - Used for modular composition by implementing `build()` to assemble a child tree (`build()` is mandatory and must not return `None`).
  - Supports `rebuild()` calls.
  - Utilizes `scope()`, `render_scope()`, or `invalidate_scope_id()` for partial recomposition.
  - `ComposableWidget.build()` is mandatory and must return a `Widget` (never `None`).
  - Examples: Pages, Routes, Overlays, and components that swap subtrees based on state.

## Inheritance Structure (MRO)

`Widget` is a leaf-friendly base class and does not assume `build()` exists. Widgets that use `build()`, `rebuild()`, or `scope()` must inherit from `ComposableWidget`.

Following Python's MRO (Method Resolution Order), method calls chain from top to bottom.

```python
class Widget(
    AnimationHostMixin,   # Animation
    BindingHostMixin,     # Data binding (Observable)
    LifecycleHostMixin,   # Lifecycle (mount/unmount)
    InputHubMixin,        # Input events
    ChildContainerMixin,  # Child element management (children)
    WidgetKernel,         # Basic layout and rendering
):
    ...

class ComposableWidget(
  BuilderHostMixin,     # Composition (build/scope/rebuild)
  Widget,
):
  ...
```

## Role of Each Mixin

### 1. Widget (Leaf-Friendly Base)

- **Role**: A leaf-friendly base that integrates all mixins.
- **Responsibilities**:
  - Serves as the foundation for layout, rendering, input, and lifecycle.
  - Does not execute `build()` (composition is limited to `ComposableWidget`).

### 2. ComposableWidget (Composition Root)

- **Role**: An explicit base class for incorporating `BuilderHostMixin`.
- **Responsibilities**:
  - Distinguishes widgets that possess a `build()` method.
  - `build()` is mandatory and must return a `Widget` (never `None`).
  - Enables partial recomposition using `scope()` or `render_scope()`.

### 3. BuilderHostMixin (Composition)

- **Role**: Manages widget composition via the `build()` method.
- **Responsibilities**:
  - Executes `build()` and maintains the generated subtree (`_built`).
  - Overrides `layout`, `paint`, and `hit_test` to delegate processing to `_built` when it exists.
    - `layout`: Executes `_built.layout()` after `super().layout()`.
    - `hit_test`: Attempts `_built.hit_test()` first; if it doesn't hit, falls back to `super().hit_test()`.
    - Delegates higher-level events targeting the composed subtree to `_built` when present (e.g., back navigation via `handle_back_event`).
  - Synchronizes the lifecycle of `_built` during `on_mount` and `on_unmount`.

### 4. LifecycleHostMixin (Lifecycle)

- **Role**: Manages application connection and lifecycle events.
- **Responsibilities**:
  - Implements the driver for `mount(app)` and `unmount()` (the entry point for recursive calls).
  - Provides `on_mount` and `on_unmount` hooks.
  - Manages `on_dispose` callbacks.

### 5. BindingHostMixin (Reactivity)

- **Role**: Manages subscriptions for data binding (Observables).
- **Responsibilities**:
  - Registers subscriptions via `bind` or `bind_to`.
  - Automatically unsubscribes (Disposes) during `on_unmount`.

### 6. AnimationHostMixin (Animation)

- **Role**: Manages animations and frame update requests.
- **Responsibilities**:
  - Provides `animate` and `animate_value` methods.
  - Delegates redrawing requests via the `invalidate` method.

### 7. InputHubMixin (Input)

- **Role**: Handles routing and handling of input events.
- **Responsibilities**:
  - Dispatches pointer, keyboard, focus, and scroll events.
  - Registers event handlers like `on_click`.

### 8. ChildContainerMixin (Children)

- **Role**: Manages the direct list of child elements (`children`).
- **Responsibilities**:
  - Provides the `children` property.
  - Provides operational APIs like `add_child` and `remove_child`.
  - Maintains child elements using `ChildrenStore`.

### 9. WidgetKernel (Base Element)

- **Role**: A base class providing the physical entity and basic behavior of a widget.
- **Responsibilities**:
  - Manages `width`, `height`, and `padding` properties.
  - Stores `_layout_rect` (layout calculation result) and `_last_rect` (rendered result).
  - Handles basic `layout` (updating `_layout_rect` and propagating size to children).
  - Handles basic `paint` (rendering child elements).
  - Handles basic `hit_test` (checking child elements and self for hits).
    - Remains unaware of `_built`, focusing only on `children` and its own rectangle.

## Example Interaction Flows

### Execution flow for mount()

```python
widget.mount(app)
  ↓
LifecycleHostMixin.mount()  # 1. Driver starts. Retains app and calls on_mount.
  ↓ self.on_mount()
ComposableWidget (BuilderHostMixin).on_mount() # 2. (Composable only) Executes build, generates _built, and mounts it.
  ↓ super().on_mount()
LifecycleHostMixin.on_mount() # 3. User-defined hook (does nothing by default).
  ↓
(Return to LifecycleHostMixin.mount and recursively execute mount for children)
```

### Execution flow for layout()

```python
widget.layout(width, height)
  ↓
ComposableWidget (BuilderHostMixin).layout()   # 1. (Composable only) Calls layout for _built if it exists.
  ↓ super().layout()
WidgetKernel.layout()                        # 2. Basic implementation. Calls layout for children.
```

## Widget Optimization

To achieve high performance in Python, the framework implements caching and scoping strategies.

### 1. Recompose Scope API

- **Goal**: Minimize the cost of rebuilding widget trees when state changes.
- **Mechanism**:
  - `RecomposeScope` allows wrapping a subtree in a named scope.
  - `ScopeHandle` provides methods (`invalidate()`, `invalidate_scope_id()`) to trigger rebuilds only for that specific scope.
  - Binding invalidations are routed through `_lookup_scope_ids_for_dependency()`, ensuring that only the affected scopes are rebuilt.

### 2. Layout & Dimension Caching

- **Goal**: Avoid redundant layout calculations and parsing overhead.
- **Dimension Cache**:
  - `Dimension` objects (parsed from `SizingLike`) are memoized in `dimension.py`.
  - Reduces the overhead of parsing strings like `"50%"` or `"auto"` repeatedly.
- **Layout Cache**:
  - `LayoutEngine` caches preferred size, inner rect, and child placement results.
  - Caches are keyed by `_layout_cache_token` and dimension signatures.
  - Invalidation is strictly controlled via `_layout_dependencies` and scope updates.

### 3. Paint Cache & Snapshot Reuse

- **Goal**: Reduce Skia drawing commands for static content.
- **Mechanism**:
  - `CachedPaintMixin` allows widgets to render their background/content into a reusable Skia surface.
  - `paint_cache()` context manager handles the recording and playback of these surfaces.
  - `_paint_dependencies` or explicit `invalidate_paint_cache()` calls manage cache invalidation.
  - Hit testing continues to use the authoritative `_last_rect`.
