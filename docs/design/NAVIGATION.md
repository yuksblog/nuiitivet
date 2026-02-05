# Navigation System Design

## 1. Core Architectural Structure

### 1.1 Relationship Between Overlay and Navigator

#### Policy: Physical Separation + Shared Internal Implementation

The user-facing API should be intuitive and reflect the physical structure, while internal route/stack management is shared.

- `Navigator.push()` to "transition screens"
- `Overlay.show()` to "display on the topmost layer"

Internally, the `Navigator` acts as a stack managing `PageRoute` objects, while the `Overlay` maintains an internal `_modal_navigator` that treats Dialogs and Snackbars as routes.

```text
┌─────────────────────────────────────┐
│ App                                  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ Overlay (Physical Layer)       │  │ ← Always on top
│  │  Internal: _modal_navigator   │  │
│  │    ├─ DialogRoute             │  │
│  │    └─ SnackbarRoute           │  │
│  └───────────────────────────────┘  │
│                                      │
│  ┌───────────────────────────────┐  │
│  │ Content                       │  │
│  │  ┌──────────────────┐         │  │
│  │  │ Navigator (Part) │         │  │ ← Placed by user
│  │  │  ├─ PageRoute    │         │  │
│  │  │  └─ PageRoute    │         │  │
│  │  └──────────────────┘         │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 1.2 Root Navigator Design

Fullscreen transitions are a common pattern, making a root Navigator essentially mandatory. `App` provides a root Navigator by default along with a global access API.

```python
# Global access (concise, recommended)
Navigator.root().push(...)

# Context-based (for future extensibility, detailed control)
Navigator.of(context).push(...)              # Nearest Navigator
Navigator.of(context, root=True).push(...)   # Root Navigator
```

### 1.3 Context Lookup Pattern

To support independent Navigators (transition histories) per tab, we implement `Navigator.of(context)`.

- Implementation simply traverses up the parent chain.
- The root Navigator can be retrieved in O(1) via `Navigator.root()`, ensuring common cases are concise and fast.

```python
class Widget:
    def find_ancestor(self, widget_type: type["T"]) -> "T | None":
        """Find the nearest ancestor of the specified type."""
        current = self._parent
        while current is not None:
            if isinstance(current, widget_type):
                return current
            current = current._parent
        return None


class Navigator(Widget):
    _root_navigator: "Navigator | None" = None

    @classmethod
    def root(cls) -> "Navigator":
        """Get the root navigator."""
        if cls._root_navigator is None:
            raise RuntimeError("No root navigator found.")
        return cls._root_navigator

    @classmethod
    def of(cls, context: Widget, root: bool = False) -> "Navigator":
        """Find the nearest Navigator in the widget tree."""
        if root:
            return cls.root()

        navigator = context.find_ancestor(Navigator)
        if navigator is None:
            raise RuntimeError(
                "No Navigator found in the widget tree above "
                f"{context.__class__.__name__}. "
                "Did you forget to wrap your widget in a Navigator?"
            )
        return navigator
```

### 1.4 Interface for ViewModels (Protocol)

To ensure ViewModels do not depend on the implementation details of `Navigator`, we provide `INavigator`.

```python
from __future__ import annotations

from typing import Any, Protocol


class INavigator(Protocol):
    def push(self, content: Any) -> None:
        ...

    def pop(self, result: Any | None = None) -> None:
        ...
```

## 2. Intent System Design (Navigation Perspective)

### 2.0 What is the Intent System?

The Intent System is a mechanism for declaring screen transitions not just by passing Widgets/Routes directly, but as data representing an "intent," which the framework resolves to a Route for execution.

```python
# Caller side (Intent)
Navigator.root().push(ProductDetailIntent(product_id=123))

# Framework side (Resolution)
# - Look up the factory from routes using type(intent) as the key
# - Generate a Route using factory(intent)
```

### 2.1 Intent Type System

Intents are defined as arbitrary dataclasses, requiring no base class or Protocol.

```python
from dataclasses import dataclass


@dataclass
class HomeIntent:
    pass


@dataclass
class ProductDetailIntent:
    product_id: int
```

### 2.2 Route Mapping (routes)

`routes` is treated as a dictionary that maps `Intent instance -> Route`.

```python
routes: dict[type, callable[[object], "Route"]] = {
    HomeIntent: lambda intent: PageRoute(builder=lambda: HomeScreen()),
    ProductDetailIntent: lambda intent: PageRoute(
        builder=lambda: ProductDetailScreen(intent.product_id)
    ),
}

Navigator.root().push(ProductDetailIntent(product_id=123))
```

### 2.3 `push` Overload Design

`Navigator.push()` accepts the following three patterns:

- Widget
- Route
- Intent

```python
# Pattern 1: Widget
Navigator.root().push(SettingsScreen())

# Pattern 2: Route
Navigator.root().push(PageRoute(builder=lambda: SettingsScreen()))

# Pattern 3: Intent
Navigator.root().push(SettingsIntent())
```

### 2.4 Handling Missing Intents

If an unregistered Intent is used, a `RuntimeError` is thrown to catch configuration errors early.

```python
Navigator.root().push(UnknownIntent())
# → RuntimeError: Intent 'UnknownIntent' not found in routes
```

### 2.5 `App.navigation(...)` Initialization Pattern

To enable ViewModels to request screen transitions based on Intents without depending on View (Widget) details, `App.navigation(...)` is provided as an alternative initialization pattern.

```python
# App with navigation
App.navigation(
    routes={
        HomeIntent: lambda intent: PageRoute(builder=...),
        DetailIntent: lambda intent: PageRoute(builder=...),
        SettingsIntent: lambda intent: PageRoute(builder=...),
    },
    initial_route=HomeIntent(),
    title="My App",
)
```

## 3. Back Button Handling

### 3.1 Event Propagation Priority

The default behavior for events equivalent to `Esc` / `Back` is processed in the following order:

1. Close the topmost Overlay entry.
2. `pop()` the topmost Navigator.
3. Do nothing if at the root route.

```python
class App:
    def on_key_pressed(self, event):
        if event.key == "ESCAPE":
            if self._overlay.has_entries():
                self._overlay.close()
                return True

            if self._root_navigator and self._root_navigator.can_pop():
                self._root_navigator.pop()
                return True

            return False
```

### 3.2 Handling Rapid Back Button Presses (Multiple Inputs)

In cases where `Esc` / `Back` are input in rapid succession (key repeat, hammering, multiple OS-level events), the implementation must safely handle "back requests."

#### Policy

- `App.handle_back_event()` processes exactly one request per input.
- If the Overlay is empty, it calls `Navigator.request_back()`.
- `Navigator.request_back()` acts as the user input API, absorbing re-entrancy during transitions.

#### Navigator Strategy

- If a back occurs during a **Pop** animation: add the request to a queue (`pending_pop_requests`) and immediately complete the current pop transition.
- When consuming the queue: skip animations for intermediate pops and treat only the final pop with normal behavior.
- If a back occurs during a **Push** animation: immediately complete the push and then perform a single pop.
- If `handle_back_event()` (equivalent to will-pop) returns a cancellation, discard the queue and stop further pops.

### 3.3 `will_pop()` Modifier

Custom handling, such as confirmation before a back transition, is implemented as a Modifier.

```python
from nuiitivet.modifiers import will_pop

EditScreen().modifier(will_pop(on_will_pop=self._on_will_pop))


async def _on_will_pop(self) -> bool:
    """Return True to continue pop, False to cancel."""
    if self.has_unsaved_changes.value:
        confirmed = await Overlay.root().dialog(
            AlertDialog(
                title=Text("Confirmation"),
                content=Text("Go back without saving?"),
                actions=[
                    TextButton("Cancel", on_pressed=lambda: False),
                    TextButton("Back", on_pressed=lambda: True),
                ],
            )
        )
        return confirmed
    return True
```

### 3.4 Integration with Navigator

Check the `will_pop` chain immediately before `Navigator.pop()` to allow for cancellation.

```python
class Navigator(Widget):
    async def pop(self, result=None):
        if not self.can_pop():
            return

        route = self._routes[-1]
        widget = route.widget

        if hasattr(widget, "_modifier_element"):
            element = widget._modifier_element
            should_pop = await self._check_will_pop(element)
            if not should_pop:
                return

        self._routes.pop()
        route.dispose()
        self.mark_needs_layout()

    async def _check_will_pop(self, element) -> bool:
        if hasattr(element, "handle_back_event"):
            return await element.handle_back_event()
        return True
```
