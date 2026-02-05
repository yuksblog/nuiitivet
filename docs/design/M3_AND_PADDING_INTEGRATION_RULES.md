# Integration Rules for M3 Specs and Framework Padding

See [BOX_MODEL.md](BOX_MODEL.md) for the single source of truth on `padding`, hit testing, and visual overflow (`outsets`).

## Essence of the Problem

**M3 does not have the concept of `padding` or `margin` in the CSS sense.**

In the M3 specification, the sizes of each component are defined as:

- **Touch Target** (Interaction area)
- **Container Size** (Visual container)
- **Content Size** (Internal content)
- **State Layer** (Feedback area)

However, the terms **"padding" or "margin" are not used**.

## Actual Representation in M3

### Example 1: Button (M3 Specs)

```text
Container height: 40dp
Horizontal padding: 24dp (Distance between internal text and container edge)
Minimum width: 48dp (Touch target)
```

→ M3 calls it "padding," but this refers to the **content layout within the container**.

### Example 2: Checkbox (M3 Specs)

```text
Container: 18×18dp (Icon)
State layer: 40×40dp (Circular)
Minimum touch target: 48×48dp
```

→ The word "padding" is not used; **the sizes for each layer are defined independently**.

### Example 3: List Item (M3 Specs)

```text
Container height: 56dp
Leading element: 24×24dp icon
Content padding: 16dp (From leading/trailing edge)
Spacing between icon and text: 16dp
```

→ "Padding" is used as an **internal sequence rule for placing content**.

## Implicit Rules of M3

An implicit hierarchical structure exists in M3:

```text
Component (Total component area)
├─ Touch Target (Minimum 48×48dp, Interaction area)
├─ Container (Visual boundary)
├─ State Layer (Hover/Press feedback)
└─ Content (Internal content)
    └─ Internal Spacing/Padding (Content placement)
```

**Important**: These are all part of the **internal structure of the component** and are **independent of external layout**.

## Meaning of `padding` in the Framework

In our framework:

```python
Widget(padding=...)
```

This is a **feature of the Widget base class**, having two interpretations:

### Interpretation A: Internal Padding (Container-like)

```text
┌─────────────────────────────┐
│ Widget Boundary             │
│  ┌─────────────────────┐    │
│  │ padding (Inner space) │    │
│  │  ┌───────────────┐  │    │
│  │  │   Content     │  │    │
│  │  └───────────────┘  │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

→ Corresponds to M3's "content placement within a Container."

### Interpretation B: Appears as "Outer Margin" (Common Misconception)

```text
┌─────────────────────────────┐
│ Parent Layout               │
│  ┌─────────────────────┐    │
│  │ padding (insets)    │    │
│  │  ┌───────────────┐  │    │
│  │  │   Widget      │  │    │
│  │  │   Boundary    │  │    │
│  │  └───────────────┘  │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

→ M3 has no corresponding concept (however, Framework `padding` is not margin).
- `padding` itself is the `allocated` → `content` insets.
- Depending on the painting/hit testing rules of a leaf widget, it may look or behave like "outer margin."

## Proposal: 2-Layer Model

### Rule 1: M3 Component = Self-contained Internal Structure

Each M3 component (Button, Checkbox, etc.) is a **closed unit with an internal structure**.

```python
# M3 components have "M3-spec sizes"
Checkbox(size=48)  # M3's "48dp touch target"
Button(height=40)  # M3's "40dp container height"
```

→ These are **M3-spec parameters** and are unrelated to `padding`.

### Rule 2: Widget.padding = allocated → content insets

`Widget.padding` represents the **insets used to derive the content rect from the allocated rect**.

Note: In leaf widgets, this can appear as "outer margin."

- If the visual painting (e.g., no background) is aligned with the content rect, the padding area often appears visually blank.
- However, since hit testing is (generally) based on the `allocated rect`, the padding area may still be part of the touch target.

```python
# M3 component + Framework layout adjustment
Checkbox(size=48, padding=10)
#        ^         ^
#        M3 spec   insets (padding)
```

**Illustration**:

```text
┌─────────────────────────────────────┐
│ Widget (Included in preferred_size)   │
│  ┌─────────────────────────────┐    │
│  │ padding=10 (insets)         │    │
│  │  ┌───────────────────────┐  │    │
│  │  │ M3 Component          │  │    │
│  │  │ (size=48)             │  │    │
│  │  │  - Touch Target       │  │    │
│  │  │  - State Layer        │  │    │
│  │  │  - Icon               │  │    │
│  │  └───────────────────────┘  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
preferred_size = 48 + 10*2 = 68dp
```

### Rule 3: M3 Internal Structure is Auto-calculated

The internal structure of M3 components (Icon/State Layer/Touch Target) is **calculated automatically according to M3 specs**.

```python
class Checkbox(Widget):
    def __init__(self, size=48, padding=0, ...):
        super().__init__(width=size, height=size, padding=padding)
        
        # Internal structure per M3 spec (not touched by user)
        self._touch_target = size              # 48dp
        self._state_layer = size * (40/48)     # 40dp (M3 ratio)
        self._icon_size = size * (18/48)       # 18dp (M3 ratio)
    
    def preferred_size(self):
        # M3 size + padding
        l, t, r, b = self.padding
        return (self._touch_target + l + r,
                self._touch_target + t + b)
    
    def paint(self, canvas, x, y, width, height):
        # Apply padding to get content area
        cx, cy, cw, ch = self.content_rect(x, y, width, height)
        
        # Place M3 component within content area
        # (Draw M3 internal structure here)
        self._paint_m3_component(canvas, cx, cy, cw, ch)
```

## Unified Rule Definition

### ✅ Adopted Rules

**`Widget.padding` = `allocated` → `content` insets (Common to all Widgets)**

1. **M3-spec parameters**: `size`, `height`, `width`, etc.
    - Follows official M3 specifications.
    - Defines internal component structure.

2. **Framework padding**: `padding` parameter.
    - `allocated` → `content` insets.
    - Included in `preferred_size()` (as a result, may behave as "surrounding space" in the layout).

3. **M3 internal structure**: Auto-calculated.
    - Touch Target, State Layer, Icon, etc.
    - Calculated automatically using M3 ratios.
    - Usually not something users need to worry about.

### Implementation Patterns

#### Pattern 1: Fixed-size Widget (Checkbox, Icon)

```python
class Checkbox(Widget):
    def __init__(self, size=48, padding=0, ...):
        # M3: size = Touch Target
        # Framework: padding = allocated→content insets
        super().__init__(width=size, height=size, padding=padding)
        self._m3_size = size
    
    def preferred_size(self):
        l, t, r, b = self.padding
        return (self._m3_size + l + r, self._m3_size + t + b)
```

#### Pattern 2: Variable-size Widget (Button)

```python
class Button(Widget):
    def __init__(self, label, padding=0, ...):
        # M3: Internal padding (24dp horizontal) is a separate parameter
        # Framework: padding = allocated→content insets
        super().__init__(padding=padding)
        self._m3_horizontal_padding = 24  # M3 Internal
        self._m3_height = 40              # M3 Spec
    
    def preferred_size(self):
        # M3: text width + M3 internal padding
        text_w = self._measure_text()
        m3_width = text_w + self._m3_horizontal_padding * 2
        m3_height = self._m3_height
        
        # Framework: M3 size + padding
        l, t, r, b = self.padding
        return (m3_width + l + r, m3_height + t + b)
```

#### Pattern 3: Layout Widget (Column, Row)

```python
class Column(Widget):
    def __init__(self, children, spacing=0, padding=0, ...):
        # M3: Not applicable (Layout is a framework feature)
        # Framework: padding = Inner padding before placing children
        super().__init__(padding=padding)
        self._spacing = spacing  # Spacing between children
    
    def preferred_size(self):
        # Size of children + spacing
        children_size = self._calculate_children_size()
        
        # Framework: children + padding
        l, t, r, b = self.padding
        return (children_size.w + l + r, children_size.h + t + b)
```

## Terminology Cleanup

### M3 Term → Framework Term Mapping

| M3 Term | Framework Term | Description |
| -------- | --------------- | ------ |
| Container size | `size`, `width`, `height` | Size of the M3 component |
| Content padding (Internal) | M3 Parameter or Auto-calculated | Internal layout within the component |
| Touch target | M3 Parameter (usually `size`) | Interaction area |
| State layer | Auto-calculated | Determined using M3 ratios |
| Spacing (between items) | `spacing` | Distance between child elements |
| **(N/A)** | `padding` | `allocated` → `content` insets (may appear as visual surrounding space) |

### Important Distinction

```python
# ❌ Concept that does not exist in M3
m3_component.margin = ...  # No margin in M3

# ✅ Concept added in the Framework
widget.padding = ...  # allocated→content insets

# ✅ M3 Concepts
m3_component.size = 48           # Touch target (M3 spec)
m3_component.container_height = 40  # Container (M3 spec)
```

## Specific Example: Checkbox

### M3 Specification

```text
Touch target: 48×48dp (minimum)
State layer: 40dp diameter
Icon: 18×18dp
```

### Framework Implementation

```python
Checkbox(
    size=48,      # M3: Touch target
    padding=0,    # Framework: insets (default)
)

# preferred_size() = 48×48 (M3 size)
# Internal structure:
#   touch_target = 48dp (size)
#   state_layer = 40dp (Auto-calculated: 48 * 40/48)
#   icon = 18dp (Auto-calculated: 48 * 18/48)
```

### When Layout Adjustments are Needed

```python
Checkbox(
    size=48,       # M3: Touch target
    padding=10,    # Framework: insets
)

# preferred_size() = 68×68 (48 + 10*2)
# M3 internal structure remains drawn within a 48dp region.
# Insets shrink the content rect, which may result in visual surrounding blank space.
```

## Summary: Unified Rules

### ✅ Decisions

1. **M3-spec parameters (`size`, `width`, `height`, etc.)**
    - Defines the **internal structure** of the M3 component.
    - Follows official M3 specifications.
    - Independent of `padding`.

2. **Framework padding**
    - `allocated` → `content` insets (a concept that does not exist in M3).
    - Included in `preferred_size()`.
    - Default value is `0`.

3. **Terminology usage**
    - "M3 internal padding" → M3-spec parameter or auto-calculated.
    - "Widget padding" → `allocated` → `content` insets.

4. **Implementation Policy**
    - M3 components are self-contained.
    - `padding` is common to all Widgets as `allocated` → `content` insets.
    - Layout Widgets (Column/Row) use `padding` as internal spacing.

### 🎯 Guaranteeing Consistency

```python
# Unified across all Widgets
Column(padding=10)      # Inner spacing before child placement
Row(padding=10)         # Inner spacing before child placement
Text(padding=10)        # Surrounding space for text
Checkbox(padding=10)    # allocated→content insets (appears as surrounding space in leaf)
Icon(padding=10)        # allocated→content insets (appears as surrounding space in leaf)
Button(padding=10)      # allocated→content insets
```

**Meaning**: Unified under "spacing included in `preferred_size`."

**M3 internal structure**: Managed independently by each Widget (independent of `padding`).

## Prep Checklist for the Future

To ensure smooth MD3 compliance, prepare the following before starting implementation.

### 1) Define Target Widgets

- Widget name (e.g., Switch / Radio / Slider / ListItem, etc.)
- Variant (e.g., Filled/Outlined, Small/Medium/Large, etc.)
- Platform differences (Differences between Android/iOS/Web, if any)

### 2) MD3 Specification Data (Numbers)

At a minimum, collect the following numbers for each variant:

- Touch target (Minimum size)
- Container size (Height/Width, Shape)
- Content insets (leading/trailing/top/bottom)
- Icon/indicator size
- Gap/spacing (Between elements)
- State layer (Size, shape, display conditions)
- Typography (Font size, line height, weight, etc.)

Note:
- M3's "padding" generally refers to the **layout of content within a Container**.
- Framework `Widget.padding` is treated as `allocated` → `content` insets (per BOX_MODEL rules).

### 3) State-specific Differences (Visuals and Input)

- enabled / disabled
- hovered / pressed
- focused (Presence of focus ring/outline, whether it's an outset)
- selected / checked / indeterminate

Specify whether "the size changes" or "only the rendering changes" for each state.

### 4) Rule Integration (Mapping to BOX_MODEL)

- Preferred size: Does it meet the touch target? (e.g., min 48)
- Paint: Where is the container drawn? (e.g., centered as 40 within 48)
- Hit test: Is it based on the allocated rect? (Exception: viewport/clip)
- Outsets: Are shadows/focus/overlays treated as outsets? (Not included in layout/hit test)

### 5) Theme / Style Design

- Tokens to include in `*Style` (e.g., `container_height`, `content_insets`, `spacing`, `min_height`)
- Whether to reference via `ThemeData` or allow overrides via Widget arguments.
- Changes where breaking existing Styles/APIs is acceptable (do not consider backward compatibility).

### 6) Acceptance Criteria (Testing Perspective)

- Expected `preferred_size` (Fixed value or range)
- Ensure `padding` is included in `preferred_size`.
- Ensure `hit_test` follows the `allocated rect`.
- Ensure visible region constraints of clip/viewport are not broken.

If possible, prepare visual verification samples in `src/samples/*_demo.py` simultaneously.

## Template: From Specification to Implementation

In the future, fill out this template to turn a task into an implementation task.

### Widget: <NAME>

#### MD3 Spec (per variant)

| Variant | Touch target | Container | Insets (L/T/R/B) | Icon | Gap | Font | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| default | 48x48 | 40h | 16/0/16/0 | 20 | 8 | 14 | |

#### State differences

- disabled:
- hovered:
- pressed:
- focused:
- selected:

#### Framework mapping

- `Widget.padding`:
- `preferred_size`:
- `paint` (container placement):
- `hit_test`:
- `outsets`:

#### Style/Theme tokens

- Style fields to add/update:
- ThemeData wiring:

#### Tests / Demo

- Tests to add/update:
- Demo to add/update:
