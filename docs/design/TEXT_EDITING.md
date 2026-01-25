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

The `TextField` widget follows the Material Design 3 specification and is structured to support multiple visual variants while sharing core logic.

- **Base Class (`TextField`)**:
  - Handles all interaction logic (focus, keyboard, mouse, IME).
  - Manages the internal state (`TextEditingValue`).
  - Implements the core rendering pipeline (Template Method pattern).
  - Defines abstract/hook methods for variant-specific rendering (e.g., `_draw_container`).

- **Concrete Classes**:
  - **`FilledTextField`**: Implements the M3 "Filled" style with a background container and bottom indicator.
  - **`OutlinedTextField`**: Implements the M3 "Outlined" style with a border and transparent background.

- **Styling (`TextFieldStyle`)**:
  - An immutable dataclass (`frozen=True`) defining all visual properties (colors, dimensions, fonts).
  - Provides factory methods `TextFieldStyle.filled()` and `TextFieldStyle.outlined()` for default M3 configurations.
  - Subclasses initialize their default style using these factories if no custom style is provided.

- **Rendering Pipeline**:
  The `paint` method in the base class orchestrates the drawing order:
  1. `_draw_container` (Subclass responsibility)
  2. `_draw_label` (Floating label animation)
  3. `_draw_text_and_cursor` (Content)
  4. `_draw_icons` (Leading/Trailing icons)
  5. `_draw_error` (Error message below the field)

### State Management

`TextField` holds an internal `Observable[TextEditingValue]`. It synchronizes this internal state with any external `value` (if provided as an Observable) or `on_change` callback.

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
