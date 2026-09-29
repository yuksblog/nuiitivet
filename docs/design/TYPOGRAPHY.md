# Typography

Text is described by three objects that never overlap: a `TypeScaleToken` for
the MD3 metrics, the `Text` widget for layout inside its box, and a
`TextStyle` for the reusable look. Why `Icon` stays a numeric `size` and is
not coupled to the type scale is in [SIZE_POLICY.md](SIZE_POLICY.md).

## The Three Layers

Every property lands in exactly one layer, by one test:

> 1. An **MD3 type-scale metric** → `TypeScaleToken`.
> 2. Affects **layout or wrapping inside the box** → the `Text` widget.
> 3. Otherwise a **reusable visual property** → `TextStyle`.

| Layer | Owns | Examples |
| :--- | :--- | :--- |
| `TypeScaleToken` | Metrics that vary per type-scale role | `font_size`, `line_height`, `weight`, `tracking` |
| `Text` | Layout and flow | `alignment`, `max_lines`, `overflow`, `truncation`, `soft_wrap`, `padding`, `width`, `height` |
| `TextStyle` | Look, orthogonal to role and layout | `color`, `font_family` |

Because the fields never overlap there is no precedence question when a `Text`
receives both a `type_scale` and a `style`; they describe different things, and
at paint time `Text` reads typography from one and colour from the other with
no merged object in between. A `TypeScaleToken` is never expanded into a
`TextStyle`, and a `TextStyle` never carries typography or alignment.

Two boundary cases fixed by the test: italic goes to `TextStyle`, because no
MD3 role defines it; `word_spacing` would go to `TextStyle` while `tracking`
is on the token, because tracking is role-defined and word spacing is not.

## The Token Is a Struct

A type-scale role is a structured value, four metrics, not a bare font size.
`Text` needs the whole bundle, and the struct blocks a collision at the type
level: a token does not satisfy `Icon(size=...)`, whose `SizingLike` is
`int | "auto" | "wt"`, so a text role cannot leak into icon sizing. MD3
defines no mapping from a type-scale role to an icon size, and a role's font
size (16) is not an icon optical size (20/24/40/48).

`TypeScale` exposes the MD3 baseline roles as static tokens, and a `Text`
without a `type_scale` uses `BODY_MEDIUM`. A size that comes from a widget's
`*Style` config rather than a role is wrapped by `TypeScaleToken.from_size`,
which still yields a full token, so the `Icon(size=...)` guard holds there
too. All four metrics reach the Skia text path; `tracking` is applied in width
and ink measurement as well as paint, so wrapping and ellipsis agree with what
is drawn.

## Why Not Ambient Inheritance

An ambient icon theme, a Flutter `IconTheme`-style scope through which an
`Icon` sizes itself to the adjacent text, was rejected as the primary model.
The framework's first-class model is explicit parent-to-child passing;
ambient inheritance is reserved for coarse, stable, cross-cutting values
(theme, locale, text direction). A per-subtree type-scale scope is
fine-grained and changes often, so it carries the cost of implicit context
without the payoff. And "icon matches adjacent text" almost always happens
inside a composite widget, a list item, a chip, a button, a rail label, where
the common parent takes one type scale and hands explicit sizes to its `Text`
and `Icon` children with no sibling coupling.

`Icon` therefore exposes no type-scale parameter and keeps its numeric `size`.

## Composite Widgets

A Material component that pairs text and icon owns its typography. Where MD3
fixes the role it uses the role: a dialog title is `HEADLINE_SMALL`, dialog
content `BODY_MEDIUM`, a collapsed rail label `LABEL_MEDIUM` and an expanded
one `LABEL_LARGE`. A config-driven numeric size (`*Style.label_font_size`)
goes through `TypeScaleToken.from_size`. The `TextStyle` fields a `*Style`
exposes carry visual overrides only, `color` and `font_family`; the role is
fixed by the component.
