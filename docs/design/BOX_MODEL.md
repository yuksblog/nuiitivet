# Box Model

One vocabulary connects layout (the allocated rect), padding (the content
rect), hit testing (the interactive bounds) and visual overflow (outsets). It
holds for widgets, layout containers and modifiers alike.

## Rects

A widget is painted with an **allocated rect**, the `(x, y, width, height)` its
parent hands to `paint()`. Its **padding** insets that to the **content rect**.
Separately, it may report **outsets**: paint-only expansion past the allocated
rect, such as a shadow or a focus ring.

```text
visual bounds (allocated + outsets)
┌──────────────────────────────────┐
│  allocated rect                  │
│  ┌────────────────────────────┐  │
│  │ padding                    │  │
│  │  ┌──────────────────────┐  │  │
│  │  │ content rect         │  │  │
│  │  └──────────────────────┘  │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

## Padding

`Widget.padding` always means: allocated rect to content rect.

Every widget that occupies a rect has `padding`, and it is included in
`preferred_size`. Exempt are widgets that occupy no rect of their own — a
provider that lifts its children into the parent (`ForEach`), a descriptor
rendered by another widget (`RailItem`) — and hosts whose rect is whatever the
parent hands them (`Navigator`, `Overlay`, the app and window scopes).

What the widget draws goes inside the content rect. For a leaf (`Text`,
`Icon`, `Divider`) and for a component that draws its own boundary (`Button`,
`Fab`, `Chip`), the padding band is therefore transparent, and it reads as
outer space. That is the intended behaviour, not a side effect:
`Fab(padding=24)` is `Container(padding=24, child=Fab(...))` one node lighter,
and a `Box` wrapping either paints the whole allocated rect, so the same band
reads as inner padding there. Which one it "is" depends on who draws the
boundary, never on the widget class.

Two layers own two different insets, and they never share a property:

| Layer | Owner | Meaning |
| --- | --- | --- |
| Box model | `Widget.padding` | allocated rect → content rect |
| MD3 spec | `*Style.content_insets` (and the other spec tokens) | container edge → content, inside the component |

M3 internal spacing (button label insets, menu vertical inset, dialog inset)
is component-internal layout: it lives on an inner node or on a style field
named for what it is, never on the component's own `Widget.padding`. A
component's visual container (background, border, state layer, focus ring)
sits inside the padding. Its MD3 touch target (`min_width` / `min_height`) is
part of the container's rect, not of the padding.

## Hit Testing

**Interactive bounds** are what receives pointer events. **Visual bounds** are
what may be drawn, overflow included. The two are decided separately.

### Default: the allocated rect

A layout box or a leaf has no boundary of its own, so its padding is part of
what the user sees as "the widget". Hit-testing the content rect there would
make a band that is visible but not clickable.

### Own boundary: the content rect

A component that draws its own boundary (`InteractiveWidget` and its
subclasses) hit-tests on the content rect. Its padding is a transparent band
outside the container; a `Fab(padding=24)` that answered clicks across the
band would be a 104px target showing a 56px circle. The MD3 touch target is
inside the content rect (the container is floored at `min_width` /
`min_height`), so it is unaffected.

### Visible region: a viewport and a clip are one concept

A widget or modifier may define a **visible region** that constrains its
subtree. The **effective visible region** is the intersection of all ancestor
visible regions. Descendants receive no pointer events outside it, and when
clipping is on they are not drawn outside it either. A scroll viewport clamps
hit testing to its viewport rect; a `Clip` clamps drawing and hit testing to
its shape.

One rule serves `ScrollViewport`, `Clip` and a future `Mask` / `ClipPath`, so
none of them is a special case. It constrains the subtree only; it changes
nothing about padding, content or outsets, and with no visible region the
allocated rect stays the interactive bound.

## Outsets: Visual Overflow Only

Outsets are not part of layout and not part of hit testing. They exist so that
a paint cache does not clip a shadow, so that a container can skip painting a
child whose visual bounds lie outside the canvas clip, and so that shadows,
focus rings and overlays extend past the allocated rect naturally.

The second point makes `paint_outsets()` a contract, not a hint: a widget that
draws outside its allocated rect — a shadow, a focus ring, a paint-time
translation or scale — must report the overflow, or a container may decide it
cannot be seen and never call its `paint()`. Outsets are reported per widget,
not per subtree; a small slack band around the clip covers the ordinary case
of a grandchild's shadow.

Visual overlap is allowed by default: an outset may cover a neighbouring
widget. Coupling layout or hit testing to a visual effect was rejected, and
most UIs accept a shadow or a focus ring crossing into the next element. Where
overlap is unwanted, the fix is layout space (`gap`, the parent's `padding`)
or an explicit clip at the right boundary (a card surface, a scroll viewport).
Outsets are never treated as spacing, and hit testing is never expanded to
match them.
