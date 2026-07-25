# Window Operations

Nuiitivet provides APIs to perform basic window operations programmatically. These operations allow you to control the window state from within your application logic using the Intent system.

You can dispatch these intents using `App.of(context).dispatch(intent)`.

## Available Intents

The following intents are available in `nuiitivet.runtime.intents` for window management:

- **`CloseWindowIntent`**: Closes the application window.
- **`MaximizeWindowIntent`**: Maximizes the window to fill the screen.
- **`MinimizeWindowIntent`**: Minimizes the window to the taskbar or dock.
- **`RestoreWindowIntent`**: Restores the window from a minimized or maximized state.
- **`FullScreenIntent`**: Puts the window into fullscreen mode.
- **`CenterWindowIntent`**: Centers the window on the current screen.
- **`MoveWindowIntent(x, y)`**: Moves the window to the specified coordinates.
- **`ResizeWindowIntent(width, height)`**: Resizes the window to the specified dimensions.
- **`ExitAppIntent(exit_code)`**: Exits the entire application with the given exit code.

## Example Usage

Here is an example of how to use these intents with buttons to control the window:

```python
import nuiitivet.material as nv
from nuiitivet.runtime.intents import CenterWindowIntent, CloseWindowIntent, MaximizeWindowIntent, MinimizeWindowIntent, RestoreWindowIntent

def build_window_controls():
    return nv.Column(
        children=[
            nv.Text("Window Controls"),
            nv.Button(
                child=nv.Text("Maximize"),
                on_click=lambda ctx: nv.App.of(ctx).dispatch(MaximizeWindowIntent())
            ),
            nv.Button(
                child=nv.Text("Minimize"),
                on_click=lambda ctx: nv.App.of(ctx).dispatch(nv.MinimizeWindowIntent())
            ),
            nv.Button(
                child=nv.Text("Restore"),
                on_click=lambda ctx: nv.App.of(ctx).dispatch(RestoreWindowIntent())
            ),
            nv.Button(
                child=nv.Text("Center"),
                on_click=lambda ctx: nv.App.of(ctx).dispatch(CenterWindowIntent())
            ),
            nv.Button(
                child=nv.Text("Close"),
                on_click=lambda ctx: nv.App.of(ctx).dispatch(nv.CloseWindowIntent())
            ),
        ],
        spacing=10,
        padding=20
    )

app = nv.App(
    root=build_window_controls(),
    width=400,
    height=400
)
app.run()
```
