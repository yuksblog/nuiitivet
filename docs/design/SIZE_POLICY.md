# Size Policy

This document defines how widgets determine their size (Layout) and how they draw their content within that size (Paint).

## Core Principles

1. **Separation of Layout and Paint**
    * **Layout (Allocated Rect):** Determined by the parent and the widget's `width`/`height` sizing. This defines the interaction area (hit test).
    * **Paint (Content Sizing):** Determined by how the widget fits its visual content into the Allocated Rect.

2. **No Runtime Enforcement**
    * The framework does not forbid specific sizing kinds (e.g., `flex` on Checkbox).
    * All widgets accept `fixed`, `auto`, and `flex` on both axes.
    * We rely on sensible default behaviors rather than restrictions.

## 1. Layout Policy (Allocated Rect)

The **Allocated Rect** is the space assigned to the widget by its parent during the layout pass.

* **Control:** Controlled by `width` and `height` parameters (Sizing).
* **Flex Behavior:** If `width="flex"` (or `height="flex"`) is specified, the widget's Allocated Rect **always expands** to fill the available space provided by the parent.
* **Hit Testing:** The **entire Allocated Rect** is hit-testable.
  * This ensures that expanding a widget (e.g., for easier touch access) works as expected, even if the visual content remains small.

## 2. Content Policy (Paint)

Once the Allocated Rect is determined, the widget decides how to draw its content. This is conceptually controlled by a **Content Mode** (often called `fit`).

`fit` and `content_alignment` are primarily discussed as *paint concepts*.
Some widgets may expose them as explicit parameters (e.g., Image in the future), while others do not.
Even when not exposed (e.g., Checkbox/Radio/Icon), the widget still behaves as if it had these settings via internal defaults.

### Content Modes (`fit`)

* **`contain` (Scale to Fit):**
  * Scales the content to the largest size that fits within the Allocated Rect while preserving aspect ratio.
  * Used when the user intends to resize the graphic (e.g., Icon, Image).
* **`none` (Fixed / Center):**
  * Draws the content at its intrinsic size (e.g., 24dp Icon, 18dp Checkbox graphic), usually centered.
  * Does not scale even if the Allocated Rect is large.
* **`cover`:**
  * Scales the content to fill the Allocated Rect, cropping if necessary (preserving aspect ratio).
* **`fill` (Stretch):**
  * Stretches the content to fill the Allocated Rect (ignoring aspect ratio).

### Content Alignment

If the content does not fill the Allocated Rect (e.g., `fit="contain"` with aspect ratio mismatch, or `fit="none"`), `content_alignment` determines where the content is drawn (default: `center`).

## 3. Widget Specific Behaviors (Defaults)

We define default behaviors to match intuitive expectations.

| Widget | Default `fit` | Behavior Description |
| :--- | :--- | :--- |
| **Checkbox** | **`contain`** | **Scales with the rect.** <br> If `width` is default (fixed), it looks standard. If `width="flex"` or large fixed size, the checkbox graphic expands. |
| **Radio** | **`contain`** | Same as Checkbox. |
| **Icon** | **`contain`** | **Scales with the rect.** <br> Vector icons are resolution-independent and often resized. |
| **Button Family** | (Container) | **Includes TextButton, IconButton, FAB.** <br> They act as containers. They fill the Allocated Rect and align their content (Text/Icon) inside. |
| **Image** | `contain` | (Future) Will support explicit `fit` parameter. Default is `contain`. |

### Rationale for Checkbox `contain`

While many frameworks default to `none` (fixed size) for Checkboxes to enforce design consistency (preventing accidental resizing), we chose `contain` as the default to prioritize **intuitiveness**.

1. **Intuitive:** If a user explicitly sets `width="flex"` or `width=100`, they likely intend to resize the widget. We respect this intent over enforcing design constraints.
2. **Safe Default:** The default `width` for Checkbox is `fixed` (standard size), so it appears standard-sized unless explicitly changed. This provides a "guardrail" for quality while allowing freedom.
3. **Consistency:** It aligns with `Icon` and `Image` behavior, simplifying the mental model.
4. **Vector Rendering:** Unlike legacy bitmap-based controls, our vector-based rendering ensures the checkbox remains crisp at any size.
