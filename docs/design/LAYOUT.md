# Layout System Design

## Overview

See [BOX_MODEL.md](BOX_MODEL.md) for the single source of truth on rect terminology (allocated/content), hit testing rules, and visual overflow (outsets).

The layout system of this framework is expressed by the Widget tree structure itself.
It aims for intuitive control through properties and composition, rather than external stylesheets or complex constraint systems.

## Core Principles

### 1. Spacing: Padding & Gap (No Margin)

Spacing control between Widgets is unified under `padding` and `gap`. `margin` (outer spacing) is not used.

* **Padding (Inner Spacing)**
    * All Widgets have a `padding` property.
    * It controls the space between the content and the boundary (Border/Background).

* **Gap (Spacing Between Children)**
    * Containers with multiple children (`Row`, `Column`, etc.) have a `gap` property.
    * It inserts a consistent interval between child Widgets.

* **Flow 2-axis Gap**
    * Multi-run layouts (`Flow`) have `main_gap` and `cross_gap` in anticipation of future `direction` additions.
        - `main_gap`: Interval within a run (main direction).
        - `cross_gap`: Interval between runs (cross direction).
    * Equivalent to CSS `gap` / `row-gap` / `column-gap` or Flutter's `Wrap(spacing, runSpacing)`.

* **Grid row/column Gap**
    * 2D layouts (`Grid`) have fixed axes, so they use `row_gap` and `column_gap`.
        - `row_gap`: Interval between rows (Y direction).
        - `column_gap`: Interval between columns (X direction).
    * Shares the same intent as CSS `row-gap` / `column-gap`.

* **Why No Margin?**
    * Having both `margin` and `padding` causes confusion about which to use.
    * Allowing components to have "outer spacing" compromises reusability (the required outer spacing changes depending on the context).
    * If spacing is needed, use the parent container's `gap`, the parent's `padding`, or a transparent `Spacer` Widget.

### 2. Sizing System

Widget sizes are abstracted by the `Sizing` type and specified via `width` and `height` properties.

#### Sizing Types

* **`fixed(value)`**: Fixed pixel value.
* **`auto`**: Size determined by content (Intrinsic size).
* **`flex(weight=1.0)`**: Fills available space (remaining space) of the parent.
    - Equivalent to Flexbox's `flex-grow`.
    - If multiple `flex` elements exist, space is distributed according to the `weight` ratio.
    - Specifying a string like `"50%"` is interpreted as `flex(50.0)`.
        - Note: This is treated as "weight 50", not an absolute size of "50% of parent." If all siblings use `%`, they will be proportional, but if fixed-size elements are mixed in, the allocation is relative to the "remaining space."

#### Grid: Room Allocation and Fill

Note: The responsibility of `Grid` is "room allocation" (determining rows, columns, areas, and the allocated rect for each cell).
How the allocated room is used (intrinsic or full fill) is decided by the child Widget's `width` / `height` (`Sizing`).

Example: To fill a cell, explicitly specify `Sizing.flex(1)`.

```python
cell = MaterialContainer(
    Text("Cell"),
    width=Sizing.flex(1),
    height=Sizing.flex(1),
)
```

#### The `size` Parameter (Specific Widgets)

Widgets where being square is essential (like `Icon` or `Checkbox`) provide `size` as an initialization parameter.

* **Purpose**: Enforces an aspect ratio (1:1) and prevents inconsistency between `width` and `height`.
* **Behavior**:
    - Takes `size` at initialization and internally sets both `width` and `height` to the same value.
    - These Widgets typically do not accept separate `width` / `height` arguments in their constructors.

### 3. Alignment: Parent's Responsibility

Alignment follows the principle that it is the "parent Widget's" responsibility, not the child Widget's.

#### Single Child Container

Widgets with a single child (`Container`, etc.) use the `alignment` property.

* **Values**
    - 9-point alignment:
        - `top-left`, `top-center`, `top-right`
        - `center-left`, `center`, `center-right`
        - `bottom-left`, `bottom-center`, `bottom-right`

Note: Alignment only determines the positioning. To fill the space, specify `width` / `height` (e.g., `Sizing.flex(...)`).

Note: The term `alignment` can mean different things. CSS-related (`align-*` / `justify-*`) sometimes includes the concept of "stretch" (absorbing excess space), but this framework adopts a GUI-centric approach where alignment consistently means "positioning only."

#### Multi Child Container

Widgets with multiple children (`Row`, `Column`, etc.) use Flexbox-like alignment control.

* **`main-alignment` (Main axis)**
    - `start`, `center`, `end`
    - `space-between`, `space-around`, `space-evenly`
* **`cross-alignment` (Cross axis)**
    - `start`, `center`, `end`

### 4. Overflow Strategy

**Overflow** occurs when a child Widget's painted content or layout size exceeds the area (bounds) allocated by its parent.
While overflow control generally includes Visible, Clip, or Scroll, this framework defaults to **Visible** based on the following design philosophy.

* **Default: Visible**
    - By default, content is rendered as-is even if it overflows the bounds (not clipped).
    - **Design Rationale**:
        - **Web Standard Alignment**: Matches the CSS default `overflow: visible`.
        - **Fail Loudly**: With the Sizing system, content shouldn't overflow under normal circumstances. Overflow indicates a layout design bug; keeping it visible makes bugs easier to notice and fix than silent clipping.
        - **Design Freedom**: Visual effects like shadows or focus rings often naturally overflow parent boundaries.
        - **Role of Modifiers**: `Clip` (visual effect) and `Scroll` (functional addition) are the responsibilities of Modifiers; default Widgets should render plainly.
        - **Performance First**: Clipping operations (`saveLayer` / `clipRect`) are expensive. Defaulting to Visible maximizes framework performance.

* **Handling Overflow**
    - **Clipping**: Use the `Clip` Modifier when visual truncation is required.
    - **Scrolling**: Use the `Scroll` Modifier when scrolling within a region is needed.

### 5. Role of Modifiers in Layout

**Modifiers** wrap existing Widgets to add capabilities or visual effects. See [MODIFIER.md](MODIFIER.md) for detailed design.

* **Principle: Layout is Property-driven**
    - Layout (size, spacing, alignment) is controlled via Widget-own properties (`width`, `height`, `padding`, `alignment`).
    - Avoid directly changing layout size or alignment via Modifiers.

## Window (App) Sizing / Positioning

The `width` / `height` of the `App` (OS window) is distinct from Widget `Sizing`.

* Window `width` / `height` is treated as `WindowSizing` (or `WindowSizingLike`).
    - Accepts fixed **px** values or `"auto"` (preferred size).
* `"50%"`-style specification is **not supported** (as it conflicts with the meaning of Widget `Sizing.flex(...)`).

Window positions are specified using 9-point Alignment vocabulary.

* Specified like `WindowPosition.alignment("bottom-center", offset=(0, -24))`.
* `offset` is applied after alignment.
    - Units in px.
    - Coordinate system matches the UI: $+x$ is right, $+y$ is down.
