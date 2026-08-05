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
- **closed or disabled** — a closed `Collapsible`, a disabled `Clickable`: the
  same `FocusTraversalBlocker` test that keeps the subtree out of the Tab
  sequence;
- **kept off screen by its container** — a `Deck` showing another page, a
  **covered navigation route**: these keep every child mounted (that is how a
  page or screen preserves its state) and show one at a time, so without this
  check the *previous screen's* shortcuts would keep firing on the current one.
  The container declares what it is showing via `focus_traversal_children()`;
- **occluded by a blocking overlay** — a modal dialog or a light-dismiss popup
  swallows interaction, so background commands must not fire behind it. A
  `modeless` (passthrough) entry does not occlude.

This is deliberately the same set of questions Tab asks (see
`INTERACTION_ARCHITECTURE.md` § What Tab Can Reach), so a shortcut and a Tab stop
buried in the same hidden content agree about being out of reach.

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
3. **Text-input guard**: if the focused chain takes text and this key is one text
   input may claim, stop. No binding is consulted. See below.
4. `FOCUS`-scoped bindings enclosing the focused node, **innermost first**.
5. `FOREGROUND`-scoped bindings whose subtree is on the topmost interactable
   layer.
6. `MOUNT`-scoped bindings.

The first tier that matches wins; later tiers are not consulted.

### Ambiguity

Within tier 4 the innermost binding wins, which is always well-defined.

Within tiers 5 and 6 there is no such ordering: two displayed panes can both bind
`Accel+S` with no way to choose between them. Following Qt's "ambiguous shortcut
overload", this **fires nothing and logs a warning** rather than picking
arbitrarily. `FOCUS` is the escape hatch that makes such a case expressible — and
that is precisely why the scope exists.

### The text-input guard (tier 3)

Tier 2 rests on the focused widget *claiming* the keys it uses by returning
`True` from `on_key`. A text field cannot honour that on its own, because its key
consumption is split across two routes: `on_key` carries `Enter` and the `Accel`
editing combos, while the **characters themselves arrive on `on_text`**. So when
a printable key arrives, `EditableText.on_key` truthfully returns `False` (it
really does nothing on that route) and then `on_text` inserts the character
anyway. Read at face value, that `False` would hand a bare `b` to the shortcut
tier — the letter is typed *and* `key_shortcut("b", ...)` fires (#331).

Tier 3 closes this by withholding such keys from the bindings outright. It asks
two questions, and **both** must hold:

- **Does the focused chain take text?** `FocusNode.accepts_text_input` walks the
  same `parent` chain that `handle_text_event` delivers along, so what it reports
  and where the text actually goes cannot drift apart. This is a fact.
- **Can this key be text?** `produces_text(key, modifier_keys)`. This one is an
  **approximation**, and deliberately so.

Nothing is asked of `EditableText`: it keeps returning `False` for printable
keys. Any widget that registers an `on_text` handler on its `FocusNode` is
covered automatically, and IME composition is covered for free — the handler
stays registered throughout.

#### Why `produces_text` cannot be exact, and which way it errs

Whether a key yields a character is not decidable from the key and the
modifier-key mask:

- Windows and X11 report **AltGr as `Ctrl+Alt`**, and on a German layout
  `AltGr+Q` types `@`. So even a `Ctrl`-bearing gesture can be text.
- macOS **`Option` types characters** (`Option+A` → `å`) and starts **dead-key**
  compositions that resolve only on the *next* keystroke.
- The active keyboard layout can change at runtime, so no static table is ever
  more than an approximation of one layout at one moment.

The design decision is therefore not to chase precision but to **fix the
direction of the error**: a misjudgement must cost a shortcut that does not fire
— recoverable, and obvious to the user, who can unfocus the field — never a
keystroke that silently runs a command. `produces_text` is biased toward text:

| Gesture | Text? |
| --- | --- |
| bare printable (`b`), `Shift`+printable (`Shift+B`), `Space` | yes |
| **anything with `Alt`** (`Alt+X`, `Ctrl+Alt+X`) | **yes** — see above |
| `Ctrl`/`Cmd` without `Alt` (`Accel+S`) | no |
| function and navigation keys (`F5`, arrows, `Escape`, `Enter`) | no |

**Consequence, and the accepted cost:** `Alt`-based shortcuts do not fire while a
text field holds focus. This is narrow — `Ctrl+Alt` gestures already collide with
AltGr on European layouts and are discouraged for that reason (Qt says the same)
— and it is the price of never stealing a keystroke from the user's typing.

The exact alternative — defer the shortcut tiers until `on_text` has (or has not)
arrived, and use *that* as the answer — was considered and rejected: it delays
every shortcut by an event cycle, forces a redesign of what `on_key_press`
returns to the backend, and leans on platform-specific ordering guarantees
between `on_key_press` and `on_text`. Not worth it to recover the `Alt` case
alone.

#### Known limitation: `Enter` through a field that does not use it

`produces_text` classifies `Enter` as non-text, so it reaches the shortcut tier
unless the focused field claims it on the `on_key` route first. `EditableText` is
single-line: it claims `Enter` only when an `on_submit` is set (there is a
callback to run), and declines it otherwise. A field with no `on_submit`
therefore lets `Enter` fall through to a `key_shortcut("enter", ...)`.

The *outcome* is often what one wants — the `Enter` a plain field does nothing
with is exactly the one a dialog's default action should get. But this is a
**limitation, not a designed behaviour**: it makes the destination of `Enter`
depend on how the focused field happens to be configured, which is not something
the author of the shortcut can see. There is no notion of a default action in the
framework yet; when one is added, `Enter` should route through it explicitly
rather than arriving by way of a field that declined it.

Until then, `Enter` is not a dependable gesture on a screen that also holds text
fields.

## Value types

- `Shortcut` — a frozen value: a normalized key name plus a `MOD_*` bitmask.
  `Shortcut.parse("Accel+Shift+S")` builds one from a spec string;
  `key_shortcut()` accepts the spec directly, so the common case needs no
  explicit parse.
- `MOD_ACCEL` — the logical primary modifier key. It is resolved to `MOD_META` on
  macOS and `MOD_CTRL` elsewhere **at match time**, never baked in at
  construction, so one `Shortcut` value stays portable across platforms.
- `ShortcutBinding` — a gesture plus the callback it triggers plus its scope.
  Kept as a type rather than a bare callable so that command semantics
  (`can_execute`, menu binding) can be added without touching call sites.
- `ShortcutNode` — an `InteractionNode` holding the bindings attached to one
  widget. Bindings are keyed by gesture, so re-applying the modifier during
  recomposition replaces a binding rather than stacking a second one.
