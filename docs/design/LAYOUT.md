# Layout

A widget's size and spacing are its own properties. Its parent places it.

## Overview

Five groups of modules take part, with the Material components and the app at
their edges.

### Structure

```mermaid
flowchart LR
    sizing[The Sizing]
    containers[The Containers]
    providers[The Providers]
    composable[The Composable]
    fit[The Fit]
    window[The Window Sizing]
    material[the Material components]
    app[the app]

    app -- "width · height · padding · gap · alignment" --> containers
    app -- "builder(items, fn) · lazy(items, fn)" --> providers
    containers -- "provide_layout_children() · item_count() · set_window(start, stop)" --> providers
    containers -- "parse_sizing(value) · width_sizing · height_sizing · padding" --> sizing
    containers -- "width_sizing · height_sizing · layout_align · cross_align" --> composable
    material -- "width · length · size, per open axis" --> sizing
    app -- "fit · content_alignment" --> fit
    app -- "Window(width, height, position)" --> window
    window -- "the nine-point vocabulary" --> containers
```

| Module | Role |
| --- | --- |
| The Sizing | how a widget asks for space on one axis |
| The Containers | place their children and share the room out |
| The Providers | build a container's children from data, all of them or the ones in view |
| The Composable | reports the layout metadata of the widget it built |
| The Fit | places a widget's content inside the rect it was given |
| The Window Sizing | the window's size and position, resolved before layout |
| the Material components | the MD3 widgets ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |
| the app | sizes, spaces and aligns widgets |

### Promises

- `padding` and `gap` are the two spacing properties.
- A modifier never changes layout ([MODIFIER.md](MODIFIER.md)).
- Alignment belongs to the parent.

## The Sizing

A `Sizing` is how a widget asks for space on one axis.

### Structure

```mermaid
flowchart LR
    sizing[rendering/sizing.py]
    kernel[widgeting/widget_kernel.py]
    row[layout/row.py · column.py]
    engine[layout/layout_engine.py]
    material[the Material components]

    kernel -- "parse_sizing(value) · sizing_signature(value)" --> sizing
    row -- "width_sizing · height_sizing: kind, value" --> kernel
    engine -- "sizing_signature(value), in the cache key" --> sizing
    row -- "preferred_size(widget, max_w, max_h)" --> measure
    measure[layout/measure.py]
    material -- "parse_sizing(length, default=Sizing.weight()) · style tokens for the fixed axis" --> sizing
```

| Module | Role |
| --- | --- |
| `rendering/sizing.py` | `Sizing`, one of `fixed`, `auto` and `weight`, and its parser |
| `widgeting/widget_kernel.py` | holds a widget's two sizings ([BOX_MODEL.md](BOX_MODEL.md)) |
| `layout/row.py · column.py` | share an axis out by the children's sizings (The Containers) |
| `layout/layout_engine.py` | keys its caches on the sizings (The Containers) |
| `layout/measure.py` | the measurement cache (The Containers) |
| the Material components | the fixed axes' style tokens |

### Sequence

#### A row shares its width out

```mermaid
sequenceDiagram
    participant R as layout/row.py · column.py
    participant M as layout/measure.py
    participant C as the children

    R->>M: preferred_size(child, max_w, max_h), each child
    R->>R: the fixed and auto children take their size
    R->>R: the remainder, split by weight
    R->>C: set_layout_rect(x, y, w, h)
```

### Promises

- Only the space left after the `fixed` and `auto` children is shared by
  weight.
- A `weight` child measures as its content.
- An axis MD3 leaves open is a constructor parameter, named `width`, `length`
  or `size` by its degree of freedom. An axis MD3 fixes is a style token.

## The Containers

A container measures its children and allocates each a rect.

### Structure

```mermaid
flowchart LR
    row[layout/row.py · column.py]
    grid[layout/grid.py]
    stack[layout/stack.py]
    container[layout/container.py]
    flow[layout/flow.py · uniform_flow.py]
    alignment[layout/alignment.py]
    engine[layout/layout_engine.py]
    measure[layout/measure.py]
    utils[layout/layout_utils.py]
    children[the children]

    row & grid & stack & flow & container -- "preferred_size(max_w, max_h) · layout_child_if_needed · set_layout_rect(x, y, w, h)" --> children
    row & grid & stack & flow & container -- "preferred_size(widget, max_w, max_h)" --> measure
    container -- "preferred_size · compute_inner_rect · compute_child_placement · resolve_child_geometry" --> engine
    row & grid & stack & container -- "normalize_alignment(value) · alignment_to_point(alignment, w, h)" --> alignment
    row & flow -- "layout_child_if_needed(child, w, h) · paint_laid_out_children(...)" --> utils
```

| Module | Role |
| --- | --- |
| `layout/row.py · column.py` | one axis shared out by sizing, `main_alignment` and `cross_alignment` across it, a `gap` between the children |
| `layout/grid.py` | rows, columns and areas; allocates each cell's rect |
| `layout/stack.py` | children over one another, each the sole claimant of both axes |
| `layout/container.py` | one child, placed by `alignment` |
| `layout/flow.py · uniform_flow.py` | children wrapped into lines |
| `layout/alignment.py` | the nine-point vocabulary and its point in a rect |
| `layout/layout_engine.py` | the padding, border and placement arithmetic, cached ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `layout/measure.py` | the measurement cache ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `layout/layout_utils.py` | lays a child out and paints the children ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| the children | measured and placed |

### Promises

- Alignment positions a child. It never stretches one.
- Whether a child fills its `Grid` cell is the child's own sizing.
- Nothing clips a child larger than its rect.

## The Providers

A provider builds a container's children from a data collection. A lazy
container's provider builds the items in view, and the ones around them
while the loop is idle.

### Structure

```mermaid
flowchart LR
    for_each[layout/for_each.py]
    lazy[layout/lazy.py]
    containers[layout/row.py · column.py · uniform_flow.py]
    utils[layout/layout_utils.py]
    viewport[layout/scroll_viewport.py]
    controller[scrolling/controller.py]
    builder[widgeting/widget_builder.py]
    idle[widgeting/idle_work.py]

    containers -- "ForEach(items, fn, key_fn) · LazyItems(provider, axis, extent)" --> for_each & lazy
    containers -- "expand_layout_children(children)" --> utils
    utils -- "provide_layout_children()" --> for_each
    containers -- "count() · item_extent(cross_limit) · visible_span(container, length) · index_range(span, count, extent, gap, pad) · materialize(container, first, stop, pitch, place)" --> lazy
    lazy -- "place(child, index), for an item built in idle time" --> containers
    lazy -- "item_count() · set_window(start, stop) · window_children()" --> for_each
    lazy -- "visual_clip_rect() · visual_offset() · controller" --> viewport
    lazy -- "axis_state(axis).offset.subscribe(cb)" --> controller
    lazy -- "request_idle_work(prefetch) · cancel_idle_work(prefetch)" --> idle
    for_each -- "render_scope_with_handle(handle, factory) · _prune_unused_scopes()" --> builder
```

| Module | Role |
| --- | --- |
| `layout/for_each.py` | `ForEach`: one scoped fragment per item, found by its key; with a window, per item in the window |
| `layout/lazy.py` | `LazyItems`: the item extent, the span the viewport shows, the index range it covers, the held range around it and the lead; follows the viewport's offset while mounted, builds ahead of it in idle time and keeps the items a view's length behind it |
| `layout/row.py · column.py · uniform_flow.py` | `builder()` and `lazy()`; place the provided children, a lazy one at its index times the pitch (The Containers) |
| `layout/layout_utils.py` | replaces a provider with its children (The Containers) |
| `layout/scroll_viewport.py` | the clip rect, the displacement and the controller it scrolls by ([BOX_MODEL.md](BOX_MODEL.md)) |
| `scrolling/controller.py` | the offset `Observable` |
| `widgeting/widget_builder.py` | the recompose scopes ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `widgeting/idle_work.py` | the tasks the frame loop runs before it waits ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |

### Sequence

#### A scroll moves the window

```mermaid
sequenceDiagram
    participant S as scrolling/controller.py
    participant L as layout/lazy.py
    participant C as layout/column.py
    participant V as layout/scroll_viewport.py
    participant F as layout/for_each.py

    S->>L: offset changed
    L->>L: note the direction and the items one step moves
    L->>C: mark_needs_layout()
    V->>C: preferred_size(max_w): count × extent plus the gaps
    V->>C: layout(w, h)
    C->>L: visible_span(self, h)
    L->>V: visual_clip_rect() · visual_offset()
    C->>L: index_range(span, count, extent, gap, pad)
    C->>L: materialize(self, first, stop, pitch, place)
    L->>L: the held range: the view, plus the built items within a view's length on each side
    L->>F: set_window(held_first, held_stop)
    F->>F: build the items that entered the view, unmount the ones a view's length away
    L->>I: request_idle_work(prefetch), when the lead is not full
    C->>C: place item i at pad + i × (extent + gap)
```

#### Idle time builds ahead of the view

```mermaid
sequenceDiagram
    participant E as backends/pyglet/event_loop.py
    participant I as widgeting/idle_work.py
    participant L as layout/lazy.py
    participant F as layout/for_each.py
    participant C as layout/column.py

    E->>I: run_idle_work(budget), before a wait
    I->>L: prefetch(deadline)
    loop until the deadline or the lead is full
        L->>L: the next item: the scroll's side first, at rest the side with fewer
        L->>F: set_window(the held range grown by one)
        F->>F: build the item
        L->>C: place(child, index)
    end
    L-->>I: whether the lead is still not full
    I-->>E: whether work remains
```

### Promises

- A provider is never laid out or painted. Its children take its place in the
  container.
- A lazy container holds a widget for each item in view, for the built items
  within a view's length on each side of it, and for none beyond.
- An item that left the view keeps its widget until it lies a view's length
  away. The item comes back into view without a build.
- The layout pass builds the items that entered the view and no other.
- The lead is filled in idle time, one item at a time, the scroll's side
  first.
- At rest the lead is the same on both sides. While scrolling it grows with
  the items one scroll step moves.
- Every item of a lazy container has one main-axis extent: the given one,
  else the measured extent of the first item in view.
- A lazy container's window is the span its nearest enclosing scroll viewport
  shows. With no viewport, the window is its own rect.
- A lazy container's extent on its axis is the sum of its items and gaps,
  known without building them.
- A lazy container takes the cross-axis extent it is offered.

## The Composable

A `ComposableWidget` reports the layout metadata of its built child.

### Structure

```mermaid
flowchart LR
    widget[widgeting/widget.py]
    builder[widgeting/widget_builder.py]
    kernel[widgeting/widget_kernel.py]
    parent[the parent container]

    parent -- "width_sizing · height_sizing · layout_align · cross_align" --> widget
    widget -- "_built" --> builder
    widget -- "the built child's metadata, or its own" --> kernel
```

| Module | Role |
| --- | --- |
| `widgeting/widget.py` | the declared flags and the getters |
| `widgeting/widget_builder.py` | the built child ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `widgeting/widget_kernel.py` | the stored values (The Sizing) |
| the parent container | reads the metadata |

### Promises

- A declared value wins. An undeclared one is derived from the built child.

## The Fit

A leaf with content of its own places that content inside its rect by a fit
mode.

### Structure

```mermaid
flowchart LR
    fit[rendering/fit.py]
    image[widgets/image.py]
    icon[material/icon.py]
    selection[material/selection_controls.py]
    app[the app]

    app -- "fit · content_alignment" --> image
    image -- "Fit: contain · cover · fill · none" --> fit
    icon & selection -- "contain" --> fit
```

| Module | Role |
| --- | --- |
| `rendering/fit.py` | the four modes |
| `widgets/image.py` | exposes `fit` and `content_alignment` |
| `material/icon.py` | contains its glyph |
| `material/selection_controls.py` | `Checkbox` and `RadioButton` contain their graphic |
| the app | picks a mode for an image |

### Promises

- `cover` and `fill` exist for `Image` alone.

## The Window Sizing

A window's size and position are resolved before layout.

### Structure

```mermaid
flowchart LR
    sizing[runtime/window_sizing.py]
    window[runtime/window.py]
    placement[backends/pyglet/window_placement.py]
    runner[backends/pyglet/runner.py]
    alignment[layout/alignment.py]

    window -- "parse_window_sizing(value) · parse_window_position(value)" --> sizing
    window -- "the parsed WindowPosition" --> runner
    runner -- "apply_initial_position(pyglet_window, pos)" --> placement
    placement -- "the nine-point vocabulary" --> alignment
```

| Module | Role |
| --- | --- |
| `runtime/window_sizing.py` | `WindowSizing`, fixed or auto; `WindowPosition`, an alignment on a screen plus an offset |
| `runtime/window.py` | resolves its size from the content's preferred size when auto ([APP_WINDOW.md](APP_WINDOW.md)) |
| `backends/pyglet/window_placement.py` | places the outer frame in the screen's work area |
| `backends/pyglet/runner.py` | applies the position when the OS window is created ([APP_WINDOW.md](APP_WINDOW.md)) |
| `layout/alignment.py` | the nine points (The Containers) |

### Promises

- A window position is resolved against the screen's work area, never its
  bounds. It places the outer frame, never the client area.
