# Overlay

`Overlay.show()` puts a layer on top of the window. It stands on the same
transition kernel as the navigator ([NAVIGATION.md](NAVIGATION.md)).

## Overview

Four groups of modules take part, with the window, the kernel, the reload
snapshot and the consumers at their edges.

### Structure

```mermaid
flowchart LR
    overlay[The Overlay]
    layer[The Layer]
    handle[The Handle]
    material[The Material Layer]
    window[runtime/window.py]
    kernel[transition/]
    snapshot[dev/overlay_snapshot.py]
    consumers[the consumers]

    window -- "overlay_factory() · Stack([navigator, overlay]) · occluding_content_widget() · async_request_close_topmost()" --> overlay
    consumers -- "Overlay.of(context).show(content, passthrough, dismiss_on_outside_tap, backdrop, timeout, position, transition)" --> overlay
    overlay -- "build_layer(layer)" --> layer
    overlay -- "OverlayHandle(overlay, entry) · complete the future" --> handle
    overlay -- "StackRuntime · TransitionEngine · TransitionSpec" --> kernel
    material -- "is a · show(...) with the MD3 transition" --> overlay
    material -- "MaterialOverlayLayerComposer" --> layer
    snapshot -- "snapshot_stack() · restore_stack(records)" --> overlay
```

| Module | Role |
| --- | --- |
| The Overlay | keeps the stack of entries and resolves which overlay a context belongs to |
| The Layer | builds what one entry puts in the tree |
| The Handle | closes an entry and reports how it ended |
| The Material Layer | adds the MD3 presets, the intents and the scrim |
| `runtime/window.py` | builds the overlay from a factory beside the navigator, holds it for the lookup, asks what blocks the keyboard ([APP_WINDOW.md](APP_WINDOW.md)) |
| `transition/` | the stack runtime and the transition engine ([NAVIGATION.md](NAVIGATION.md)) |
| `dev/overlay_snapshot.py` | carries the open intents across a hot reload ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| the consumers | the widgets and modifiers that show a layer, and the shortcut dispatch that asks what blocks |

### Promises

- `overlay` imports nothing from `navigation`. Both import `transition`.
- One overlay per window.

## The Overlay

`Overlay` keeps a private stack of layers, one per entry.

### Structure

```mermaid
flowchart LR
    overlay[overlay/overlay.py]
    stackrt[transition/stack.py]
    engine[transition/engine.py]
    layout[layout/stack.py]
    window[runtime/window.py]
    lookup[widgeting/context_lookup.py]
    shortcuts[runtime/shortcut_dispatch.py]
    app[the app]

    app -- "Overlay.of(self) · show(...) · close(value, target)" --> overlay
    overlay -- "find_provider(context, cls) · find_window(context)" --> lookup
    window -- "overlay_factory() · _overlay · async_request_close_topmost() · occluding_content_widget()" --> overlay
    overlay -- "push(layer) · mark_active · mark_exiting · pop · can_pop" --> stackrt
    overlay -- "start(start, target, apply, on_complete, motion)" --> engine
    overlay -- "add_child(widget) · remove_child(widget)" --> layout
    shortcuts -- "occluding_content_widget()" --> overlay
```

| Module | Role |
| --- | --- |
| `overlay/overlay.py` | `Overlay`: the entries, their layers, their futures; `_LayerStack`, the `Stack` of layer widgets; `_OverlayLayer`, one entry with its transition state |
| `transition/stack.py` | tracks which layers enter, stay and exit ([NAVIGATION.md](NAVIGATION.md)) |
| `transition/engine.py` | drives a transition's progress ([ANIMATION_SYSTEM.md](ANIMATION_SYSTEM.md)) |
| `layout/stack.py` | paints the layers in order ([LAYOUT.md](LAYOUT.md)) |
| `runtime/window.py` | holds the overlay as a sibling of the navigator, routes a back action to it, asks what blocks the keyboard ([NAVIGATION.md](NAVIGATION.md)) |
| `widgeting/context_lookup.py` | the ancestor search and the window lookup behind `Overlay.of` |
| `runtime/shortcut_dispatch.py` | asks what blocks the keyboard ([KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)) |
| the app | shows and closes entries |

### Sequence

#### An entry is shown and closed

```mermaid
sequenceDiagram
    participant A as the app
    participant O as overlay.py
    participant R as transition/stack.py
    participant E as transition/engine.py
    participant L as layout/stack.py

    A->>O: show(content, ...)
    O->>R: push(layer)
    O->>L: add_child(layer widget)
    alt the layer has a transition
        O->>E: start(0, 1, apply, on_complete), the enter motion
        E->>O: apply(progress), invalidate
        E->>O: on_complete
        O->>R: mark_active(layer)
    else
        O->>R: mark_active(layer)
    end
    A->>O: handle.close(value)
    O->>R: mark_exiting(layer)
    opt the layer has a transition
        O->>E: start(0, 1, apply, on_complete), the exit motion
        E->>O: on_complete
    end
    O->>R: pop
    O->>L: remove_child(layer widget)
    O->>O: entry.dispose(), the widget unmounts
```

### Promises

- Paint order is insertion order.
- An entry's widget mounts once, when shown. It unmounts once, when its entry
  leaves the stack. The other layers are untouched by a show or a close.
- `Overlay.of` searches the ancestors for the calling class first, then
  falls back to the window's overlay.
- An entry stays open until its exit transition finishes.
- The keyboard side of `passthrough` is read through
  `occluding_content_widget()`, the content of the topmost layer shown with
  `passthrough=False`.
- A window takes its overlay as it takes its content. An instance keeps the
  window hot-reload inert. A factory is re-invoked on a reload.

## The Layer

`build_layer` assembles the widget one entry puts in the tree.

### Structure

```mermaid
flowchart LR
    overlay[overlay/overlay.py]
    composer[overlay/layer_composer.py]
    position[overlay/overlay_position.py]
    hit[widgeting/hit_participation.py]
    interaction[widgets/interaction.py]
    layout[layout/stack.py]
    mcomposer[material/overlay_visual_state.py]

    overlay -- "compose(OverlayLayerCompositionContext(content, transition_state, backdrop, position_content))" --> composer
    composer -- "OverlayLayerPaint(content, backdrop)" --> overlay
    overlay -- "make_position_content(content)" --> position
    overlay -- "HitParticipationBox(backdrop, descend_children=False, self_opaque=False) · HitParticipationBox(blocker, descend_children=True, self_opaque=True)" --> hit
    overlay -- "ensure_interaction_region(blocker).enable_click(on_outside_tap, any_button=True)" --> interaction
    overlay -- "Stack([backdrop, blocker, content])" --> layout
    mcomposer -- "is a" --> composer
```

| Module | Role |
| --- | --- |
| `overlay/overlay.py` | `build_layer`, assembles the layer; `_PassthroughRectBox`, exempts one window rect from the blocker; `_DefaultOverlayLayerComposer`, a neutral backdrop |
| `overlay/layer_composer.py` | `OverlayLayerComposer`, the protocol a design system implements; the context it receives, the paint it returns |
| `overlay/overlay_position.py` | `OverlayPosition`: `aligned`, `anchored`, `at_point`, `at_pointer`; each wraps the content in a widget that places it |
| `widgeting/hit_participation.py` | a box that decides whether a hit descends to its child and whether the box itself catches ([HIT_TESTING.md](HIT_TESTING.md)) |
| `widgets/interaction.py` | the region that turns a hit on the blocker into the outside tap ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `layout/stack.py` | stacks the three ([LAYOUT.md](LAYOUT.md)) |
| `material/overlay_visual_state.py` | the Material composer (The Material Layer) |

### Sequence

#### A tap lands on a blocking layer

```mermaid
sequenceDiagram
    actor U as the user
    participant L as layout/stack.py
    participant O as overlay.py
    participant H as hit_participation.py
    participant I as widgets/interaction.py

    U->>L: a tap, hit_test(x, y)
    L->>L: the content first
    alt the tap is on the content
        L-->>U: the content acts
    else outside the content
        L->>O: _PassthroughRectBox.hit_test(x, y)
        alt the passthrough_rect contains the tap
            O-->>L: None, the app behind receives the tap
        else
            O->>H: the blocker box
            H-->>L: the box itself
            L->>I: the pointer event, any button
            I->>O: on_outside_tap, when dismiss_on_outside_tap
            O->>O: _request_dismiss_entry(entry, OUTSIDE_TAP), through will_pop
        end
    end
```

### Promises

- A composer returns the content and the backdrop side by side. The core
  stacks them.
- The backdrop never catches a hit.
- A layer with `passthrough=False` has a blocker that catches every hit the
  content does not.
- The composition context carries visual facts only. No `passthrough`, no
  dismissibility, no barrier colour reaches a composer.

## The Handle

`show()` returns a handle. The handle closes its entry and awaits its
result.

### Structure

```mermaid
flowchart LR
    overlay[overlay/overlay.py]
    entry[overlay/overlay_entry.py]
    handle[overlay/overlay_handle.py]
    result[overlay/result.py]
    aware[overlay/overlay_aware.py]
    willpop[modifiers/will_pop.py]
    clock[observable/runtime.py]
    snapshot[dev/overlay_snapshot.py]
    app[the app]

    overlay -- "OverlayEntry(builder, on_dispose) · build_widget() · dispose()" --> entry
    overlay -- "OverlayHandle(overlay, entry)" --> handle
    handle -- "_close_entry(entry, value) · _request_dismiss_entry(entry, value, reason) · _future_for_entry(entry)" --> overlay
    overlay -- "OverlayResult(value, reason)" --> result
    overlay -- "_set_overlay_handle(handle)" --> aware
    overlay -- "handle_back_event()" --> willpop
    overlay -- "schedule_once(on_timeout, timeout)" --> clock
    snapshot -- "snapshot_stack() · restore_stack(records)" --> overlay
    app -- "handle.close(value) · await handle · handle.done()" --> handle
```

| Module | Role |
| --- | --- |
| `overlay/overlay.py` | one future per entry; completes it with a reason; the records of the entries shown from an intent |
| `overlay/overlay_entry.py` | `OverlayEntry`: builds the layer widget on demand, unmounts it on dispose, names its content without building |
| `overlay/overlay_handle.py` | `OverlayHandle`: `close`, `request_close`, `done`, `result`, awaitable |
| `overlay/result.py` | `OverlayResult`, the value and the reason: `CLOSED`, `OUTSIDE_TAP`, `TIMEOUT` or `DISPOSED` |
| `overlay/overlay_aware.py` | `OverlayAware`, a content widget that receives its own handle |
| `modifiers/will_pop.py` | lets the content refuse a dismissal ([MODIFIER.md](MODIFIER.md)) |
| `observable/runtime.py` | the installed clock, for `timeout` ([OBSERVABLE.md](OBSERVABLE.md)) |
| `dev/overlay_snapshot.py` | the reload's snapshot of the overlay ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| the app | holds the handle |

### Sequence

#### A handle is awaited

```mermaid
sequenceDiagram
    participant A as the app
    participant H as overlay_handle.py
    participant O as overlay.py
    participant P as modifiers/will_pop.py

    A->>H: await handle
    H->>O: _future_for_entry(entry)
    alt handle.close(value)
        H->>O: _close_entry(entry, value)
        O->>O: the future: OverlayResult(value, CLOSED)
    else an outside tap, Escape, or request_close
        O->>P: handle_back_event(), on the content
        alt refused
            Note over O: the entry stays open
        else
            O->>O: the future: OverlayResult(value, OUTSIDE_TAP or CLOSED)
        end
    else the timeout fires
        O->>O: the future: OverlayResult(None, TIMEOUT)
    else the entry is removed any other way
        O->>O: the future: OverlayResult(None, DISPOSED)
    end
    O-->>A: the result
```

#### A reload carries an entry

```mermaid
sequenceDiagram
    participant S as dev/overlay_snapshot.py
    participant Old as the old overlay.py
    participant New as the new overlay.py

    S->>Old: snapshot_stack()
    Old->>Old: mark the entries shown from an intent as carried
    Old-->>S: the records, intent and replay and handle
    Note over Old: unmount, the carried entries complete nothing
    S->>New: restore_stack(records)
    loop each record
        New->>New: replay(self, intent), a new entry
        New->>Old: take the entry's future
        New->>New: the old handle now points at the new entry
    end
```

### Promises

- An await never hangs. An entry removed without a close completes with
  `DISPOSED`, unless a snapshot carried it to the rebuilt overlay.
- A result is settled once. A settled result survives the entry's removal
  until the handle reads it.
- `OverlayAware` content holds its handle before its first build.
- An entry shown from an intent survives a reload with its handle. One shown
  from a widget does not.
- A refusal from `will_pop` keeps the entry open.
- Unmounting the overlay removes every entry at once, without exit
  transitions.

## The Material Layer

The Material design system subclasses the overlay.

### Structure

```mermaid
flowchart LR
    moverlay[material/overlay.py]
    overlay[overlay/overlay.py]
    mcomposer[material/overlay_visual_state.py]
    resolver[overlay/intent_resolver.py]
    protocols[material/protocols.py]
    mwindow[material/window.py]
    transitions[material/transitions.py]
    theme[theme/theme.py]

    moverlay -- "is a · show(content, backdrop, dismiss_on_outside_tap, position, transition) · _record_for_restore(handle, intent, replay)" --> overlay
    moverlay -- "layer_composer=MaterialOverlayLayerComposer()" --> mcomposer
    moverlay -- "resolve(intent)" --> resolver
    moverlay -- "is a: MaterialOverlayProtocol" --> protocols
    moverlay -- "MaterialTransitions.dialog() · snackbar() · side_sheet() · bottom_sheet()" --> transitions
    mcomposer -- "ColorRole.SCRIM" --> theme
    mwindow -- "_build_default_overlay(): MaterialOverlay()" --> moverlay
```

| Module | Role |
| --- | --- |
| `material/overlay.py` | `MaterialOverlay`: the presets, each a `show` with the MD3 transition and position; `WhileLoading`, the context manager |
| `overlay/overlay.py` | the core (The Overlay) |
| `material/overlay_visual_state.py` | `MaterialOverlayLayerComposer`, the scrim at the theme's `SCRIM` colour, faded with the transition |
| `overlay/intent_resolver.py` | `IntentResolver` and `MappingIntentResolver`, an intent type to the widget that shows it |
| `material/protocols.py` | `MaterialOverlayProtocol`, exported as `nv.OverlayProtocol`, what a ViewModel sees |
| `material/window.py` | `MaterialWindow`, whose default overlay is a `MaterialOverlay` |
| `material/transitions.py` | the MD3 transition specs ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |
| `theme/theme.py` | the colour roles ([STYLE_THEME.md](STYLE_THEME.md)) |

### Promises

- An intent cannot change how its entry enters.
- No design-system colour appears in `overlay/`. The default composer's
  backdrop is a private constant.
