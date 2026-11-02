# Widget Architecture

`Widget` is composed from mixins by cooperative multiple inheritance, one
module per responsibility. `ComposableWidget` adds `BuilderHostMixin`.

## Overview

Six mixin modules and the module that composes them make up a widget. A call
chains down the method resolution order.

### Structure

```mermaid
flowchart TB
    widget[widgeting/widget.py]
    builder[widgeting/widget_builder.py]
    binding[widgeting/widget_binding.py]
    lifecycle[widgeting/widget_lifecycle.py]
    input[widgeting/widget_input.py]
    children[widgeting/widget_children.py]
    kernel[widgeting/widget_kernel.py]

    widget -- "ComposableWidget is a" --> builder
    builder -- "super(), into Widget" --> widget
    widget -- "Widget is a, in this order" --> binding
    binding -- "super()" --> lifecycle
    lifecycle -- "super()" --> input
    input -- "super()" --> children
    children -- "super()" --> kernel
```

| Module | Role |
| --- | --- |
| `widgeting/widget.py` | `Widget`, the leaf-friendly base; `ComposableWidget`, a widget with a `build()`; the layout and paint dependency declarations |
| `widgeting/widget_builder.py` | `BuilderHostMixin`: `build()`, the built subtree, the recompose scopes |
| `widgeting/widget_binding.py` | `BindingHostMixin`: the subscriptions a widget holds for its mounted life |
| `widgeting/widget_lifecycle.py` | `LifecycleHostMixin`: `mount`, `unmount` and their hooks |
| `widgeting/widget_input.py` | `InputHubMixin`: the pointer, key, focus and scroll entry points ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgeting/widget_children.py` | `ChildContainerMixin`: the child list, backed by a `ChildrenStore` |
| `widgeting/widget_kernel.py` | `WidgetKernel`: the sizing, the padding, the rects, `layout`, `paint`, `hit_test` ([LAYOUT.md](LAYOUT.md)) |

### Promises

- `Widget` never assumes a `build()`.
- The rects and the layout flag are written through `set_layout_rect`,
  `set_last_rect`, `mark_needs_layout` and `clear_needs_layout`. The built
  subtree is read as `built_child`.
- `_parent` is written by the children store and the builder only.

## The Lifecycle

`mount` and `unmount` run the hooks, the callbacks and the children. Each
checks that an override chained to its base.

### Structure

```mermaid
flowchart LR
    lifecycle[widgeting/widget_lifecycle.py]
    lookup[widgeting/context_lookup.py]
    callbacks[widgeting/callbacks.py]
    binding[widgeting/widget_binding.py]
    builder[widgeting/widget_builder.py]
    store[widgeting/children_store.py]
    pointer[runtime/pointer.py]
    app[the app]

    store -- "mount(app) · unmount()" --> lifecycle
    lifecycle -- "forget_app_scope(widget)" --> lookup
    lifecycle -- "report_contained(exc, owner, site) · invoke_event_handler(callback)" --> callbacks
    binding -- "on_unmount(): _dispose_bindings()" --> lifecycle
    builder -- "on_mount(): evaluate_build() · on_unmount(): _unmount_built()" --> lifecycle
    lifecycle -- "cancel_all_for(widget)" --> pointer
    app -- "on_mount() · on_unmount() overrides · add_mount_callback · on_dispose" --> lifecycle
```

| Module | Role |
| --- | --- |
| `widgeting/widget_lifecycle.py` | `LifecycleHostMixin`: the app link, the mounted flags, the mount and unmount callbacks, the dispose callbacks, the chain checks |
| `widgeting/context_lookup.py` | the remembered `AppScope` a mount or unmount forgets ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `widgeting/callbacks.py` | contains a hook's exception and reports it ([ERROR_HANDLING.md](ERROR_HANDLING.md)) |
| `widgeting/widget_binding.py` | its `on_unmount` (The Bindings) |
| `widgeting/widget_builder.py` | its `on_mount` and `on_unmount` (The Builder) |
| `widgeting/children_store.py` | the caller of `mount` and `unmount` (The Children) |
| `runtime/pointer.py` | the pointer captures released when a widget unmounts ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| the app | the widget's overrides and callbacks |

### Sequence

#### A widget mounts

```mermaid
sequenceDiagram
    participant S as children_store.py
    participant L as widget_lifecycle.py
    participant A as the app
    participant B as widget_builder.py

    S->>L: mount(app)
    L->>L: _mounted = True, _app = app, forget_app_scope
    L->>A: on_mount(), contained
    A->>B: super().on_mount()
    B->>L: super().on_mount(), down the MRO, sets _on_mount_chained
    B->>B: evaluate_build(), _mount_built(built)
    L->>L: the mount callbacks
    L->>L: mount(app) on each child
    alt the override ran clean and a build host never chained
        L->>L: raise RuntimeError naming the widget and the hook
    end
```

#### A widget unmounts

```mermaid
sequenceDiagram
    participant S as children_store.py
    participant L as widget_lifecycle.py
    participant A as the app
    participant B as widget_builder.py
    participant Bi as widget_binding.py

    S->>L: unmount()
    L->>A: on_unmount(), contained
    A->>B: super().on_unmount()
    B->>B: _unmount_built()
    B->>Bi: super().on_unmount()
    Bi->>Bi: _dispose_bindings()
    Bi->>L: super().on_unmount(), sets _on_unmount_chained
    L->>L: the unmount callbacks, the dispose callbacks, cancel the mount tasks
    L->>L: unmount() on each child, cancel the pointer captures
    L->>L: _app = None, forget_app_scope
    alt the override ran clean and never chained
        L->>L: raise RuntimeError naming the widget and the hook
    end
```

### Promises

- A second `mount(app)` on a widget mounted to the same app returns at once.
- The base `on_mount` and `on_unmount` end the chains. An override that
  never reaches them is reported after the mount or the unmount, for
  `on_mount` on build hosts only.
- A contained hook exception stops the app only from the root widget.

## The Bindings

A widget subscribes to an `Observable` for its mounted life. The
subscription names what a change invalidates.

### Structure

```mermaid
flowchart LR
    binding[widgeting/widget_binding.py]
    widget[widgeting/widget.py]
    builder[widgeting/widget_builder.py]
    observable[observable/]
    window[runtime/window.py]
    app[the app]

    app -- "observe(observable, callback) · bind(disposable) · bind_to(observable, setter, dependency, scope_id)" --> binding
    binding -- "subscribe(on_value) · dispose()" --> observable
    binding -- "invalidate(), on the first entry" --> widget
    window -- "flush_binding_invalidations()" --> binding
    binding -- "_handle_dependency_invalidation(dependency or scope_id)" --> widget
    widget -- "_handle_scope_invalidation(scope_id) · _handle_scope_dependency(dependency)" --> builder
```

| Module | Role |
| --- | --- |
| `widgeting/widget_binding.py` | `BindingHostMixin`: the `Disposable`s a widget holds; the queue of pending invalidations and its flush |
| `widgeting/widget.py` | drops the cache a dependency names |
| `widgeting/widget_builder.py` | routes a dependency to the scopes that read it (The Builder) |
| `observable/` | the source and its subscription ([OBSERVABLE.md](OBSERVABLE.md)) |
| `runtime/window.py` | flushes the queue at the start of a frame ([GEOMETRY.md](GEOMETRY.md)) |
| the app | a widget passing an `Observable` into its own state |

### Sequence

#### An observable fires into a widget

```mermaid
sequenceDiagram
    participant O as observable/
    participant B as widget_binding.py
    participant W as widget.py
    participant Bu as widget_builder.py
    participant Win as runtime/window.py

    O->>B: on_value(value), any writer
    B->>B: setter(value), queue (widget, dependency, scope_id)
    opt the first entry for this widget
        B->>W: invalidate()
    end
    Note over Win: the next frame starts
    Win->>B: flush_binding_invalidations()
    B->>W: _handle_dependency_invalidation(scope_id), each scope
    W->>Bu: _handle_scope_invalidation(scope_id)
    B->>W: _handle_dependency_invalidation(dependency), when no scope took it
    W->>W: drop the layout cache, the paint cache, or both
```

### Promises

- Every subscription a widget takes through the mixin is disposed in its
  `on_unmount`.
- A frame sees one invalidation per widget, whatever fired. A widget with no
  app flushes at once.

## The Builder

A `ComposableWidget` assembles a subtree in `build()`. A scope of it
recomposes alone.

### Structure

```mermaid
flowchart LR
    builder[widgeting/widget_builder.py]
    widget[widgeting/widget.py]
    lifecycle[widgeting/widget_lifecycle.py]
    kernel[widgeting/widget_kernel.py]
    dependency[theme/dependency.py]
    window[runtime/window.py]
    foreach[layout/for_each.py]
    app[the app]

    app -- "build() · render_scope(name, factory) · handle.invalidate()" --> builder
    builder -- "push_theme_reader(host) · pop_theme_reader(), around build()" --> dependency
    builder -- "built._parent = host" --> kernel
    builder -- "built.mount(app) · built.unmount()" --> lifecycle
    builder -- "layout · paint · hit_test · preferred_size, delegated to _built" --> kernel
    builder -- "invalidate(), on the first entry · mark_needs_layout(), after a rebuild" --> widget
    window -- "flush_scope_recompositions()" --> builder
    foreach -- "invalidate_scope_id(scope_id), for an item whose value changed" --> builder
```

| Module | Role |
| --- | --- |
| `widgeting/widget_builder.py` | `BuilderHostMixin`: `evaluate_build`, the built subtree, `rebuild`; `RecomposeScope` and `ScopeHandle`; the dirty scopes and the queue of pending recompositions |
| `widgeting/widget.py` | `invalidate`, `mark_needs_layout` (Overview) |
| `widgeting/widget_lifecycle.py` | mounts and unmounts the built subtree (The Lifecycle) |
| `widgeting/widget_kernel.py` | the parent link and the geometry the built subtree is delegated to |
| `theme/dependency.py` | attributes a theme read inside `build()` to the host ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `runtime/window.py` | flushes the recompositions at the start of a frame ([GEOMETRY.md](GEOMETRY.md)) |
| `layout/for_each.py` | a host that invalidates a scope itself ([LAYOUT.md](LAYOUT.md)) |
| the app | the widget's `build()` and the scopes it renders |

### Sequence

#### A scope recomposes

```mermaid
sequenceDiagram
    participant A as the app
    participant B as widget_builder.py
    participant W as widget.py
    participant Win as runtime/window.py

    A->>B: handle.invalidate()
    B->>B: _schedule_scope_recomposition(scope_id): dirty, queued
    opt the first entry for this host
        B->>W: invalidate()
    end
    Note over Win: the next frame starts
    Win->>B: flush_scope_recompositions()
    B->>B: _process_scope_recompositions(scope_ids)
    B->>B: fragment.rebuild(), the scope alone
```

### Promises

- A build result is parented to its host as soon as it is built.
- A host rebuild rebuilds no scope. The caller that changed a scope's inputs
  invalidates the scope.
- `preferred_size` never calls `build()` on a mounted host.

## The Children

A widget's children live in a `ChildrenStore`. The store links each child to
its owner.

### Structure

```mermaid
flowchart LR
    children[widgeting/widget_children.py]
    store[widgeting/children_store.py]
    lifecycle[widgeting/widget_lifecycle.py]
    kernel[widgeting/widget_kernel.py]
    layout[layout/]
    window[runtime/window.py]
    app[the app]

    app -- "add_child(widget) · remove_child(widget) · clear_children()" --> children
    children -- "add(w) · remove(w) · clear() · reconcile(desired) · snapshot() · view()" --> store
    store -- "w._parent = owner · _detach_parent(child, owner)" --> kernel
    store -- "mount(owner._app) · unmount()" --> lifecycle
    layout -- "children_snapshot()" --> children
    window -- "focus_traversal_children()" --> children
```

| Module | Role |
| --- | --- |
| `widgeting/widget_children.py` | `ChildContainerMixin`: `children`, the snapshot, the children keyboard traversal descends into |
| `widgeting/children_store.py` | `ChildrenStore`: the ordered children, the capacity and overflow policy, the parent link |
| `widgeting/widget_lifecycle.py` | mounts and unmounts a child (The Lifecycle) |
| `widgeting/widget_kernel.py` | holds the parent link |
| `layout/` | the containers that lay the children out ([LAYOUT.md](LAYOUT.md)) |
| `runtime/window.py` | the Tab traversal ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| the app | adds and removes children |

### Promises

- A child added to a mounted owner is mounted at once. A child removed is
  unmounted.
- The store clears a child's `_parent` only while it still points at the
  store's owner.
