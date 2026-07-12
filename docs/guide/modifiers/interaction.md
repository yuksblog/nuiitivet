# Interaction Modifiers

Interaction modifiers are used to add interactivity to Widgets, such as clickability, hoverability, and focusability.

## Clickable

You can make a Widget clickable using the `clickable` modifier. It takes an `on_click` callback that is invoked when the Widget is clicked.

```python
from nuiitivet.modifiers import background, clickable, corner_radius

# Clickable box
box = Container(child=Text("Click Me!")).modifier(
    background("#4CAF50")
    | corner_radius(8)
    | clickable(on_click=lambda: print("Clicked!"))
)
```

![Clickable](../../assets/modifier_interaction_clickable.png)

## Hoverable

You can make a Widget hoverable using the `hoverable` modifier. It takes an `on_hover_change` callback that is invoked when the mouse pointer enters or leaves the Widget.

```python
import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, hoverable, corner_radius
from nuiitivet.observable import Observable

class HoverDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.is_hovered = Observable(False)

    def _set_hovered(self, hovered: bool) -> None:
        self.is_hovered.value = hovered

    def build(self):
        bg_color = self.is_hovered.map(lambda h: "#2196F3" if h else "#E0E0E0")

        return nv.Container(
            width=200,
            height=50,
            child=md.Text("Hover Me!"),
            alignment="center",
        ).modifier(
            background(bg_color)
            | corner_radius(8)
            | hoverable(on_hover_change=self._set_hovered)
        )
```

![Hoverable](../../assets/modifier_interaction_hoverable.png)

## Focusable

You can make a Widget focusable using the `focusable` modifier. It takes an `on_focus_change` callback that is invoked when the Widget gains or loses focus.

```python
import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import background, focusable, border, corner_radius
from nuiitivet.observable import Observable

class FocusDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.is_focused = Observable(False)

    def _set_focused(self, focused: bool) -> None:
        self.is_focused.value = focused

    def build(self):
        border_color = self.is_focused.map(lambda f: "#2196F3" if f else "#00000000")
        
        return nv.Container(
            width=200,
            height=50,
            child=md.Text("Focus with Tab"),
            alignment="center",
        ).modifier(
            background("#E0E0E0")
            | corner_radius(8)
            | border(color=border_color, width=2)
            | focusable(on_focus_change=self._set_focused)
        )
```

![Focusable](../../assets/modifier_interaction_focusable.png)

## Raw pointer input

`clickable` and `hoverable` are convenience layers: they collapse a press and
release into a single click, and reduce hover to a `bool`. When you need the
individual pointer events — for example to draw strokes on a canvas — use
`pointer_input`. It is the low-level "Listener" layer, mirroring Compose's
`Modifier.pointerInput` and Flutter's `Listener`.

Each callback receives a `PointerEvent` and may be sync or async:

```python
import nuiitivet as nv
from nuiitivet.input import BUTTON_LEFT, MOD_CTRL
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.modifiers import corner_radius, pointer_input

def on_press(e: PointerEvent) -> None:
    if e.modifier_keys & MOD_CTRL:
        pick_color(e.local_x, e.local_y)
    else:
        begin_stroke(e.local_x, e.local_y)

def on_move(e: PointerEvent) -> None:
    if e.buttons & BUTTON_LEFT:      # a button is held — a stroke is in progress
        extend_stroke(e.local_x, e.local_y)

canvas = nv.Image(png_bytes, fit="fill", width=320, height=240).modifier(
    corner_radius(8)
    | pointer_input(
        on_press=on_press,
        on_move=on_move,
        on_release=lambda e: end_stroke(),
        buttons=(BUTTON_LEFT,),   # only the left button triggers press/release
        capture=True,             # keep delivering move/release off the widget
    )
)
```

### Coordinates: local vs screen

A `PointerEvent` carries two coordinate pairs:

- `local_x` / `local_y` are **widget-relative** — measured from the top-left of
  the widget that received the event. Use these to map a press onto your content.
- `x` / `y` are **screen (window)** coordinates.

For an `Image` that scales its source bitmap, `local_x` / `local_y` are relative
to the displayed rect; mapping them back to source-image pixels (accounting for
your fit / aspect-ratio choice) stays your responsibility.

### Held buttons

`event.buttons` is a bitmask of the buttons currently held down (OR-ed
`BUTTON_*` codes). Because a plain hover move and a drag both arrive as moves,
check `event.buttons` inside `on_move` to tell whether a stroke is actually in
progress. `event.button` (singular) is only the button that caused *this*
press/release.

### Capture

With `capture=True` (the default) the pointer is captured on press, so `on_move`
and `on_release` keep arriving even after the pointer leaves the widget bounds —
essential for a stroke that runs off the edge. With `capture=False`, moving
outside the bounds delivers `on_leave` and stops `on_move`.

### Reacting to modifier keys while stationary

Reading `event.modifier_keys` handles `Ctrl`+click for free — the mask rides on
every pointer event, so you never track modifier state yourself (that state
desyncs on focus change and window deactivation). The one case it misses is the
pointer sitting **still** while the user presses a modifier: no pointer event is
generated. `on_modifier_keys_change` fills that gap — it fires whenever the held
modifier-key mask changes while the pointer is inside or captured, delivering a
`PointerEvent` synthesized at the current position:

```python
from nuiitivet.input import MOD_ALT

def on_modifier_keys_change(e: PointerEvent) -> None:
    set_cursor(EYEDROPPER if e.modifier_keys & MOD_ALT else BRUSH)

canvas.modifier(pointer_input(on_modifier_keys_change=on_modifier_keys_change))
```

It fires during a capture too (i.e. mid-stroke, even when the pointer is outside
the widget), and never fires for non-modifier keys or when the pointer is
neither inside nor captured. See the runnable
[paint sample](https://github.com/yuksblog/nuiitivet/blob/main/samples/modifiers/interaction/pointer_input.py).

`pointer_input` composes with `clickable` on the same widget without either
clobbering the other, so you can keep a semantic click alongside the raw stream.

## Keyboard shortcuts

`focusable(on_key=...)` delivers *raw keys to the focused widget*. A **shortcut**
is a different thing: a key gesture bound to a **command** (`Ctrl+S` → save).
`key_shortcut` binds one:

```python
from nuiitivet.modifiers import key_shortcut

editor.modifier(key_shortcut("Accel+S", on_trigger=self.save))
```

`Accel` is the primary modifier — **Cmd on macOS, Ctrl everywhere else** — so one
declaration covers every platform. It is resolved when the key is matched, not
when the shortcut is built, so a `Shortcut` value stays portable. Write
`Ctrl`/`Meta` explicitly only when you really mean that one physical key. The
gesture also accepts a typed form, `Shortcut("s", MOD_ACCEL | MOD_SHIFT)`, when
you want to build it from masks rather than parse a string.

### Shortcuts are focus-scoped

A `key_shortcut` binding is live **only while the focused widget is inside the
subtree it is attached to**, and only after the focused widget has *declined* the
key press. Two consequences worth internalizing:

- A focused `TextField` still eats a bare `s` — the shortcut tier is never
  reached. An unhandled `Accel+S` falls through to it.
- With nothing focused, no `key_shortcut` fires at all.

When nested subtrees bind the same gesture, the **innermost** one containing
focus wins; the outer one does not also fire.

### Which target does the command act on?

This is what focus scoping buys you. Give each editor pane its own Save and
`Accel+S` saves **the pane that holds focus**, with no collision between panes:

```python
class TextEditorPane(nv.ComposableWidget):
    def build(self):
        return editor_subtree.modifier(
            key_shortcut("Accel+S", on_trigger=self.save)
        )
```

See the runnable
[two-pane editor sample](https://github.com/yuksblog/nuiitivet/blob/main/samples/modifiers/interaction/key_shortcut.py).

### Bind where the command is owned

**The binding location must follow who owns the command — never "the nearest
convenient widget."**

Saving a painting is a *document* concern. It is not owned by the Canvas (whose
concern is drawing) and not owned by the Save menu item (that item is one *UI
that triggers* the command; menus get unmounted, and `Ctrl+S` must still work).
Both the menu item and the shortcut merely reference the same callback.

So the owner decides where the gesture lives:

| Owner of the command | Where it belongs |
| --- | --- |
| A subtree — the target is decided by **which pane is active** (per-editor Save) | `key_shortcut` |
| The app — a **single unambiguous target** that must fire with nothing focused (New Window, Open, Quit) | App-level registry |

The anti-pattern to avoid: hanging a singular app command off a leaf widget with
`key_shortcut` because it was handy. That silently couples the command to that
widget's focus and mount state — the shortcut stops working the moment focus
moves elsewhere, which is exactly not what "Quit" means.
