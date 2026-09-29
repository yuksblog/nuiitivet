# Keyboard Shortcuts

A shortcut is a key gesture bound to a command: `Ctrl+S` saves. It is a
separate layer from the focus route (`focusable(on_key=...)`), which delivers
raw keys to the focused widget and has no notion of a command.

## Why a Separate Layer

The focus route answers "the focused widget got a key"; a shortcut answers "a
command was invoked". Two things follow. A shortcut fires without anything
focused: `Ctrl+Z` in a paint app undoes a stroke whether or not the canvas
holds focus, and most of the time nothing in a paint app holds focus at all.
And a gesture is portable: `Accel+S` means Cmd+S on macOS and Ctrl+S
elsewhere, from one declaration.

A shortcut layer that required focus would collapse into sugar over
`focusable(on_key=...)`, since the focus route already bubbles keys to
ancestors. The value of this layer is its independence from focus.

## Scopes

A binding's scope says when the gesture is live. The three widen in order,
each a superset of the one before:

| Scope | Live when |
| --- | --- |
| `FOCUS` | the subtree contains the focused node |
| `FOREGROUND` (default) | the subtree is on the topmost interactable layer |
| `MOUNT` | the subtree is in the widget tree at all |

### `FOREGROUND` Is the Default

"You can click it, so its shortcuts work" is what users expect and what the
industry defaults to: Qt's `QShortcut` defaults to `Qt::WindowShortcut`,
SwiftUI's `.keyboardShortcut` is live while the view is in the displayed
scene, GTK4 offers a window-wide `GLOBAL` scope. None requires focus.

`FOREGROUND` excludes a subtree that is hidden by `visible(False)`; closed or
disabled (a closed `Collapsible`, a disabled `Clickable`, by the same
`FocusTraversalBlocker` test that keeps it out of the Tab sequence); kept off
screen by its container (a `Deck` showing another page, a covered navigation
route, which keep every child mounted so a page keeps its state, declared via
`focus_traversal_children()`; without this the previous screen's shortcuts
would fire on the current one); or occluded by a blocking overlay (a dialog or
a menu popup swallows interaction; a `passthrough=True` entry such as a toast
or tooltip does not). These are the questions Tab asks in
[INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md), so a shortcut and
a Tab stop buried in the same hidden content agree about being out of reach.

### `FOCUS` Is the Exception

`FOCUS` is needed only when the same command has two or more targets on
screen at once, so nothing but focus can decide which one acts: a dual-pane
file manager where `F5` copies from the focused pane, a split-view editor
where `Ctrl+S` saves the focused side, a two-list picker where `Delete`
removes from the focused list. And it earns its keep only when the binding
sits on an ancestor of the focused widget (the pane root, while a text field
inside it holds focus); if the command's target is the focused widget itself,
`focusable(on_key=...)` suffices. A tabbed editor is not an instance: the
inactive tab is not displayed, so `FOREGROUND` already disambiguates it.

### `MOUNT` Is the App-Wide Command

`App(Window(content=X))` makes `X` the initial route of the default navigator,
mounted for the life of the app, so an app-wide command is a `MOUNT` binding
on the content root. It keeps working after a route push, which occludes the
root but does not unmount it.

An app-level registry outside the widget tree (the SwiftUI `.commands` shape)
was rejected. `FOCUS` to `MOUNT` are predicates over the widget's own state in
the tree, exactly what a modifier can express, and `MOUNT` is the widest scope
a modifier can have: a binding that fired after its widget unmounted would
have no owner. An "application scope" is not a point further up the same
axis but a different owner, the app, and it would need a registry to exist.
Since a `MOUNT` binding on the content root already survives navigation and
occlusion, the registry would add a second way to say the same thing, and the
less honest one: a binding on the root ties the command's lifetime to a widget
one can point at.

The one case this does not cover is a command that must outlive its own
subtree, an app that `replace`s its root route (login screen to main screen)
and hangs a global command off the login screen. That is a modelling error:
the command was never owned by the login screen. Shortcuts live in every
window of a multi-window app would be outside the tree, and are deferred
until multi-window exists.

## Ownership

The binding location follows who owns the command, never the nearest
convenient widget. Saving a painting is a document concern: not the canvas's,
whose concern is drawing, and not the Save menu item's, which is one UI that
triggers the command and gets unmounted while `Ctrl+S` must still work. Menu
item and shortcut reference the same callback; neither owns it. The scope
follows from the owner: a subtree chosen by which pane is active takes
`FOCUS`; a subtree unambiguous while displayed takes `FOREGROUND`; the app
takes `MOUNT` on the content root.

## Dispatch

`Window._dispatch_key_press` resolves a key press in tiers, in one order:
whatever is closest to the user's attention gets first refusal.

1. `Escape` / `Tab` special-casing.
2. The focused `FocusNode` and its ancestors (`focusable(on_key=...)`). If
   consumed, stop: a focused text field still eats a bare `s`.
3. The text-input guard: if the focused chain takes text and this key is one
   text input may claim, stop. No binding is consulted.
4. `FOCUS` bindings enclosing the focused node, innermost first.
5. `FOREGROUND` bindings whose subtree is on the topmost interactable layer.
6. `MOUNT` bindings.

The first tier that matches wins. Within tier 4 the innermost binding wins,
which is always well-defined. Within tiers 5 and 6 there is no such ordering:
two displayed panes can both bind `Accel+S`. Following Qt's ambiguous-shortcut
overload, this fires nothing and logs a warning rather than picking
arbitrarily; `FOCUS` is what makes such a case expressible, and that is why
the scope exists.

### The Text-Input Guard

Tier 2 rests on the focused widget claiming the keys it uses by returning
`True` from `on_key`. A text field cannot honour that alone, because its key
consumption is split across two routes: `on_key` carries `Enter` and the
`Accel` editing combos, while the characters arrive on `on_text`. When a
printable key arrives, `EditableText.on_key` truthfully returns `False`, and
`on_text` then inserts the character. Read at face value, that `False` would
hand a bare `b` to the shortcut tier: the letter is typed and
`key_shortcut("b", ...)` fires.

Tier 3 withholds such keys from the bindings outright, on two questions that
must both hold. *Does the focused chain take text?* `FocusNode.accepts_text_input`
walks the same `parent` chain that `handle_text_event` delivers along, so what
it reports and where the text goes cannot drift apart. *Can this key be
text?* `produces_text(key, modifier_keys)`, an approximation by design.
Nothing is asked of `EditableText`; any widget that registers an `on_text`
handler is covered, and IME composition with it, since the handler stays
registered throughout.

Whether a key yields a character is not decidable from the key and the
modifier mask. Windows and X11 report AltGr as `Ctrl+Alt`, and on a German
layout `AltGr+Q` types `@`, so a `Ctrl`-bearing gesture can be text. macOS
`Option` types characters (`Option+A` is `å`) and starts dead-key compositions
that resolve only on the next keystroke. The layout can change at runtime, so
no static table is more than an approximation of one layout at one moment.

The decision is therefore to fix the direction of the error rather than chase
precision: a misjudgement costs a shortcut that does not fire, recoverable and
obvious to a user who can unfocus the field, never a keystroke that silently
runs a command. `produces_text` is biased toward text:

| Gesture | Text? |
| --- | --- |
| bare printable (`b`), `Shift`+printable, `Space` | yes |
| anything with `Alt` (`Alt+X`, `Ctrl+Alt+X`) | yes |
| `Ctrl` / `Cmd` without `Alt` (`Accel+S`) | no |
| function and navigation keys (`F5`, arrows, `Escape`, `Enter`) | no |

The accepted cost: `Alt` shortcuts do not fire while a text field holds
focus. It is narrow, since `Ctrl+Alt` gestures already collide with AltGr on
European layouts and are discouraged for that reason, and it is the price of
never stealing a keystroke. The exact alternative, deferring the shortcut
tiers until `on_text` has or has not arrived and using that as the answer,
was rejected: it delays every shortcut by an event cycle, forces a redesign of
what `on_key_press` returns to the backend, and leans on platform ordering
between `on_key_press` and `on_text`, to recover the `Alt` case alone.

`Enter` is classified non-text, so it reaches the shortcut tier unless the
focused field claims it on the `on_key` route. `EditableText` claims `Enter`
only when an `on_submit` is set, and a field without one lets `Enter` fall
through to a `key_shortcut("enter", ...)`. The outcome is often wanted, the
`Enter` a plain field does nothing with is the one a dialog's default action
should get, but it is a limitation: the destination of `Enter` depends on how
the focused field happens to be configured, which the shortcut's author cannot
see. There is no default action in the framework; when one is added, `Enter`
routes through it explicitly rather than by way of a field that declined it.

## Values

`Shortcut` is a frozen value, a normalised key name plus a `MOD_*` bitmask.
`MOD_ACCEL` is the logical primary modifier, resolved to `MOD_META` on macOS
and `MOD_CTRL` elsewhere at match time, never at construction, so one
`Shortcut` stays portable. `ShortcutBinding` is gesture plus callback plus
scope, a type rather than a bare callable so that command semantics
(`can_execute`, menu binding) can be added without touching call sites.
`ShortcutNode` is the `InteractionNode` holding one widget's bindings, keyed
by gesture, so re-applying the modifier during recomposition replaces a
binding rather than stacking a second one.
