# Geometry

The parent decides a widget's size in layout. The measurement is recorded
as a layout result. This page is how it reaches the code that reads it.

## Overview

Three groups of modules carry a measurement from the layout that made it to
the code that reads it.

### Structure

```mermaid
flowchart LR
    queue[The Queue]
    providers[The Providers]
    frame[The Frame]
    app[the app]

    providers -- "queue_size_change · add_size_callback" --> queue
    frame -- "flush_size_change_callbacks()" --> queue
    frame -- "Geometry(content)" --> providers
    app -- "Geometry.of(self).size · on_size_changed(callback)" --> providers
    queue -- "callback(size)" --> app
```

| Module | Role |
| --- | --- |
| The Queue | holds a measurement between the layout that made it and the frame that reports it |
| The Providers | `Geometry` for a subtree, `on_size_changed` for one widget |
| The Frame | drains the queue at the start of each frame |
| the app | the widgets that read a `Geometry` or carry a size callback |

### Promises

- No `State` is written during layout. No size callback runs during
  layout.

## The Queue

A measurement waits here from the layout that made it to the start of the
next frame.

### Structure

```mermaid
flowchart LR
    kernel[widgeting/widget_kernel.py]
    sizechange[widgeting/widget_size_change.py]
    window[runtime/window.py]
    geometry[layout/geometry.py]
    scroll[scrolling/controller.py]
    app[the app]

    kernel -- "queue_size_change(widget, size), from set_layout_rect" --> sizechange
    geometry -- "queue_size_change(self, size), from layout" --> sizechange
    scroll -- "queue_deferred_publish(state, publish_metrics, widget)" --> sizechange
    sizechange -- "invalidate(), on the first queued entry" --> kernel
    window -- "flush_size_change_callbacks()" --> sizechange
    sizechange -- "_dispatch_size_change(size)" --> kernel
    kernel -- "callback(size)" --> app
```

| Module | Role |
| --- | --- |
| `widgeting/widget_kernel.py` | stores the layout result on the widget, holds its size callbacks, runs them |
| `widgeting/widget_size_change.py` | the queue and its flush |
| `runtime/window.py` | the flush's caller (The Frame) |
| `layout/geometry.py` | queues its own size (The Providers) |
| `scrolling/controller.py` | queues the publish of the scroll metrics |
| the app | the size callbacks |

### Sequence

#### A measurement reaches its consumers

```mermaid
sequenceDiagram
    participant K as widget_kernel.py
    participant Q as widget_size_change.py
    participant W as runtime/window.py
    participant S as scrolling/controller.py
    participant C as the app

    Note over K: set_layout_rect(x, y, width, height), from the parent's layout in frame N
    K->>Q: queue_size_change(widget, size)
    Q->>K: invalidate(), on the first entry
    Note over W: frame N+1 starts
    W->>Q: flush_size_change_callbacks()
    Q->>S: publish_metrics(), each deferred publish
    Q->>K: _dispatch_size_change(size), once per widget
    K->>C: callback(size)
    Note over W: the frame continues (The Frame)
```

### Promises

- A size callback runs once per changed size.
- A widget dropped or unmounted before the flush is skipped.

## The Providers

`Geometry` publishes its own measured size to its subtree as a
`State[Size]`. `on_size_changed` reports a widget's size to the widget
that carries it.

### Structure

```mermaid
flowchart LR
    geometry[layout/geometry.py]
    modifier[modifiers/size_changed.py]
    lookup[widgeting/context_lookup.py]
    kernel[widgeting/widget_kernel.py]
    sizechange[widgeting/widget_size_change.py]
    app[the app]

    geometry -- "layout(cw, ch), the child at its own size" --> app
    geometry -- "queue_size_change(self, size)" --> sizechange
    geometry -- "add_size_callback(_publish_size)" --> kernel
    app -- "Geometry.of(self).size" --> geometry
    geometry -- "find_provider(context, Geometry)" --> lookup
    app -- "on_size_changed(callback)" --> modifier
    modifier -- "add_size_callback(callback)" --> kernel
```

| Module | Role |
| --- | --- |
| `layout/geometry.py` | `Geometry`, a widget around one child, publishing `size` |
| `modifiers/size_changed.py` | `on_size_changed`, the callback registered on the widget it is applied to |
| `widgeting/context_lookup.py` | resolves a `.of()` lookup along the parent chain |
| `widgeting/widget_kernel.py` | the size callbacks a widget holds (The Queue) |
| `widgeting/widget_size_change.py` | the queue (The Queue) |
| the app | the child a `Geometry` lays out, the descendants that read it, the widgets that carry a modifier |

### Promises

- Constraints are not published.
- `size` is one `State`, never a width and a height apart.
- The nearest `Geometry` wins.
- `on_size_changed` adds no node to the tree. It creates no scope.

## The Frame

The window runs the frame the queue was drained for. `render_to_png` drains
the queue again until nothing runs, before it paints.

### Structure

```mermaid
flowchart LR
    window[runtime/window.py]
    sizechange[widgeting/widget_size_change.py]
    binding[widgeting/widget_binding.py]
    builder[widgeting/widget_builder.py]
    tree[the widget tree]

    window -- "flush_size_change_callbacks()" --> sizechange
    window -- "flush_binding_invalidations()" --> binding
    window -- "flush_scope_recompositions()" --> builder
    window -- "Geometry(content), under the scopes" --> tree
    window -- "layout(w, h) · paint(canvas)" --> tree
```

| Module | Role |
| --- | --- |
| `runtime/window.py` | runs the frame |
| `widgeting/widget_size_change.py` | the queue (The Queue) |
| `widgeting/widget_binding.py` | the binding invalidations ([OBSERVABLE.md](OBSERVABLE.md)) |
| `widgeting/widget_builder.py` | the scope recompositions ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| the widget tree | the scopes, the root `Geometry` (The Providers), the content |

### Sequence

#### A frame starts

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant Q as widget_size_change.py
    participant B as widget_binding.py
    participant R as widget_builder.py
    participant T as the widget tree

    W->>Q: flush_size_change_callbacks()
    W->>B: flush_binding_invalidations()
    W->>R: flush_scope_recompositions()
    W->>T: layout(w, h)
    W->>T: paint(canvas)
```

#### A snapshot drains the queue before it paints

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant Q as widget_size_change.py
    participant B as widget_binding.py
    participant R as widget_builder.py
    participant T as the widget tree

    Note over W: render_to_png: mount, layout(w, h)
    loop a bounded number of times
        W->>Q: flush_size_change_callbacks()
        alt nothing ran
            Q-->>W: False
        else something ran
            W->>B: flush_binding_invalidations()
            W->>R: flush_scope_recompositions()
            W->>T: layout(w, h)
        end
    end
    W->>T: paint(canvas)
    Note over W: unmount
```

### Promises

- The live frame runs no size callback between layout and paint.
- A snapshot paints after a bounded number of drains.
- The window wraps the content in a `Geometry`.
