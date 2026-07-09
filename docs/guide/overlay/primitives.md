# Overlay Primitives

The base `Overlay` exposes three primitives for displaying content above the widget tree. Each primitive determines how user input is handled while the overlay is visible. See [Overview](index.md) for context.

## `show_modal`

Displays content with a blocking modal barrier. Background interaction is disabled — all pointer events are captured by the overlay layer.

Use `show_modal` for actions that require user attention before the application can continue: confirmation dialogs, error alerts, bottom sheets.

```python
from nuiitivet.overlay import Overlay, OverlayPosition
from nuiitivet.layout.container import Container
from nuiitivet.material.text import Text

overlay = Overlay.root()

handle = overlay.show_modal(
    Container(
        width=300, height=200,
        child=Text("Modal content"),
    ),
)

result = await handle   # OverlayResult[Any]
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `content` | `Widget \| Route` | required | Widget or route to display |
| `dismiss_on_outside_tap` | `bool` | `False` | Dismiss when tapping the barrier |
| `barrier_color` | `tuple[int, int, int, int]` | `(0, 0, 0, 128)` | RGBA barrier color |
| `timeout` | `float \| None` | `None` | Auto-dismiss after seconds |
| `position` | `OverlayPosition \| None` | `None` (center) | Positioning strategy |
| `transition_spec` | `TransitionSpec \| None` | `None` | Entry/exit transition |

## `show_modeless`

Displays content above the widget tree without blocking background interaction. Pointer events pass through to the layers below.

Use `show_modeless` for informational overlays that do not require user action: toasts, progress indicators, snackbar messages.

```python
from nuiitivet.overlay import Overlay, OverlayPosition
from nuiitivet.material.text import Text

overlay = Overlay.root()

handle = overlay.show_modeless(
    Text("Operation complete"),
    timeout=3.0,
    position=OverlayPosition.alignment("bottom-center", offset=(0, -24)),
)
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `content` | `Widget \| Route` | required | Widget or route to display |
| `timeout` | `float \| None` | `None` | Auto-dismiss after seconds |
| `position` | `OverlayPosition \| None` | `None` (center) | Positioning strategy |
| `transition_spec` | `TransitionSpec \| None` | `None` | Entry/exit transition |

## `show_light_dismiss`

Displays content with an invisible full-screen hit layer. Tapping outside the content closes the overlay and consumes the outside tap. Background interaction is blocked while the overlay is visible.

Use `show_light_dismiss` for menus and dropdowns that should close when the user clicks away.

```python
from nuiitivet.overlay import Overlay, OverlayPosition

overlay = Overlay.root()

handle = overlay.show_light_dismiss(
    MenuWidget(),
    position=OverlayPosition.alignment("top-left"),
)
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `content` | `Widget \| Route` | required | Widget or route to display |
| `timeout` | `float \| None` | `None` | Auto-dismiss after seconds |
| `position` | `OverlayPosition \| None` | `None` (center) | Positioning strategy |
| `transition_spec` | `TransitionSpec \| None` | `None` | Entry/exit transition |

## OverlayHandle and OverlayResult

All three primitives return an `OverlayHandle`. You can close the overlay programmatically or await the result.

```python
handle = overlay.show_modal(widget)

# Close programmatically
handle.close("confirmed")

# Await the result
result = await handle   # OverlayResult[Any]
print(result.value)     # "confirmed"
print(result.reason)    # OverlayDismissReason.CLOSED
```

`OverlayResult` carries the value passed to `close()` and a `reason` indicating how the overlay was dismissed:

| Reason | Trigger |
| ------ | ------- |
| `CLOSED` | `handle.close(value)` called explicitly |
| `OUTSIDE_TAP` | User tapped outside (`dismiss_on_outside_tap=True` or `show_light_dismiss`) |
| `TIMEOUT` | `timeout` elapsed |
| `DISPOSED` | Entry removed without explicit close |

## OverlayPosition

`OverlayPosition.alignment(alignment, *, offset=(0, 0))` specifies where the content appears within the overlay root. Supported alignment values:

`top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right`

```python
# Bottom center with 24 px upward offset
position = OverlayPosition.alignment("bottom-center", offset=(0, -24))
```

## OverlayAware

Widgets that need to close themselves can implement `OverlayAware[T]`. When displayed through any `Overlay` show API, the framework automatically injects the handle into the widget before mounting:

```python
from nuiitivet.overlay import OverlayAware
from nuiitivet.widgeting.widget import ComposableWidget, Widget

class MyDialog(ComposableWidget, OverlayAware[str]):
    def on_confirm(self) -> None:
        self.overlay_handle.close("confirmed")

    def build(self) -> Widget:
        ...
```
