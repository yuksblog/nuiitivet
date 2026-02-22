# Window Size and Position

You can control how the window is sized and where it appears on the screen using `WindowSizing` and `WindowPosition`. These are configured when initializing your `App` or `MaterialApp`.

## WindowSizing

`WindowSizing` determines how the window calculates its dimensions. You can specify the `width` and `height` parameters of your application using `WindowSizing` objects, integers (which are treated as fixed sizes), or the string `"auto"`.

- **`fixed`**: The window has a fixed size specified by width and height.
- **`auto`**: The window automatically resizes itself to fit its content.

### Fixed Size Example

```python
from nuiitivet import App, WindowSizing
from nuiitivet.widgets import Text

app = App(
    root=Text("Fixed Size Window"),
    width=WindowSizing.fixed(800), # Or simply width=800
    height=WindowSizing.fixed(600) # Or simply height=600
)
app.run()
```

### Auto Size Example

When using `"auto"`, the window will calculate its size based on the preferred size of its root widget.

```python
from nuiitivet import App, WindowSizing
from nuiitivet.widgets import Text, Container

app = App(
    root=Container(
        child=Text("Auto Sized Window"),
        padding=50
    ),
    width=WindowSizing.auto(), # Or simply width="auto"
    height=WindowSizing.auto() # Or simply height="auto"
)
app.run()
```

## WindowPosition

`WindowPosition` allows you to specify the exact location of the window on the screen. You can pass a `WindowPosition` object to the `window_position` parameter of your application.

- **Alignment**: You can align the window to specific parts of the screen (e.g., center, top-left, bottom-right).
- **Offset**: You can apply an X and Y offset from the chosen alignment.
- **Screen Index**: In multi-monitor setups, you can specify which screen the window should appear on.

### Positioning Example

```python
from nuiitivet import App, WindowPosition
from nuiitivet.widgets import Text

app = App(
    root=Text("Positioned Window"),
    width=400,
    height=300,
    window_position=WindowPosition.alignment(
        alignment="top-right",
        offset=(-20, 20), # 20 pixels left, 20 pixels down from top-right corner
        screen_index=0    # Primary monitor
    )
)
app.run()
```
