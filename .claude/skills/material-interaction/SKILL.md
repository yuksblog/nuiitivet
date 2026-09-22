---
name: material-interaction
description: Implement or verify an interactive Material Design 3 widget on InteractiveWidget: focus ring, state layer, key handling.
---

# Material Interaction

Rules for implementing or verifying an interactive Material Design 3 widget.

## Inheritance

**Every interactive Material widget inherits from `InteractiveWidget`.**

```python
from nuiitivet.material.interactive_widget import InteractiveWidget

class MyWidget(InteractiveWidget):
    ...
```

It gives the widget:

- `Space`/`Enter` key handling
- the focus ring, hidden when focus came from the pointer
- state layer priority: Drag > Press > Hover

## Focus vs Focus Ring

- Logical focus, `self.state.focused`: input handling.
- Visual focus, `self.should_show_focus_ring`: drawing the ring.
- Do not draw the ring from `state.focused` alone, and do not check
  `focus_from_pointer` by hand; `should_show_focus_ring` already does.

## State Layer

- Do not write `if hovered: ... elif pressed: ...`.
- Use `self._get_active_state_layer_opacity()` or `self.draw_state_layer()`:
  they hold the Drag > Press > Hover priority and the opacity values (0.08,
  0.12, ...).

## Checklist

- [ ] Inherits `InteractiveWidget`
- [ ] `paint()` calls `self.draw_state_layer()`
- [ ] `paint()` calls `self.draw_focus_indicator()`, guarded by `should_show_focus_ring`
- [ ] No manual `on_click` handling; `InteractiveWidget`/`Clickable` handle it via `PointerInputNode`
- [ ] No manual Space/Enter handlers; `InteractiveWidget` handles them
