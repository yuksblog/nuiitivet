<!-- markdownlint-disable MD060 -->

# Extended FABs MD3 Specs

Source: <https://m3.material.io/components/extended-fab/specs>
Collected: 2026-05-25

## Summary

- The active Extended FAB token viewer exposes nine expressive token sets: three size sets and six color mappings.
- Resolved values below use the viewer's default Android / 1P Baseline / Light / Default-contrast context. The viewer also exposes Dark, Medium contrast, and High contrast variants.
- The expressive size scale is 56dp small, 80dp medium, and 96dp large, with icon sizes of 24dp, 28dp, and 36dp and rounded corner sizes of 16dp, 20dp, and 28dp.
- Small, medium, and large label text map to `md.sys.typescale.title-medium`, `md.sys.typescale.title-large`, and `md.sys.typescale.headline-small` respectively.
- All six active color mappings share the same state behavior: enabled, focused, and pressed stay at 6dp elevation; hovered rises to 8dp; hover opacity is 0.08; focus and press opacity are 0.1.
- The page's Measurements section explicitly states a 16dp outer margin. Other concrete size and padding values are sourced from the live size token sets because the measurement diagrams are image-first.

## Tokens & Specs

Deprecated compatibility rows embedded in the `Extended FAB - Color - Primary`, `Extended FAB - Color - Secondary`, and `Extended FAB - Color - Tertiary` viewers are omitted below.

### Token sets discovered

| Token set                              | Count | Notes                                                           |
|----------------------------------------|------:|-----------------------------------------------------------------|
| Extended FAB - Size - Small            |     7 | Expressive small extended FAB size tokens.                      |
| Extended FAB - Size - Medium           |     7 | Expressive medium extended FAB size tokens.                     |
| Extended FAB - Size - Large            |     7 | Expressive large extended FAB size tokens.                      |
| Extended FAB - Color - Tonal primary   |    20 | Primary-container mapping.                                      |
| Extended FAB - Color - Tonal secondary |    20 | Secondary-container mapping.                                    |
| Extended FAB - Color - Tonal tertiary  |    20 | Tertiary-container mapping.                                     |
| Extended FAB - Color - Primary         |    20 | Solid primary mapping; deprecated compatibility rows omitted.   |
| Extended FAB - Color - Secondary       |    20 | Solid secondary mapping; deprecated compatibility rows omitted. |
| Extended FAB - Color - Tertiary        |    20 | Solid tertiary mapping; deprecated compatibility rows omitted.  |

### Extended FAB - Size - Small

| Token set                   | Group      | Label                               | Token                                       | Source token                  | Value                                | Notes                                                                        |
|-----------------------------|------------|-------------------------------------|---------------------------------------------|-------------------------------|--------------------------------------|------------------------------------------------------------------------------|
| Extended FAB - Size - Small | Layout     | Extended FAB small container height | md.comp.extended-fab.small.container.height |                               | 56dp                                 |                                                                              |
| Extended FAB - Size - Small | Typography | Extended FAB small label text       | md.comp.extended-fab.small.label-text       | md.sys.typescale.title-medium | Google Sans Text / 500 / 16pt / 24pt | Composite typography token; tracking is not exposed in the resolved payload. |
| Extended FAB - Size - Small | Layout     | Extended FAB small icon size        | md.comp.extended-fab.small.icon.size        |                               | 24dp                                 |                                                                              |
| Extended FAB - Size - Small | Shape      | Extended FAB small container shape  | md.comp.extended-fab.small.container.shape  | md.sys.shape.corner.large     | 16dp                                 | Rounded corners.                                                             |
| Extended FAB - Size - Small | Layout     | Extended FAB small leading space    | md.comp.extended-fab.small.leading-space    |                               | 16dp                                 |                                                                              |
| Extended FAB - Size - Small | Layout     | Extended FAB small icon label space | md.comp.extended-fab.small.icon-label-space |                               | 8dp                                  |                                                                              |
| Extended FAB - Size - Small | Layout     | Extended FAB small trailing space   | md.comp.extended-fab.small.trailing-space   |                               | 16dp                                 |                                                                              |

### Extended FAB - Size - Medium

| Token set                    | Group      | Label                                | Token                                        | Source token                        | Value                           | Notes                                                                        |
|------------------------------|------------|--------------------------------------|----------------------------------------------|-------------------------------------|---------------------------------|------------------------------------------------------------------------------|
| Extended FAB - Size - Medium | Layout     | Extended FAB medium container height | md.comp.extended-fab.medium.container.height |                                     | 80dp                            |                                                                              |
| Extended FAB - Size - Medium | Typography | Extended FAB medium label text       | md.comp.extended-fab.medium.label-text       | md.sys.typescale.title-large        | Google Sans / 400 / 22pt / 28pt | Composite typography token; tracking is not exposed in the resolved payload. |
| Extended FAB - Size - Medium | Layout     | Extended FAB medium icon size        | md.comp.extended-fab.medium.icon.size        |                                     | 28dp                            |                                                                              |
| Extended FAB - Size - Medium | Shape      | Extended FAB medium container shape  | md.comp.extended-fab.medium.container.shape  | md.sys.shape.corner.large-increased | 20dp                            | Rounded corners.                                                             |
| Extended FAB - Size - Medium | Layout     | Extended FAB medium leading space    | md.comp.extended-fab.medium.leading-space    |                                     | 26dp                            |                                                                              |
| Extended FAB - Size - Medium | Layout     | Extended FAB medium icon label space | md.comp.extended-fab.medium.icon-label-space |                                     | 12dp                            |                                                                              |
| Extended FAB - Size - Medium | Layout     | Extended FAB medium trailing space   | md.comp.extended-fab.medium.trailing-space   |                                     | 26dp                            |                                                                              |

### Extended FAB - Size - Large

| Token set                   | Group      | Label                               | Token                                       | Source token                    | Value                           | Notes                                                                        |
|-----------------------------|------------|-------------------------------------|---------------------------------------------|---------------------------------|---------------------------------|------------------------------------------------------------------------------|
| Extended FAB - Size - Large | Layout     | Extended FAB large container height | md.comp.extended-fab.large.container.height |                                 | 96dp                            |                                                                              |
| Extended FAB - Size - Large | Typography | Extended FAB large label text       | md.comp.extended-fab.large.label-text       | md.sys.typescale.headline-small | Google Sans / 400 / 24pt / 32pt | Composite typography token; tracking is not exposed in the resolved payload. |
| Extended FAB - Size - Large | Layout     | Extended FAB large icon size        | md.comp.extended-fab.large.icon.size        |                                 | 36dp                            |                                                                              |
| Extended FAB - Size - Large | Shape      | Extended FAB large container shape  | md.comp.extended-fab.large.container.shape  | md.sys.shape.corner.extra-large | 28dp                            | Rounded corners.                                                             |
| Extended FAB - Size - Large | Layout     | Extended FAB large leading space    | md.comp.extended-fab.large.leading-space    |                                 | 28dp                            |                                                                              |
| Extended FAB - Size - Large | Layout     | Extended FAB large icon label space | md.comp.extended-fab.large.icon-label-space |                                 | 16dp                            |                                                                              |
| Extended FAB - Size - Large | Layout     | Extended FAB large trailing space   | md.comp.extended-fab.large.trailing-space   |                                 | 28dp                            |                                                                              |

### Extended FAB - Color - Tonal primary

| Token set                            | Group   | Label                                                  | Token                                                              | Source token                             | Value   | Notes |
|--------------------------------------|---------|--------------------------------------------------------|--------------------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Tonal primary | Enabled | Extended FAB tonal primary container color             | md.comp.extended-fab.primary-container.container.color             | md.sys.color.primary-container           | #D3E3FD |       |
| Extended FAB - Color - Tonal primary | Enabled | Extended FAB tonal primary container shadow color      | md.comp.extended-fab.primary-container.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Tonal primary | Enabled | Extended FAB tonal primary label text color            | md.comp.extended-fab.primary-container.label-text.color            | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Enabled | Extended FAB tonal primary container icon color        | md.comp.extended-fab.primary-container.icon.color                  | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Hovered | Extended FAB tonal primary hovered state layer color   | md.comp.extended-fab.primary-container.hovered.state-layer.color   | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Hovered | Extended FAB tonal primary hovered label text color    | md.comp.extended-fab.primary-container.hovered.label-text.color    | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Hovered | Extended FAB tonal primary hovered icon color          | md.comp.extended-fab.primary-container.hovered.icon.color          | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Hovered | Extended FAB tonal primary hovered state layer opacity | md.comp.extended-fab.primary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Tonal primary | Hovered | Extended FAB tonal primary hovered container elevation | md.comp.extended-fab.primary-container.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Tonal primary | Enabled | Extended FAB tonal primary container elevation         | md.comp.extended-fab.primary-container.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal primary | Pressed | Extended FAB tonal primary pressed container elevation | md.comp.extended-fab.primary-container.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal primary | Pressed | Extended FAB tonal primary pressed state layer color   | md.comp.extended-fab.primary-container.pressed.state-layer.color   | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Pressed | Extended FAB tonal primary pressed state layer opacity | md.comp.extended-fab.primary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Tonal primary | Pressed | Extended FAB tonal primary pressed label text color    | md.comp.extended-fab.primary-container.pressed.label-text.color    | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Pressed | Extended FAB tonal primary pressed icon color          | md.comp.extended-fab.primary-container.pressed.icon.color          | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Focused | Extended FAB tonal primary focused container elevation | md.comp.extended-fab.primary-container.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal primary | Focused | Extended FAB tonal primary focused state layer color   | md.comp.extended-fab.primary-container.focused.state-layer.color   | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Focused | Extended FAB tonal primary focused state layer opacity | md.comp.extended-fab.primary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Tonal primary | Focused | Extended FAB tonal primary focused label text color    | md.comp.extended-fab.primary-container.focused.label-text.color    | md.sys.color.on-primary-container        | #0842A0 |       |
| Extended FAB - Color - Tonal primary | Focused | Extended FAB tonal primary focused icon color          | md.comp.extended-fab.primary-container.focused.icon.color          | md.sys.color.on-primary-container        | #0842A0 |       |

### Extended FAB - Color - Tonal secondary

| Token set                              | Group   | Label                                                    | Token                                                                | Source token                             | Value   | Notes |
|----------------------------------------|---------|----------------------------------------------------------|----------------------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Tonal secondary | Enabled | Extended FAB tonal secondary container color             | md.comp.extended-fab.secondary-container.container.color             | md.sys.color.secondary-container         | #C2E7FF |       |
| Extended FAB - Color - Tonal secondary | Enabled | Extended FAB tonal secondary container elevation         | md.comp.extended-fab.secondary-container.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal secondary | Enabled | Extended FAB tonal secondary container shadow color      | md.comp.extended-fab.secondary-container.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Tonal secondary | Enabled | Extended FAB tonal secondary label text color            | md.comp.extended-fab.secondary-container.label-text.color            | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Enabled | Extended FAB tonal secondary container icon color        | md.comp.extended-fab.secondary-container.icon.color                  | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Hovered | Extended FAB tonal secondary hovered container elevation | md.comp.extended-fab.secondary-container.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Tonal secondary | Hovered | Extended FAB tonal secondary hovered state layer color   | md.comp.extended-fab.secondary-container.hovered.state-layer.color   | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Hovered | Extended FAB tonal secondary hovered state layer opacity | md.comp.extended-fab.secondary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Tonal secondary | Hovered | Extended FAB tonal secondary hovered label text color    | md.comp.extended-fab.secondary-container.hovered.label-text.color    | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Hovered | Extended FAB tonal secondary hovered icon color          | md.comp.extended-fab.secondary-container.hovered.icon.color          | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Focused | Extended FAB tonal secondary focused container elevation | md.comp.extended-fab.secondary-container.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal secondary | Focused | Extended FAB tonal secondary focused state layer color   | md.comp.extended-fab.secondary-container.focused.state-layer.color   | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Focused | Extended FAB tonal secondary focused state layer opacity | md.comp.extended-fab.secondary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Tonal secondary | Focused | Extended FAB tonal secondary focused label text color    | md.comp.extended-fab.secondary-container.focused.label-text.color    | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Focused | Extended FAB tonal secondary focused icon color          | md.comp.extended-fab.secondary-container.focused.icon.color          | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Pressed | Extended FAB tonal secondary pressed container elevation | md.comp.extended-fab.secondary-container.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal secondary | Pressed | Extended FAB tonal secondary pressed state layer color   | md.comp.extended-fab.secondary-container.pressed.state-layer.color   | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Pressed | Extended FAB tonal secondary pressed state layer opacity | md.comp.extended-fab.secondary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Tonal secondary | Pressed | Extended FAB tonal secondary pressed label text color    | md.comp.extended-fab.secondary-container.pressed.label-text.color    | md.sys.color.on-secondary-container      | #004A77 |       |
| Extended FAB - Color - Tonal secondary | Pressed | Extended FAB tonal secondary pressed icon color          | md.comp.extended-fab.secondary-container.pressed.icon.color          | md.sys.color.on-secondary-container      | #004A77 |       |

### Extended FAB - Color - Tonal tertiary

| Token set                             | Group   | Label                                                   | Token                                                               | Source token                             | Value   | Notes |
|---------------------------------------|---------|---------------------------------------------------------|---------------------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Tonal tertiary | Enabled | Extended FAB tonal tertiary container color             | md.comp.extended-fab.tertiary-container.container.color             | md.sys.color.tertiary-container          | #C4EED0 |       |
| Extended FAB - Color - Tonal tertiary | Enabled | Extended FAB tonal tertiary container elevation         | md.comp.extended-fab.tertiary-container.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal tertiary | Enabled | Extended FAB tonal tertiary container shadow color      | md.comp.extended-fab.tertiary-container.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Tonal tertiary | Enabled | Extended FAB tonal tertiary label text color            | md.comp.extended-fab.tertiary-container.label-text.color            | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Enabled | Extended FAB tonal tertiary container icon color        | md.comp.extended-fab.tertiary-container.icon.color                  | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Hovered | Extended FAB tonal tertiary hovered container elevation | md.comp.extended-fab.tertiary-container.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Tonal tertiary | Hovered | Extended FAB tonal tertiary hovered state layer color   | md.comp.extended-fab.tertiary-container.hovered.state-layer.color   | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Hovered | Extended FAB tonal tertiary hovered state layer opacity | md.comp.extended-fab.tertiary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Tonal tertiary | Hovered | Extended FAB tonal tertiary hovered label text color    | md.comp.extended-fab.tertiary-container.hovered.label-text.color    | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Hovered | Extended FAB tonal tertiary hovered icon color          | md.comp.extended-fab.tertiary-container.hovered.icon.color          | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Focused | Extended FAB tonal tertiary focused container elevation | md.comp.extended-fab.tertiary-container.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal tertiary | Focused | Extended FAB tonal tertiary focused state layer color   | md.comp.extended-fab.tertiary-container.focused.state-layer.color   | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Focused | Extended FAB tonal tertiary focused state layer opacity | md.comp.extended-fab.tertiary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Tonal tertiary | Focused | Extended FAB tonal tertiary focused label text color    | md.comp.extended-fab.tertiary-container.focused.label-text.color    | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Focused | Extended FAB tonal tertiary focused icon color          | md.comp.extended-fab.tertiary-container.focused.icon.color          | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Pressed | Extended FAB tonal tertiary pressed container elevation | md.comp.extended-fab.tertiary-container.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tonal tertiary | Pressed | Extended FAB tonal tertiary pressed state layer color   | md.comp.extended-fab.tertiary-container.pressed.state-layer.color   | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Pressed | Extended FAB tonal tertiary pressed state layer opacity | md.comp.extended-fab.tertiary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Tonal tertiary | Pressed | Extended FAB tonal tertiary pressed label text color    | md.comp.extended-fab.tertiary-container.pressed.label-text.color    | md.sys.color.on-tertiary-container       | #0F5223 |       |
| Extended FAB - Color - Tonal tertiary | Pressed | Extended FAB tonal tertiary pressed icon color          | md.comp.extended-fab.tertiary-container.pressed.icon.color          | md.sys.color.on-tertiary-container       | #0F5223 |       |

### Extended FAB - Color - Primary

| Token set                      | Group   | Label                                            | Token                                                    | Source token                             | Value   | Notes |
|--------------------------------|---------|--------------------------------------------------|----------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Primary | Enabled | Extended FAB primary container color             | md.comp.extended-fab.primary.container.color             | md.sys.color.primary                     | #0B57D0 |       |
| Extended FAB - Color - Primary | Enabled | Extended FAB primary container elevation         | md.comp.extended-fab.primary.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Primary | Enabled | Extended FAB primary container shadow color      | md.comp.extended-fab.primary.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Primary | Enabled | Extended FAB primary label text color            | md.comp.extended-fab.primary.label-text.color            | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Enabled | Extended FAB primary container icon color        | md.comp.extended-fab.primary.icon.color                  | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Hovered | Extended FAB primary hovered container elevation | md.comp.extended-fab.primary.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Primary | Hovered | Extended FAB primary hovered state layer color   | md.comp.extended-fab.primary.hovered.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Hovered | Extended FAB primary hovered state layer opacity | md.comp.extended-fab.primary.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Primary | Hovered | Extended FAB primary hovered label text color    | md.comp.extended-fab.primary.hovered.label-text.color    | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Hovered | Extended FAB primary hovered icon color          | md.comp.extended-fab.primary.hovered.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Focused | Extended FAB primary focused container elevation | md.comp.extended-fab.primary.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Primary | Focused | Extended FAB primary focused state layer color   | md.comp.extended-fab.primary.focused.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Focused | Extended FAB primary focused state layer opacity | md.comp.extended-fab.primary.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Primary | Focused | Extended FAB primary focused label text color    | md.comp.extended-fab.primary.focused.label-text.color    | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Focused | Extended FAB primary focused icon color          | md.comp.extended-fab.primary.focused.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Pressed | Extended FAB primary pressed container elevation | md.comp.extended-fab.primary.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Primary | Pressed | Extended FAB primary pressed state layer color   | md.comp.extended-fab.primary.pressed.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Pressed | Extended FAB primary pressed state layer opacity | md.comp.extended-fab.primary.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Primary | Pressed | Extended FAB primary pressed label text color    | md.comp.extended-fab.primary.pressed.label-text.color    | md.sys.color.on-primary                  | #FFFFFF |       |
| Extended FAB - Color - Primary | Pressed | Extended FAB primary pressed icon color          | md.comp.extended-fab.primary.pressed.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |

### Extended FAB - Color - Secondary

| Token set                        | Group   | Label                                              | Token                                                      | Source token                             | Value   | Notes |
|----------------------------------|---------|----------------------------------------------------|------------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Secondary | Enabled | Extended FAB secondary container color             | md.comp.extended-fab.secondary.container.color             | md.sys.color.secondary                   | #00639B |       |
| Extended FAB - Color - Secondary | Enabled | Extended FAB secondary container elevation         | md.comp.extended-fab.secondary.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Secondary | Enabled | Extended FAB secondary container shadow color      | md.comp.extended-fab.secondary.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Secondary | Enabled | Extended FAB secondary label text color            | md.comp.extended-fab.secondary.label-text.color            | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Enabled | Extended FAB secondary container icon color        | md.comp.extended-fab.secondary.icon.color                  | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Pressed | Extended FAB secondary pressed container elevation | md.comp.extended-fab.secondary.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Secondary | Pressed | Extended FAB secondary pressed state layer color   | md.comp.extended-fab.secondary.pressed.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Pressed | Extended FAB secondary pressed state layer opacity | md.comp.extended-fab.secondary.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Secondary | Pressed | Extended FAB secondary pressed label text color    | md.comp.extended-fab.secondary.pressed.label-text.color    | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Pressed | Extended FAB secondary pressed icon color          | md.comp.extended-fab.secondary.pressed.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Hovered | Extended FAB secondary hovered container elevation | md.comp.extended-fab.secondary.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Secondary | Hovered | Extended FAB secondary hovered state layer color   | md.comp.extended-fab.secondary.hovered.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Hovered | Extended FAB secondary hovered state layer opacity | md.comp.extended-fab.secondary.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Secondary | Hovered | Extended FAB secondary hovered label text color    | md.comp.extended-fab.secondary.hovered.label-text.color    | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Hovered | Extended FAB secondary hovered icon color          | md.comp.extended-fab.secondary.hovered.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Focused | Extended FAB secondary focused container elevation | md.comp.extended-fab.secondary.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Secondary | Focused | Extended FAB secondary focused state layer color   | md.comp.extended-fab.secondary.focused.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Focused | Extended FAB secondary focused state layer opacity | md.comp.extended-fab.secondary.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Secondary | Focused | Extended FAB secondary focused label text color    | md.comp.extended-fab.secondary.focused.label-text.color    | md.sys.color.on-secondary                | #FFFFFF |       |
| Extended FAB - Color - Secondary | Focused | Extended FAB secondary focused icon color          | md.comp.extended-fab.secondary.focused.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |

### Extended FAB - Color - Tertiary

| Token set                       | Group   | Label                                             | Token                                                     | Source token                             | Value   | Notes |
|---------------------------------|---------|---------------------------------------------------|-----------------------------------------------------------|------------------------------------------|---------|-------|
| Extended FAB - Color - Tertiary | Enabled | Extended FAB tertiary container color             | md.comp.extended-fab.tertiary.container.color             | md.sys.color.tertiary                    | #146C2E |       |
| Extended FAB - Color - Tertiary | Enabled | Extended FAB tertiary container elevation         | md.comp.extended-fab.tertiary.container.elevation         | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tertiary | Enabled | Extended FAB tertiary container shadow color      | md.comp.extended-fab.tertiary.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| Extended FAB - Color - Tertiary | Enabled | Extended FAB tertiary label text color            | md.comp.extended-fab.tertiary.label-text.color            | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Enabled | Extended FAB tertiary container icon color        | md.comp.extended-fab.tertiary.icon.color                  | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Pressed | Extended FAB tertiary pressed container elevation | md.comp.extended-fab.tertiary.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tertiary | Pressed | Extended FAB tertiary pressed state layer color   | md.comp.extended-fab.tertiary.pressed.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Pressed | Extended FAB tertiary pressed state layer opacity | md.comp.extended-fab.tertiary.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| Extended FAB - Color - Tertiary | Pressed | Extended FAB tertiary pressed label text color    | md.comp.extended-fab.tertiary.pressed.label-text.color    | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Pressed | Extended FAB tertiary pressed icon color          | md.comp.extended-fab.tertiary.pressed.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Hovered | Extended FAB tertiary hovered container elevation | md.comp.extended-fab.tertiary.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| Extended FAB - Color - Tertiary | Hovered | Extended FAB tertiary hovered state layer color   | md.comp.extended-fab.tertiary.hovered.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Hovered | Extended FAB tertiary hovered state layer opacity | md.comp.extended-fab.tertiary.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| Extended FAB - Color - Tertiary | Hovered | Extended FAB tertiary hovered label text color    | md.comp.extended-fab.tertiary.hovered.label-text.color    | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Hovered | Extended FAB tertiary hovered icon color          | md.comp.extended-fab.tertiary.hovered.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Focused | Extended FAB tertiary focused container elevation | md.comp.extended-fab.tertiary.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| Extended FAB - Color - Tertiary | Focused | Extended FAB tertiary focused state layer color   | md.comp.extended-fab.tertiary.focused.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Focused | Extended FAB tertiary focused state layer opacity | md.comp.extended-fab.tertiary.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| Extended FAB - Color - Tertiary | Focused | Extended FAB tertiary focused label text color    | md.comp.extended-fab.tertiary.focused.label-text.color    | md.sys.color.on-tertiary                 | #FFFFFF |       |
| Extended FAB - Color - Tertiary | Focused | Extended FAB tertiary focused icon color          | md.comp.extended-fab.tertiary.focused.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |

## Measurements

| Category | Item                      | Value | Notes                                                       |
|----------|---------------------------|-------|-------------------------------------------------------------|
| Margin   | Extended FAB outer margin | 16dp  | Explicitly called out in the Measurements section.          |
| Small    | Container height          | 56dp  | From the active `Extended FAB - Size - Small` token set.    |
| Small    | Icon size                 | 24dp  | From the active `Extended FAB - Size - Small` token set.    |
| Small    | Corner size               | 16dp  | Rounded corners from `md.sys.shape.corner.large`.           |
| Small    | Leading space             | 16dp  | From the active `Extended FAB - Size - Small` token set.    |
| Small    | Icon-label space          | 8dp   | From the active `Extended FAB - Size - Small` token set.    |
| Small    | Trailing space            | 16dp  | From the active `Extended FAB - Size - Small` token set.    |
| Medium   | Container height          | 80dp  | From the active `Extended FAB - Size - Medium` token set.   |
| Medium   | Icon size                 | 28dp  | From the active `Extended FAB - Size - Medium` token set.   |
| Medium   | Corner size               | 20dp  | Rounded corners from `md.sys.shape.corner.large-increased`. |
| Medium   | Leading space             | 26dp  | From the active `Extended FAB - Size - Medium` token set.   |
| Medium   | Icon-label space          | 12dp  | From the active `Extended FAB - Size - Medium` token set.   |
| Medium   | Trailing space            | 26dp  | From the active `Extended FAB - Size - Medium` token set.   |
| Large    | Container height          | 96dp  | From the active `Extended FAB - Size - Large` token set.    |
| Large    | Icon size                 | 36dp  | From the active `Extended FAB - Size - Large` token set.    |
| Large    | Corner size               | 28dp  | Rounded corners from `md.sys.shape.corner.extra-large`.     |
| Large    | Leading space             | 28dp  | From the active `Extended FAB - Size - Large` token set.    |
| Large    | Icon-label space          | 16dp  | From the active `Extended FAB - Size - Large` token set.    |
| Large    | Trailing space            | 28dp  | From the active `Extended FAB - Size - Large` token set.    |

## Implementation Notes

- Treat the baseline extended FAB as deprecated. New work should target the expressive small, medium, and large size sets instead of the legacy baseline configuration.
- Support six active color mappings: primary-container, secondary-container, tertiary-container, primary, secondary, and tertiary. The spec explicitly allows all six as equivalent contrast-safe styles.
- Keep state-layer color aligned with the foreground icon and label-text color for the non-default mappings; the spec calls this out in the States guidance.
- Hover is the only interaction state that changes elevation, rising from 6dp to 8dp. Focused and pressed preserve the base 6dp elevation and vary only the state-layer treatment.
- Small/medium/large typography scales are materially different, so size changes should switch typography tokens rather than only scaling container dimensions.
- The live token viewers for the solid primary, secondary, and tertiary mappings still contain deprecated compatibility rows; those values should not be wired into new expressive implementations.
