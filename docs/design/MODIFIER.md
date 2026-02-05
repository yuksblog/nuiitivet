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

## Available Modifiers

### Visual Effects

* **`background(color)`**: Sets the background color.
* **`border(color, width)`**: Draws a border.
* **`shadow(color, blur, offset_x, offset_y)`**: Draws a drop shadow.
* **`corner_radius(radius)`**: Applies rounded corners (affects background and borders).
* **`clip()`**: Clips child elements if they overflow the boundaries.

### Layout

Modifiers do not handle layout in `nuiitivet`.

Layout is controlled exclusively through layout Widgets and their parameters. This ensures that users can understand and define the layout simply by looking at the Widgets and their properties. Allowing Modifiers to handle layout would compromise this simplicity.

### Interaction & Behavior

* **`clickable(on_click)`**: Processes click events.
* **`hoverable(on_hover_change)`**: Detects changes in hover state.
* **`scrollable(axis)`**: Adds scroll functionality.

## Implementation Details

### `ModifierElement` vs `Modifier`

* **`ModifierElement`**: The smallest unit of a Modifier with a single function (e.g., `BackgroundModifier`).
* **`Modifier`**: A list or chain of multiple `ModifierElement`s.

### `ModifierBox`

Many visual Modifiers (such as background, border, padding, etc.) are internally aggregated into a single Widget called `ModifierBox`. This optimization prevents the Widget tree from becoming needlessly deep when multiple Modifiers are applied, improving rendering performance.

`ModifierBox` is a subclass of `Widget` that holds the information from applied Modifiers and reflects them during the paint phase.
