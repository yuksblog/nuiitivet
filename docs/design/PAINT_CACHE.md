# Paint Cache

A frame's paint cost is the Python walk of the widget tree. Three caches
skip part of that walk: one widget's own visuals, the whole frame, and the
children of a container.

## Overview

Three groups of modules take part, one per cache, with the invalidation
paths at their edges.

### Structure

```mermaid
flowchart LR
    own[The Own Visuals]
    frame[The Whole Frame]
    children[The Child Pictures]
    widget[widgeting/widget.py]
    kernel[widgeting/widget_kernel.py]
    runner[backends/pyglet/runner.py]
    dev[dev/]

    widget -- "_invalidate_paint_cache(), from a paint dependency setter" --> own
    widget -- "invalidate(): app.invalidate(content=True)" --> frame
    widget -- "invalidate(): _mark_replay_dirty()" --> kernel
    kernel -- "_replay_dirty" --> children
    runner & dev -- "invalidate(content=False)" --> frame
```

| Module | Role |
| --- | --- |
| The Own Visuals | one widget's background layers, as a Skia surface |
| The Whole Frame | the last painted tree, as an image |
| The Child Pictures | a picture of each clean child of a container |
| `widgeting/widget.py` | `Widget.invalidate` ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `widgeting/widget_kernel.py` | the replay mark on every widget |
| `backends/pyglet/runner.py` | drives the frames ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `dev/` | the overlays drawn over the tree ([DEV_MODES.md](DEV_MODES.md)) |

### Promises

- Every paint-affecting change passes through `Widget.invalidate()`.
- The own-visuals cache answers to its widget's own properties only. The
  frame and the child pictures are marked by every change below them.

## The Own Visuals

A widget with heavy own visuals records its background layers once and blits
them until one of its own properties changes.

### Structure

```mermaid
flowchart LR
    cache[rendering/skia/paint_cache.py]
    box[widgets/box.py]
    widget[widgeting/widget.py]
    dependency[theme/dependency.py]
    skia[rendering/skia/skia_module.py]

    box -- "is a · replay_paint_cache(canvas, x, y, w, h) · with paint_cache(canvas, x, y, w, h) as target" --> cache
    widget -- "_invalidate_paint_cache(), when a name in _paint_dependencies is set" --> cache
    dependency -- "invalidate_paint_cache(), on a theme change" --> widget
    cache -- "Surface · makeImageSnapshot · drawImage" --> skia
```

| Module | Role |
| --- | --- |
| `rendering/skia/paint_cache.py` | `CachedPaintMixin`: the offscreen surface, its snapshot, and the size, outsets and device scale it was recorded at |
| `widgets/box.py` | `Box`, the mixin's user; its background, border and shadow are the recorded layers ([BOX_MODEL.md](BOX_MODEL.md)) |
| `widgeting/widget.py` | clears the cache when a declared paint dependency is set; `invalidate_paint_cache`, the explicit clear ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `theme/dependency.py` | re-measures and clears the cache of a marked leaf on a theme change ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `rendering/skia/skia_module.py` | the Skia binding ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |

### Promises

- A descendant's change leaves the cache in place.
- A cache recorded for another size, outset or device scale is not drawn.
  The widget records again.

## The Whole Frame

A redraw whose content did not change re-blits the last painted tree. The
overlays are painted fresh over it.

### Structure

```mermaid
flowchart LR
    window[runtime/window.py]
    gpu[backends/pyglet/gpu_frame.py]
    runner[backends/pyglet/runner.py]
    dev[dev/]
    widget[widgeting/widget.py]

    widget -- "invalidate(immediate), content=True" --> window
    runner -- "invalidate(immediate=True, content=False), on show and activate" --> window
    dev -- "invalidate(content=False)" --> window
    gpu -- "_paint_dirty · _gpu_frame_cache · _gpu_frame_cache_size" --> window
    runner -- "draw_gpu_frame(window)" --> gpu
    window -- "_render_display_frame(scale): _content_image" --> window
```

| Module | Role |
| --- | --- |
| `runtime/window.py` | the two dirty flags, and the raster path's tree image |
| `backends/pyglet/gpu_frame.py` | the GPU path's full-frame cache |
| `backends/pyglet/runner.py` | drives the frame; asks for one with the tree unchanged on show and activate ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `dev/` | the overlays drawn over the tree ([DEV_MODES.md](DEV_MODES.md)) |
| `widgeting/widget.py` | `Widget.invalidate`, a content change (Overview) |

### Sequence

#### A frame is drawn

```mermaid
sequenceDiagram
    participant R as runner.py
    participant W as runtime/window.py
    participant G as gpu_frame.py

    R->>G: draw_gpu_frame(window)
    alt _paint_dirty is clear, and the cache matches the physical size
        G->>G: clear, drawImage(cache) at 1:1
    else
        G->>W: root.paint(canvas)
        G->>W: _gpu_frame_cache = surface snapshot, _paint_dirty = False
    end
    G->>G: paint the dev overlays
    G->>W: _dirty = False
```

### Promises

- `_dirty` says a frame was requested. `_paint_dirty` says the tree must be
  painted again. A content change sets both. A redraw with the tree
  unchanged sets the first only.
- The cached frame holds no dev overlay.
- The raster path and the GPU path keep the same two flags.
- A cached frame fills the whole back buffer.
- A content change paints the tree from its root.

## The Child Pictures

A container keeps a picture of a child and replays it while the child is
clean.

### Structure

```mermaid
flowchart LR
    containers[the containers]
    utils[layout/layout_utils.py]
    viewport[layout/scroll_viewport.py]
    kernel[widgeting/widget_kernel.py]
    replay[widgeting/paint_replay.py]
    events[runtime/app_events.py]
    tree[the widget tree]
    skia[rendering/skia/skia_module.py]

    containers -- "paint_laid_out_children(container, canvas, x, y) · paint_children_at_layout_rects(children, canvas, x, y)" --> utils
    viewport -- "content.paint(canvas, x, y, w, h), the scroll offset subtracted" --> tree
    utils -- "_replay_dirty · _replay_picture · _replay_origin · _replay_key · _replay_skip" --> kernel
    utils -- "_replay_safe on paint and the draw_* hooks" --> replay
    utils -- "paint(target, x, y, w, h), to record a child · paint_outsets()" --> tree
    utils -- "PictureRecorder · drawPicture" --> skia
    events -- "_mark_replay_dirty()" --> kernel
```

| Module | Role |
| --- | --- |
| the containers | `Column`, `Row`, `Flow`, `Grid`, `UniformFlow` and `Stack`; each hands its children to the child painter ([LAYOUT.md](LAYOUT.md)) |
| `layout/layout_utils.py` | paints a container's children; records a clean child and replays its picture ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `layout/scroll_viewport.py` | paints its content at a position with the scroll offset subtracted ([LAYOUT.md](LAYOUT.md)) |
| `widgeting/widget_kernel.py` | the replay mark, the picture and its key on each widget |
| `widgeting/paint_replay.py` | `replay_safe`, the declaration on a draw method that skipping it on a clean frame is safe |
| `runtime/app_events.py` | delivers pointer events ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| the widget tree | a container's children and the widgets under them |
| `rendering/skia/skia_module.py` | the Skia binding |

### Sequence

#### A container paints its children

```mermaid
sequenceDiagram
    participant C as the containers
    participant U as layout_utils.py
    participant K as widget_kernel.py
    participant T as the widget tree

    C->>U: paint_laid_out_children(container, canvas, x, y), or a Stack's paint_children_at_layout_rects(children, canvas, x, y)
    loop each child
        alt culled, outside the clip
            U->>K: _replay_picture = None, _replay_key = None, the child and every widget below it
        else culled, beyond the bounds of the recording under way
            U->>K: _replay_picture = None, _replay_key = None, the child and every widget below it
            U->>U: the recording under way left a widget out
        else the canvas is skewed, rotated or a stand-in
            U->>T: paint(canvas, x, y, w, h)
        else changed, or at a new size or scale, since its last paint
            U->>K: _replay_dirty = False, _replay_key, _replay_picture = None
            U->>T: paint(canvas, x, y, w, h)
        else with a picture
            U->>U: drawPicture, shifted to the child's device position
        else without a picture
            U->>K: _replay_dirty = False, _replay_key
            alt a recording is under way, the child is outside the clip or larger than it, or _replay_skip is set
                U->>T: paint(canvas, x, y, w, h)
            else undeclared
                U->>K: _replay_skip = True
                U->>T: paint(canvas, x, y, w, h)
            else
                U->>T: paint(recorder, x, y, w, h), under the canvas matrix
                U->>U: drawPicture
                alt the recording left a widget out
                    U->>K: _replay_skip = True
                else
                    U->>K: _replay_picture, _replay_origin
                end
            end
        end
    end
```

### Promises

- A child is replayed only when every widget in it declares each of its draw
  methods with `replay_safe`.
- A child is marked changed by every invalidation at or below it.
- A handled pointer event marks the widget that handled it.
- A scroll marks nothing below the viewport.
- A scroll viewport's paint is undeclared.
- A move marks nothing at or below the moved child.
- A layout mark clears `_replay_skip` on the widget and on every widget above
  it.
- A declared widget takes the position its input needs from layout, never
  from its last paint.
- No picture is held at or below a child the cull skipped.
- A picture holds everything its child draws.
