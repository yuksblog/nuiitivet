<!-- markdownlint-disable MD060 -->

# Carousel MD3 Specs

Source: <https://m3.material.io/components/carousel/specs>
Collected: 2026-05-25

## Summary

- Carousel exposes one active token set in the live viewer: `Carousel item` with `Default, Light` context chips.
- Base carousel items use `md.sys.color.surface`, `md.sys.elevation.level0`, `md.sys.shape.corner.extra-large`, and `md.sys.color.shadow`, which resolves here to a white container, 0dp elevation, 28dp corners, and a black shadow color.
- Hover is the only elevated interaction state at 1dp; focus and pressed return to 0dp while reusing `md.sys.color.on-surface` state layers with 0.1 opacity, and hover uses the same state-layer color at 0.08 opacity.
- Outlined carousel items are modeled by `md.comp.carousel-item.with-outline.*` tokens with a 1dp outline and `md.sys.color.outline` for enabled, hover, pressed, and disabled states; focus promotes the outline to `md.sys.color.on-surface`.
- Non-full-screen layouts consistently use 28dp item corners, 8dp vertical padding, and 8dp inter-item spacing; most also use 16dp leading or leading/trailing padding.

## Tokens & Specs

### Token sets discovered

| Token set     | Status | Notes                                                                                                                              |
|---------------|--------|------------------------------------------------------------------------------------------------------------------------------------|
| Carousel item | Active | Viewer context chips show `Default, Light`. Includes base container tokens plus `with-outline` tokens for outlined carousel items. |

### Carousel item

| Token set     | Group                          | Label                                            | Token                                                       | Source token                              | Value   | Notes                                                                                |
|---------------|--------------------------------|--------------------------------------------------|-------------------------------------------------------------|-------------------------------------------|---------|--------------------------------------------------------------------------------------|
| Carousel item | Enabled / Container            | Carousel item container color                    | md.comp.carousel-item.container.color                       | md.sys.color.surface                      | #FFFFFF |                                                                                      |
| Carousel item | Enabled / Container            | Carousel item container elevation                | md.comp.carousel-item.container.elevation                   | md.sys.elevation.level0                   | 0dp     |                                                                                      |
| Carousel item | Enabled / Container            | Carousel item container shadow color             | md.comp.carousel-item.container.shadow-color                | md.sys.color.shadow                       | #000000 |                                                                                      |
| Carousel item | Enabled / Container            | Carousel item container shape                    | md.comp.carousel-item.container.shape                       | md.sys.shape.corner.extra-large           | 28dp    | Rounded corners.                                                                     |
| Carousel item | Enabled / Container            | Carousel item container surface tint layer color | md.comp.carousel-item.container.surface-tint-layer.color    | md.sys.color.surface-tint                 | #6991D6 | Deprecated surface tint layer token; prefer the resolved container role in new work. |
| Carousel item | Enabled / Outline              | Carousel item outline color                      | md.comp.carousel-item.with-outline.outline.color            | md.sys.color.outline                      | #747775 | Applies to outlined carousel items.                                                  |
| Carousel item | Enabled / Outline              | Carousel item outline width                      | md.comp.carousel-item.with-outline.outline.width            |                                           | 1dp     | Applies to outlined carousel items.                                                  |
| Carousel item | Hover / Container              | Carousel item hover container elevation          | md.comp.carousel-item.hover.container.elevation             | md.sys.elevation.level1                   | 1dp     |                                                                                      |
| Carousel item | Hover / State layer            | Carousel item hover state layer color            | md.comp.carousel-item.hover.state-layer.color               | md.sys.color.on-surface                   | #1F1F1F |                                                                                      |
| Carousel item | Hover / State layer            | Carousel item hover state layer opacity          | md.comp.carousel-item.hover.state-layer.opacity             | md.sys.state.hover.state-layer-opacity    | 0.08    |                                                                                      |
| Carousel item | Hover / Outline                | Carousel item hover outline color                | md.comp.carousel-item.with-outline.hover.outline.color      | md.sys.color.outline                      | #747775 | Applies to outlined carousel items.                                                  |
| Carousel item | Focus / Container              | Carousel item focus container elevation          | md.comp.carousel-item.focus.container.elevation             | md.sys.elevation.level0                   | 0dp     |                                                                                      |
| Carousel item | Focus / Focus indicator        | Carousel item focus indicator color              | md.comp.carousel-item.focus.indicator.color                 | md.sys.color.secondary                    | #00639B |                                                                                      |
| Carousel item | Focus / Focus indicator        | Carousel item focus indicator thickness          | md.comp.carousel-item.focus.indicator.thickness             | md.sys.state.focus-indicator.thickness    | 3dp     |                                                                                      |
| Carousel item | Focus / Focus indicator        | Carousel focus indicator offset                  | md.comp.carousel-item.focus.indicator.outline.offset        | md.sys.state.focus-indicator.outer-offset | 2dp     |                                                                                      |
| Carousel item | Focus / State layer            | Carousel item focus state layer color            | md.comp.carousel-item.focus.state-layer.color               | md.sys.color.on-surface                   | #1F1F1F |                                                                                      |
| Carousel item | Focus / State layer            | Carousel item focus state layer opacity          | md.comp.carousel-item.focus.state-layer.opacity             | md.sys.state.focus.state-layer-opacity    | 0.1     |                                                                                      |
| Carousel item | Focus / Outline                | Carousel item focus outline color                | md.comp.carousel-item.with-outline.focus.outline.color      | md.sys.color.on-surface                   | #1F1F1F | Applies to outlined carousel items.                                                  |
| Carousel item | Pressed (ripple) / Container   | Carousel item pressed container elevation        | md.comp.carousel-item.pressed.container.elevation           | md.sys.elevation.level0                   | 0dp     |                                                                                      |
| Carousel item | Pressed (ripple) / State layer | Carousel item pressed state layer color          | md.comp.carousel-item.pressed.state-layer.color             | md.sys.color.on-surface                   | #1F1F1F |                                                                                      |
| Carousel item | Pressed (ripple) / State layer | Carousel item pressed state layer opacity        | md.comp.carousel-item.pressed.state-layer.opacity           | md.sys.state.pressed.state-layer-opacity  | 0.1     |                                                                                      |
| Carousel item | Pressed (ripple) / Outline     | Carousel item pressed outline color              | md.comp.carousel-item.with-outline.pressed.outline.color    | md.sys.color.outline                      | #747775 | Applies to outlined carousel items.                                                  |
| Carousel item | Disabled / Container           | Carousel item disabled container color           | md.comp.carousel-item.disabled.container.color              | md.sys.color.surface                      | #FFFFFF | Used with the disabled container opacity token.                                      |
| Carousel item | Disabled / Container           | Carousel item disabled container elevation       | md.comp.carousel-item.disabled.container.elevation          | md.sys.elevation.level0                   | 0dp     |                                                                                      |
| Carousel item | Disabled / Container           | Carousel item disabled container opacity         | md.comp.carousel-item.disabled.container.opacity            |                                           | 0.38    |                                                                                      |
| Carousel item | Disabled / Outline             | Carousel item disabled outline color             | md.comp.carousel-item.with-outline.disabled.outline.color   | md.sys.color.outline                      | #747775 | Applies to outlined carousel items.                                                  |
| Carousel item | Disabled / Outline             | Carousel item disabled outline opacity           | md.comp.carousel-item.with-outline.disabled.outline.opacity |                                           | 0.12    | Applies to outlined carousel items.                                                  |

## Measurements

| Category                       | Item                     | Value               | Notes                                                                              |
|--------------------------------|--------------------------|---------------------|------------------------------------------------------------------------------------|
| Dynamic widths                 | Large item max width     | Customizable        | Large items adapt to the container width and can use a user-defined maximum width. |
| Dynamic widths                 | Small item width         | 40-56dp             | Small carousel items have a minimum width of 40dp and a maximum width of 56dp.     |
| Dynamic widths                 | Item resizing            | Dynamic             | Items change size as they move through the carousel layout.                        |
| Multi-browse                   | Alignment                | Vertically centered |                                                                                    |
| Multi-browse                   | Leading/trailing padding | 16dp                | Padding on both sides of the container.                                            |
| Multi-browse                   | Top/bottom padding       | 8dp                 |                                                                                    |
| Multi-browse                   | Padding between elements | 8dp                 |                                                                                    |
| Multi-browse                   | Large item width         | Dynamic or user-set |                                                                                    |
| Multi-browse                   | Medium item width        | Dynamic             |                                                                                    |
| Multi-browse                   | Small item width         | 40-56dp, dynamic    |                                                                                    |
| Multi-browse                   | Item corner radius       | 28dp                |                                                                                    |
| Uncontained                    | Alignment                | Vertically centered |                                                                                    |
| Uncontained                    | Leading padding          | 16dp                | Items bleed over the side padding while scrolling.                                 |
| Uncontained                    | Top/bottom padding       | 8dp                 |                                                                                    |
| Uncontained                    | Padding between elements | 8dp                 |                                                                                    |
| Uncontained                    | Item corner radius       | 28dp                |                                                                                    |
| Uncontained multi-aspect ratio | Alignment                | Vertically centered |                                                                                    |
| Uncontained multi-aspect ratio | Leading padding          | 16dp                | Only leading padding is used.                                                      |
| Uncontained multi-aspect ratio | Top/bottom padding       | 8dp                 |                                                                                    |
| Uncontained multi-aspect ratio | Padding between elements | 8dp                 |                                                                                    |
| Uncontained multi-aspect ratio | Item corner radius       | 28dp                |                                                                                    |
| Hero                           | Alignment                | Vertically centered |                                                                                    |
| Hero                           | Leading/trailing padding | 16dp                | Padding on both sides of the container.                                            |
| Hero                           | Top/bottom padding       | 8dp                 |                                                                                    |
| Hero                           | Padding between elements | 8dp                 |                                                                                    |
| Hero                           | Large item width         | Dynamic             |                                                                                    |
| Hero                           | Small item width         | 40-56dp, dynamic    |                                                                                    |
| Hero                           | Item corner radius       | 28dp                |                                                                                    |
| Center-aligned hero            | Alignment                | Vertically centered |                                                                                    |
| Center-aligned hero            | Leading/trailing padding | 16dp                | Padding on both sides of the container.                                            |
| Center-aligned hero            | Top/bottom padding       | 8dp                 |                                                                                    |
| Center-aligned hero            | Padding between elements | 8dp                 |                                                                                    |
| Center-aligned hero            | Large item width         | Dynamic             |                                                                                    |
| Center-aligned hero            | Small item width         | 40-56dp, dynamic    |                                                                                    |
| Center-aligned hero            | Item corner radius       | 28dp                |                                                                                    |
| Full-screen                    | Alignment                | Centered            |                                                                                    |
| Full-screen                    | Leading/trailing padding | 0dp                 | Edge-to-edge layout.                                                               |
| Full-screen                    | Top/bottom padding       | 0dp                 | Edge-to-edge layout.                                                               |
| Full-screen                    | Padding between elements | 16dp                |                                                                                    |

## Implementation Notes

- Use `md.sys.shape.corner.extra-large` as a real 28dp corner radius across carousel layouts unless a container-specific override is introduced locally.
- Treat the base carousel item as a 0dp surface-backed container, with hover as the only elevated interaction state at 1dp.
- Reuse the shared state-layer pattern from the tokens table: `md.sys.color.on-surface` with 0.08 opacity on hover and 0.1 on focus and pressed.
- Model outlined carousel items as an optional treatment driven by `md.comp.carousel-item.with-outline.*`, not as a separate token set.
- Most carousel layouts share the same spacing ladder: 16dp outer horizontal padding, 8dp vertical padding, and 8dp between items. Full-screen is the main exception with 0dp outer padding and 16dp between items.
