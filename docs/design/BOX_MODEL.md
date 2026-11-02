# Box Model

A parent hands a widget an allocated rect. The widget's padding insets it to
the content rect. A widget may paint past the allocated rect and reports how
far.

## Overview

Four modules give the rects their meaning: the kernel every widget is built
on, the box that paints a surface, the MD3 component, and the scroll
viewport that displaces its content.

### Structure

```mermaid
flowchart LR
    kernel[The Kernel]
    box[The Box]
    component[The Component]
    viewport[The Viewport]
    layout[layout/]
    window[runtime/window.py]

    layout -- "preferred_size(max_w, max_h) · layout(w, h) · set_layout_rect(x, y, w, h)" --> kernel
    window -- "root.hit_test(x, y)" --> kernel
    box -- "is a" --> kernel
    component -- "is a" --> box
    viewport -- "is a · hit_test(x, y) with the offset undone" --> kernel
    kernel -- "visual_offset()" --> viewport
```

| Module | Role |
| --- | --- |
| The Kernel | the rects, the padding, the hit resolution, the overflow contract |
| The Box | a painted surface, a clip, a shadow |
| The Component | an MD3 container drawn inside the padding |
| The Viewport | content painted displaced and clipped |
| `layout/` | the containers that allocate rects ([LAYOUT.md](LAYOUT.md)) |
| `runtime/window.py` | the pointer dispatch ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |

### Promises

- `Widget.padding` means allocated rect to content rect, on every widget.
- Outsets take part in neither layout nor hit testing.
- Hit testing reads layout state, never paint state.

## The Kernel

`WidgetKernel` holds the rects and resolves a hit.

```text
visual bounds (allocated + outsets)
┌──────────────────────────────────┐
│  allocated rect                  │
│  ┌────────────────────────────┐  │
│  │ padding                    │  │
│  │  ┌──────────────────────┐  │  │
│  │  │ content rect         │  │  │
│  │  └──────────────────────┘  │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### Structure

```mermaid
flowchart LR
    kernel[widgeting/widget_kernel.py]
    padding[rendering/padding.py]
    input[widgeting/widget_input.py]
    participation[widgeting/hit_participation.py]
    transform[modifiers/transform.py]
    bounds[rendering/visual_bounds.py]
    utils[layout/layout_utils.py]
    cache[rendering/skia/paint_cache.py]
    layout[layout/]

    kernel -- "parse_padding(pad)" --> padding
    layout -- "preferred_size(max_w, max_h) · layout(w, h) · set_layout_rect(x, y, w, h)" --> kernel
    kernel -- "_hit_is_interactive()" --> input
    participation -- "is a · descend_children · self_opaque" --> kernel
    transform -- "is a · paint_outsets()" --> kernel
    transform -- "transformed_outsets(w, h, translate, scale, rotation, origin)" --> bounds
    utils -- "paint_outsets() · layout_rect" --> kernel
    cache -- "paint_outsets()" --> kernel
```

| Module | Role |
| --- | --- |
| `widgeting/widget_kernel.py` | the padding and the two rects; `hit_test`, which descends into the children and then asks the widget's own surface; `global_visual_rect`; the base `paint_outsets`, zero |
| `rendering/padding.py` | the four-tuple from a number, a pair or a tuple |
| `widgeting/widget_input.py` | answers whether the widget handles pointer or scroll input ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgeting/hit_participation.py` | the explicit hit postures ([HIT_TESTING.md](HIT_TESTING.md)) |
| `modifiers/transform.py` | reports where the transformed corners land ([MODIFIER.md](MODIFIER.md)) |
| `rendering/visual_bounds.py` | the bounding box of a rect under a transform |
| `layout/layout_utils.py` | skips a child whose rect plus outsets lies outside the clip, with a slack band ([PAINT_CACHE.md](PAINT_CACHE.md)) |
| `rendering/skia/paint_cache.py` | sizes a widget's cache to its rect plus outsets ([PAINT_CACHE.md](PAINT_CACHE.md)) |
| `layout/` | the containers ([LAYOUT.md](LAYOUT.md)) |

### Promises

- Every widget that occupies a rect of its own has `padding`. `preferred_size`
  includes it.
- What a widget draws goes inside the content rect.
- A layout box or a leaf hit-tests on its allocated rect.
- A widget that paints outside its allocated rect reports the overflow in
  `paint_outsets()`. Outsets are reported per widget, not per subtree.
- `global_visual_rect` is the layout rect plus every ancestor's
  `visual_offset()`. Input bounds and overlay anchors read it, never
  `last_rect`.

## The Box

`Box` paints a background, a border and a shadow on its allocated rect.

### Structure

```mermaid
flowchart LR
    box[widgets/box.py]
    kernel[widgeting/widget_kernel.py]
    shadow[rendering/shadow.py]
    clip[modifiers/clip.py]
    corner[modifiers/corner_radius.py]
    decoration[modifiers/background.py · border.py · shadow.py]

    box -- "is a · _hit_self_opaque() · paint_outsets() · hit_test(x, y)" --> kernel
    box -- "shadow_outsets(layers)" --> shadow
    clip & corner -- "clip_content = True" --> box
    decoration -- "Box(child, background_color, border_width, shadows, ...)" --> box
```

| Module | Role |
| --- | --- |
| `widgets/box.py` | `Box`: the painted surface, `clip_content`, the shadow's reach |
| `widgeting/widget_kernel.py` | the base hit resolution and outsets (The Kernel) |
| `rendering/shadow.py` | how far a shadow's layers blur and offset |
| `modifiers/clip.py` | turns the clip on ([MODIFIER.md](MODIFIER.md)) |
| `modifiers/corner_radius.py` | rounds the corners and turns the clip on |
| `modifiers/background.py · border.py · shadow.py` | wrap a widget in a `Box` |

### Promises

- A `Box` with a background, a border or a shadow catches a hit on its own
  rect. A bare `Box` defers to its children.
- With `clip_content`, a hit outside the box's rect reaches no child.
- The shadow's reach is the box's outset.

## The Component

`InteractiveWidget` draws its container on the content rect. The padding
band stays transparent.

### Structure

```mermaid
flowchart LR
    iw[material/interactive_widget.py]
    box[widgets/box.py]
    kernel[widgeting/widget_kernel.py]
    styles[material/styles/]

    iw -- "is a · paint_outsets()" --> box
    iw -- "content_rect(x, y, w, h) · _in_local_bounds(x, y)" --> kernel
    iw -- "content_insets · min_width · min_height" --> styles
```

| Module | Role |
| --- | --- |
| `material/interactive_widget.py` | `InteractiveWidget`: the container, the state layer, the border and the focus ring on the content rect; the focus ring's reach |
| `widgets/box.py` | the surface it is built on (The Box) |
| `widgeting/widget_kernel.py` | the content rect (The Kernel) |
| `material/styles/` | the MD3 tokens: the container's insets and its minimum size ([STYLE_THEME.md](STYLE_THEME.md)) |

### Promises

- A component hit-tests on its content rect.
- A component's internal spacing lives on a style token, never on
  `Widget.padding`.
- The touch target is inside the content rect.
- The focus ring's reach is the component's outset while it is enabled.

## The Viewport

`ScrollViewport` paints its content displaced by the scroll offset and
clipped to its rect.

### Structure

```mermaid
flowchart LR
    viewport[layout/scroll_viewport.py]
    kernel[widgeting/widget_kernel.py]
    box[widgets/box.py]
    perception[_interaction/perception.py]
    overlay[overlay/overlay_position.py]

    viewport -- "is a · hit_test(x, y + offset)" --> kernel
    kernel -- "visual_offset(), each ancestor" --> viewport
    perception -- "visual_offset() · visual_clip_rect(), probed by name" --> viewport & box
    overlay -- "global_visual_rect" --> kernel
```

| Module | Role |
| --- | --- |
| `layout/scroll_viewport.py` | `ScrollViewport`: the displaced paint, the hit test inside its rect, `visual_offset`, `visual_clip_rect` ([LAYOUT.md](LAYOUT.md)) |
| `widgeting/widget_kernel.py` | `global_visual_rect` (The Kernel) |
| `widgets/box.py` | publishes its clip rect the same way (The Box) |
| `_interaction/perception.py` | reads where a widget is on screen ([DEV_BRIDGE.md](DEV_BRIDGE.md)) |
| `overlay/overlay_position.py` | anchors a layer to a widget's on-screen rect ([OVERLAY.md](OVERLAY.md)) |

### Sequence

#### A pointer hits a scrolled component

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant K as widget_kernel.py
    participant V as scroll_viewport.py
    participant B as widgets/box.py
    participant C as interactive_widget.py

    W->>K: root.hit_test(x, y)
    K->>V: hit_test(x - rx, y - ry)
    alt outside the viewport rect
        V-->>K: None
    else
        V->>K: hit_test(x, y + offset), the content
        K->>B: hit_test(...), a child
        alt clip_content, and outside the box's rect
            B-->>K: None
        else
            B->>C: hit_test(...), a child
            C->>C: _in_local_bounds: the content rect
            C-->>W: the component, or None
        end
    end
```

### Promises

- A descendant receives no pointer event outside the effective visible
  region, the intersection of every ancestor's.
- A visible region constrains the subtree only. Padding, content and outsets
  are unchanged by it.
- A container that paints its children away from their layout position
  publishes `visual_offset()`.
