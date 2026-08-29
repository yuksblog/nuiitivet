# Multiple Windows

An app is not tied to one window. `nv.Window` is a window of its own — with
its own widget tree, overlay, navigator, focus and menu bar — constructed as
a model and shown with `open()`:

```python
import nuiitivet.material as nv


class Main(nv.ComposableWidget):
    def _open_palette(self) -> None:
        nv.Window(
            content=lambda: Palette(self.state),
            title="Palette",
            width=280,
            height=170,
        ).open()

    ...


app = nv.App(nv.Window(content=Main, title="My app"))
app.run()
```

`nv.App` takes its **main window** as the first argument, plus the
app-level options (`theme`, `exit_policy`). Every window-flavored keyword
(`width`, `height`, `title`, `chrome`, `menu`, ...) belongs to
`nv.Window` — the same constructor whether it builds the main window or a
secondary one.

A runnable demo is at
[`samples/window/multi_window.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/multi_window.py).

## One object, one window lifetime

`Window(...)` builds a model — no OS window yet. `open()` realizes it (from
anywhere: before `app.run()`, or from a callback while the app runs) and
returns the window for chaining. `close()` destroys it: the tree is
unmounted and the object is finished — to show the same content again,
construct a new `Window`. The OS close button is equivalent to `close()`.

State that must survive a window therefore lives **in the app layer** — an
`Observable` created outside the window and passed into its content. This is
the framework's ordinary state idiom; a palette rebuilt from the same shared
state reopens exactly where it left off:

```python
class AppState:
    def __init__(self) -> None:
        self.color = nv.Observable("#6750A4")

state = AppState()
nv.Window(content=lambda: Palette(state), title="Palette").open()
```

`window.is_open` is an `Observable[bool]`, and `await window.closed`
resolves once the window has closed.

## Everything resolves per window

Each window has its own overlay, navigator, and focus state.
`Overlay.of(context)`, `Navigator.of(context)` and every other
`.of(context)` lookup resolve to the window the context belongs to, so
dialogs, menus and navigation confine themselves to their own window with no
extra plumbing. `nv.Window.of(context)` returns the window itself — the way
content closes its own window:

```python
nv.Button("Done", on_click=lambda: nv.Window.of(self).close())
```

The menu bar is per window too: `Window(menu=...)` (and `window.menu = ...`
for wholesale replacement). On macOS, where the menu renders on the global bar, currently only
the **main window's** menu is bridged; following the focused window is
planned.

## Parent, child, modal

`parent=` makes a child window: it stacks with its parent and closes,
transitively, when the parent closes. `modal=True` (requires `parent`)
additionally blocks pointer and keyboard input to the parent chain while the
child is open — a settings window the main window must wait for:

```python
nv.Window(
    content=lambda: Settings(state),
    title="Settings",
    parent=nv.Window.of(self),
    modal=True,
).open()
```

Modality is enforced by the framework (the OS backend has no cross-platform
window modality): sibling top-level windows stay interactive, and activating
a blocked parent hands focus back to its modal child.

## Window operations and intents

The window-management verbs are imperative methods on the window:
`maximize()`, `minimize()`, `restore()`, `full_screen()`, `center()`,
`move_to(x, y)`, `resize(w, h)`, `close()`. For declarative wiring (menu
items, accelerators) the same operations exist as **window-scoped intents**,
dispatched through the window of the dispatching context:

```python
nv.Window.of(context).dispatch(nv.CloseWindowIntent())
```

App-scoped intents — `ExitAppIntent`, the theme intents — dispatch through
`App.of(context).dispatch(...)` instead. The split is strict: dispatching an
intent at the wrong scope raises rather than being silently misdelivered, so
the call site always tells you where an intent lands. Menu-bar standard
items (`MenuEntry.close_window()`, `MenuEntry.quit()`, ...) route
themselves correctly.

## When the app exits

`App(..., exit_policy=...)` decides when `app.run()` returns:

| Policy | Behavior |
| --- | --- |
| `nv.ExitPolicy.LAST_WINDOW_CLOSED` | Default — exit once no window remains open. |
| `nv.ExitPolicy.MAIN_WINDOW_CLOSED` | Closing the main window closes every other window and exits. |
| `nv.ExitPolicy.EXPLICIT` | Only `ExitAppIntent` (or `app.exit()`) exits; the app keeps running with zero windows, so keep some way to reopen one. |

`ExitAppIntent` always closes every window and exits, under any policy.

## Theme

The theme is app-wide: `App(..., theme=...)` supplies every window, and the theme
intents stay app-scoped. Per-window theme overrides are a planned extension
(`Window(theme=...)`), not yet implemented.
