# Title Bar

The title bar is the top section of the window that typically contains the application title and window controls (minimize, maximize, close). Nuiitivet provides two ways to configure the title bar: `DefaultTitleBar` and `CustomTitleBar`.

You can set the title bar when initializing your application using the `title_bar` parameter in `App` or `MaterialApp`.

## DefaultTitleBar

`DefaultTitleBar` is the standard title bar provided by the OS or the framework. You can easily configure its basic properties such as the title string.

```python
from nuiitivet import App, DefaultTitleBar
from nuiitivet.widgets import Text

app = App(
    root=Text("Hello World"),
    title_bar=DefaultTitleBar(
        title="My Application"
    )
)
app.run()
```

## CustomTitleBar

If you need a fully customized title bar that matches your application's design, you can use `CustomTitleBar`. This allows you to place any widget inside the title bar area, giving you complete control over its appearance and layout.

When using `CustomTitleBar`, Nuiitivet automatically handles the window dragging behavior for the area occupied by your custom widget.

```python
from nuiitivet import App, CustomTitleBar
from nuiitivet.widgets import Text, Row, Container
from nuiitivet.rendering import Color

# Create a custom widget for the title bar
my_title_bar_widget = Container(
    child=Row(
        children=[
            Text("Custom Title", color=Color.WHITE),
            # Add custom buttons or other widgets here
        ],
        cross_axis_alignment="center"
    ),
    background_color=Color.BLUE,
    height=40,
    padding=(10, 0)
)

app = App(
    root=Text("Main Content"),
    title_bar=CustomTitleBar(
        content=my_title_bar_widget,
        title="App Title for OS Taskbar" # Used by the OS, not rendered in the window
    )
)
app.run()
```
