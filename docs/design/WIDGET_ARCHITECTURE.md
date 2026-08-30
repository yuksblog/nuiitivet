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

A subclass that overrides `on_mount` **must** call `super().on_mount()` — it is
what runs `build()`, and omitting it mounts the widget with no children. Put it
anywhere in the body: first usually, last when `build()` reads what the override
computes (`samples/advanced/geometry/scoped_size.py`). Checked at runtime; see
[Lifecycle chain checks](#lifecycle-chain-checks).

### 4. LifecycleHostMixin (Lifecycle)

- **Role**: Manages application connection and lifecycle events.
- **Responsibilities**:
  - Implements the driver for `mount(app)` and `unmount()` (the entry point for recursive calls).
  - Provides `on_mount` and `on_unmount` hooks.
  - Manages `on_dispose` callbacks.
  - Verifies that lifecycle overrides called `super()` (below).

#### Lifecycle chain checks

An override that forgets `super()` fails silently — the body completes, so
nothing raises and nothing is logged; the widget just never builds (§3) or never
releases its bindings (§5). The base implementations here end both chains, so
each sets a flag that `mount`/`unmount` read back, raising a `RuntimeError`
naming the widget, the hook, and what was lost.

| Hook | Checked on | What is lost |
| --- | --- | --- |
| `on_mount` | Build hosts only (`_requires_on_mount_chain`) | `build()` never runs |
| `on_unmount` | Every widget | Bindings are never disposed |

The scopes differ because the damage does: `LifecycleHostMixin.on_mount` is a
no-op, so a plain `Widget` skipping it loses nothing, while binding disposal is
universal.

Two limits are part of the contract. The check runs under `if __debug__` only,
like the `assert_ui_thread` beside it, so `python -O` never reports. And it
stays silent when the override itself raised: `_call_contained` has already
reported that failure, and a missing-`super()` message on top of it would point
at the wrong line.

Nested in the tree, the raise is contained by the parent's `_safe_call` and
forwarded to `report_contained`: visible in `runtime_log`, fatal to a test, but
not to the frame. Only a root widget stops the app.

`find_missing_super_on_mount` in `skills/nuiitivet-app/scripts/check_idioms.py`
is the static counterpart, catching the same mistake in code being written
rather than code being run.

### 5. BindingHostMixin (Reactivity)

- **Role**: Owns `Disposable`s for the duration of the widget's mounted life.
- **Responsibilities**:
  - Registers disposables via `observe`, `bind`, or `bind_to`.
  - Disposes everything registered during `on_unmount`.

#### API surface

| Method | Subscribes | Applies current value first |
| --- | --- | --- |
| `observe(observable, callback)` | Yes | Yes |
| `bind(disposable)` | No — the caller already did | n/a |
| `bind_to(observable, setter, *, dependency, scope_id)` | Yes | Yes |

All three are widget-implementation APIs: they exist so a widget can accept an
`Observable` constructor argument and apply it to its own internal state.
`observe` carries the bulk of that work in-tree — `gap`, `padding`, sizing,
transform properties, external value sync. Application code does not normally
reach for them; it passes Observables into widgets, derives with
`map` / `combine`, and uses `on_size_changed` for size-driven state.

`observe` and `bind_to` seed identically; the only difference is the dependency
invalidation described below.

A source with no `.value` — a subscribe-only emitter — is subscribed without a
seed rather than treated as an error.

#### `bind_to` and dependency invalidation

`bind_to` does one thing `observe` does not: on every *change* it calls
`_invalidate_binding_dependency(dependency, scope_id)` after the setter. The
`dependency` is a label naming *what* the new value invalidates.
`Widget._handle_dependency_invalidation` matches it against the class-level
`_layout_dependencies` / `_paint_dependencies` tuples and drops only the
affected cache; `dependency=None` drops both.

The initial seed deliberately skips this: it runs before the widget has laid
out or painted, so there is no cache to drop and no frame worth requesting.

Invalidations are queued per widget and flushed at the frame boundary by
`App` (`flush_binding_invalidations`), so several observables firing together
coalesce into one re-render. A widget with no `_app` — not yet mounted, or used
standalone in a test — flushes immediately instead.

Choosing a dependency label therefore requires knowing which caches the widget
keeps. A widget with no such caches gains nothing from `bind_to` and should use
`observe`, letting the callback decide what to invalidate.

#### Disposal contract

`BindingHostMixin.on_unmount` calls `_dispose_bindings()`, which disposes and
clears every registered disposable, then delegates to `super().on_unmount()`.

A subclass that overrides `on_unmount` **must** call `super().on_unmount()`.
Omitting it skips `_dispose_bindings()` entirely, and because remounting
(navigation, hot reload) re-runs `on_mount`, subscriptions accumulate: one
source event then invokes N callbacks against N detached widgets. This is
checked at runtime — see [Lifecycle chain checks](#lifecycle-chain-checks).

See [OBSERVABLE.md](OBSERVABLE.md) for `Observable` itself; this section covers
only how a widget takes ownership of a subscription to one.

### 6. InputHubMixin (Input)

- **Role**: Handles routing and handling of input events.
- **Responsibilities**:
  - Dispatches pointer, keyboard, focus, and scroll events.
  - Registers event handlers like `on_click`.

### 7. ChildContainerMixin (Children)

- **Role**: Manages the direct list of child elements (`children`).
- **Responsibilities**:
  - Provides the `children` property.
  - Provides operational APIs like `add_child` and `remove_child`.
  - Maintains child elements using `ChildrenStore`.

### 8. WidgetKernel (Base Element)

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
LifecycleHostMixin.on_mount() # 3. End of the chain. Records that it was reached.
  ↓
(Return to LifecycleHostMixin.mount and recursively execute mount for children,
 then verify step 3 was reached -- see "Lifecycle chain checks" in §4)
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
- **Idempotent Recomposition Contract** (issue #244):
  - A scope's subtree is rebuilt only when it is **new, unbuilt, or explicitly invalidated**. Invalidation is tracked in `_dirty_scopes`, and `_schedule_scope_recomposition()` is the single funnel through which a scope is marked dirty.
  - Re-evaluating the host's `build()` does **not** rebuild scopes that were not invalidated. Re-entering `build()` on every measure must never tear down a live subtree (which would discard focus, scroll, animation, and pointer state).
  - Callers own the responsibility to invalidate a scope when the inputs of its `render_scope` factory change. For example, `ForEach` fires `invalidate_scope_id` for an item's scope when that item's value changes. Relying on a host rebuild to refresh an un-invalidated scope will not work.

### 2. Layout & Dimension Caching

- **Goal**: Avoid redundant layout calculations and parsing overhead.
- **Dimension Cache**:
  - `Dimension` objects (parsed from `SizingLike`) are memoized in `dimension.py`.
  - Reduces the overhead of parsing strings like `"wt2"` or `"auto"` repeatedly.
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
