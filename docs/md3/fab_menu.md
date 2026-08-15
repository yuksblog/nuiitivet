<!-- markdownlint-disable MD060 -->

# FAB Menu MD3 Specs

Source: <https://m3.material.io/components/fab-menu/specs>
Collected: 2026-05-25

## Summary

- The active FAB menu token viewer exposes seven non-deprecated token sets: one shared geometry set, three close-button color sets, and three list-item color sets.
- Resolved values below use the viewer's default Android / 1P Baseline / Light / Default-contrast context, with Standard motion, Static font, and no iOS dark elevation override.
- The common set fixes both the close button and menu item height at 56dp, uses fully rounded corners, and sets the menu-item padding rhythm to 24dp leading, 8dp icon-label spacing, 24dp trailing, and 4dp between-item spacing.
- Close-button color sets use solid `primary`, `secondary`, and `tertiary` fills with `on-*` foreground colors; list-item color sets use the corresponding `*-container` fills with `on-*-container` foreground colors.
- Hover is the only interaction state that raises elevation to 8dp. Focused and pressed keep 6dp elevation, while state-layer opacities follow the standard MD3 0.08 hover and 0.1 focus/press values.
- The Measurements section explicitly calls out a 56dp close button, 16dp outer FAB margins, a 40dp opened bottom margin from medium FABs, a 56dp opened bottom margin from large FABs, and a recommended 4dp web gap between the FAB and menu.

## Tokens & Specs

State-layer opacity rows below use the live token viewer's displayed values. The embedded payload preserves the semantic source tokens but omits the resolved numeric opacity in `resolvedValue`.

### Token sets discovered

| Token set                                 | Count | Notes                                                                                  |
|-------------------------------------------|------:|----------------------------------------------------------------------------------------|
| FAB menu - Common                         |    15 | Shared geometry, shape, elevation, and typography for the close button and menu items. |
| FAB menu close button - Color - Primary   |    15 | Solid primary close-button mapping.                                                    |
| FAB menu close button - Color - Secondary |    15 | Solid secondary close-button mapping.                                                  |
| FAB menu close button - Color - Tertiary  |    15 | Solid tertiary close-button mapping.                                                   |
| FAB menu list items - Color - Primary     |    19 | Primary-container list-item mapping.                                                   |
| FAB menu list items - Color - Secondary   |    19 | Secondary-container list-item mapping.                                                 |
| FAB menu list items - Color - Tertiary    |    19 | Tertiary-container list-item mapping.                                                  |

### FAB menu - Common

| Token set         | Group        | Label                                     | Token                                             | Source token                  | Value                                | Notes                                                                                             |
|-------------------|--------------|-------------------------------------------|---------------------------------------------------|-------------------------------|--------------------------------------|---------------------------------------------------------------------------------------------------|
| FAB menu - Common | Close button | FAB menu close button container height    | md.comp.fab-menu.close-button.container.height    |                               | 56dp                                 |                                                                                                   |
| FAB menu - Common | Close button | FAB menu close width                      | md.comp.fab-menu.close-button.container.width     |                               | 56dp                                 |                                                                                                   |
| FAB menu - Common | Close button | FAB menu close button icon size           | md.comp.fab-menu.close-button.icon.size           |                               | 20dp                                 |                                                                                                   |
| FAB menu - Common | Close button | FAB menu close button container elevation | md.comp.fab-menu.close-button.container.elevation | md.sys.elevation.level3       | 6dp                                  |                                                                                                   |
| FAB menu - Common | Close button | FAB menu close button container shape     | md.comp.fab-menu.close-button.container.shape     | md.sys.shape.corner.full      | Fully rounded                        |                                                                                                   |
| FAB menu - Common | Close button | FAB menu close button between space       | md.comp.fab-menu.close-button.between-space       |                               | 8dp                                  |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item container height     | md.comp.fab-menu.menu-item.container.height       |                               | 56dp                                 |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item label text           | md.comp.fab-menu.menu-item.label-text             | md.sys.typescale.title-medium | Google Sans Text / 500 / 16pt / 24pt | Composite typography token; tracking is not exposed in the resolved payload.                      |
| FAB menu - Common | List item    | FAB menu - menu item icon size            | md.comp.fab-menu.menu-item.icon.size              |                               | 24dp                                 |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item container elevation  | md.comp.fab-menu.menu-item.container.elevation    | md.sys.elevation.level0       | 0dp                                  | Level-0 elevation is serialized without a numeric value in the payload and was normalized to 0dp. |
| FAB menu - Common | List item    | FAB menu - menu item container shape      | md.comp.fab-menu.menu-item.container.shape        | md.sys.shape.corner.full      | Fully rounded                        |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item leading space        | md.comp.fab-menu.menu-item.leading-space          |                               | 24dp                                 |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item icon label space     | md.comp.fab-menu.menu-item.icon-label-space       |                               | 8dp                                  |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item trailing space       | md.comp.fab-menu.menu-item.trailing-space         |                               | 24dp                                 |                                                                                                   |
| FAB menu - Common | List item    | FAB menu - menu item between space        | md.comp.fab-menu.menu-item.between-space          |                               | 4dp                                  |                                                                                                   |

### FAB menu close button - Color - Primary

| Token set                               | Group   | Label                                                     | Token                                                             | Source token                             | Value   | Notes |
|-----------------------------------------|---------|-----------------------------------------------------------|-------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu close button - Color - Primary | Enabled | FAB menu primary close button container color             | md.comp.fab-menu.primary.close-button.container.color             | md.sys.color.primary                     | #6750A4 |       |
| FAB menu close button - Color - Primary | Enabled | FAB menu primary close button container shadow color      | md.comp.fab-menu.primary.close-button.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu close button - Color - Primary | Enabled | FAB menu primary close button icon color                  | md.comp.fab-menu.primary.close-button.icon.color                  | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Focused | FAB menu primary close button focused container elevation | md.comp.fab-menu.primary.close-button.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Primary | Focused | FAB menu primary close button focused state layer color   | md.comp.fab-menu.primary.close-button.focused.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Focused | FAB menu primary close button focused state layer opacity | md.comp.fab-menu.primary.close-button.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu close button - Color - Primary | Focused | FAB menu primary close button focused icon color          | md.comp.fab-menu.primary.close-button.focused.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Hovered | FAB menu primary close button hovered container elevation | md.comp.fab-menu.primary.close-button.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu close button - Color - Primary | Hovered | FAB menu primary close button hovered state layer color   | md.comp.fab-menu.primary.close-button.hovered.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Hovered | FAB menu primary close button hovered state layer opacity | md.comp.fab-menu.primary.close-button.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu close button - Color - Primary | Hovered | FAB menu primary close button hovered icon color          | md.comp.fab-menu.primary.close-button.hovered.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Pressed | FAB menu primary close button pressed container elevation | md.comp.fab-menu.primary.close-button.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Primary | Pressed | FAB menu primary close button pressed state layer color   | md.comp.fab-menu.primary.close-button.pressed.state-layer.color   | md.sys.color.on-primary                  | #FFFFFF |       |
| FAB menu close button - Color - Primary | Pressed | FAB menu primary close button pressed state layer opacity | md.comp.fab-menu.primary.close-button.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu close button - Color - Primary | Pressed | FAB menu primary close button pressed icon color          | md.comp.fab-menu.primary.close-button.pressed.icon.color          | md.sys.color.on-primary                  | #FFFFFF |       |

### FAB menu close button - Color - Secondary

| Token set                                 | Group   | Label                                                       | Token                                                               | Source token                             | Value   | Notes |
|-------------------------------------------|---------|-------------------------------------------------------------|---------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu close button - Color - Secondary | Enabled | FAB menu secondary close button container color             | md.comp.fab-menu.secondary.close-button.container.color             | md.sys.color.secondary                   | #625B71 |       |
| FAB menu close button - Color - Secondary | Enabled | FAB menu secondary close button container shadow color      | md.comp.fab-menu.secondary.close-button.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu close button - Color - Secondary | Enabled | FAB menu secondary close button icon color                  | md.comp.fab-menu.secondary.close-button.icon.color                  | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Focused | FAB menu secondary close button focused container elevation | md.comp.fab-menu.secondary.close-button.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Secondary | Focused | FAB menu secondary close button focused state layer color   | md.comp.fab-menu.secondary.close-button.focused.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Focused | FAB menu secondary close button focused state layer opacity | md.comp.fab-menu.secondary.close-button.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu close button - Color - Secondary | Focused | FAB menu secondary close button focused icon color          | md.comp.fab-menu.secondary.close-button.focused.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Hovered | FAB menu secondary close button hovered container elevation | md.comp.fab-menu.secondary.close-button.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu close button - Color - Secondary | Hovered | FAB menu secondary close button hovered state layer color   | md.comp.fab-menu.secondary.close-button.hovered.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Hovered | FAB menu secondary close button hovered state layer opacity | md.comp.fab-menu.secondary.close-button.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu close button - Color - Secondary | Hovered | FAB menu secondary close button hovered icon color          | md.comp.fab-menu.secondary.close-button.hovered.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Pressed | FAB menu secondary close button pressed container elevation | md.comp.fab-menu.secondary.close-button.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Secondary | Pressed | FAB menu secondary close button pressed state layer color   | md.comp.fab-menu.secondary.close-button.pressed.state-layer.color   | md.sys.color.on-secondary                | #FFFFFF |       |
| FAB menu close button - Color - Secondary | Pressed | FAB menu secondary close button pressed state layer opacity | md.comp.fab-menu.secondary.close-button.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu close button - Color - Secondary | Pressed | FAB menu secondary close button pressed icon color          | md.comp.fab-menu.secondary.close-button.pressed.icon.color          | md.sys.color.on-secondary                | #FFFFFF |       |

### FAB menu close button - Color - Tertiary

| Token set                                | Group   | Label                                                      | Token                                                              | Source token                             | Value   | Notes |
|------------------------------------------|---------|------------------------------------------------------------|--------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu close button - Color - Tertiary | Enabled | FAB menu tertiary close button container color             | md.comp.fab-menu.tertiary.close-button.container.color             | md.sys.color.tertiary                    | #7D5260 |       |
| FAB menu close button - Color - Tertiary | Enabled | FAB menu tertiary close button container shadow color      | md.comp.fab-menu.tertiary.close-button.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu close button - Color - Tertiary | Enabled | FAB menu tertiary close button icon color                  | md.comp.fab-menu.tertiary.close-button.icon.color                  | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Focused | FAB menu tertiary close button focused container elevation | md.comp.fab-menu.tertiary.close-button.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Tertiary | Focused | FAB menu tertiary close button focused state layer color   | md.comp.fab-menu.tertiary.close-button.focused.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Focused | FAB menu tertiary close button focused state layer opacity | md.comp.fab-menu.tertiary.close-button.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu close button - Color - Tertiary | Focused | FAB menu tertiary close button focused icon color          | md.comp.fab-menu.tertiary.close-button.focused.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Hovered | FAB menu tertiary close button hovered container elevation | md.comp.fab-menu.tertiary.close-button.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu close button - Color - Tertiary | Hovered | FAB menu tertiary close button hovered state layer color   | md.comp.fab-menu.tertiary.close-button.hovered.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Hovered | FAB menu tertiary close button hovered state layer opacity | md.comp.fab-menu.tertiary.close-button.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu close button - Color - Tertiary | Hovered | FAB menu tertiary close button hovered icon color          | md.comp.fab-menu.tertiary.close-button.hovered.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Pressed | FAB menu tertiary close button pressed container elevation | md.comp.fab-menu.tertiary.close-button.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu close button - Color - Tertiary | Pressed | FAB menu tertiary close button pressed state layer color   | md.comp.fab-menu.tertiary.close-button.pressed.state-layer.color   | md.sys.color.on-tertiary                 | #FFFFFF |       |
| FAB menu close button - Color - Tertiary | Pressed | FAB menu tertiary close button pressed state layer opacity | md.comp.fab-menu.tertiary.close-button.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu close button - Color - Tertiary | Pressed | FAB menu tertiary close button pressed icon color          | md.comp.fab-menu.tertiary.close-button.pressed.icon.color          | md.sys.color.on-tertiary                 | #FFFFFF |       |

### FAB menu list items - Color - Primary

| Token set                             | Group   | Label                                                  | Token                                                                    | Source token                             | Value   | Notes |
|---------------------------------------|---------|--------------------------------------------------------|--------------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu list items - Color - Primary | Enabled | FAB menu primary list item container color             | md.comp.fab-menu.primary-container.list-item.container.color             | md.sys.color.primary-container           | #EADDFF |       |
| FAB menu list items - Color - Primary | Enabled | FAB menu primary list item container shadow color      | md.comp.fab-menu.primary-container.list-item.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu list items - Color - Primary | Enabled | FAB menu primary list item icon color                  | md.comp.fab-menu.primary-container.list-item.icon.color                  | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Enabled | FAB menu primary list item label text color            | md.comp.fab-menu.primary-container.list-item.label-text.color            | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Focused | FAB menu primary list item focused container elevation | md.comp.fab-menu.primary-container.list-item.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Primary | Focused | FAB menu primary list item focused state layer color   | md.comp.fab-menu.primary-container.list-item.focused.state-layer.color   | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Focused | FAB menu primary list item focused state layer opacity | md.comp.fab-menu.primary-container.list-item.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu list items - Color - Primary | Focused | FAB menu primary list item focused icon color          | md.comp.fab-menu.primary-container.list-item.focused.icon.color          | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Focused | FAB menu primary list item focused label text color    | md.comp.fab-menu.primary-container.list-item.focused.label-text.color    | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Hovered | FAB menu primary list item hovered container elevation | md.comp.fab-menu.primary-container.list-item.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu list items - Color - Primary | Hovered | FAB menu primary list item hovered state layer color   | md.comp.fab-menu.primary-container.list-item.hovered.state-layer.color   | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Hovered | FAB menu primary list item hovered state layer opacity | md.comp.fab-menu.primary-container.list-item.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu list items - Color - Primary | Hovered | FAB menu primary list item hovered icon color          | md.comp.fab-menu.primary-container.list-item.hovered.icon.color          | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Hovered | FAB menu primary list item hovered label text color    | md.comp.fab-menu.primary-container.list-item.hovered.label-text.color    | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Pressed | FAB menu primary list item pressed container elevation | md.comp.fab-menu.primary-container.list-item.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Primary | Pressed | FAB menu primary list item pressed state layer color   | md.comp.fab-menu.primary-container.list-item.pressed.state-layer.color   | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Pressed | FAB menu primary list item pressed state layer opacity | md.comp.fab-menu.primary-container.list-item.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu list items - Color - Primary | Pressed | FAB menu primary list item pressed icon color          | md.comp.fab-menu.primary-container.list-item.pressed.icon.color          | md.sys.color.on-primary-container        | #4F378B |       |
| FAB menu list items - Color - Primary | Pressed | FAB menu primary list item pressed label text color    | md.comp.fab-menu.primary-container.list-item.pressed.label-text.color    | md.sys.color.on-primary-container        | #4F378B |       |

### FAB menu list items - Color - Secondary

| Token set                               | Group   | Label                                                    | Token                                                                      | Source token                             | Value   | Notes |
|-----------------------------------------|---------|----------------------------------------------------------|----------------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu list items - Color - Secondary | Enabled | FAB menu secondary list item container color             | md.comp.fab-menu.secondary-container.list-item.container.color             | md.sys.color.secondary-container         | #E8DEF8 |       |
| FAB menu list items - Color - Secondary | Enabled | FAB menu secondary list item container shadow color      | md.comp.fab-menu.secondary-container.list-item.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu list items - Color - Secondary | Enabled | FAB menu secondary list item icon color                  | md.comp.fab-menu.secondary-container.list-item.icon.color                  | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Enabled | FAB menu secondary list item label text color            | md.comp.fab-menu.secondary-container.list-item.label-text.color            | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Focused | FAB menu secondary list item focused container elevation | md.comp.fab-menu.secondary-container.list-item.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Secondary | Focused | FAB menu secondary list item focused state layer color   | md.comp.fab-menu.secondary-container.list-item.focused.state-layer.color   | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Focused | FAB menu secondary list item focused state layer opacity | md.comp.fab-menu.secondary-container.list-item.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu list items - Color - Secondary | Focused | FAB menu secondary list item focused icon color          | md.comp.fab-menu.secondary-container.list-item.focused.icon.color          | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Focused | FAB menu secondary list item focused label text color    | md.comp.fab-menu.secondary-container.list-item.focused.label-text.color    | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Hovered | FAB menu secondary list item hovered container elevation | md.comp.fab-menu.secondary-container.list-item.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu list items - Color - Secondary | Hovered | FAB menu secondary list item hovered state layer color   | md.comp.fab-menu.secondary-container.list-item.hovered.state-layer.color   | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Hovered | FAB menu secondary list item hovered state layer opacity | md.comp.fab-menu.secondary-container.list-item.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu list items - Color - Secondary | Hovered | FAB menu secondary list item hovered icon color          | md.comp.fab-menu.secondary-container.list-item.hovered.icon.color          | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Hovered | FAB menu secondary list item hovered label text color    | md.comp.fab-menu.secondary-container.list-item.hovered.label-text.color    | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Pressed | FAB menu secondary list item pressed container elevation | md.comp.fab-menu.secondary-container.list-item.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Secondary | Pressed | FAB menu secondary list item pressed state layer color   | md.comp.fab-menu.secondary-container.list-item.pressed.state-layer.color   | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Pressed | FAB menu secondary list item pressed state layer opacity | md.comp.fab-menu.secondary-container.list-item.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu list items - Color - Secondary | Pressed | FAB menu secondary list item pressed icon color          | md.comp.fab-menu.secondary-container.list-item.pressed.icon.color          | md.sys.color.on-secondary-container      | #4A4458 |       |
| FAB menu list items - Color - Secondary | Pressed | FAB menu secondary list item pressed label text color    | md.comp.fab-menu.secondary-container.list-item.pressed.label-text.color    | md.sys.color.on-secondary-container      | #4A4458 |       |

### FAB menu list items - Color - Tertiary

| Token set                              | Group   | Label                                                   | Token                                                                     | Source token                             | Value   | Notes |
|----------------------------------------|---------|---------------------------------------------------------|---------------------------------------------------------------------------|------------------------------------------|---------|-------|
| FAB menu list items - Color - Tertiary | Enabled | FAB menu tertiary list item container color             | md.comp.fab-menu.tertiary-container.list-item.container.color             | md.sys.color.tertiary-container          | #FFD8E4 |       |
| FAB menu list items - Color - Tertiary | Enabled | FAB menu tertiary list item container shadow color      | md.comp.fab-menu.tertiary-container.list-item.container.shadow-color      | md.sys.color.shadow                      | #000000 |       |
| FAB menu list items - Color - Tertiary | Enabled | FAB menu tertiary list item icon color                  | md.comp.fab-menu.tertiary-container.list-item.icon.color                  | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Enabled | FAB menu tertiary list item label text color            | md.comp.fab-menu.tertiary-container.list-item.label-text.color            | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Focused | FAB menu tertiary list item focused container elevation | md.comp.fab-menu.tertiary-container.list-item.focused.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Tertiary | Focused | FAB menu tertiary list item focused state layer color   | md.comp.fab-menu.tertiary-container.list-item.focused.state-layer.color   | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Focused | FAB menu tertiary list item focused state layer opacity | md.comp.fab-menu.tertiary-container.list-item.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity   | 0.1     |       |
| FAB menu list items - Color - Tertiary | Focused | FAB menu tertiary list item focused icon color          | md.comp.fab-menu.tertiary-container.list-item.focused.icon.color          | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Focused | FAB menu tertiary list item focused label text color    | md.comp.fab-menu.tertiary-container.list-item.focused.label-text.color    | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Hovered | FAB menu tertiary list item hovered container elevation | md.comp.fab-menu.tertiary-container.list-item.hovered.container.elevation | md.sys.elevation.level4                  | 8dp     |       |
| FAB menu list items - Color - Tertiary | Hovered | FAB menu tertiary list item hovered state layer color   | md.comp.fab-menu.tertiary-container.list-item.hovered.state-layer.color   | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Hovered | FAB menu tertiary list item hovered state layer opacity | md.comp.fab-menu.tertiary-container.list-item.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity   | 0.08    |       |
| FAB menu list items - Color - Tertiary | Hovered | FAB menu tertiary list item hovered icon color          | md.comp.fab-menu.tertiary-container.list-item.hovered.icon.color          | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Hovered | FAB menu tertiary list item hovered label text color    | md.comp.fab-menu.tertiary-container.list-item.hovered.label-text.color    | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Pressed | FAB menu tertiary list item pressed container elevation | md.comp.fab-menu.tertiary-container.list-item.pressed.container.elevation | md.sys.elevation.level3                  | 6dp     |       |
| FAB menu list items - Color - Tertiary | Pressed | FAB menu tertiary list item pressed state layer color   | md.comp.fab-menu.tertiary-container.list-item.pressed.state-layer.color   | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Pressed | FAB menu tertiary list item pressed state layer opacity | md.comp.fab-menu.tertiary-container.list-item.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1     |       |
| FAB menu list items - Color - Tertiary | Pressed | FAB menu tertiary list item pressed icon color          | md.comp.fab-menu.tertiary-container.list-item.pressed.icon.color          | md.sys.color.on-tertiary-container       | #633B48 |       |
| FAB menu list items - Color - Tertiary | Pressed | FAB menu tertiary list item pressed label text color    | md.comp.fab-menu.tertiary-container.list-item.pressed.label-text.color    | md.sys.color.on-tertiary-container       | #633B48 |       |

## Measurements

| Category   | Item                            | Value                                | Notes                                                                                   |
|------------|---------------------------------|--------------------------------------|-----------------------------------------------------------------------------------------|
| Geometry   | Close button size               | 56dp                                 | Explicitly called out in Measurements and reinforced by the common token set.           |
| Geometry   | Close button icon size          | 20dp                                 | From the common token set.                                                              |
| Geometry   | Close button corner treatment   | Fully rounded                        | From `md.comp.fab-menu.close-button.container.shape`.                                   |
| Geometry   | Close button between space      | 8dp                                  | From the common token set.                                                              |
| Geometry   | Menu item height                | 56dp                                 | Menu items share the same measurements as the medium button specs.                      |
| Typography | Menu item label text            | Google Sans Text / 500 / 16pt / 24pt | Mapped to `md.sys.typescale.title-medium`.                                              |
| Geometry   | Menu item icon size             | 24dp                                 | From the common token set.                                                              |
| Geometry   | Menu item corner treatment      | Fully rounded                        | From `md.comp.fab-menu.menu-item.container.shape`.                                      |
| Geometry   | Menu item base elevation        | 0dp                                  | `md.sys.elevation.level0`, normalized from a unit-only payload entry.                   |
| Geometry   | Menu item leading space         | 24dp                                 | From the common token set.                                                              |
| Geometry   | Menu item icon-label space      | 8dp                                  | From the common token set.                                                              |
| Geometry   | Menu item trailing space        | 24dp                                 | From the common token set.                                                              |
| Geometry   | Menu item between space         | 4dp                                  | From the common token set.                                                              |
| Placement  | FAB outer margin                | 16dp                                 | The spec explicitly says the FAB should always have 16dp margins.                       |
| Placement  | Medium FAB opened bottom margin | 40dp                                 | The opened menu places the close button higher to align with the top of the medium FAB. |
| Placement  | Large FAB opened bottom margin  | 56dp                                 | The opened menu places the close button higher to align with the top of the large FAB.  |
| Placement  | Anchor point                    | Top trailing corner                  | The close button and FAB share the same top trailing anchor position.                   |
| Motion     | Expansion direction             | From the FAB's top trailing edge     | Explicitly called out in Measurements for smooth animation.                             |
| Web        | Recommended FAB-to-menu gap     | 4dp                                  | The gap can vary on web, but 4dp is recommended.                                        |
| Web        | Baseline behavior source        | Baseline menu component              | The web FAB menu inherits states and specs from the baseline menu component.            |

- The FAB menu animates from the top trailing edge of the FAB to ensure a smooth animation.
- Larger FABs will place the FAB menu slightly higher, with larger margins underneath.

## Implementation Notes

- Keep the geometry token set separate from the color token sets in implementation. The spec treats the close button and list-item layout as common across all color variants.
- Use solid theme colors for the close button and container theme colors for list items. The page's color section and token viewer align on that distinction.
- Wire hover to `md.sys.elevation.level4` and focus/press to `md.sys.elevation.level3` for both close buttons and list items.
- Treat menu-item base elevation as `md.sys.elevation.level0` even though the raw payload serializes the value without an explicit numeric component.
- Preserve the 24dp / 8dp / 24dp menu-item internal spacing and the 4dp between-item gap; those values materially shape the menu's visual rhythm.
- On web, keep the FAB menu visually tied to the invoking FAB and start from the baseline menu behavior, with a recommended 4dp separation.
