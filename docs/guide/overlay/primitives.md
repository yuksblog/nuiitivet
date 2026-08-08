# Overlay Primitives

The base `Overlay` exposes one primitive, `show()`, for displaying content above the widget tree. Instead of a scenario name, you pick the behaviour with three independent flags. See [Overview](index.md) for context.

## `show`

```python
import nuiitivet.material as nv

overlay = nv.Overlay.root()

handle = overlay.show(
    nv.Container(
        width=300, height=200,
        child=nv.Text("Modal content"),
    ),
    backdrop=True,
)

result = await handle   # OverlayResult[Any]
```

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `content` | `Widget \| Route` | required | Widget or route to display |
| `passthrough` | `bool` | `False` | Whether input reaches the content behind the overlay |
| `dismiss_on_outside_tap` | `bool` | `False` | Dismiss when a tap lands outside the content |
| `backdrop` | `bool` | `False` | Whether the design system paints a backdrop behind the content |
| `timeout` | `float \| None` | `None` | Auto-dismiss after seconds |
| `position` | `OverlayPosition \| None` | `None` (center) | Positioning strategy |
| `transition_spec` | `TransitionSpec \| None` | `None` | Entry/exit transition |

Two of these are about **input** and one is about **appearance**:

- `passthrough` decides whether the app behind the overlay stays usable — for pointer *and* keyboard.
- `dismiss_on_outside_tap` decides whether a tap outside the content closes the overlay. Any button dismisses, not just the primary one.
- `backdrop` only decides whether a dimming layer is painted. It never blocks input on its own; that is `passthrough`'s job. `backdrop=True, passthrough=True` (dimmed but clickable through) is legal.

### Common combinations

```python
# Dialog: blocks the app, dims it, closes on an outside tap
overlay.show(dialog, backdrop=True, dismiss_on_outside_tap=True)

# Toast: floats above the UI without blocking it, auto-dismisses
overlay.show(
    nv.Text("Operation complete"),
    passthrough=True,
    timeout=3.0,
    position=OverlayPosition.aligned("bottom-center", offset=(0, -24)),
)

# Menu: blocks the app without dimming it, closes on an outside tap
overlay.show(
    MenuWidget(),
    dismiss_on_outside_tap=True,
    position=OverlayPosition.aligned("top-left"),
)
```

`passthrough=True` together with an explicit `dismiss_on_outside_tap=True` raises `ValueError`: pointer dispatch resolves a single hit target, so a layer can pass a tap through or observe it, never both.

## OverlayHandle and OverlayResult

`show()` returns an `OverlayHandle`. You can close the overlay programmatically or await the result.

```python
handle = overlay.show(widget, backdrop=True)

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
| `OUTSIDE_TAP` | User tapped outside (`dismiss_on_outside_tap=True`) |
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

`anchored()` lines up `content_anchor` on the content with `target_anchor` on the anchor widget. The rect is resolved on every layout pass, so the content follows the anchor as it moves. This is what the [`popup` modifier](../modifiers/popup.md) builds for you.

### Relative to a point

A point has no extent, so there is no `target_anchor` to choose — `content_anchor` alone decides which corner of the content lands on the point.

```python
def on_press(event: nv.PointerEvent) -> None:
    nv.Overlay.root().show(
        indicator,
        passthrough=True,
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
