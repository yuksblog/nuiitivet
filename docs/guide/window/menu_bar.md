# Menu Bar

`App(menu=...)` gives the application a menu bar. The menu is a **declarative
model** registered on the App — not widgets in the tree — and renders as a bar
at the top of the content area, below the window chrome:

```python
import nuiitivet.material as nv


class Editor(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.can_save = nv.Observable(False)
        self.word_wrap = nv.Observable(False)

    ...


editor = Editor()
app = nv.App(
    content=editor,
    title="Editor",
    menu=nv.MenuBar([
        nv.MenuBarItem("File", submenu=[
            nv.MenuBarItem("Open...", shortcut="Accel+O", on_select=editor.open),
            nv.MenuBarItem("Save", shortcut="Accel+S",
                           on_select=editor.save, enabled=editor.can_save),
            nv.MenuBarItem.separator(),
            nv.MenuBarItem.quit(),
        ]),
        nv.MenuBarItem("View", submenu=[
            nv.MenuBarItem("Word Wrap", on_select=editor.wrap_changed,
                           checked=editor.word_wrap),
        ]),
    ]),
)
app.run()
```

A runnable demo is at
[`samples/window/menu_bar.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/menu_bar.py).

## Items

One type, `nv.MenuBarItem`, covers every role:

| Role | Construction |
| --- | --- |
| Action | `nv.MenuBarItem("Open...", on_select=..., shortcut="Accel+O")` |
| Submenu | `nv.MenuBarItem("File", submenu=[...])` — nesting is unlimited |
| Separator | `nv.MenuBarItem.separator()` |
| Standard item | `nv.MenuBarItem.quit()` and friends |

An item is exactly one of these; the constructor raises on any other
combination (e.g. `on_select` together with `submenu`). `on_select` is
called with no arguments and may be sync or async.

### Standard items

Standard items are prebuilt commands — no `on_select` needed — whose labels
and accelerators follow platform conventions (`quit()` is "Quit ⌘Q" on macOS
and "Exit" elsewhere):

- `nv.MenuBarItem.quit()` — exit the application
- `nv.MenuBarItem.close_window()`
- `nv.MenuBarItem.minimize()` / `nv.MenuBarItem.maximize()`
- `nv.MenuBarItem.full_screen()` — enters full screen; pair it with
  `restore()` to offer the way back
- `nv.MenuBarItem.restore()` — exit full screen / restore the pre-maximize
  size / bring a minimized window back

`label`, `shortcut` and `enabled` are overridable on each factory.

## Shortcuts

`shortcut` takes the same spec strings as
[`key_shortcut()`](../modifiers/interaction.md) — `"Accel+S"`,
`"Ctrl+Shift+Z"` — or a `Shortcut` value. The one declaration does both jobs:

- The accelerator is **displayed** next to the item, in the platform's form
  (`⌘S` on macOS, `Ctrl+S` elsewhere).
- The gesture **fires the item app-wide**, without opening the menu. A
  disabled item does not fire.

Do not also register the same gesture with `key_shortcut()` — the menu item
*is* the registration.

## Reactive properties

`label` and `enabled` accept an `Observable` and update the rendered menu
live. `checked` makes the item checkable and must be a **writable**
`Observable[bool]`: activating the item toggles the value first, then calls
`on_select`, and the check mark follows the observable from anywhere.

Structure is not observable. To add or remove items, assign a whole new
model — item properties keep updating live in between:

```python
app.menu = nv.MenuBar([...])   # wholesale replacement
```

## Placement

By default the bar appears at the top of the content area, under either
`OSChrome` or a `CustomChrome` header. To render it somewhere else — say
inside a custom title bar, VS Code-style — mount `nv.MenuBarArea` there:

```python
chrome = nv.CustomChrome(
    header=nv.Row(children=[
        nv.Text("Editor"),
        nv.MenuBarArea(),
    ]),
)
```

A mounted `MenuBarArea` suppresses the automatic insertion; the model stays
on the App either way, so menus, callbacks and shortcuts are unaffected by
placement. An area with no registered menu renders nothing.

## Keyboard

With a menu open: `Up`/`Down` rove the items, `Left`/`Right` walk into and
out of a submenu — and, at the top level, switch to the neighboring menu —
`Enter` activates, `Escape` closes. A focused bar title opens its menu with
`Down` or `Enter`.

## Styling

Geometry and per-instance colors live in `nv.MenuBarStyle`, attached to the
model:

```python
nv.MenuBar(items, style=nv.MenuBarStyle(bar_height=40))
```

Colors come from the active theme, so the bar and its popups follow
light/dark switching automatically. To override individual colors for one
menu bar, set the corresponding `MenuBarStyle` fields (`bar_background`,
`popup_background`, ...); a field left `None` follows the theme.

## Platform notes

- **Windows / Linux** — the bar is drawn in-app, below the chrome (or at a
  `MenuBarArea`), as described above.
- **macOS** — the same model goes to the **global menu bar** (`NSMenu`);
  nothing is drawn in the window and a mounted `MenuBarArea` collapses to
  zero size. An application menu is synthesized automatically — a
  `MenuBarItem.quit()` found in one of your menus is relocated into it, and
  one is added if you have none. Accelerators become native key equivalents
  (`⌘S`). No platform branching is needed in app code.
