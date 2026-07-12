# Interaction Architecture

This document defines the unified architecture for handling user interactions, including pointer events, focus management, and keyboard input.

## Core Concepts

The interaction system is built around a **Node-based** architecture, where `InteractionRegion` (or any `InteractionHostMixin` widget) acts as a host for specialized logic nodes.

### 1. Interaction Nodes

Logic is split into specialized nodes inheriting from `InteractionNode`:

- **`PointerInputNode`**: Handles pointer events (hover, click, press). Formerly known as `InteractionController`.
- **`FocusNode`**: Handles focus state, traversal participation, and key events.
- **`FocusScope`**: Marks a subtree as one traversal group, roving between its members (see [Focus Traversal Groups](#focus-traversal-groups-focusscope)).

### 2. Hosting Strategy

Widgets can host these nodes in two ways:

1. **External Composition (via Modifiers)**:
    - `Modifier.focusable()` wraps a widget in an `InteractionRegion`.
    - The `InteractionRegion` hosts the `FocusNode`.
    - Used for making arbitrary widgets focusable.

2. **Internal Composition (Standard Widgets)**:
    - Core widgets like `Button`, `Checkbox`, `TextField` inherit from `InteractionHostMixin`.
    - They instantiate and add `FocusNode` (and `PointerInputNode`) directly in their `__init__`.
    - **Benefit**: Reduces widget tree depth by avoiding wrapper widgets for standard controls.

### 3. Shared State

All interaction nodes attached to a host share a single `InteractionState` object. This ensures that visual states (hovered, pressed, focused, disabled) are centralized and easily accessible by the widget for rendering.

- **`hovered`**: True when a pointer is within the widget's bounds.
- **`pressed`**: True when a pointer is down within the widget.
- **`focused`**: True when the widget has keyboard focus.
- **`disabled`**: Disables all interaction logic when True.

## Pointer System

Pointer events are handled by `PointerInputNode`.

- **Dispatch**: Events flow from `App` -> `Widget` -> `InteractionHostMixin` -> `PointerInputNode`.
- **Hit Testing**: `PointerInputNode` checks if the event coordinates are within the widget's bounds.
- **State Updates**: Automatically updates `hovered` and `pressed` flags in the shared `InteractionState`.
- **Callbacks**: Triggers `on_click` callbacks when a valid press-and-release sequence is detected.

## Focus System

### Focusable vs. Traversable

Holding focus and being a stop in the Tab sequence are **two separate properties**:

| Property | Carrier | Meaning |
| :--- | :--- | :--- |
| Focusable | owning a `FocusNode` | The widget can hold focus, receive key events, and paint a focus ring. |
| Traversable | `FocusNode.traversable` (default `True`) | The global Tab sequence stops on it. |

`App._collect_focus_nodes` collects only the **traversable** nodes. A node with `traversable=False` is still focusable: it can be focused programmatically (typically by the `FocusScope` that owns it), it still receives keys, and its keys still bubble — Tab merely never lands on it. `Clickable` and `InteractiveWidget` expose `traversable` as a constructor argument.

This split is what makes a group (menu, multi-handle slider) expressible: without it, every focusable part of a widget is unavoidably its own Tab stop.

### Focus Traversal

- **Order**: Depth-first search (visual order) through the widget tree, collecting the traversable `FocusNode`s.
- **Navigation**: `Tab` moves forward, `Shift+Tab` moves backward.
- **State**: `FocusNode` maintains a `focused` boolean state. This state syncs with `InteractionState.focused` on the host widget to drive visual updates (e.g., focus rings).
- **Scopes first**: On Tab, the `FocusScope` enclosing the focused node is consulted **before** the global sequence (see below).

### Click-to-Focus and the Focus Source

`PointerInputNode` automatically requests focus for its host if a `FocusNode` is present when a press event occurs. Focus carries a `FocusSource` (`KEYBOARD` / `POINTER`), and MD3 suppresses the focus ring when focus is pointer-driven (`InteractiveWidget.should_show_focus_ring`).

The source can change **without focus moving** — dragging a slider that Tab focused makes it pointer-driven; Tab-ing between its handles makes it keyboard-driven again. Since both `App.request_focus` and `FocusNode._set_focused` short-circuit when nothing changes, `FocusNode.notify_focus_source(source)` re-announces the source to the widget in that case. Without it, the ring state gets stuck at whatever the last *focus change* said.

## Key Event Routing

Key events follow a **Bubbling** model:

1. **Dispatch**: The `App` sends the key event to the currently focused `FocusNode`.
2. **Handle**: The node's `on_key` handler is invoked.
3. **Bubble**: If the handler returns `False` (not handled), the event bubbles up to the nearest ancestor `FocusNode` in the widget tree.
4. **Root Fallback**: If the event reaches the root without being handled, the `App` may handle default actions (like Tab traversal).

### Text Input Events

In addition to raw key events (`on_key`), `FocusNode` supports high-level text input events necessary for implementing text fields. These events are dispatched by the `App` to the focused node.

- **`on_text(text: str)`**: Called when a character is committed (typed).
- **`on_text_motion(motion: int)`**: Called for navigation actions like Arrow keys, Home, End, Backspace, and Delete.
- **`on_ime_composition(text: str, start: int, length: int)`**: Called when the IME updates the composition string.
  - `text`: The full text being composed (or the text to be inserted).
  - `start`, `length`: The range within `text` that is currently selected or highlighted by the IME.

## Focus Traversal Groups (`FocusScope`)

Some widgets own keyboard navigation *inside* themselves: `RangeSlider` navigates between handles, `Menu` between items. Both are the same problem — a widget that traverses its own parts and decides when Tab escapes to the outside — and both are expressed with one primitive.

A `FocusScope` is an interaction node marking a subtree as **one group**: the unit Tab enters and leaves. It delegates to a `FocusTraversalPolicy`, which enumerates the group's members and tracks the current one.

### Policy contract

Deliberately small, so that real-node owners and virtual-stop owners implement the same thing:

| Method | Purpose |
| :--- | :--- |
| `members()` | The members, in traversal order. |
| `current_index()` | Index of the current member, or `-1` if none. |
| `set_current(index)` | Make that member current (focusing it, if it is a real node). |
| `on_boundary(direction)` | Tab stepped past the last / before the first member: consume it, or let it escape. |

A **member** is whatever the owner traverses between. Two shapes are built in:

- **`FocusNodePolicy`** — members are real child `FocusNode`s (a menu's items), which are marked `traversable=False` so only the policy moves focus between them.
- **`VirtualStopPolicy`** — members are virtual stops the owner keeps for itself (a slider's handle indices). Focus stays on the owner's own `FocusNode` while the scope roves between them.

### Scope behavior

- **Entry direction** — Tab enters the group at its first member, Shift+Tab at its last (`FocusScope.on_enter`). `App` calls this when traversal focuses a widget that hosts a scope, so Shift+Tab into a `RangeSlider` lands on the far handle.
- **Roving** — `FocusScope.move(step, wrap=)` moves to the adjacent member. Whether *Tab* does the roving is the scope's `tab_roves` flag: a slider roves on Tab; a menu roves on the arrow keys and sets `tab_roves=False`, so every Tab is a boundary.
- **Boundary** — the policy decides: returning `False` (the default) lets Tab escape to the next stop outside the group; returning `True` consumes it (a popup menu dismisses itself).

### Dispatch order

`App._dispatch_key_press` consults the scope enclosing the focused node **before** the global traversal, because the focused node may not be a Tab stop at all (a menu item), and the "focused node is not in the traversal list → restart from the first stop" fallback would otherwise fire first and the scope would never get to decide. Scopes resolve innermost-first, so an open submenu answers for the focus inside it rather than its parent menu.

When a scope lets Tab escape and the focused node is not itself a stop, traversal resumes from the scope owner's own stop (`App._scope_owner_node`) rather than restarting at the first stop.

### Applied

| | `Menu` (popup) | `Menu` (inline) | `RangeSlider` |
| :--- | :--- | :--- | :--- |
| Members | enabled items (real `FocusNode`s) | same | handle indices (virtual stops) |
| External Tab stops | none — entered by opening it, which focuses the first item | one (the surface); WAI-ARIA makes a permanently visible menu a single stop | one (the slider) |
| Roving key | Up / Down (`tab_roves=False`) | same | Tab |
| At the boundary | dismiss | escape to the next widget | escape to the next widget |

A single-handle `Slider` is a one-member scope: Tab enters, finds no second member, and hands the key straight back to the global sequence. Submenus are nested scopes.

### Superseded: Tab interception (`wants_tab`)

`RangeSlider` originally intercepted Tab through a per-widget `FocusNode._wants_tab` callback, chosen to avoid relaxing the "1 widget = 1 `FocusNode`" invariant. That mechanism is **removed**: it was a hand-rolled focus scope that only solved the virtual-stop case, and it could not express a menu (whose members are real focus nodes that must not be Tab stops). The invariant it protected is preserved by the `focusable`/`traversable` split, which lets a group own real focusable children without turning each into a Tab stop.

### Future Consideration

When screen reader / accessibility tree support is implemented (via `SemanticsNode`), revisit how the members of a scope are announced. Virtual stops (slider handles) carry no `FocusNode` and therefore no natural place for a per-thumb semantic label (e.g., "Start value: 30"); the `SemanticsNode` design will decide whether the policy grows a semantics hook or virtual stops become real nodes.

Widget groups not yet on this primitive — segmented buttons, radio groups, toolbars, tab bars — all want roving with a single external stop and should be migrated onto it rather than growing their own navigation.

## Node Roles & Extensibility

The Node-based architecture allows for future expansion by adding specialized nodes without modifying the core `InteractionRegion`.

| Node Type | Role & Responsibility | Notes |
| :--- | :--- | :--- |
| **`PointerInputNode`** (Core) | **Point Interaction.** Manages hover, click, and press states. Handles simple tap and mouse-over events. | Successor to `InteractionController`. Triggers "Click-to-Focus". |
| **`FocusNode`** (Core) | **Keyboard & Order.** Manages focus state, Tab traversal order (`traversable`), and key event reception/bubbling. | Gateway for IME integration. Focusable and traversable are separate properties. |
| **`FocusScope`** (Core) | **Grouped Traversal.** Marks a subtree as a single Tab stop and roves between its members via a `FocusTraversalPolicy`. | Used by `Menu` (real-node members) and `RangeSlider` (virtual stops). Replaces the `wants_tab` interception. |
| **`DraggableNode`** (Core) | **Movement (Source).** Handles drag start, delta updates, and end detection. Manages drag previews. | Distinct from `PointerInputNode`; handles movement (deltas). Includes long-press initiation logic. |
| **`DropTargetNode`** (Future) | **Acceptance (Target).** Determines whether dropped data is accepted and processes data on drop. | `InteractionRegion` hit-testing identifies this node as a drop candidate. |
| **`ScrollableNode`** (Future) | **Scrolling.** Handles mouse wheel, touchpad pan, and inertia calculations. | Collaborates with `ScrollViewport`. Consumes pointer events to produce scroll offsets. |
| **`SemanticsNode`** (Future) | **Meaning & A11y.** Provides labels, roles, and state for screen readers and bridges to OS accessibility APIs. | Decoupled from visuals/input. Collaborates with `FocusNode` to announce location. |
| **`ContextMenuNode`** (Future) | **Auxiliary Action.** Triggers context menus via right-click or long-press. | Abstracts platform-specific conventions (right-click vs long-press). |
