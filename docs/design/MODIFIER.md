# Modifier System Design

## Overview

A **Modifier** is a mechanism for wrapping an existing Widget to add capabilities or visual effects. It aims to compose functionality declaratively and flatly, avoiding the downsides of deep Widget nesting or complex inheritance hierarchies.

## Core Concepts

### 1. Modifier as a Wrapper

Essentially, a Modifier is a "function that takes a Widget and returns a new Widget." When a Modifier is applied, it wraps the original Widget in a wrapper Widget, such as a `ModifierBox`, which then handles the added functionality or rendering.

### 2. The `modifier()` Method

Every Widget has a `modifier()` method used to apply Modifiers. Previously named `apply()`, it was renamed to `modifier()` to be more declarative and noun-like.

```python
# Basic usage
widget.modifier(background("red"))
```

### 3. Chaining

Modifiers can be chained using the `|` operator. Chained Modifiers are applied in order from left to right.

```python
# Chaining example
widget.modifier(
    background("white") | border("black", 2) | padding(10)
)
```

### 4. Immutability

Both Widgets and Modifiers are treated as immutable. The `modifier()` method does not modify the original Widget; it returns a new Widget instance (the wrapper).

## Implementation Details

### `ModifierElement` and `Modifier`

* **`ModifierElement`**: The smallest unit of a Modifier with a single function (e.g., `BackgroundModifier`).
* **`Modifier`**: A list or chain of multiple `ModifierElement`s.

### Visual Effects

* **`background(color)`**: Sets the background color.
* **`border(color, width)`**: Draws a border.
* **`shadow(color, blur, offset_x, offset_y)`**: Draws a drop shadow.
* **`corner_radius(radius)`**: Applies rounded corners (affects background and borders).
* **`clip()`**: Clips child elements if they overflow the boundaries.

Many visual Modifiers (such as background, border, padding, etc.) are internally aggregated into a single Widget called `ModifierBox`. This optimization prevents the Widget tree from becoming needlessly deep when multiple Modifiers are applied, improving rendering performance.

`ModifierBox` is a subclass of `Widget` that holds the information from applied Modifiers and reflects them during the paint phase.

### Interaction & Behavior

* **`clickable(on_click)`**: Processes click events.
* **`hoverable(on_hover_change)`**: Detects changes in hover state.
* **`focusable()`**: Makes a widget focusable.
* **`scrollable(axis)`**: Adds scroll functionality.

Similar to `ModifierBox`, interaction-related Modifiers are aggregated into an `InteractionRegion` wrapper. This widget hosts specialized **Interaction Nodes** (such as `PointerInputNode` or `FocusNode`) that manage input logic and shared interaction states.

For details on the node-based interaction system, see [INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md).

### Scrolling

* **`scrollable(axis, show_scrollbar)`**: Adds scroll functionality to a widget.
* **Mechanism**: Internally wraps the target widget with a `Scroller` widget.
* **Integration**: The `Scroller` manages viewport clipping, scroll offsets, and optional scrollbar rendering based on the specified axis (`x` or `y`).

### WillPop

* **`will_pop(on_will_pop)`**: Intercepts and potentially cancels a back-navigation (pop) request.
* **Callback**: `on_will_pop` is an `async` function that returns `True` (allow pop) or `False` (cancel pop).
* **Usage**: Commonly used to show an `AlertDialog` for confirming unsaved changes before leaving a screen. For more details on navigation flow, see [NAVIGATION.md](NAVIGATION.md).

### Layout

Modifiers do not handle layout in `nuiitivet`.

Layout is controlled exclusively through layout Widgets and their parameters. This ensures that users can understand and define the layout simply by looking at the Widgets and their properties. Allowing Modifiers to handle layout would compromise this simplicity.
