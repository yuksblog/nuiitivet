# Window Operations

Window operations address exactly one window, so they live on the `Window`
object as plain methods. Exiting the whole application is app-scoped and
lives on the App. See [Multiple Windows](multi_window.md) for the
App / Window split.

## Window methods

For code that holds a window (its own via `Window.of(self)`, or one it
opened):

```python
window = nv.Window.of(self)
window.maximize()
window.minimize()
window.restore()      # exit full screen / restore size / bring back
window.full_screen()  # enters full screen; restore() is the way back
window.center()
window.move_to(100, 80)
window.resize(1024, 768)
window.hide()         # park the window; tree, state, and geometry survive
window.show()         # bring it back, focused — or raise an already-visible one
window.close()
```

`hide()` is not a close: the window stays open (and keeps counting for the
App's exit policy), renders no frames while parked, and `show()` restores it
instantly. `window.is_visible` is the matching `Observable[bool]`. This pair
is what a tray-resident app is built on — see [Tray Icon](tray_icon.md).

## App methods

`App.of(context)` returns the running app, typed as `nv.AppProtocol`:

```python
app = nv.App.of(self)
app.exit()                    # close every window and stop the loop
app.set_theme("dark")         # a name, "light"/"dark", or a Theme instance
app.register_themes({...})    # name → Theme, for set_theme by name
```

## In a ViewModel

A ViewModel should not depend on the full `Window` or `App` — annotate the
parameter as `nv.WindowProtocol` / `nv.AppProtocol` instead. Pass it **per
method call**, not in the constructor: a widget builds its ViewModel in
`__init__`, and `.of(context)` does not work that early (the widget is not
mounted yet). So the event handler resolves the object and hands it to the
ViewModel method:

```python
class ShellViewModel:
    def send_to_background(self, window: nv.WindowProtocol) -> None:
        window.hide()

    def quit(self, app: nv.AppProtocol) -> None:
        app.exit()


class Shell(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self._vm = ShellViewModel()

    def build(self):
        return nv.Column(
            children=[
                nv.Button("Hide", on_click=lambda: self._vm.send_to_background(nv.Window.of(self))),
                nv.Button("Quit", on_click=lambda: self._vm.quit(nv.App.of(self))),
            ],
        )
```

A test calls the ViewModel methods with hand-written fakes — no widget tree
needed. `WindowProtocol` carries the operation methods above plus `is_open`,
`is_visible`, and the awaitable `closed`. `AppProtocol` carries `exit`,
`set_theme`, and `register_themes`.

## Example Usage

```python
import nuiitivet.material as nv


class WindowControls(nv.ComposableWidget):
    def build(self):
        return nv.Column(
            children=[
                nv.Text("Window Controls"),
                nv.Button("Maximize", on_click=lambda: nv.Window.of(self).maximize()),
                nv.Button("Minimize", on_click=lambda: nv.Window.of(self).minimize()),
                nv.Button("Restore", on_click=lambda: nv.Window.of(self).restore()),
                nv.Button("Center", on_click=lambda: nv.Window.of(self).center()),
                nv.Button("Close", on_click=lambda: nv.Window.of(self).close()),
                nv.Button("Quit", on_click=lambda: nv.App.of(self).exit()),
            ],
            gap=10,
            padding=20,
        )


app = nv.App(nv.Window(content=WindowControls, width=400, height=400))
app.run()
```
