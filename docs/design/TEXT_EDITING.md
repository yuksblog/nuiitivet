# Text Editing

A text field keeps its state in an immutable value. Typed text, key
shortcuts and the OS input method all turn one value into the next.

## Overview

Four groups of modules take part, with the app and the OS input method at
their edges.

### Structure

```mermaid
flowchart LR
    value[The Value]
    editor[The Editor]
    dispatch[The Dispatch]
    ime[The IME]
    app[the app]
    os[the OS input method]

    app -- "TextField(value, on_change, on_submit, input_filter) · TextField.multiline(...)" --> editor
    editor -- "insert_text · compose_text · end_composition · apply_motion · apply_shortcut · apply(old, new)" --> value
    dispatch -- "on_text · on_key · on_text_motion · on_ime_composition · on_ime_commit" --> editor
    os -- "a composition update · where is the caret" --> ime
    ime -- "on_ime_composition(text, start, length)" --> dispatch
    editor -- "set_cursor_source(rect_fn)" --> ime
```

| Module | Role |
| --- | --- |
| The Value | the immutable editing value and the pure functions that produce the next one |
| The Editor | the widget that holds the value, mirrors its text to the app and draws it |
| The Dispatch | routes typed text, motions and compositions to the focused field |
| The IME | the patch on each platform window and the caret the OS asks for |
| the app | binds a `str` observable and the callbacks |
| the OS input method | composes text inline and places its candidates at the caret |

### Promises

- Typed text and key presses arrive on two routes. A field inserts
  characters from `on_text`. It claims keys on `on_key`.
- The IME is reached by patching the platform window, never through the
  backend's own text input.

## The Value

`TextEditingValue` is a snapshot of a field: the text, the selection and
the range the IME is still converting.

### Structure

```mermaid
flowchart LR
    value[widgets/text_editing.py]
    filter[widgets/input_filter.py]
    editor[widgets/editable_text.py]
    app[the app]

    editor -- "insert_text(value, text, filter, line_breaks) · compose_text(value, text, start, length) · end_composition(value) · apply_motion(value, motion, select) · apply_shortcut(value, key, clipboard, filter, line_breaks)" --> value
    value -- "apply(old, new)" --> filter
    app -- "allow(pattern) · deny(pattern) · digits_only() · max_length(n) · matching(pattern) · a Callable[[str], str] · a | b" --> filter
```

| Module | Role |
| --- | --- |
| `widgets/text_editing.py` | `TextRange`, `TextEditingValue`; the edits as functions from one value to the next |
| `widgets/input_filter.py` | `InputFilter.apply(old, new)`, the built-in filters, the chain |
| `widgets/editable_text.py` | the one caller of the edits (The Editor) |
| the app | composes filters |

### Promises

- The composing range is part of the text until the IME commits.
- A filter runs on typing, a paste and an IME commit. It runs on no deletion
  and on no value the app assigns.

## The Editor

`EditableText` is the field. `TextField` decorates it.

### Structure

```mermaid
flowchart LR
    editor[widgets/editable_text.py]
    base[widgets/text_field.py]
    material[material/text_fields.py]
    value[widgets/text_editing.py]
    lines[widgets/text_lines.py]
    interaction[widgets/interaction.py]
    observable[observable/]
    ime[platform/ime.py]
    app[the app]

    app -- "TextField(value, on_change, on_submit, input_filter) · TextField.multiline(min_lines, max_lines, ...)" --> material
    material -- "is a" --> base
    base -- "EditableText(value, on_change, on_submit, input_filter, multiline, ...) · value · focus()" --> editor
    editor -- "insert_text · compose_text · end_composition · apply_motion · apply_shortcut" --> value
    editor -- "break_lines · line_of · caret_x · index_at · move_lines · line_edge" --> lines
    editor -- "FocusNode(on_text, on_key, on_text_motion, on_ime_composition, on_ime_commit)" --> interaction
    editor -- "subscribe(_on_external_change) · obs.value = text" --> observable
    editor -- "set_cursor_source(_ime_caret_rect) · clear_cursor_source" --> ime
    editor -- "on_change(text) · on_submit(text)" --> app
```

| Module | Role |
| --- | --- |
| `widgets/editable_text.py` | `EditableText`: the internal `Observable[TextEditingValue]`, the mirror to the bound `str` observable, the handlers for text, keys, motions and compositions, the caret |
| `widgets/text_field.py` | `TextFieldBase`, the decorated field around one editable |
| `material/text_fields.py` | the MD3 `TextField` and its `multiline` constructor ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |
| `widgets/text_editing.py` | the edits (The Value) |
| `widgets/text_lines.py` | breaks text into lines for a width; the caret's line and x |
| `widgets/interaction.py` | the focus node the handlers hang on ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `observable/` | the bound observable ([OBSERVABLE.md](OBSERVABLE.md)) |
| `platform/ime.py` | the window's caret source (The IME) |
| the app | the bound observable and the callbacks |

### Sequence

#### A keystroke becomes the app's text

```mermaid
sequenceDiagram
    participant I as widgets/interaction.py
    participant E as editable_text.py
    participant V as text_editing.py
    participant O as observable/
    participant A as the app

    I->>E: on_text(text)
    E->>V: insert_text(value, text, filter)
    V-->>E: the new value, filtered
    E->>E: _update_value(new)
    alt composing, or the text equals the last announced
        Note over E: no announcement
    else
        E->>O: obs.value = text
        O->>E: _on_external_change(text), equal, returns
        E->>A: on_change(text)
    end
```

#### The app rewrites the text

```mermaid
sequenceDiagram
    participant A as the app
    participant O as observable/
    participant E as editable_text.py

    A->>O: obs.value = "ABC"
    O->>E: _on_external_change("ABC")
    E->>E: the caret kept, clamped into the new text
    E->>A: on_change("ABC")
```

### Promises

- `on_change` fires for every text change, from the user or from the app.
  The write-back fires for the user's edits only.
- Nothing is announced while a composition is active. Ending the
  composition announces the text, changed or not.
- The write-back loop ends on equality.
- A field without `on_submit` declines Enter.
- An Enter that confirms an IME composition is not a submit.

## The Dispatch

The window routes text, motions and compositions to the focused node. The
node bubbles them up its chain.

### Structure

```mermaid
flowchart LR
    runner[backends/pyglet/runner.py]
    window[runtime/window.py]
    interaction[widgets/interaction.py]
    editor[widgets/editable_text.py]
    shortcuts[input/shortcut.py]

    runner -- "_dispatch_text(text) · _dispatch_text_motion(motion, select) · _dispatch_ime_composition(text, start, length) · _dispatch_key_press(key, mods) · _set_os_active(active)" --> window
    window -- "handle_text_event(text) · handle_text_motion_event · handle_ime_composition_event · handle_ime_commit_event() · handle_key_event · accepts_text_input" --> interaction
    interaction -- "on_text · on_text_motion · on_ime_composition · on_ime_commit · on_key" --> editor
    window -- "produces_text(key, modifier_keys)" --> shortcuts
```

| Module | Role |
| --- | --- |
| `backends/pyglet/runner.py` | the `on_text`, `on_text_motion`, `on_ime_composition` and activate handlers ([APP_WINDOW.md](APP_WINDOW.md)) |
| `runtime/window.py` | hands each event to the focused node |
| `widgets/interaction.py` | `FocusNode`: the handlers and the bubbling to the parent node |
| `widgets/editable_text.py` | the field at the end of the chain (The Editor) |
| `input/shortcut.py` | the text guard of the shortcut tier ([KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)) |

### Sequence

#### The window loses the OS focus mid-composition

```mermaid
sequenceDiagram
    participant R as backends/pyglet/runner.py
    participant W as runtime/window.py
    participant I as widgets/interaction.py
    participant E as editable_text.py

    R->>W: _set_os_active(False)
    W->>I: handle_ime_commit_event()
    I->>E: on_ime_commit()
    E->>E: end_composition: the provisional text kept, the range cleared
```

### Promises

- A window blocked by a modal child consumes a text event.
- A key the focused chain can type reaches no shortcut.
- A field holds no live composition while its window lacks the OS focus.

## The IME

Each platform window is patched to intercept the input method before the OS
handles it. The window's `IMEManager` answers where the caret is.

### Structure

```mermaid
flowchart LR
    manager[platform/ime.py]
    macos[backends/pyglet/ime/macos.py]
    windows[backends/pyglet/ime/windows.py]
    linux[backends/pyglet/ime/linux.py]
    runner[backends/pyglet/runner.py]
    window[runtime/window.py]
    editor[widgets/editable_text.py]
    os[the OS input method]

    runner -- "install_patch(pyglet_window, window) · discard_conversation(pyglet_window)" --> macos & windows & linux
    runner -- "update_window_info(x, y, w, h), on draw" --> manager
    window -- "IMEManager()" --> manager
    editor -- "set_cursor_source(rect_fn) · clear_cursor_source(rect_fn)" --> manager
    macos & windows & linux -- "cursor_rect" --> manager
    macos & windows & linux -- "on_ime_composition(text, start, length)" --> runner
    os -- "setMarkedText · WM_IME_COMPOSITION · PreeditDraw · the caret query" --> macos & windows & linux
```

| Module | Role |
| --- | --- |
| `platform/ime.py` | `IMEManager`: the window's position and the caret source |
| `backends/pyglet/ime/macos.py` | overrides `setMarkedText:selectedRange:replacementRange:` and `firstRectForCharacterRange:actualRange:` on the `NSTextView` through the Objective-C runtime |
| `backends/pyglet/ime/windows.py` | subclasses the window procedure for the composition messages |
| `backends/pyglet/ime/linux.py` | recreates the X input context with preedit callbacks |
| `backends/pyglet/runner.py` | installs the patch when the window is realised; drops the OS conversation on deactivate ([APP_WINDOW.md](APP_WINDOW.md)) |
| `runtime/window.py` | owns the manager ([APP_WINDOW.md](APP_WINDOW.md)) |
| `widgets/editable_text.py` | the focused field, the caret source (The Editor) |
| the OS input method | composes and asks for the caret |

### Sequence

#### The OS asks where the caret is

```mermaid
sequenceDiagram
    participant OS as the OS input method
    participant P as ime/macos.py, windows.py or linux.py
    participant M as platform/ime.py
    participant E as editable_text.py

    OS->>P: the caret query
    P->>M: cursor_rect
    M->>E: _ime_caret_rect(), the registered source
    E->>E: the caret's line and x from layout, the scroll settled
    E-->>M: the rect in window coordinates
    M-->>P: the rect plus the window's position
    P-->>OS: the rect in screen coordinates
```

### Promises

- One `IMEManager` per window.
- The focused field is its window's caret source. It withdraws on unmount.
- The caret rect is computed when the OS asks, from layout state. Nothing
  publishes it on paint.
- A window that loses the OS focus drops its OS-side conversation.
