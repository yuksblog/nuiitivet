# Keyboard Shortcuts

This document defines the keyboard **shortcut** layer: a key gesture bound to a
command (`Ctrl+S` → save). It is a separate concern from the **focus route**
(`focusable(on_key=...)`), which delivers raw keys to the focused widget and has
no notion of a command.

## Why a separate layer

The focus route answers "the focused widget got a key". A shortcut answers "a
command was invoked". Two things follow from that difference:

- A shortcut must be able to fire **without anything focused**. `Ctrl+Z` in a
  paint app undoes a stroke whether or not the canvas holds focus — most of the
  time nothing in a paint app holds focus at all.
- A gesture is **portable**: `Accel+S` means Cmd+S on macOS and Ctrl+S
  elsewhere, from a single declaration.

A shortcut layer that required focus would collapse into sugar over
`focusable(on_key=...)` — the focus route already bubbles keys to ancestors, so
nothing new would be expressed. The value of this layer *is* its independence
from focus.

## Scopes

A binding's **scope** answers: under what condition is this gesture live? The
scopes form a widening chain — each one is a superset of the one before it.

| Scope | Live when | Use for |
| --- | --- | --- |
| `FOCUS` | the subtree contains the focused node | multiple instances of the same command target displayed **simultaneously** |
| `FOREGROUND` (default) | the subtree is on the topmost interactable layer | almost everything |
| `MOUNT` | the subtree is in the widget tree at all | app-wide commands that must survive navigation |

### `FOREGROUND` is the default

"You can click it, so its shortcuts work" is the rule users already expect, and
it is what the industry defaults to: Qt's `QShortcut` defaults to
`Qt::WindowShortcut`, SwiftUI's `.keyboardShortcut` is live while the view is in
the displayed scene, GTK4 offers a window-wide `GLOBAL` scope. None of them
require focus.

`FOREGROUND` excludes a subtree that is:

- hidden by `visible(False)` — the widget stays mounted but is not displayed;
- on a **covered navigation route** — `Navigator` keeps covered routes in the
  tree and only paints the top one, so without this check the *previous screen's*
  shortcuts would keep firing on the current screen;
- **occluded by a blocking overlay** — a modal dialog or a light-dismiss popup
  swallows interaction, so background commands must not fire behind it. A
  `modeless` (passthrough) entry does not occlude.

### `FOCUS` is the exception, not the rule

`FOCUS` is needed only when **the same command has two or more targets on screen
at once**, so nothing but focus can decide which one acts:

- a dual-pane file manager — `F5` copies from **the focused pane**;
- a split-view / diff editor — `Ctrl+S` saves the focused side;
- a two-list picker — `Delete` removes from the focused list.

Note the second condition: `FOCUS` earns its keep only when the binding sits on
an **ancestor** of the focused widget (the pane root, while a text field inside
it holds focus). If the command's target *is* the focused widget itself,
`focusable(on_key=...)` already suffices.

A tabbed editor is **not** an instance of this: the inactive tab is not
displayed, so `FOREGROUND` already disambiguates it.

### `MOUNT` is how an app-wide command is expressed

`App(content=X)` makes `X` the initial route of the default navigator, and it
stays mounted for the life of the app. So an app-wide command is a `MOUNT`-scoped
binding on the content root:

```python
App(content=home.modifier(key_shortcut("Accel+Q", on_trigger=quit, scope=MOUNT)))
```

This keeps working after a route push, which occludes `home` but does not unmount
it.

### Why there is no `APPLICATION` scope, and no `App(shortcuts=...)`

An earlier design proposed an app-level registry outside the widget tree (the
SwiftUI `.commands` shape). It is not needed, and the reason is structural:

`FOCUS` … `MOUNT` are all predicates over **the widget's own state in the tree**,
which is exactly what a modifier can express. `MOUNT` is therefore the widest
scope a modifier *can* have — a binding that fired after its widget unmounted
would have no owner at all; only a detached callback would remain. So
"application scope" is not a point further up the same axis: it is a different
**owner** (the App rather than a widget), and it would need a registry outside
the tree to exist.

Since a `MOUNT`-scoped binding on the content root already survives navigation
and occlusion, that registry would buy nothing but a second way to say the same
thing. Binding on the content root is also the more honest of the two: the
command's lifetime is visible in the code, tied to a widget you can point at,
rather than living in a global hook.

The one case it does not cover is a command that must outlive its own subtree —
e.g. an app that `replace`s its root route (login screen → main screen) and hangs
a global command off the login screen. That is a modelling error, not a gap: the
command was never owned by the login screen. Genuine multi-window shortcuts
(live in *every* window) would be outside the tree, and are deferred until
multi-window exists.

## Ownership: bind where the command lives

**The binding location must follow who owns the command, never "the nearest
convenient widget."**

Saving a painting is a *document* concern. It is not owned by the Canvas (whose
concern is drawing) and not by the Save menu item (that item is one *UI that
triggers* the command; menus get unmounted, and `Ctrl+S` must still work). The
menu item and the shortcut both reference the same callback; neither owns it.

The scope follows from the owner:

| Owner | Scope |
| --- | --- |
| a subtree, chosen by which pane is active | `FOCUS` |
| a subtree, unambiguous while displayed | `FOREGROUND` |
| the app, must survive navigation | `MOUNT`, on the content root |

## Dispatch

`Application._dispatch_key_press` resolves a key press in tiers. The order
encodes one principle: **whatever is closest to the user's attention gets first
refusal.**

1. `Escape` / `Tab` special-casing.
2. The focused `FocusNode` and its ancestors (`focusable(on_key=...)`). If
   consumed, stop — a focused text field still eats a bare `s`.
3. `FOCUS`-scoped bindings enclosing the focused node, **innermost first**.
4. `FOREGROUND`-scoped bindings whose subtree is on the topmost interactable
   layer.
5. `MOUNT`-scoped bindings.

The first tier that matches wins; later tiers are not consulted.

### Ambiguity

Within tier 3 the innermost binding wins, which is always well-defined.

Within tiers 4 and 5 there is no such ordering: two displayed panes can both bind
`Accel+S` with no way to choose between them. Following Qt's "ambiguous shortcut
overload", this **fires nothing and logs a warning** rather than picking
arbitrarily. `FOCUS` is the escape hatch that makes such a case expressible — and
that is precisely why the scope exists.

### A focused widget must consume the keys it uses

Tier 2 is load-bearing: it is what keeps a bare-letter shortcut (`B` for brush)
from firing while the user types "b" into a text field. This only works if the
focused widget *claims* the key by returning `True` from `on_key`. `EditableText`
currently returns `False` for printable keys — its text arrives through the
separate `on_text` route — so it does not claim them. Tracked in #331; until it is
fixed, bare-letter shortcuts are unsafe when a text field can hold focus.

## Value types

- `Shortcut` — a frozen value: a normalized key name plus a `MOD_*` bitmask.
  `Shortcut.parse("Accel+Shift+S")` builds one from a spec string;
  `key_shortcut()` accepts the spec directly, so the common case needs no
  explicit parse.
- `MOD_ACCEL` — the logical primary modifier. It is resolved to `MOD_META` on
  macOS and `MOD_CTRL` elsewhere **at match time**, never baked in at
  construction, so one `Shortcut` value stays portable across platforms.
- `ShortcutBinding` — a gesture plus the callback it triggers plus its scope.
  Kept as a type rather than a bare callable so that command semantics
  (`can_execute`, menu binding) can be added without touching call sites.
- `ShortcutNode` — an `InteractionNode` holding the bindings attached to one
  widget. Bindings are keyed by gesture, so re-applying the modifier during
  recomposition replaces a binding rather than stacking a second one.
