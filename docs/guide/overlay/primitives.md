# Overlay Primitives

The base `Overlay` exposes three primitives for displaying content above the widget tree. Each primitive determines how user input is handled while the overlay is visible. See [Overview](index.md) for context.

## `show_modal`

Displays content with a blocking modal barrier. Background interaction is disabled — all pointer events are captured by the overlay layer.

Use `show_modal` for actions that require user attention before the application can continue: confirmation dialogs, error alerts, bottom sheets.

```python
import nuiitivet.material as nv

overlay = nv.Overlay.root()

handle = overlay.show_modal(
    nv.Container(
        width=300, height=200,
        child=nv.Text("Modal content"),
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
import nuiitivet.material as nv
from nuiitivet.overlay import OverlayPosition

overlay = nv.Overlay.root()

handle = overlay.show_modeless(
    nv.Text("Operation complete"),
    timeout=3.0,
    position=OverlayPosition.aligned("bottom-center", offset=(0, -24)),
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
import nuiitivet.material as nv
from nuiitivet.overlay import OverlayPosition

overlay = nv.Overlay.root()

handle = overlay.show_light_dismiss(
    MenuWidget(),
    position=OverlayPosition.aligned("top-left"),
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

`OverlayPosition` is the single type describing where overlay content goes. Build one with a named constructor — never by calling the class directly — and pass it as `position=` to any show API.

| Constructor | Places content relative to |
| --- | --- |
| `OverlayPosition.aligned(alignment, *, offset)` | the overlay root (the whole window) |
| `OverlayPosition.anchored(rect_provider, target_anchor, content_anchor, offset)` | a widget's screen rect |
| `OverlayPosition.at_point(x, y, *, content_anchor, offset)` | a screen point |
| `OverlayPosition.at_pointer(event, *, content_anchor, offset)` | a `PointerEvent`'s screen point |

### Relative to the overlay root

`aligned()` takes one of the nine-point placements: `top-left`, `top-center`, `top-right`, `center-left`, `center`, `center-right`, `bottom-left`, `bottom-center`, `bottom-right`.

```python
# Bottom center with 24 px upward offset
position = OverlayPosition.aligned("bottom-center", offset=(0, -24))
```

### Relative to a widget

`anchored()` lines up `content_anchor` on the content with `target_anchor` on the anchor widget. The rect is resolved on every layout pass, so the content follows the anchor as it moves. This is what the [`modeless` / `light_dismiss` modifiers](../modifiers/popup.md) build for you.

### Relative to a point

A point has no extent, so there is no `target_anchor` to choose — `content_anchor` alone decides which corner of the content lands on the point.

```python
def on_press(event: nv.PointerEvent) -> None:
    nv.Overlay.root().show_modeless(
        indicator,
        position=nv.OverlayPosition.at_pointer(
            event,
            content_anchor="bottom-center",
            offset=(0, -8),
        ),
    )

image.modifier(nv.pointer_input(on_press=on_press))
```

Prefer `at_pointer(event)` over `at_point(event.x, event.y)`: a `PointerEvent` carries both screen (`x`/`y`) and widget-relative (`local_x`/`local_y`) coordinates, and only the screen pair is meaningful to an overlay. Passing the event lets the constructor pick the right one.

For the common "right-click → menu at the cursor" case, reach for the [`context_menu` modifier](../modifiers/popup.md#context_menu) instead — it owns the click coordinate and the open state for you.

### Staying on screen

Anchored and point positions keep their content inside the viewport, so a menu opened near the right or bottom edge is pulled back into view rather than clipped. Pass `clamp=False` to opt out.

## OverlayAware

Widgets that need to close themselves can implement `OverlayAware[T]`. When displayed through any `Overlay` show API, the framework automatically injects the handle into the widget before mounting:

```python
import nuiitivet.material as nv

class MyDialog(nv.ComposableWidget, nv.OverlayAware[str]):
    def on_confirm(self) -> None:
        self.overlay_handle.close("confirmed")

    def build(self) -> nv.Widget:
        ...
```
