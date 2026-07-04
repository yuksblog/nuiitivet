# Typography

This document defines how text typography is modeled in nuiitivet: the MD3
type-scale token system and the three-layer separation of concerns across
`TypeScaleToken`, the `Text` widget, and `TextStyle`.

See also: [SIZE_POLICY.md](SIZE_POLICY.md) (why `Icon` stays a numeric `size`
axis and is *not* coupled to the text type-scale).

## 0. The three-layer model

Every property that used to live loosely on "the text style" is assigned to
exactly one of three layers by a single litmus:

> 1. Is it an **MD3 type-scale metric**? → `TypeScaleToken`.
> 2. Does it affect **layout / wrapping inside the box**? → the `Text` widget.
> 3. Otherwise, is it a **reusable visual property**? → `TextStyle`.

| Layer | Owns | Examples |
| :--- | :--- | :--- |
| **`TypeScaleToken`** | MD3 metrics that vary *per type-scale role* | `font_size`, `line_height`, `weight`, `tracking` |
| **`Text` (widget)** | Layout / flow behavior | `alignment`, `max_lines`, `overflow`, `truncation`, `soft_wrap`, `padding`, `width`, `height` |
| **`TextStyle`** | Reusable visual look, orthogonal to role & layout | `color`, `font_family` (+ future, see §4) |

The three layers are **orthogonal**: a `TypeScaleToken` is never expanded into
`TextStyle`, and `TextStyle` never carries typography or alignment. Because
their fields never overlap, there is no precedence question when both a
`type_scale` and a `style` are supplied to a `Text` — they simply describe
different things.

```python
Text("Heading",
     type_scale=TypeScale.TITLE_MEDIUM,     # typography
     style=TextStyle(color=ColorRole.ERROR), # visual look
     alignment="center", max_lines=2)         # layout / flow
```

At paint time `Text` reads typography from `type_scale` and color from `style`;
no merged object is constructed.

## 1. `TypeScaleToken`

A type-scale role is a *structured value*, not a bare number:

```python
@dataclass(frozen=True)
class TypeScaleToken:
    font_size: float
    line_height: float   # absolute px (faithful to MD3), affects multi-line only
    weight: int          # 100-900; MD3 uses 400 (Regular) / 500 (Medium)
    tracking: float      # letter-spacing px; may be negative
```

Why structured and not a plain `int`:

* A role carries more than a size (line height / weight / tracking); `Text`
  needs the whole bundle.
* Being a struct means a token does **not** satisfy `Icon(size=...)` (a
  `SizingLike` of `int | "auto" | "%"`). The collision that would let a text
  role leak into icon sizing is blocked *at the type level*. MD3 defines no
  type-scale → icon-size mapping, and a role's font size (e.g. 16) is not an
  icon optical size (20/24/40/48).

### Overrides

Single-metric tweaks live on the token:

```python
TypeScale.TITLE_MEDIUM.copy_with(weight=700)
```

### Raw sizes without a role

When a size comes from a widget's `*Style` config (a numeric `label_font_size`,
etc.) rather than a semantic role, build a token from the size:

```python
TypeScaleToken.from_size(18)   # line_height defaults to size * 1.25
```

`from_size` still yields a full, four-field token, so the `Icon(size=...)`
guard above continues to hold.

### The 15 baseline roles

`TypeScale` exposes the MD3 2021 baseline scale as static tokens:
`(font_size, line_height, weight, tracking)`.

| Role | size | line height | weight | tracking |
| :--- | ---: | ---: | ---: | ---: |
| `DISPLAY_LARGE` | 57 | 64 | 400 | -0.25 |
| `DISPLAY_MEDIUM` | 45 | 52 | 400 | 0 |
| `DISPLAY_SMALL` | 36 | 44 | 400 | 0 |
| `HEADLINE_LARGE` | 32 | 40 | 400 | 0 |
| `HEADLINE_MEDIUM` | 28 | 36 | 400 | 0 |
| `HEADLINE_SMALL` | 24 | 32 | 400 | 0 |
| `TITLE_LARGE` | 22 | 28 | 400 | 0 |
| `TITLE_MEDIUM` | 16 | 24 | 500 | 0.15 |
| `TITLE_SMALL` | 14 | 20 | 500 | 0.1 |
| `BODY_LARGE` | 16 | 24 | 400 | 0.5 |
| `BODY_MEDIUM` | 14 | 20 | 400 | 0.25 |
| `BODY_SMALL` | 12 | 16 | 400 | 0.4 |
| `LABEL_LARGE` | 14 | 20 | 500 | 0.1 |
| `LABEL_MEDIUM` | 12 | 16 | 500 | 0.5 |
| `LABEL_SMALL` | 11 | 16 | 500 | 0.5 |

`DEFAULT_TYPE_SCALE` is `BODY_MEDIUM`; a `Text` created without an explicit
`type_scale` uses it.

> **Rendering status:** `font_size` and `line_height` are wired into layout and
> paint today. `weight` and `tracking` are defined on the token but not yet
> applied by the Skia text path — that is deferred to a follow-up. Defining all
> four fields now keeps the data model MD3-complete and avoids a future breaking
> change to the token.

## 2. Why not ambient inheritance

An earlier proposal ("ambient icon theme", issue #258) would have let an `Icon`
auto-size to adjacent text via a Flutter-`IconTheme`-style scope inherited
through the widget tree. We rejected this as the primary model:

* The framework's first-class model is **explicit parent → child** prop passing.
  Ambient inheritance (action-at-a-distance) is reserved for coarse, stable,
  cross-cutting concerns (theme, locale, text direction), e.g. `Theme.of()`.
* A *per-subtree, frequently-changing* type-scale scope is fine-grained and
  dynamic — it carries the cognitive cost of implicit context without enough
  payoff.
* "Icon matches adjacent text" is almost always inside a **composite widget**
  (list item, chip, button, nav-rail label). The natural solution is: the
  common parent takes one type-scale and hands explicit sizes to its `Text` and
  `Icon` children. Pure parent → child, no ambient scope, no sibling coupling.

Consequently `Icon` exposes **no** type-scale parameter; it keeps its numeric
`size`. Composite widgets pick the appropriate optical size internally.

## 3. Composite widgets

Material components that pair text and icon own their typography internally:

* Semantic roles are used where MD3 fixes them, e.g. dialog title →
  `HEADLINE_SMALL`, dialog content → `BODY_MEDIUM`, nav-rail collapsed label →
  `LABEL_MEDIUM`, expanded label → `LABEL_LARGE`.
* Config-driven numeric sizes (a `*Style.label_font_size`, etc.) use
  `TypeScaleToken.from_size(...)`.

Their `*Style` dataclasses keep only visual overrides (`color`, `font_family`)
in the `TextStyle` fields they expose; typography roles are fixed by the
component.

## 4. Future `TextStyle` growth

`TextStyle` is intentionally thin today (`color`, `font_family`) but will grow
with reusable visual properties that are neither type-scale metrics nor layout:

* `decoration` / `decoration_color` / `decoration_style` / `decoration_thickness`
* `shadows`, `background_color`, gradient/`foreground` fill
* `font_style` (italic), `font_features`, `font_variations`
* `word_spacing`, `text_baseline`, `locale`

Boundary cases fixed by the litmus in §0:

* **italic (`font_style`) → `TextStyle`** — MD3 roles do not define italic; it is
  orthogonal to role.
* **`word_spacing` → `TextStyle`**, but **`tracking` → `TypeScaleToken`** —
  tracking is role-defined, word-spacing is not.
