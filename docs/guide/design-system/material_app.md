# Material App

`nv.App(nv.Window(content=...))` is the entry point for a Material Design application: the `Window` sets up the Material Overlay and Navigator, and the `App` supplies the Material Theme — all with sensible defaults so you can focus on building your UI.

## Basic Usage

```python
import nuiitivet.material as nv


class HomeScreen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Hello, Material Design!"),
                    nv.Button("Get Started", style=nv.ButtonStyle.filled()),
                ],
            ),
        )


nv.App(nv.Window(content=HomeScreen(), title="Material App")).run()
```

![Material App Basic Usage](../../assets/material_app_basic_usage.png)

## Window

Control the window size, position, and resize behavior:

```python
import nuiitivet.material as nv
from nuiitivet.runtime.window_sizing import WindowPosition

nv.App(
    nv.Window(
        content=HomeScreen(),
        width=1280,
        height=800,
        window_position=WindowPosition("center"),
        resizable=False,
    ),
).run()
```

See [Window](../window/index.md) for detailed usage.

## Window Chrome

By default `Window` uses OS-managed chrome (`OSChrome`), which draws the standard OS title bar. Set its text with the `title=` parameter:

```python
import nuiitivet.material as nv

nv.App(nv.Window(content=HomeScreen(), title="My App")).run()
```

### Custom Chrome

Replace the OS title bar with your own header widget via `chrome=CustomChrome(...)`. Nuiitivet wraps the header in a drag area so the window can still be moved by dragging it:

```python
import nuiitivet.material as nv

header = nv.Row(
    children=[nv.Text("My App")],
    cross_alignment="center",
    width="wt",
    height=40,
    padding=(12, 0),
).modifier(nv.background("#1a237e"))

nv.App(
    nv.Window(
        content=HomeScreen(),
        title="My App",
        chrome=nv.CustomChrome(header=header, corner_radius=8),
    ),
).run()
```

See [Window Chrome](../window/chrome.md) for detailed usage.

## Theme

Pass a `ThemeFactory` to change the seed color or switch to dark mode:

```python
import nuiitivet.material as nv

nv.App(nv.Window(content=HomeScreen()), theme=nv.ThemeFactory.dark("#00639B")).run()
```

See [Material Theme](material_theme.md) for detailed usage.

## Overlay Routes

Register custom overlay intents that can be dispatched from anywhere in the widget tree:

```python
import nuiitivet.material as nv

nv.App(
    nv.Window(
        content=HomeScreen(),
        overlay_routes={
            MyIntent: lambda intent: nv.BasicDialog(title=intent.title, message=intent.message),
        },
    ),
).run()
```

See [Material Overlay](material_overlay.md) for detailed usage.

---

[API Reference](../../api/material.md#nuiitivet.material.App)
