# Layout System Design

The layout is the widget tree itself. A widget's size, spacing and alignment
are its own properties, and a container places its children by its own. There
is no stylesheet and no constraint solver. The rect vocabulary (allocated
rect, content rect, outsets) is defined in [BOX_MODEL.md](BOX_MODEL.md).

## Spacing: Padding and Gap, No Margin

`padding` is the inset from a widget's allocated rect to its content rect.
`gap` is the interval a container inserts between its children. There is no
`margin`.

Leaving margin out does not forbid outer space. It means there is exactly one
property for insets, so the reader never chooses between margin and padding.
Space between siblings is the parent's `gap`; space around the whole group is
the parent's `padding`; an adjustment to one element is that element's own
`padding`. A widget that draws its own boundary draws it inside the padding,
so its padding reads as outer space. This is the shape of SwiftUI's
`.padding()`, which has no margin either.

## Sizing

A widget asks for space on each axis with a `Sizing`: `fixed`, `auto` or
`weight`. `weight` is a share of the space left over by the `fixed` and `auto`
siblings, in the sense of WPF star sizing, not Flexbox `flex-grow`: there is
no `flex-basis`, and the weight applies to the remainder alone. The share rules
and the rejected percentage spelling are in [SIZE_POLICY.md](SIZE_POLICY.md).

A `weight` child measures as its content; the weight decides only how the
parent's room is shared out. A parent sized by its content, such as a window
with no height, thus fits the child's content. Measuring a `weight` child as
zero was rejected: a grid of `"wt"` cards in such a window would come up empty.

### Grid Allocates Room; the Child Fills It

`Grid` decides rows, columns, areas and the allocated rect of each cell.
Whether the child fills that rect or keeps its intrinsic size is the child's
own `width` / `height`. A cell is filled with `width="wt", height="wt"`, not by
a `Grid` option.

### Which Dimensions Are Constructor Parameters

Whether a size is a public constructor parameter is decided per axis by one
rule: MD3 leaves the axis open, so it is a constructor parameter; MD3 fixes
it, so it is style only. The rule and what follows from it are in
[SIZE_POLICY.md](SIZE_POLICY.md).

## Alignment Is the Parent's

Alignment belongs to the parent, not to the child. A single-child container
takes `alignment`, one of nine points. A multi-child container takes
`main_alignment` along its axis and `cross_alignment` across it.

Alignment positions only; it never stretches. To fill the space the child
takes `width="wt"` / `height="wt"`. CSS `align-*` lets alignment also absorb
excess space (`stretch`); that meaning was left out so that alignment answers
one question, where the child goes, and `Sizing` the other, how big it is.

## Overflow Is Visible

A child larger than its allocated rect is painted as it is; nothing clips it.
Visible was chosen over clip for three reasons:

- With `Sizing`, content does not overflow a correct layout. Overflow is a
  layout bug, and a visible one is found; a clipped one is not.
- Shadows, focus rings and popups overflow their widget by design.
- Clipping (`saveLayer` / `clipRect`) is expensive. Paying it on every widget
  for the few that want it was rejected.

Clipping and scrolling are added where wanted: `clip()` is a modifier, and
scrolling is a viewport widget.

## Modifiers Do Not Lay Out

Size, spacing and alignment are widget properties. A modifier adds a
capability or a visual effect and never changes layout; the reason is in
[MODIFIER.md](MODIFIER.md).

## Window Size Is Not a Sizing

The window's `width` / `height` is a `WindowSizing`: a fixed pixel value or
`"auto"`, the content's preferred size. It is a separate type because a window
is resolved before layout and has no parent. `"wt"` has nothing to take a
share of, so it is not accepted.

A window position is a nine-point alignment on the screen plus a pixel
offset, the same vocabulary as widget alignment. The alignment is resolved
against the screen's work area and the window's outer frame, not the screen
bounds and the client area the OS API takes: aligning the client area would
push a `top` window's title bar off screen and a `bottom` window under the
taskbar.
