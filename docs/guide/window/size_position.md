# Window Size and Position

You can control how the window is sized and where it appears on the screen when constructing your `Window`.

## WindowSizing

The `width` and `height` parameters accept an integer (a fixed size in pixels) or the string `"auto"`.

- **fixed**: The window has a fixed size specified by width and height.
- **`"auto"`**: The window automatically resizes itself to fit its content.

Both are shorthands for `nv.WindowSizing` values — `nv.WindowSizing.fixed(800)` and `nv.WindowSizing.auto()` — which you only need when annotating a type or holding the value in a variable.

### Fixed Size Example

```python
import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Fixed Size Window")


app = nv.App(
    nv.Window(
        content=build_root,
        width=800,
        height=600,
    ),
)
app.run()
```

### Auto Size Example

When using `"auto"`, the window will calculate its size based on the preferred size of its root widget.

```python
import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Container(
        child=nv.Text("Auto Sized Window"),
        padding=50,
    )


app = nv.App(
    nv.Window(
        content=build_root,
        width="auto",
        height="auto",
    ),
)
app.run()
```

## WindowPosition

The `window_position` parameter accepts a nine-point alignment string: `"center"`, `"top-left"`, `"bottom-right"`, and so on.

```python
import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Positioned Window")


app = nv.App(
    nv.Window(
        content=build_root,
        width=400,
        height=300,
        window_position="center",
    ),
)
app.run()
```

### Offsets and multiple monitors

An offset from the alignment point, or a specific screen in a multi-monitor setup, needs the explicit `nv.WindowPosition` form:

```python
import nuiitivet.material as nv


def build_root() -> nv.Widget:
    return nv.Text("Positioned Window")


app = nv.App(
    nv.Window(
        content=build_root,
        width=400,
        height=300,
        window_position=nv.WindowPosition.alignment(
            alignment="top-right",
            offset=(-20, 20),  # 20 pixels left, 20 pixels down from top-right corner
            screen_index=0,    # Primary monitor
        ),
    ),
)
app.run()
```
