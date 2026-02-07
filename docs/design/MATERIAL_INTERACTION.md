# Material Design Interaction & State Layers

This document outlines the implementation standards for Material Design 3 interactive components in this framework.

## 1. Inheritance Strategy

All interactive Material widgets (Button, Checkbox, Radio, Switch, etc.) **must** inherit from `InteractiveWidget`.

```python
from nuiitivet.material.interactive_widget import InteractiveWidget

class MyMaterialWidget(InteractiveWidget):
    """
    Inheriting from InteractiveWidget automatically provides:
    - InteractionHostMixin (Pointer/Focus handling)
    - State Layer drawing logic
    - Focus Ring management
    - Standard Keyboard bindings (Space/Enter -> Click)
    """
    ...
```

## 2. Interaction Logic

### Key Concepts

`InteractiveWidget` centralizes the logic for "Visual State" vs "Logical State" to satisfy Material Design 3 specifications.

1. **Logical Focus (`state.focused`)**:
    * Indicates the widget is the current input target.
    * `True` whether clicked by mouse or navigated by keyboard.
    * **Always** used for input routing (e.g. Space key).

2. **Visual Focus Ring (`should_show_focus_ring`)**:
    * Indicates the widget should display the visual focus indicator (Ring).
    * `True` **only** when focused via Keyboard (Tab) or Programmatic means.
    * `False` when focused via Pointer (Click), preventing "sticky focus" visuals.

### State Layer Hierarchy

Visual overlays (State Layers) are resolved with the following priority in `_get_active_state_layer_opacity`:

1. **Drag** (`state.dragging`): Highest priority.
2. **Press** (`state.pressed`): While pointer is held down.
3. **Hover** (`state.hovered`): While pointer is within bounds.
4. **Key Focus**: (Note: Modern MD3 style often disables the colored State Layer for Focus, preferring just the Ring. Our implementation follows this by default).

## 3. Implementation Guide

### Drawing the State Layer

In your `paint` method, you generally delegate the state rendering to `InteractiveWidget`.

```python
def paint(self, canvas, x, y, w, h):
    # 1. Draw your widget background/content
    draw_background(...)

    # 2. Draw standard State Layer (Hover/Press)
    # This automatically checks state priorities and opacity constants.
    self.draw_state_layer(canvas, x, y, w, h)

    # 3. Draw Focus Ring
    # This only draws if should_show_focus_ring is True.
    # Note: paint_outsets() should also be overridden if the ring extends outside.
    if self.should_show_focus_ring:
        self.draw_focus_indicator(canvas, x, y, w, h)
```

### Handling Opacity

Do not manually calculate opacities in your widget unless you have custom requirements. Use `_get_active_state_layer_opacity()` which respects the priority rules.

```python
# GOOD: Reusing standardized logic
opacity = self._get_active_state_layer_opacity()

# BAD: Reimplementing logic locally
if self.state.pressed:
    opacity = 0.12
elif self.state.hovered: ...
```

## 4. Default Constants (MD3)

`InteractiveWidget` defines standard opacities:

* `_HOVER_OPACITY`: 0.08
* `_FOCUS_OPACITY`: 0.12
* `_PRESS_OPACITY`: 0.12
* `_DRAG_OPACITY`: 0.16

These can be overridden per-instance if necessary, but consistent use is recommended.
