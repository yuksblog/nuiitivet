---
layout: default
---

# InteractionRegion / InteractionState (Advanced)

> ⚠️ This document targets advanced users who need to integrate deeply with the interaction system. Regular Modifier chaining (`hoverable()`, `clickable()`) already covers the common cases without exposing these types.

## Overview

`nuiitivet.widgets.interaction.InteractionRegion` is the thin wrapper that powers pointer-related Modifiers. Whenever you chain `hoverable()` or `clickable()` the modifier ensures that the target Widget is wrapped in a single InteractionRegion instance. Multiple pointer modifiers automatically reuse the same wrapper, so order does not matter.

```text
┌──────────────┐   hoverable()   clickable()
│   Widget     │ ─────────────▶ InteractionRegion (shared)
└──────────────┘
```

The region hosts an `InteractionState` object that records the live pointer flags:

| Field | Meaning |
| --- | --- |
| `hovered` | Pointer is inside the region (or captured and still over the rect). |
| `pressed` | Active press sequence is in progress. |
| `focused` | Widget is focused (set by App-level focus handling). See `docs/design/tasks/FOCUS_AND_KEYBOARD.md`. |
| `disabled` | Modifier or widget marked the interaction as disabled. |
| `dragging` / `scrolling` | Reserved for drag/scroll modifiers. |
| `selected`, `checked`, `toggled_on` | Convenience flags for composite controls. |
| `pointer_position` | Latest pointer coordinate while hovering. |
| `press_position` | Coordinate of the press that started the current gesture. |

The same state object is injected into the wrapped child, so advanced widgets can read or mutate it directly if needed (e.g., a custom control syncing `state.disabled` with its own model).

## Programmatic Access

```python
from nuiitivet.widgets.interaction import InteractionRegion, InteractionState

state = InteractionState(disabled=False)
region = InteractionRegion(custom_child, state=state)
region.enable_hover()
region.enable_click(on_click=lambda: print("clicked"))
```

### InteractionController

InteractionRegion internally uses `InteractionController` to translate pointer events into `InteractionState` updates. You usually do not need to touch it, but advanced widgets (such as `BaseButton`) can embed the controller directly to keep their concrete class (and public API) intact:

```python
from nuiitivet.widgets.interaction import InteractionController, InteractionState

class FancyControl(Widget):
    def __init__(self):
        super().__init__()
        self.interaction_state = InteractionState()
        self._interaction = InteractionController(self, self.interaction_state)
        self._interaction.enable_hover()
        self._interaction.enable_click(on_click=self._on_activate)

    def on_pointer_event(self, event: PointerEvent) -> bool:
        return self._interaction.handle_pointer_event(event, getattr(self, "_last_rect", None))
```

Using the controller directly keeps the widget class (and its attributes) visible to the outside world, while still benefiting from the shared pointer logic.

## Practical Guidelines

1. **Do not expose InteractionRegion in beginner-facing docs or APIs.** End users should only see `Modifier.hoverable()` / `Modifier.clickable()`.
2. **Limit manual usage to custom containers** that need to intercept pointer events before decoration or layout occurs.
3. **State-first design.** Widgets should read `interaction_state` when computing overlays, focus rings, etc., so modifiers and direct integrations stay in sync.
4. **Release-triggered clicks.** The controller follows standard UI semantics: press captures the pointer, release inside the rect fires the click. Make sure your tests reflect this order.
5. **No shim layers.** If you need bespoke behavior (e.g., drag handles), implement a dedicated modifier or controller hook instead of stacking ad-hoc event handlers.
