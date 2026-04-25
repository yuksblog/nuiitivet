<!-- markdownlint-disable MD060 -->

# Floating Action Buttons MD3 Specs

**Source:** <https://m3.material.io/components/floating-action-button/specs>  
**Collected:** 2026-04-25

## Summary

- Material Design 3 FAB specifications covering three current tonal color variants and three current size variants (baseline 56 dp, medium 80 dp, large 96 dp).
- Four interactive states documented for color variants: Enabled, Hovered, Focused, and Pressed.
- Color values were scraped from the live FAB token viewer resources for the Default / Light expressive context.
- Baseline (default) size measurements come from the Specs page Measurements section; live token viewer omits a dedicated `FAB - Size - Default` table, so values are sourced from the FAB measurements diagram.
- Deprecated baseline token sets, including Small FAB and legacy surface variants, are excluded from this document.

## Tokens & Specs

### Token Sets Discovered

| Token Set | Count | Type | Status |
|---|---:|---|---|
| FAB - Color - Tonal primary | 16 | Color | Active |
| FAB - Color - Tonal secondary | 16 | Color | Active |
| FAB - Color - Tonal tertiary | 16 | Color | Active |
| FAB - Size - Default | 4 | Size | Active |
| FAB - Size - Medium | 4 | Size | Active |
| FAB - Size - Large | 4 | Size | Active |

### FAB - Color - Tonal primary

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Color - Tonal primary | Enabled | FAB tonal primary container shadow color | md.comp.fab.primary-container.container.shadow-color | md.sys.color.shadow | #000000 |  |
| FAB - Color - Tonal primary | Focused | FAB tonal primary focused state layer color | md.comp.fab.primary-container.focused.state-layer.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Hovered | FAB tonal primary hovered state layer color | md.comp.fab.primary-container.hovered.state-layer.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Pressed | FAB tonal primary pressed state layer color | md.comp.fab.primary-container.pressed.state-layer.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Enabled | FAB tonal primary container elevation | md.comp.fab.primary-container.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal primary | Focused | FAB tonal primary focused state layer opacity | md.comp.fab.primary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal primary | Hovered | FAB tonal primary hovered state layer opacity | md.comp.fab.primary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| FAB - Color - Tonal primary | Pressed | FAB tonal primary pressed state layer opacity | md.comp.fab.primary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal primary | Focused | FAB tonal primary focused icon color | md.comp.fab.primary-container.focused.icon.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Hovered | FAB tonal primary hovered icon color | md.comp.fab.primary-container.hovered.icon.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Enabled | FAB tonal primary icon color | md.comp.fab.primary-container.icon.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Pressed | FAB tonal primary pressed icon color | md.comp.fab.primary-container.pressed.icon.color | md.sys.color.on-primary-container | #4F378B |  |
| FAB - Color - Tonal primary | Enabled | FAB tonal primary container color | md.comp.fab.primary-container.container.color | md.sys.color.primary-container | #EADDFF |  |
| FAB - Color - Tonal primary | Focused | FAB tonal primary focused container elevation | md.comp.fab.primary-container.focused.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal primary | Hovered | FAB tonal primary hovered container elevation | md.comp.fab.primary-container.hovered.container.elevation | md.sys.elevation.level4 | 8dp |  |
| FAB - Color - Tonal primary | Pressed | FAB tonal primary pressed container elevation | md.comp.fab.primary-container.pressed.container.elevation | md.sys.elevation.level3 | 6dp |  |

### FAB - Color - Tonal secondary

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Color - Tonal secondary | Enabled | FAB tonal secondary container shadow color | md.comp.fab.secondary-container.container.shadow-color | md.sys.color.shadow | #000000 |  |
| FAB - Color - Tonal secondary | Focused | FAB tonal secondary focused state layer color | md.comp.fab.secondary-container.focused.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Hovered | FAB tonal secondary hovered state layer color | md.comp.fab.secondary-container.hovered.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Pressed | FAB tonal secondary pressed state layer color | md.comp.fab.secondary-container.pressed.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Enabled | FAB tonal secondary container elevation | md.comp.fab.secondary-container.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal secondary | Focused | FAB tonal secondary focused state layer opacity | md.comp.fab.secondary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal secondary | Hovered | FAB tonal secondary hovered state layer opacity | md.comp.fab.secondary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| FAB - Color - Tonal secondary | Pressed | FAB tonal secondary pressed state layer opacity | md.comp.fab.secondary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal secondary | Focused | FAB tonal secondary focused icon color | md.comp.fab.secondary-container.focused.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Hovered | FAB tonal secondary hovered icon color | md.comp.fab.secondary-container.hovered.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Enabled | FAB tonal secondary icon color | md.comp.fab.secondary-container.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Pressed | FAB tonal secondary pressed icon color | md.comp.fab.secondary-container.pressed.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| FAB - Color - Tonal secondary | Enabled | FAB tonal secondary container color | md.comp.fab.secondary-container.container.color | md.sys.color.secondary-container | #E8DEF8 |  |
| FAB - Color - Tonal secondary | Focused | FAB tonal secondary focused container elevation | md.comp.fab.secondary-container.focused.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal secondary | Hovered | FAB tonal secondary hovered container elevation | md.comp.fab.secondary-container.hovered.container.elevation | md.sys.elevation.level4 | 8dp |  |
| FAB - Color - Tonal secondary | Pressed | FAB tonal secondary pressed container elevation | md.comp.fab.secondary-container.pressed.container.elevation | md.sys.elevation.level3 | 6dp |  |

### FAB - Color - Tonal tertiary

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Color - Tonal tertiary | Enabled | FAB tonal tertiary container shadow color | md.comp.fab.tertiary-container.container.shadow-color | md.sys.color.shadow | #000000 |  |
| FAB - Color - Tonal tertiary | Focused | FAB tonal tertiary focused state layer color | md.comp.fab.tertiary-container.focused.state-layer.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Hovered | FAB tonal tertiary hovered state layer color | md.comp.fab.tertiary-container.hovered.state-layer.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Pressed | FAB tonal tertiary pressed state layer color | md.comp.fab.tertiary-container.pressed.state-layer.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Enabled | FAB tonal tertiary container elevation | md.comp.fab.tertiary-container.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal tertiary | Focused | FAB tonal tertiary focused state layer opacity | md.comp.fab.tertiary-container.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal tertiary | Hovered | FAB tonal tertiary hovered state layer opacity | md.comp.fab.tertiary-container.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| FAB - Color - Tonal tertiary | Pressed | FAB tonal tertiary pressed state layer opacity | md.comp.fab.tertiary-container.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| FAB - Color - Tonal tertiary | Focused | FAB tonal tertiary focused icon color | md.comp.fab.tertiary-container.focused.icon.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Hovered | FAB tonal tertiary hovered icon color | md.comp.fab.tertiary-container.hovered.icon.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Enabled | FAB tonal tertiary icon color | md.comp.fab.tertiary-container.icon.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Pressed | FAB tonal tertiary pressed icon color | md.comp.fab.tertiary-container.pressed.icon.color | md.sys.color.on-tertiary-container | #633B48 |  |
| FAB - Color - Tonal tertiary | Enabled | FAB tonal tertiary container color | md.comp.fab.tertiary-container.container.color | md.sys.color.tertiary-container | #FFD8E4 |  |
| FAB - Color - Tonal tertiary | Focused | FAB tonal tertiary focused container elevation | md.comp.fab.tertiary-container.focused.container.elevation | md.sys.elevation.level3 | 6dp |  |
| FAB - Color - Tonal tertiary | Hovered | FAB tonal tertiary hovered container elevation | md.comp.fab.tertiary-container.hovered.container.elevation | md.sys.elevation.level4 | 8dp |  |
| FAB - Color - Tonal tertiary | Pressed | FAB tonal tertiary pressed container elevation | md.comp.fab.tertiary-container.pressed.container.elevation | md.sys.elevation.level3 | 6dp |  |

### FAB - Size - Default

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Size - Default | Layout | FAB container height | md.comp.fab.container.height |  | 56dp | Baseline FAB size per Specs Measurements. |
| FAB - Size - Default | Layout | FAB container width | md.comp.fab.container.width |  | 56dp | Baseline FAB size per Specs Measurements. |
| FAB - Size - Default | Layout | FAB icon size | md.comp.fab.icon.size |  | 24dp | Baseline FAB icon size per Specs Measurements. |
| FAB - Size - Default | Shape | FAB container shape | md.comp.fab.container.shape | md.sys.shape.corner.large | 16dp | Resolved as rounded corners. |

### FAB - Size - Medium

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Size - Medium | Layout | FAB medium container height | md.comp.fab.medium.container.height |  | 80dp |  |
| FAB - Size - Medium | Layout | FAB medium container width | md.comp.fab.medium.container.width |  | 80dp |  |
| FAB - Size - Medium | Layout | FAB medium icon size | md.comp.fab.medium.icon.size |  | 28dp |  |
| FAB - Size - Medium | Shape | FAB medium container shape | md.comp.fab.medium.container.shape | md.sys.shape.corner.large-increased | 20dp | Resolved as rounded corners. |

### FAB - Size - Large

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| FAB - Size - Large | Layout | FAB large container height | md.comp.fab.large.container.height |  | 96dp |  |
| FAB - Size - Large | Layout | FAB large container width | md.comp.fab.large.container.width |  | 96dp |  |
| FAB - Size - Large | Layout | FAB large icon size | md.comp.fab.large.icon.size |  | 36dp |  |
| FAB - Size - Large | Shape | FAB large container shape | md.comp.fab.large.container.shape | md.sys.shape.corner.extra-large | 28dp | Resolved as rounded corners. |
