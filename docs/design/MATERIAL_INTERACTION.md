# Material Interaction

Every interactive Material widget is an `InteractiveWidget`.

## Overview

Three groups of modules take part.

### Structure

```mermaid
flowchart LR
    interactive[The Interactive Widget]
    overrides[The Overrides]
    transitions[The Transitions]
    focus[widgets/interaction.py]
    theme[theme/]
    navigator[material/navigator.py]
    overlay[material/overlay.py]

    focus -- "on_focus_change(focused, source) · on_key(key, mods) · hovered · pressed · dragging" --> interactive
    interactive -- "ColorRole.ON_SURFACE · ColorRole.SECONDARY" --> theme
    overrides -- "is a · _get_active_state_layer_opacity() · draw_focus_indicator()" --> interactive
    navigator & overlay -- "MaterialTransitions.page() · dialog() · snackbar() · side_sheet() · bottom_sheet()" --> transitions
```

| Module | Role |
| --- | --- |
| The Interactive Widget | the base every interactive Material widget is built on |
| The Overrides | the components that draw the focus layer or the ring differently |
| The Transitions | the MD3 transition presets and the visual spec they resolve to |
| `widgets/interaction.py` | the focus node and the interaction state ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `theme/` | the colour roles ([STYLE_THEME.md](STYLE_THEME.md)) |
| `material/navigator.py` | the page transitions ([NAVIGATION.md](NAVIGATION.md)) |
| `material/overlay.py` | the dialog, snackbar and sheet transitions ([OVERLAY.md](OVERLAY.md)) |

### Promises

- Whether a widget is focused and whether it shows a ring are two separate
  answers.
- `navigation/` and `overlay/` import nothing from `material/`. The Material
  motion reaches them as a `TransitionSpec`.

## The Interactive Widget

`InteractiveWidget` is a `Clickable` with the MD3 state layer, the focus ring
and the Space and Enter binding.

### Structure

```mermaid
flowchart LR
    iw[material/interactive_widget.py]
    clickable[widgets/clickable.py]
    interaction[widgets/interaction.py]
    box[widgets/box.py]
    theme[theme/theme.py]
    skia[rendering/skia/]

    iw -- "is a" --> clickable
    clickable -- "is a" --> box
    iw -- "FocusNode(traversable, on_focus_change, on_key) · state.hovered · pressed · dragging · focused" --> interaction
    iw -- "_pointer_node._emit_click(), on Space and Enter" --> interaction
    iw -- "Theme.of(self), resolving ON_SURFACE and SECONDARY" --> theme
    iw -- "draw_round_rect(canvas, rect, radii, paint)" --> skia
```

| Module | Role |
| --- | --- |
| `material/interactive_widget.py` | `InteractiveWidget`: the state layer's opacity by state, the ring outside the content rect, the pointer flag the ring reads |
| `widgets/clickable.py` | `Clickable`: the click, the disabled state, the focus node ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgets/interaction.py` | tells the widget it is focused, and how ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgets/box.py` | the container it paints on the content rect ([BOX_MODEL.md](BOX_MODEL.md)) |
| `theme/theme.py` | the colour roles ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `rendering/skia/` | the paint |

### Sequence

#### Focus arrives and the ring follows the source

```mermaid
sequenceDiagram
    participant F as widgets/interaction.py
    participant I as material/interactive_widget.py

    Note over F: the window focuses the node with a source
    F->>I: on_focus_change(True, source)
    I->>I: _focus_from_pointer = source is POINTER, invalidate
    Note over F: a Tab within the scope, the source changes without a move
    F->>I: on_focus_change(True, KEYBOARD)
    I->>I: _focus_from_pointer = False, invalidate
    Note over I: paint: the ring when focused and not from the pointer
```

### Promises

- Keyboard focus draws no state layer by default.
- The ring is drawn for keyboard and programmatic focus, never for pointer
  focus. It follows the latest `FocusSource`, whether or not focus moved.
- The ring's reach is the widget's outset ([BOX_MODEL.md](BOX_MODEL.md)).

## The Overrides

Two components draw the focus differently from the base.

### Structure

```mermaid
flowchart LR
    menu[material/menu.py]
    rail[material/navigation_rail.py]
    iw[material/interactive_widget.py]
    scope[widgets/interaction.py]

    menu -- "is a · _get_active_state_layer_opacity() · should_show_focus_ring" --> iw
    rail -- "is a · draw_focus_indicator() · draw_focus_ring(canvas, rect, radii)" --> iw
    menu & rail -- "FocusScope, roving with the arrow keys" --> scope
```

| Module | Role |
| --- | --- |
| `material/menu.py` | `MenuItem`, roved with the arrow keys |
| `material/navigation_rail.py` | the rail item, roved with the arrow keys, its active indicator its focus shape |
| `material/interactive_widget.py` | the base (The Interactive Widget) |
| `widgets/interaction.py` | the scope the items rove in ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |

### Promises

- A roved menu item layers focus.
- A rail item keeps the ring alone, inset on the active indicator.

## The Transitions

The Material layer ships the MD3 transitions as presets over the transition
kernel.

### Structure

```mermaid
flowchart LR
    presets[material/transition_spec.py]
    factories[material/transitions.py]
    visual[material/transition_visual_spec.py]
    motion[material/motion.py]
    kernel[transition/]
    navigator[material/navigator.py]
    overlay[material/overlay.py]
    navstate[material/navigation_visual_state.py]
    overlaystate[material/overlay_visual_state.py]
    app[the app]

    app -- "MaterialTransitions.dialog(enter=FadeIn() | ScaleIn(), exit_=FadeOut())" --> presets
    navigator -- "the route's TransitionSpec" --> navstate
    overlay -- "the layer's TransitionSpec" --> overlaystate
    presets -- "FadeIn · FadeOut · ScaleIn · ScaleOut · SlideInVertically · SlideOutVertically" --> factories
    factories -- "BezierMotion · the MD3 durations" --> motion
    presets -- "TransitionDefinition · FadePattern · ScalePattern · SlidePattern" --> kernel
    navigator & overlay -- "MaterialTransitions.page() · dialog() · snackbar() · side_sheet() · bottom_sheet()" --> presets
    navstate & overlaystate -- "resolve_material_transition_visual_spec(spec, phase, progress, kind)" --> visual
    visual -- "content_opacity · content_scale · content_translation · barrier_opacity" --> navstate & overlaystate
```

| Module | Role |
| --- | --- |
| `material/transition_spec.py` | `MaterialTransitionSpec`, an enter and an exit definition with a barrier mode and the backward variants; `MaterialTransitions`, the presets per component |
| `material/transitions.py` | the fade, scale and slide factories with the MD3 durations |
| `material/transition_visual_spec.py` | resolves a spec, a phase and a progress into opacity, scale, translation and barrier opacity |
| `material/motion.py` | the MD3 motion curves |
| `transition/` | the kernel's definitions and patterns ([ANIMATION_SYSTEM.md](ANIMATION_SYSTEM.md)) |
| `material/navigator.py` | the Material navigator, with the page preset as its default ([NAVIGATION.md](NAVIGATION.md)) |
| `material/overlay.py` | the Material overlay, each preset supplying its surface's transition ([OVERLAY.md](OVERLAY.md)) |
| `material/navigation_visual_state.py` | paints a route frame from the resolved spec |
| `material/overlay_visual_state.py` | paints a layer frame from the resolved spec, the scrim included |
| the app | customises a preset's enter and exit |

### Promises

- A spec with no backward variant plays its forward definition on a pop.
- The barrier fades with the progress where the spec says `fade`.
- A painter reads the resolved visual spec and composes nothing else.
