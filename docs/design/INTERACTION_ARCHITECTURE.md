# Interaction Architecture

This document defines the unified architecture for handling user interactions, including pointer events, focus management, and keyboard input.

## Core Concepts

The interaction system is built around a **Node-based** architecture, where `InteractionRegion` (or any `InteractionHostMixin` widget) acts as a host for specialized logic nodes.

### 1. Interaction Nodes

Logic is split into specialized nodes inheriting from `InteractionNode`:

- **`PointerInputNode`**: Handles pointer events (hover, click, press). Formerly known as `InteractionController`.
- **`FocusNode`**: Handles focus state, traversal participation, and key events.

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

### Focusability

Focusability is explicit. A widget is focusable if and only if it has an attached `FocusNode`.

### Focus Traversal

- **Order**: Depth-first search (visual order) through the widget tree, collecting all active `FocusNode`s.
- **Navigation**: `Tab` moves forward, `Shift+Tab` moves backward.
- **State**: `FocusNode` maintains a `focused` boolean state. This state syncs with `InteractionState.focused` on the host widget to drive visual updates (e.g., focus rings).

### Click-to-Focus

`PointerInputNode` automatically requests focus for its host if a `FocusNode` is present when a press event occurs.

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

## Node Roles & Extensibility

The Node-based architecture allows for future expansion by adding specialized nodes without modifying the core `InteractionRegion`.

The Node-based architecture allows for future expansion by adding specialized nodes without modifying the core `InteractionRegion`.

| Node Type | Role & Responsibility | Notes |
| :--- | :--- | :--- |
| **`PointerInputNode`** (Core) | **Point Interaction.** Manages hover, click, and press states. Handles simple tap and mouse-over events. | Successor to `InteractionController`. Triggers "Click-to-Focus". |
| **`FocusNode`** (Core) | **Keyboard & Order.** Manages focus state, Tab traversal order, and key event reception/bubbling. | Primary subject of this task. Gateway for IME integration. |
| **`DraggableNode`** (Core) | **Movement (Source).** Handles drag start, delta updates, and end detection. Manages drag previews. | Distinct from `PointerInputNode`; handles movement (deltas). Includes long-press initiation logic. |
| **`DropTargetNode`** (Future) | **Acceptance (Target).** Determines whether dropped data is accepted and processes data on drop. | `InteractionRegion` hit-testing identifies this node as a drop candidate. |
| **`ScrollableNode`** (Future) | **Scrolling.** Handles mouse wheel, touchpad pan, and inertia calculations. | Collaborates with `ScrollViewport`. Consumes pointer events to produce scroll offsets. |
| **`SemanticsNode`** (Future) | **Meaning & A11y.** Provides labels, roles, and state for screen readers and bridges to OS accessibility APIs. | Decoupled from visuals/input. Collaborates with `FocusNode` to announce location. |
| **`ContextMenuNode`** (Future) | **Auxiliary Action.** Triggers context menus via right-click or long-press. | Abstracts platform-specific conventions (right-click vs long-press). |
