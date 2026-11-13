# Hit Testing

Hit testing names the widget under a point. Two axes decide it for every
widget. One is whether the widget's own rectangle catches. The other is
whether the test descends into its children.

## Overview

Three groups of modules take part, with the pointer dispatch and the overlay
at their edges.

### Structure

```mermaid
flowchart LR
    resolution[The Resolution]
    box[The Participation Box]
    postures[The Postures]
    window[runtime/window.py]
    overlay[overlay/overlay.py]
    app[the app]

    window -- "root.hit_test(x, y)" --> resolution
    box -- "_hit_test_children(x, y) · _resolve_hit(x, y, child_hit, self_opaque)" --> resolution
    postures -- "HitParticipationBox(child, condition, descend_children, self_opaque)" --> box
    overlay -- "HitParticipationBox(child, condition, descend_children, self_opaque)" --> box
    app -- "defer_pointer() · block_pointer() · absorb_pointer() · passthrough_pointer()" --> postures
```

| Module | Role |
| --- | --- |
| The Resolution | the descent into the children and the widget's own surface |
| The Participation Box | one wrapper that fixes both axes while a condition holds |
| The Postures | the four modifiers, each a setting of the box |
| `runtime/window.py` | asks for the target of a pointer event ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `overlay/overlay.py` | builds its blocking and click-through layers from the box ([OVERLAY.md](OVERLAY.md)) |
| the app | picks a posture |

### Promises

- The hit region is the rectangle, never the painted shape.
- The two axes are not public. A posture is named, never spelled as flags.
- Every widget's hit resolves through `_resolve_hit`.

## The Resolution

`WidgetKernel.hit_test` combines the children's answer with the widget's own
surface.

### Structure

```mermaid
flowchart LR
    kernel[widgeting/widget_kernel.py]
    input[widgeting/widget_input.py]
    box[widgets/box.py]
    iw[material/interactive_widget.py]
    deck[layout/deck.py]
    position[overlay/overlay_position.py]
    window[runtime/window.py]
    children[the child widgets]

    window -- "root.hit_test(x, y)" --> kernel
    kernel -- "hit_test(x - rx, y - ry), topmost first" --> children
    kernel -- "_hit_is_interactive()" --> input
    box -- "is a · _hit_self_opaque(): a painted surface" --> kernel
    iw -- "is a · _in_local_bounds(x, y): the content rect" --> box
    deck & position -- "_resolve_hit(x, y, child_hit, self_opaque=False)" --> kernel
```

| Module | Role |
| --- | --- |
| `widgeting/widget_kernel.py` | the descent, the own-surface policy and the bounds test |
| `widgeting/widget_input.py` | answers whether the widget handles pointer or scroll input ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgets/box.py` | catches on its own surface when it paints a background, a border or a shadow ([BOX_MODEL.md](BOX_MODEL.md)) |
| `material/interactive_widget.py` | bounds the hit to its content rect ([BOX_MODEL.md](BOX_MODEL.md)) |
| `layout/deck.py` | a pure pass-through wrapper ([LAYOUT.md](LAYOUT.md)) |
| `overlay/overlay_position.py` | a pure pass-through wrapper ([OVERLAY.md](OVERLAY.md)) |
| `runtime/window.py` | asks for the target (Overview) |
| the child widgets | each a kernel of its own |

### Sequence

#### A point is resolved

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant K as widgeting/widget_kernel.py
    participant C as the child widgets

    W->>K: hit_test(x, y)
    loop each child, topmost first
        alt the child has a rect with area
            K->>K: skip the child when the point is outside its rect
            K->>C: hit_test(x - rx, y - ry)
        else
            K->>C: hit_test(x, y), untranslated
        end
    end
    alt a child caught
        K-->>W: that widget
    else the widget handles input or paints a surface, and the point is in its bounds
        K-->>W: the widget
    else
        K-->>W: None
    end
```

### Promises

- A widget that handles pointer or scroll input catches its rect. A widget
  that paints a surface catches its rect. Any other widget defers to its
  children.
- A size-less provider such as `ForEach` is no bounds gate for the subtree
  it lifts into its parent.
- A pure pass-through wrapper passes `self_opaque=False`. No wrapper keeps an
  `is self` check of its own.

## The Participation Box

`HitParticipationBox` overrides a subtree's two axes while its condition
holds.

### Structure

```mermaid
flowchart LR
    box[widgeting/hit_participation.py]
    kernel[widgeting/widget_kernel.py]
    binding[widgeting/widget_binding.py]
    observable[observable/value.py]
    shortcuts[runtime/shortcut_dispatch.py]
    modifiers[the postures]
    overlay[overlay/overlay.py]

    modifiers & overlay -- "HitParticipationBox(child, condition, descend_children, self_opaque)" --> box
    box -- "child._hit_test_children(x, y) · _resolve_hit(x, y, child_hit, self_opaque)" --> kernel
    box -- "observe(condition, _set_active)" --> binding
    binding -- "subscribe" --> observable
    shortcuts -- "is_inert" --> box
```

| Module | Role |
| --- | --- |
| `widgeting/hit_participation.py` | overrides a subtree's two axes while its condition holds; reports whether the subtree is inert |
| `widgeting/widget_kernel.py` | the resolution the box drives (The Resolution) |
| `widgeting/widget_binding.py` | the subscription to a `State` condition ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `observable/value.py` | a `State[bool]` condition ([OBSERVABLE.md](OBSERVABLE.md)) |
| `runtime/shortcut_dispatch.py` | reads whether a subtree is inert ([KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)) |
| the postures | the four modifiers that configure the box (The Postures) |
| `overlay/overlay.py` | the backdrop and the blocker ([OVERLAY.md](OVERLAY.md)) |

### Promises

- An inactive box resolves as the wrapped widget would alone.
- The condition is read at construction, never at the first hit.
- The box descends into the wrapped widget's children, not into the widget.
  The wrapped widget's own surface is governed by the box.
- `widgeting/hit_participation.py` imports no modifier.

## The Postures

Four modifiers name one setting of the box each.

### Structure

```mermaid
flowchart LR
    defer[modifiers/defer_pointer.py]
    block[modifiers/block_pointer.py]
    absorb[modifiers/absorb_pointer.py]
    passthrough[modifiers/passthrough_pointer.py]
    visible[modifiers/visible.py]
    box[widgeting/hit_participation.py]
    app[the app]

    app -- "defer_pointer(condition) · block_pointer(condition) · absorb_pointer(condition) · passthrough_pointer(condition)" --> defer & block & absorb & passthrough
    defer -- "descend_children=True, self_opaque=False" --> box
    block -- "descend_children=True, self_opaque=True" --> box
    absorb -- "descend_children=False, self_opaque=True" --> box
    passthrough -- "descend_children=False, self_opaque=False" --> box
    visible -- "passthrough_pointer(not condition)" --> passthrough
```

| Module | Role |
| --- | --- |
| `modifiers/defer_pointer.py` | self never catches, the children do |
| `modifiers/block_pointer.py` | self catches its whole rect, the children still work |
| `modifiers/absorb_pointer.py` | self catches its whole rect, nothing below it is asked |
| `modifiers/passthrough_pointer.py` | the whole subtree is click-through |
| `modifiers/visible.py` | composes the click-through posture into a hidden widget ([MODIFIER.md](MODIFIER.md)) |
| `widgeting/hit_participation.py` | the wrapper each posture configures (The Participation Box) |
| the app | picks a posture, with a `bool` or a `State[bool]` |

### Sequence

#### Two stacked postures resolve a point

```mermaid
sequenceDiagram
    participant O as hit_participation.py, the outer box
    participant I as hit_participation.py, the inner box
    participant K as widgeting/widget_kernel.py

    O->>O: hit_test(x, y)
    alt the outer box descends
        O->>I: hit_test(x, y), through the wrapped widget's children
        I->>K: _resolve_hit(x, y, child_hit, self_opaque of the inner)
        I-->>O: the inner answer
    else
        Note over I: never asked
    end
    O->>K: _resolve_hit(x, y, child_hit, self_opaque of the outer)
```

### Promises

- Stacked postures are nested boxes, the later in `a | b` outermost. The
  outermost box decides whether descent happens. Where two disagree on the
  widget's own surface, the outermost wins.
