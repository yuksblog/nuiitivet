# Keyboard Shortcuts

A shortcut is a key gesture bound to a command. It fires whether or not
anything holds focus.

## Overview

Three groups of modules take part.

### Structure

```mermaid
flowchart LR
    values[The Values]
    binding[The Binding]
    dispatch[The Dispatch]
    backend[the backend]
    app[the app]

    app -- "key_shortcut(spec, on_trigger, scope)" --> binding
    app -- "MenuEntry(shortcut=spec)" --> values
    binding -- "to_shortcut(spec) · ShortcutBinding(shortcut, on_trigger, scope) · shortcut.matches(key, modifier_keys)" --> values
    backend -- "on_key_press(key, modifier_keys)" --> dispatch
    dispatch -- "match(key, modifier_keys, scope) · trigger(binding)" --> binding
    dispatch -- "produces_text(key, modifier_keys)" --> values
    binding -- "on_trigger()" --> app
```

| Module | Role |
| --- | --- |
| The Values | the frozen value types |
| The Binding | the modifier and the menu bar, ending in a widget's `ShortcutNode` |
| The Dispatch | the key-press tiers in the window |
| the backend | the source of key presses ([APP_WINDOW.md](APP_WINDOW.md)) |
| the app | declares the bindings, owns the commands |

### Promises

- A binding lives on a widget. The widget's place in the tree decides
  whether the binding is live.

## The Values

A gesture, a binding and a scope are frozen values, shared between a menu
item and a modifier.

### Structure

```mermaid
flowchart LR
    shortcut[input/shortcut.py]
    codes[input/codes.py]
    menu[menus/model.py]
    keysc[modifiers/key_shortcut.py]
    interaction[widgets/interaction.py]
    window[runtime/window.py]

    shortcut -- "resolve_modifiers(modifiers), at match and display" --> codes
    menu -- "to_shortcut(spec) · shortcut.display" --> shortcut
    keysc -- "to_shortcut(spec) · ShortcutBinding(shortcut, on_trigger, scope)" --> shortcut
    interaction -- "shortcut.matches(key, modifier_keys)" --> shortcut
    window -- "produces_text(key, modifier_keys)" --> shortcut
```

| Module | Role |
| --- | --- |
| `input/shortcut.py` | `Shortcut`, a key name with its modifier mask; `ShortcutBinding`, the gesture with its callback and its scope, `FOCUS`, `FOREGROUND` or `MOUNT`; `produces_text`, whether a key press may become text |
| `input/codes.py` | the `MOD_*` masks; turns `MOD_ACCEL` into the platform's primary modifier |
| `menus/model.py` | `MenuEntry` holds a `Shortcut` and shows its display form ([MENU_BAR.md](MENU_BAR.md)) |
| `modifiers/key_shortcut.py` | builds the binding (The Binding) |
| `widgets/interaction.py` | matches a key press against the bindings it holds (The Binding) |
| `runtime/window.py` | asks whether a key is text (The Dispatch) |

### Promises

- `MOD_ACCEL` is resolved when a gesture is matched or displayed, never when
  it is constructed.
- Both sides of a match pass through `normalize_key_name`.

## The Binding

A binding reaches a widget through `key_shortcut` or through a menu bar. Both
end in the widget's `ShortcutNode`.

### Structure

```mermaid
flowchart LR
    keysc[modifiers/key_shortcut.py]
    interaction[widgets/interaction.py]
    bar[menubar/bar.py]
    shortcut[input/shortcut.py]
    app[the app]

    app -- "widget.modifier(key_shortcut(spec, on_trigger, scope))" --> keysc
    bar -- "KeyShortcutModifier(binding).apply(bar)" --> keysc
    keysc -- "ensure_interaction_region(widget) · region.add_node(ShortcutNode()) · node.bind(binding)" --> interaction
    interaction -- "shortcut.matches(key, modifier_keys)" --> shortcut
    interaction -- "binding.on_trigger()" --> app
```

| Module | Role |
| --- | --- |
| `modifiers/key_shortcut.py` | `key_shortcut`, the modifier that puts a binding on a widget |
| `widgets/interaction.py` | `ShortcutNode`, one widget's bindings keyed by gesture, on its `InteractionRegion` ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `menubar/bar.py` | binds each menu item's shortcut on the bar widget ([MENU_BAR.md](MENU_BAR.md)) |
| `input/shortcut.py` | the gesture (The Values) |
| the app | the widget the binding is applied to, the callback it names |

### Promises

- A `ShortcutNode` holds one binding per gesture.
- A menu item's shortcut is a `MOUNT` binding on the menu bar.
- A menu item and a `key_shortcut` binding reference the command's callback.
  Neither owns it.

## The Dispatch

The window offers a key press to the focused node first, then to the
bindings, narrowest scope first.

### Structure

```mermaid
flowchart LR
    window[runtime/window.py]
    interaction[widgets/interaction.py]
    scopes[runtime/shortcut_dispatch.py]
    overlay[overlay/overlay.py]
    shortcut[input/shortcut.py]
    backend[the backend]
    tree[the widget tree]

    backend -- "on_key_press(key, modifier_keys)" --> window
    window -- "FocusNode.handle_key_event(key, modifier_keys) · accepts_text_input" --> interaction
    window -- "produces_text(key, modifier_keys)" --> shortcut
    window -- "ShortcutNode.match(key, modifier_keys, scope) · trigger(binding)" --> interaction
    window -- "is_foreground(owner)" --> scopes
    scopes -- "Overlay.of(widget, root=True).occluding_content_widget()" --> overlay
    scopes -- "blocks_focus_traversal · is_inert · focus_traversal_children() · _stack.top()" --> tree
    window -- "children_snapshot() · built_child, from the root" --> tree
```

| Module | Role |
| --- | --- |
| `runtime/window.py` | resolves a key press in tiers; collects the `ShortcutNode`s of the tree |
| `widgets/interaction.py` | the focused `FocusNode` and the chain it bubbles along ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)); the `ShortcutNode`s (The Binding) |
| `runtime/shortcut_dispatch.py` | answers whether a widget is on the topmost interactable layer |
| `overlay/overlay.py` | names the content of the topmost blocking entry ([OVERLAY.md](OVERLAY.md)) |
| `input/shortcut.py` | `produces_text` (The Values) |
| the backend | the source of key presses ([APP_WINDOW.md](APP_WINDOW.md)) |
| the widget tree | the ancestors asked whether they hide the widget ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |

### Sequence

#### A key press reaches a binding

```mermaid
sequenceDiagram
    participant B as the backend
    participant W as runtime/window.py
    participant I as widgets/interaction.py
    participant S as shortcut_dispatch.py

    B->>W: on_key_press(key, modifier_keys)
    Note over W: Escape and Tab are handled before this
    W->>I: handle_key_event(key, modifier_keys), the focused node and its ancestors
    alt consumed
        I-->>W: True
    else declined
        W->>I: accepts_text_input
        alt the chain takes text, and produces_text(key, modifier_keys)
            Note over W: no binding is consulted
        else
            W->>I: match(key, modifier_keys, FOCUS), the focused node's ancestors innermost first
            alt one matched
                W->>I: trigger(binding)
            else none
                W->>S: is_foreground(owner), every node in the tree
                W->>I: match(key, modifier_keys, FOREGROUND), the nodes in the foreground
                alt exactly one matched
                    W->>I: trigger(binding)
                else several matched
                    Note over W: warn once, fire none
                else none
                    W->>I: match(key, modifier_keys, MOUNT), every node
                    Note over W: one fires, several warn, none falls through
                end
            end
        end
    end
```

### Promises

- A key the focused chain consumes reaches no binding.
- A key the focused chain can type reaches no binding. When text and a
  shortcut can both claim a key, the key is text.
- Among `FOCUS` bindings the innermost enclosing the focused node wins.
- Several `FOREGROUND` or `MOUNT` matches fire nothing.
- A widget is in the foreground by the same test that puts it in the Tab
  sequence.
- A blocking overlay entry puts everything outside its content out of the
  foreground. A passthrough entry blocks nothing.
