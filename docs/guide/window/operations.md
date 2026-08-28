# Window Operations

Window operations address exactly one window, so they live on the
`Window` object — as imperative methods, and as **window-scoped intents**
dispatched through `Window.of(context)`. Exiting the whole application is
app-scoped and dispatches through `App.of(context)` instead. See
[Multiple Windows](multi_window.md) for the App / Window split.

## Imperative methods

For app logic that already holds a window (its own via `Window.of(self)`,
or one it opened):

```python
window = nv.Window.of(self)
window.maximize()
window.minimize()
window.restore()      # exit full screen / restore size / bring back
window.full_screen()  # enters full screen; restore() is the way back
window.center()
window.move_to(100, 80)
window.resize(1024, 768)
window.close()
```

## Window-scoped intents

The same operations as intents, for declarative wiring (menu items,
accelerators, or handlers that should not know which method runs). They are
defined in `nuiitivet.runtime.window_intents` and dispatch through the
window of the dispatching context:

- **`CloseWindowIntent`**: Closes the window.
- **`MaximizeWindowIntent`**: Maximizes the window to fill the screen.
- **`MinimizeWindowIntent`**: Minimizes the window to the taskbar or dock.
- **`RestoreWindowIntent`**: Restores the window from a minimized or maximized state.
- **`FullScreenIntent`**: Puts the window into fullscreen mode.
- **`CenterWindowIntent`**: Centers the window on the current screen.
- **`MoveWindowIntent(x, y)`**: Moves the window to the specified coordinates.
- **`ResizeWindowIntent(width, height)`**: Resizes the window to the specified dimensions.

App-scoped, through `App.of(context).dispatch(...)`:

- **`ExitAppIntent(exit_code)`**: Closes every window and exits the
  application with the given exit code.

The scoping is strict: dispatching a window intent through `App.of` (or an
app intent through `Window.of`) raises a `TypeError` instead of being
silently misdelivered, so the call site always tells you where an intent
lands.

## Example Usage

```python
import nuiitivet.material as nv
from nuiitivet.runtime.intents import ExitAppIntent
from nuiitivet.runtime.window_intents import (
    CenterWindowIntent,
    CloseWindowIntent,
    MaximizeWindowIntent,
    MinimizeWindowIntent,
    RestoreWindowIntent,
)


class WindowControls(nv.ComposableWidget):
    def _dispatch(self, intent) -> None:
        nv.Window.of(self).dispatch(intent)

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Window Controls"),
                nv.Button("Maximize", on_click=lambda: self._dispatch(MaximizeWindowIntent())),
                nv.Button("Minimize", on_click=lambda: self._dispatch(MinimizeWindowIntent())),
                nv.Button("Restore", on_click=lambda: self._dispatch(RestoreWindowIntent())),
                nv.Button("Center", on_click=lambda: self._dispatch(CenterWindowIntent())),
                nv.Button("Close", on_click=lambda: self._dispatch(CloseWindowIntent())),
                nv.Button("Quit", on_click=lambda: nv.App.of(self).dispatch(ExitAppIntent())),
            ],
            gap=10,
            padding=20,
        )


app = nv.App(nv.Window(content=WindowControls, width=400, height=400))
app.run()
```
