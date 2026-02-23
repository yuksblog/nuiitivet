---
layout: default
---

# Layout

The layout system in NuiiTivet is designed to be simple yet powerful.
It incorporates intuitive aspects from Web (CSS) and Flutter, allowing you to build screens with Pythonic syntax.

## Key Concepts

### 1. Arranging Boxes (Box Model)

The basics are repeatedly "stacking vertically (Column)" and "arranging horizontally (Row)".
Even complex screens can be expressed by nesting these.

- [Basics: Row and Column](layout_basics.md)

### 2. Spacing and Sizing

There is no `margin`. Spacing is controlled entirely by parent container `padding` or `gap` between elements.
Sizes can be intuitively specified in three patterns: `fixed`, `auto` (fit content), and `flex` (fill space).

- [Spacing Concepts](layout_spacing.md)
- [Sizing Methods](layout_sizing.md)

### 3. Alignment

"Where to place" in the remaining space is determined by the `alignment` property.
"Center", "Right align", etc., are all controlled by this.

- [Layout Alignment](layout_alignment.md)

## Topic Guides

Refer to the following guides based on what you want to create.

| What you want to do | Reference | Main Components |
| --- | --- | --- |
| Arrange vertically or horizontally | [layout_basics.md](layout_basics.md) | `Row`, `Column` |
| Partitioning like header/sidebar | [layout_grid.md](layout_grid.md) | `Grid` |
| Overlay elements (Badges, backgrounds, etc.) | [layout_extras.md](layout_extras.md) | `Stack` |
| Create wrapping lists (Tag lists, etc.) | [layout_extras.md](layout_extras.md) | `Flow` |
| Make scrollable | [layout_overflow.md](layout_overflow.md) | `scrollable` |
| Create tab switching | [layout_extras.md](layout_extras.md) | `Deck` |

## More Details

This guide focuses on practical usage in app code.
