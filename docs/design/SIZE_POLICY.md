# Size Policy

This document defines how widgets determine their size (Layout) and how they draw their content within that size (Paint).

## Core Principles

1. **Separation of Layout and Paint**
    * **Layout (Allocated Rect):** Determined by the parent and the widget's `width`/`height` sizing. This defines the interaction area (hit test).
    * **Paint (Content Sizing):** Determined by how the widget fits its visual content into the Allocated Rect.

2. **No Runtime Enforcement**
    * The framework does not forbid specific sizing kinds (e.g., `weight` on Checkbox).
    * All widgets accept `fixed`, `auto`, and `weight` on both axes.
    * We rely on sensible default behaviors rather than restrictions.

3. **API Curation, Per-Axis (see Section 0)**
    * Whether a dimension is a *public constructor parameter* is decided **per axis, not per widget**, by a single binary rule derived from MD3.
    * This is curation of the public surface only — it is **not** runtime enforcement (Principle 2 still holds; the base-kernel escape hatch always works).

## 0. API Curation: Constructor Parameters vs Style

This section governs **which size dimensions a Material widget exposes as public constructor parameters**. It is a curation rule for the public API surface; it deliberately adds no clamping or validation (see Principle 2, *No Runtime Enforcement*).

### The Binary Per-Axis Rule

A dimension is decided **per axis**, using one binary test:

1. **MD3 leaves the axis open** → expose it as a public constructor parameter, named by its natural degree of freedom:
   * independently variable single axis → **semantic name** (`width`, `length`);
   * uniformly variable (1:1) → single **`size`**.
   * The parameter lives on the **constructor**, never inside `style`.
2. **MD3 fixes the axis** (spec token / size variant) → **do not** expose it; customization goes through `style` only.

### Supporting Decisions

* **Enforcement strength = "API curation only".** Public constructor params are curated by the rule above. Reaching into the inherited `width_sizing` / `height_sizing` of the base `WidgetKernel` still works as an unsupported **escape hatch**. We do **not** add clamping/ignore logic — this keeps the *No Runtime Enforcement* stance intact and costs nothing.
* **Semantic naming is a feature.** `size` / `length` / `width` communicate *how* each axis is meant to vary, instead of a generic `width`/`height` everywhere.
* **Icon stays variable.** MD3 defines multiple optical icon sizes (20/24/40/48dp), so the icon dimension is not MD3-fixed → `Icon(size=…)` remains a numeric `SizingLike` on the constructor.
* **Coupling Icon size to Text type-scale is out of scope** and was resolved *against* an ambient mechanism — see [TYPOGRAPHY.md](TYPOGRAPHY.md) §2. `Icon` exposes no type-scale param and keeps its numeric `size`; composite widgets pick optical sizes internally.

### Resulting Classification

> The authoritative list is derived by a fresh audit of every public constructor against the rule. The table below records the outcome of that audit (issue #249).

| Widget / axis | MD3 fixes it? | Exposure |
| :--- | :--- | :--- |
| Generic primitives / containers (`Box`, `Row`, `Column`, `Stack`, `*Scrollable`, `Card`, `Text`, `Image`) | No (both axes) | `width`, `height` |
| `Button.width` / `ToggleButton.width` | No | `width` |
| `Button.height` / `ToggleButton.height` | Yes (size variant) | style only |
| `IconButton` / `IconToggleButton` / `Fab` / `ExtendedFab` | Yes (square = container height / content-driven) | style only (no size param) |
| `GroupButton.width` | No | `width` |
| `StandardButtonGroup` / `ConnectedButtonGroup` | Fixed by variant (content-fit / `"wt"`) | no public size param (internal only) |
| `SplitButton.width` | No | `width` |
| `Checkbox` / `RadioButton` / `Switch` | Yes (48dp target + fixed graphic) | style only (`*Style.default_touch_target`) |
| Chips (`AssistChip` / `FilterChip` / `InputChip` / `SuggestionChip`) width | No | `width` |
| Chips height | Yes (32dp container) | style only |
| `Slider` / `CenteredSlider` / `RangeSlider` main axis | No | `length` |
| `Slider` cross axis | Yes (track/handle tokens) | style only, internal `Sizing.fixed(...)` |
| `Icon.size` | No (20/24/40/48dp) | `size` |
| `CircularProgressIndicator.size` / `LoadingIndicator.size` | No | `size` |
| `LinearProgressIndicator.width` (= length) | No (main) / thickness style | `width` |
| `SmallBadge` / `LargeBadge` | Yes (spec tokens) / width content-driven | style only (no size param) |
| `HorizontalDivider.width` / `VerticalDivider.height` | main No / cross Yes | axis-specific param only |
| `HorizontalScrollbar.width` / `VerticalScrollbar.height` (= `length`) | main No / cross Yes (`thickness`) | axis-specific `length` param only |
| `DockedToolbar` / `Horizontal`·`VerticalFloatingToolbar` | style-driven | no public size param |
| `TextField.width` | No | `width` |
| `TextField.height` | Yes (56dp) | style only |
| `MenuItem` / `SubMenuItem` height | Yes (48dp list item) | style only (`MenuStyle.item_height`) |
| `NavigationRail.width` | No (expanded 220–360) | `width` |
| `BasicDialog.width` | No (280–560) | `width` |
| `Menu` / `SideSheet` / `BottomSheet` / `StandardSideSheet` | style-fixed | no public size param |
| `Tooltip` / `RichTooltip` | container | `width`, `height` |

## 1. Layout Policy (Allocated Rect)

The **Allocated Rect** is the space assigned to the widget by its parent during the layout pass.

* **Control:** Controlled by `width` and `height` parameters (Sizing).
* **Weight Behavior:** If `width="wt"` (or `height="wt"`) is specified, the widget's Allocated Rect **always expands** to fill the available space provided by the parent.
* **Hit Testing:** The **entire Allocated Rect** is hit-testable.
  * This ensures that expanding a widget (e.g., for easier touch access) works as expected, even if the visual content remains small.

## 1.1 Weight Semantics: A Share of the Leftover Space

`weight` is a share of the space **left over** on an axis, in the spirit of WPF's star (`*`) sizing. The string form is `"wt"` for weight 1 and `"wt<n>"` for anything else — `parse_sizing("wt2")` returns `Sizing.weight(2)`.

The rule for an axis is:

1. `fixed` and `auto` children are given the space they ask for.
2. Whatever remains is split among the `weight` children **in proportion to their weights**.

Two consequences follow:

* **A lone weight child fills the axis, whatever its weight.** With no weight sibling to share with, it receives the entire remainder, so `"wt"` and `"wt2"` are *identical* for an only child. This holds in `Row`, `Column`, `Grid`, `Stack`, and for overlay-presented content (a `Stack` child overlaps its siblings rather than sharing an axis with them, so it is always the sole claimant; the same is true of overlay content).
* **A weight is not a fraction of the parent.** `Row([a, b])` with `a="wt"` and `b="wt3"` gives `a` a quarter of the row and `b` three quarters — the weights are normalized against each other, not against any fixed total. Adding a `fixed` sibling changes what "the remainder" is, but not the ratio between `a` and `b`.

To size a widget to a genuine fraction of its parent, use a number (`height=300`); there is no fraction-of-parent spec.

> A percentage spelling (`"50%"`) existed until #510. It was never a fraction of the parent — it parsed to a weight and the `%` was discarded — and reading it as a percentage was the most common misunderstanding of this system. It now raises `ValueError`.

## 1.2 Composable Wrappers Are Transparent to Layout Metadata

For the layout metadata a parent reads from a child — `width_sizing` /
`height_sizing` and the alignment hints `layout_align` / `cross_align` — a
`ComposableWidget` resolves each value by one rule:

> **A declared value wins; an undeclared one is derived from the widget that
> `build()` returned.**

So extracting a subtree into a composable does not change how the tree lays out.

* Sizing tracks declaration explicitly: an explicit `"auto"` is a declaration
  and pins the intrinsic size — the opt-out from derivation. For the alignment
  hints, `None` is "undeclared".
* Before `build()` has run (pre-mount intrinsic measurement), the wrapper
  reports its own defaults; `preferred_size` measures the built subtree
  directly, so intrinsic sizes stay correct.
* Scope fragments (`render_scope`) never declare metadata of their own, so they
  are always fully transparent.

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
| **Checkbox** | **`contain`** | **Scales with the rect.** <br> If `width` is default (fixed), it looks standard. If `width="wt"` or large fixed size, the checkbox graphic expands. |
| **Radio** | **`contain`** | Same as Checkbox. |
| **Icon** | **`contain`** | **Scales with the rect.** <br> Vector icons are resolution-independent and often resized. |
| **Button Family** | (Container) | **Includes Button, IconButton, FAB.** <br> They act as containers. They fill the Allocated Rect and align their content (Text/Icon) inside. |
| **Image** | `contain` | (Future) Will support explicit `fit` parameter. Default is `contain`. |

### Rationale for Checkbox `contain`

While many frameworks default to `none` (fixed size) for Checkboxes to enforce design consistency (preventing accidental resizing), we chose `contain` as the default to prioritize **intuitiveness**.

1. **Intuitive:** If a user explicitly sets `width="wt"` or `width=100`, they likely intend to resize the widget. We respect this intent over enforcing design constraints.
2. **Safe Default:** The default `width` for Checkbox is `fixed` (standard size), so it appears standard-sized unless explicitly changed. This provides a "guardrail" for quality while allowing freedom.
3. **Consistency:** It aligns with `Icon` and `Image` behavior, simplifying the mental model.
4. **Vector Rendering:** Unlike legacy bitmap-based controls, our vector-based rendering ensures the checkbox remains crisp at any size.
