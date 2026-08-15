# Text Editing Architecture

This document describes the architecture for text input, selection, IME (Input Method Editor) integration, and clipboard handling in `nuiitivet`.

## Overview

Text editing is complex due to the need to synchronize state between the application, the OS text input system (IME), and the rendering engine. `nuiitivet` adopts a **unidirectional data flow** approach for state management and a **platform-patching** strategy for deep IME integration.

## Data Model

The core of the text editing system is the `TextEditingValue` class, which is an immutable value object representing the state of a text field at a specific point in time.

### TextEditingValue

- **`text`** (`str`): The current content of the text field.
- **`selection`** (`TextRange`): The current selection range. If `start == end`, it represents the caret position.
- **`composing`** (`TextRange`): The range of text currently being composed by the IME (underlined text). If valid, this range is part of `text` but is subject to change by the IME.

### TextRange

A simple structure holding `start` and `end` indices. It provides helper methods for text manipulation (e.g., `text_before`, `text_inside`, `text_after`).

## Widget Architecture

### TextField Architecture (M3)

The `TextField` widget follows the Material Design 3 specification and uses a single class driven by a `TextFieldStyle` preset to support multiple visual variants.

- **Single Class (`TextField`)**:
  - Handles all interaction logic (focus, keyboard, mouse, IME).
  - Manages the internal state (`TextEditingValue`).
  - Implements the full rendering pipeline.
  - Visual variant (filled / outlined) is determined by `TextFieldStyle.mode`.

- **Styling (`TextFieldStyle`)**:
  - An immutable dataclass (`frozen=True`) defining all visual properties (colors, dimensions, fonts).
  - `mode` field (`"filled"` | `"outlined"`) controls the visual variant.
  - Provides factory methods `TextFieldStyle.filled()` and `TextFieldStyle.outlined()` for default M3 configurations.

- **Rendering Pipeline**:
  The `paint` method orchestrates the drawing order based on `style.mode`:
  1. `_draw_container` (filled background or outlined border)
  2. `_draw_label` (Floating label animation)
  3. `_draw_text_and_cursor` (Content)
  4. `_draw_icons` (Leading/Trailing icons)
  5. `_draw_error` (Error message below the field)

### State Management

`TextField` holds an internal `Observable[TextEditingValue]`. When `value` is given as an observable, that observable is the field's value cell in the sense of [OBSERVABLE.md §6](OBSERVABLE.md): edits are written back to it, so no separate copy of the text is kept for the caller to fall out of sync with.

It is nonetheless the framework's one **mirror** rather than a true storage substitution, and the reason is a type mismatch. The internal cell holds a `TextEditingValue` — text *and* selection *and* composing range — while the bound observable holds only a `str`. A `str` cell cannot carry the caret, so it cannot be adopted as the cell outright; the widget keeps its own `TextEditingValue` and reconciles the text half with the observable in both directions.

Three rules make that mirror behave:

- **Write-back is suppressed while a composition is active.** The provisional text of a half-converted candidate is not a value the application should see, and anything it wrote in response would fight the IME. The composition commits through the normal text path, which lands with the composing range cleared. The guard compares against the observable's own value rather than the previous text, so ending a composition reconciles even when that particular update left the text alone.
- **An incoming write keeps the caret, clamped into the new text.** Resetting it to the end would be correct only for a field nobody is editing: an application that normalizes on write-back (upper-casing, trimming, reformatting) changes the text under an actively edited field, and moving the caret to the end on every keystroke would make such a field unusable.
- **The loop terminates on equality.** A write-back delivers back into the widget, which returns early once the text it is handed already matches.

A read-only observable (a computed or mapped value) has nowhere to write, so it is displayed and not written to. Such a field is still editable, and the edits go only to the internal cell; pair it with `disabled=True` to make that visible.

**What would remove the mirror.** Accepting an `ObservableProtocol[TextEditingValue]` as `value` — a cell whose type matches the internal one — would make the field a plain storage substitution like every other input widget, and the three rules above would have nothing left to reconcile. It is not offered, because the only thing it buys is letting the application own the caret, and the reconciliation above is what a `str` cell needs anyway: every caller who wants to bind a string still needs it. Reasons to revisit, none of them present today: an application that has to restore a caret position (across navigation, or a re-created field); a second widget editing the same text alongside the field; or a caller who needs to drive the selection programmatically, which the widget's own `value` setter cannot express.

### Input Filters

An input filter is a rule applied to text between a keystroke and the value cell — `widgets/input_filter.py`, exposed as `input_filter`.

The placement is forced. Correcting text requires knowing where the caret was, what it was in, and what it became; the observable knows none of these, so a rule enforced there would return through the mirror on every keystroke and drag the caret with it. The widget is the only participant that holds all three. `_strip_control_chars` was already doing exactly this for control characters; the filter generalizes that hook.

- **A filter defines what is *typeable*, not what is *valid*.** A decimal field has to let `"1."` be typed, because otherwise `.` can never be entered. Whether a finished value is acceptable is `is_error` / `error_text`; reshaping a finished value is `on_submit`.
- **Filters run on insertion only** — typing, an IME commit, a paste. Running them over deletions as well would let a whole-string rule reject the backspace that breaks its pattern, leaving a field whose contents cannot be erased.
- **Filters do not touch values the application assigns.** The initial `value`, and a write to the bound observable, pass through untouched: the field does not silently rewrite what its owner put there.
- **The internal contract carries the selection** (`apply(old, new) -> TextEditingValue`), so the built-in filters move the caret exactly. The public shorthand is a `Callable[[str], str]`, which reports only the resulting string and therefore has its caret inferred from the length change. Widening the public escape hatch to the selection-aware form later is additive.

Composition uses `|`, matching the modifier vocabulary. Masking — displaying `1,234,567` while storing `"1234567"` — is out of scope: it needs the displayed and the stored text to differ, and whatever a filter returns *is* the value.

### Commit

`on_submit` fires when the user presses Enter **and** when the field loses focus, in both cases only if the text moved since the last commit.

Focus loss counts because commit-time work — parsing, padding an incomplete `"1."` to `"1.0"` — would otherwise only ever happen for the users who press Enter, leaving half-typed text behind for everyone who Tabs away. The "changed since last commit" guard is what makes that safe to add: an `on_submit` that runs a search or saves a record must not fire every time the field is merely tabbed through. A value the application assigns counts as already committed, so loading a record into a form does not report it straight back.

Supplying `on_submit` is also what makes the field **claim the Enter key** (see [KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md)); a field that handles commit owns Enter. The coupling is deliberate — a field with an `on_submit` that let Enter pass through to a shortcut would be harder to explain than the cost, which is that setting `on_submit` purely for blur-time normalization also takes Enter away from a shortcut.

### Interaction

It uses `InteractionHostMixin` and attaches a `FocusNode` to handle input events.

## IME Integration

Standard `pyglet` text input support is limited, often resulting in a "floating" candidate window or lack of inline composition on some platforms. `nuiitivet` implements a custom solution to achieve native-quality inline IME support.

### Platform Patching Strategy

To intercept IME events before the OS handles them (or to force inline behavior), `nuiitivet` injects platform-specific patches at runtime.

1. **macOS (Cocoa)**:
    - Uses `ctypes` and `Objective-C Runtime` to hook into `PygletTextView` (the underlying `NSTextView`).
    - Overrides `setMarkedText:selectedRange:replacementRange:` to capture composition updates.
    - Overrides `firstRectForCharacterRange:actualRange:` to report the cursor position back to the OS for correct candidate window positioning.

2. **Windows (Win32)**:
    - Subclasses the window procedure (`WndProc`) to intercept `WM_IME_COMPOSITION`.
    - Uses `ImmGetCompositionString` to retrieve the composition text and cursor position.

3. **Linux (X11/XIM)**:
    - Recreates the X11 Input Context (XIC) with `XIMPreeditCallbacks` style.
    - Registers callbacks (`PreeditStart`, `PreeditDraw`, `PreeditDone`) to receive composition data directly from the X Input Method.

### Event Flow

1. **OS Event**: The user types via IME.
2. **Patch Layer**: The platform patch intercepts the event.
3. **Application Event**: The patch dispatches a custom `on_ime_composition` event to the `pyglet.Window`.
4. **App Dispatch**: `App` receives the event and forwards it to the currently focused `FocusNode`.
5. **Widget Handling**: `TextField` receives the event via its `FocusNode`, updates the `TextEditingValue` (setting the `composing` range), and requests a redraw.

### Candidate Window Positioning

To ensure the IME candidate window appears near the cursor:

1. **IMEManager**: A singleton that stores the current window geometry and the local cursor rectangle.
2. **Update Loop**: `TextField` updates `IMEManager` with the cursor position during its `paint` phase. `App` updates `IMEManager` with the window position during the draw loop.
3. **OS Query**: When the OS asks for the cursor position (e.g., `firstRectForCharacterRange:` on macOS), the patch retrieves the data from `IMEManager` and returns the screen coordinates.

## Clipboard

Clipboard operations are abstracted via the `Clipboard` protocol.

- **`get_system_clipboard()`**: Returns the platform-specific clipboard implementation.
- **Integration**: `TextField` handles standard shortcuts (Cmd+C, Cmd+V, etc.) to interact with the clipboard.

## Key Handling

Key events are routed through the `FocusNode`.

- **`on_text`**: Handles committed character input.
- **`on_text_motion`**: Handles navigation (Arrow keys, Home, End, Backspace, Delete).
- **`on_ime_composition`**: Handles active composition updates.
