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

### Visibility

* **`visible(condition, transition=None)`**: Toggles a widget's *visibility* via paint and input.
* **`ignore_pointer(condition=True)`**: Blocks hit-testing for the wrapped subtree.

#### `visible()` is a Thin Composition

`visible()` is a lightweight convenience that composes two existing primitives:

* `opacity()` — drives the visual fade between hidden (`0.0`) and shown (`1.0`).
* `ignore_pointer()` — blocks hit-testing while the widget is logically hidden.

When `transition` is omitted, `visible(condition)` expands to literally
`opacity(condition_as_float) | ignore_pointer(not condition)`. With a
`transition` provided, an internal animation driver retargets an
`Animatable` on each condition change to drive `opacity` (and any
pattern-driven `scale` / `translate`) on enter / exit.

#### Semantics

* When `condition` is `True`, the child is fully opaque and receives input normally.
* When `condition` is `False`, the child is rendered fully transparent and
  ignores all input events (click, hover, focus, keyboard, tab traversal).
* The child **continues to occupy its normal layout space** in both states.
  `visible()` does not collapse layout to zero size.
* The child is **always eagerly mounted**; widget-local state is preserved
  across hide / show cycles.
* `condition` accepts a static `bool` or an `Observable[bool]` for reactive toggling.

#### Animated Visibility

Pass an optional `transition: TransitionDefinition` to animate enter and exit:

```python
widget.modifier(
    visible(
        self.vm.is_open,
        transition=TransitionDefinition(
            motion=LinearMotion(0.2),
            pattern=FadePattern() | ScalePattern(),
        ),
    )
)
```

The pattern's resolved `TransitionVisuals` (`opacity`, `scale_x` / `scale_y`,
`translate_x` / `translate_y`, `translate_x_fraction` / `translate_y_fraction`)
are applied during paint; **input is blocked from the moment `condition`
flips to `False`**, even while the exit animation is still playing.

#### `visible(False)` vs `opacity(0.0)` vs `ignore_pointer()`

| Behavior | `opacity(0.0)` | `ignore_pointer()` | `visible(False)` |
|----------|----------------|--------------------|------------------|
| Visually hidden | Yes | No | Yes |
| Receives input | Yes | No | No |
| Layout space | Reserved | Reserved | Reserved |

`visible()` is essentially the union of the other two columns: hidden *and*
non-interactive, while still occupying its layout slot. For animated
layout-size changes (e.g. collapsing a side sheet to zero width), use a
dedicated layout-aware Widget.

### Layout

Modifiers do not handle layout in `nuiitivet`.

Layout is controlled exclusively through layout Widgets and their parameters. This ensures that users can understand and define the layout simply by looking at the Widgets and their properties. Allowing Modifiers to handle layout would compromise this simplicity.
