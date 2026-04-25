<!-- markdownlint-disable MD060 -->

# Icon Buttons MD3 Specs

**Source:** <https://m3.material.io/components/icon-buttons/specs>  
**Collected:** 2026-04-25

## Summary

- Material Design 3 icon button specifications covering four color variants (Filled, Tonal, Outlined, Standard) and five size variants (Xsmall, Small, Medium, Large, Xlarge).
- Five interactive states documented for color variants: Enabled, Disabled, Hovered, Focused, and Pressed.
- Toggle icon button selected and unselected states are included where present in the MD3 token set.
- Values and source tokens were scraped from the live token viewer payload for the Default / Light context.

## Tokens & Specs

### Token Sets Discovered

| Token Set | Count | Type | Status |
|---|---:|---|---|
| Icon button - Color - Filled | 31 | Color | Active |
| Icon button - Color - Tonal | 31 | Color | Active |
| Icon button - Color - Outlined | 33 | Color | Active |
| Icon button - Color - Standard | 26 | Color | Active |
| Icon button - Size - Xsmall | 16 | Size | Active |
| Icon button - Size - Small | 16 | Size | Active |
| Icon button - Size - Medium | 16 | Size | Active |
| Icon button - Size - Large | 16 | Size | Active |
| Icon button - Size - Xlarge | 16 | Size | Active |

### Icon button - Color - Filled

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Color - Filled | Enabled | Icon button filled container color | md.comp.icon-button.filled.container.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Filled | Disabled | Icon button filled disabled container color | md.comp.icon-button.filled.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Filled | Hovered | Icon button filled hovered state layer color | md.comp.icon-button.filled.hovered.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Focused | Icon button filled focused state layer color | md.comp.icon-button.filled.focused.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Pressed | Icon button filled pressed state layer color | md.comp.icon-button.filled.pressed.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Enabled / Toggle unselected | Icon button filled container color - toggle (unselected) | md.comp.icon-button.filled.unselected.container.color | md.sys.color.surface-container | #F3EDF7 |  |
| Icon button - Color - Filled | Disabled | Icon button filled disabled container opacity | md.comp.icon-button.filled.disabled.container.opacity |  | 0.1 |  |
| Icon button - Color - Filled | Focused / Toggle unselected | Icon button filled focused state layer color - toggle (unselected) | md.comp.icon-button.filled.unselected.focused.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Pressed / Toggle unselected | Icon button filled pressed state layer color - toggle (unselected) | md.comp.icon-button.filled.unselected.pressed.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Disabled | Icon button filled disabled icon color | md.comp.icon-button.filled.disabled.icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Filled | Focused / Toggle selected | Icon button filled focused state layer color - toggle (selected) | md.comp.icon-button.filled.selected.focused.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Pressed / Toggle selected | Icon button filled pressed state layer color - toggle (selected) | md.comp.icon-button.filled.selected.pressed.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Disabled | Icon button filled disabled icon opacity | md.comp.icon-button.filled.disabled.icon.opacity |  | 0.38 |  |
| Icon button - Color - Filled | Hovered / Toggle unselected | Icon button filled hovered state layer color - toggle (unselected) | md.comp.icon-button.filled.unselected.hovered.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Focused | Icon button filled focused state layer opacity | md.comp.icon-button.filled.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| Icon button - Color - Filled | Enabled / Toggle selected | Icon button filled container color - toggle (selected) | md.comp.icon-button.filled.selected.container.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Filled | Hovered / Toggle selected | Icon button filled hovered state layer color - toggle (selected) | md.comp.icon-button.filled.selected.hovered.state-layer.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Focused | Icon button filled focused icon color | md.comp.icon-button.filled.focused.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Enabled | Icon button filled icon color | md.comp.icon-button.filled.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Hovered | Icon button filled hovered state layer opacity | md.comp.icon-button.filled.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Icon button - Color - Filled | Pressed | Icon button filled pressed state layer opacity | md.comp.icon-button.filled.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| Icon button - Color - Filled | Enabled / Toggle unselected | Icon button filled icon color - toggle (unselected) | md.comp.icon-button.filled.unselected.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Hovered | Icon button filled hovered icon color | md.comp.icon-button.filled.hovered.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Focused / Toggle unselected | Icon button filled focused icon color - toggle (unselected) | md.comp.icon-button.filled.unselected.focused.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Pressed | Icon button filled pressed icon color | md.comp.icon-button.filled.pressed.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Enabled / Toggle selected | Icon button filled icon color - toggle (selected) | md.comp.icon-button.filled.selected.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Hovered / Toggle unselected | Icon button filled hovered icon color - toggle (unselected) | md.comp.icon-button.filled.unselected.hovered.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Focused / Toggle selected | Icon button filled focused icon color - toggle (selected) | md.comp.icon-button.filled.selected.focused.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Pressed / Toggle unselected | Icon button filled pressed icon color - toggle (unselected) | md.comp.icon-button.filled.unselected.pressed.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Filled | Hovered / Toggle selected | Icon button filled hovered icon color - toggle (selected) | md.comp.icon-button.filled.selected.hovered.icon.color | md.sys.color.on-primary | #FFFFFF |  |
| Icon button - Color - Filled | Pressed / Toggle selected | Icon button filled pressed icon color - toggle (selected) | md.comp.icon-button.filled.selected.pressed.icon.color | md.sys.color.on-primary | #FFFFFF |  |

### Icon button - Color - Tonal

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Color - Tonal | Pressed | Icon button tonal pressed state layer color | md.comp.icon-button.tonal.pressed.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Focused | Icon button tonal focused state layer color | md.comp.icon-button.tonal.focused.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Hovered | Icon button tonal hovered state layer color | md.comp.icon-button.tonal.hovered.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Disabled | Icon button tonal disabled container color | md.comp.icon-button.tonal.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Tonal | Enabled | Icon button tonal container color | md.comp.icon-button.tonal.container.color | md.sys.color.secondary-container | #E8DEF8 |  |
| Icon button - Color - Tonal | Disabled | Icon button tonal disabled container opacity | md.comp.icon-button.tonal.disabled.container.opacity |  | 0.1 |  |
| Icon button - Color - Tonal | Enabled / Toggle unselected | Icon button tonal container color - toggle (unselected) | md.comp.icon-button.tonal.unselected.container.color | md.sys.color.secondary-container | #E8DEF8 |  |
| Icon button - Color - Tonal | Hovered / Toggle unselected | Icon button tonal hovered state layer color - toggle (unselected) | md.comp.icon-button.tonal.unselected.hovered.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Focused / Toggle unselected | Icon button tonal focused state layer color - toggle (unselected) | md.comp.icon-button.tonal.unselected.focused.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Pressed / Toggle unselected | Icon button tonal pressed state layer color - toggle (unselected) | md.comp.icon-button.tonal.unselected.pressed.state-layer.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Disabled | Icon button tonal disabled icon color | md.comp.icon-button.tonal.disabled.icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Tonal | Enabled / Toggle selected | Icon button tonal container color - toggle (selected) | md.comp.icon-button.tonal.selected.container.color | md.sys.color.secondary | #625B71 |  |
| Icon button - Color - Tonal | Hovered / Toggle selected | Icon button tonal hovered state layer color - toggle (selected) | md.comp.icon-button.tonal.selected.hovered.state-layer.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Focused / Toggle selected | Icon button tonal focused state layer color - toggle (selected) | md.comp.icon-button.tonal.selected.focused.state-layer.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Pressed / Toggle selected | Icon button tonal pressed state layer color - toggle (selected) | md.comp.icon-button.tonal.selected.pressed.state-layer.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Pressed | Icon button tonal pressed state layer opacity | md.comp.icon-button.tonal.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| Icon button - Color - Tonal | Disabled | Icon button tonal disabled icon opacity | md.comp.icon-button.tonal.disabled.icon.opacity |  | 0.38 |  |
| Icon button - Color - Tonal | Focused | Icon button tonal focused state layer opacity | md.comp.icon-button.tonal.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| Icon button - Color - Tonal | Enabled | Icon button tonal icon color | md.comp.icon-button.tonal.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Focused | Icon button tonal focused icon color | md.comp.icon-button.tonal.focused.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Enabled / Toggle unselected | Icon button tonal icon color - toggle (unselected) | md.comp.icon-button.tonal.unselected.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Pressed | Icon button tonal pressed icon color | md.comp.icon-button.tonal.pressed.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Enabled / Toggle selected | Icon button tonal icon color - toggle (selected) | md.comp.icon-button.tonal.selected.icon.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Focused / Toggle unselected | Icon button tonal focused icon color - toggle (unselected) | md.comp.icon-button.tonal.unselected.focused.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Hovered | Icon button tonal hovered state layer opacity | md.comp.icon-button.tonal.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Icon button - Color - Tonal | Focused / Toggle selected | Icon button tonal focused icon color - toggle (selected) | md.comp.icon-button.tonal.selected.focused.icon.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Pressed / Toggle unselected | Icon button tonal pressed icon color - toggle (unselected) | md.comp.icon-button.tonal.unselected.pressed.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Hovered | Icon button tonal hovered icon color | md.comp.icon-button.tonal.hovered.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Pressed / Toggle selected | Icon button tonal pressed icon color - toggle (selected) | md.comp.icon-button.tonal.selected.pressed.icon.color | md.sys.color.on-secondary | #FFFFFF |  |
| Icon button - Color - Tonal | Hovered / Toggle unselected | Icon button tonal hovered icon color - toggle (unselected) | md.comp.icon-button.tonal.unselected.hovered.icon.color | md.sys.color.on-secondary-container | #4A4458 |  |
| Icon button - Color - Tonal | Hovered / Toggle selected | Icon button tonal hovered icon color - toggle (selected) | md.comp.icon-button.tonal.selected.hovered.icon.color | md.sys.color.on-secondary | #FFFFFF |  |

### Icon button - Color - Outlined

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Color - Outlined | Hovered | Icon button outlined hovered state layer color | md.comp.icon-button.outlined.hovered.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Focused | Icon button outlined focused state layer color | md.comp.icon-button.outlined.focused.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Enabled | Icon button outlined color | md.comp.icon-button.outlined.outline.color | md.sys.color.outline-variant | #CAC4D0 |  |
| Icon button - Color - Outlined | Disabled | Icon button outlined disabled outline color | md.comp.icon-button.outlined.disabled.outline.color | md.sys.color.outline-variant | #CAC4D0 |  |
| Icon button - Color - Outlined | Focused / Toggle unselected | Icon button outlined focused state layer color - toggle (unselected) | md.comp.icon-button.outlined.unselected.focused.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Enabled / Toggle unselected | Icon button outlined color - toggle (unselected) | md.comp.icon-button.outlined.unselected.outline.color | md.sys.color.outline-variant | #CAC4D0 |  |
| Icon button - Color - Outlined | Disabled / Toggle unselected | Icon button outlined disabled outline color (unselected) | md.comp.icon-button.outlined.unselected.disabled.outline.color | md.sys.color.outline-variant | #CAC4D0 |  |
| Icon button - Color - Outlined | Enabled / Toggle selected | Icon button outlined container color - toggle (selected) | md.comp.icon-button.outlined.selected.container.color | md.sys.color.inverse-surface | #322F35 |  |
| Icon button - Color - Outlined | Focused / Toggle selected | Icon button outlined focused state layer color - toggle (selected) | md.comp.icon-button.outlined.selected.focused.state-layer.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Disabled / Toggle selected | Icon button outlined disabled container color (selected) | md.comp.icon-button.outlined.selected.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Outlined | Enabled | Icon button outlined icon color | md.comp.icon-button.outlined.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Pressed | Icon button outlined pressed state layer color | md.comp.icon-button.outlined.pressed.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Disabled / Toggle selected | Icon button outlined disabled container opacity (selected) | md.comp.icon-button.outlined.selected.disabled.container.opacity |  | 0.1 |  |
| Icon button - Color - Outlined | Enabled / Toggle unselected | Icon button outlined icon color - toggle (unselected) | md.comp.icon-button.outlined.unselected.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Hovered / Toggle unselected | Icon button outlined hovered state layer color - toggle (unselected) | md.comp.icon-button.outlined.unselected.hovered.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Pressed / Toggle unselected | Icon button outlined pressed state layer color - toggle (unselected) | md.comp.icon-button.outlined.unselected.pressed.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Disabled | Icon button outlined disabled icon color | md.comp.icon-button.outlined.disabled.icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Outlined | Enabled / Toggle selected | Icon button outlined icon color - toggle (selected) | md.comp.icon-button.outlined.selected.icon.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Hovered / Toggle selected | Icon button outlined hovered state layer color - toggle (selected) | md.comp.icon-button.outlined.selected.hovered.state-layer.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Focused | Icon button outlined focused state layer opacity | md.comp.icon-button.outlined.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| Icon button - Color - Outlined | Pressed / Toggle selected | Icon button outlined pressed state layer color - toggle (selected) | md.comp.icon-button.outlined.selected.pressed.state-layer.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Disabled | Icon button outlined disabled icon opacity | md.comp.icon-button.outlined.disabled.icon.opacity |  | 0.38 |  |
| Icon button - Color - Outlined | Hovered | Icon button outlined hovered state layer opacity | md.comp.icon-button.outlined.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Icon button - Color - Outlined | Focused | Icon button outlined focused icon color | md.comp.icon-button.outlined.focused.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Hovered | Icon button outlined hovered icon color | md.comp.icon-button.outlined.hovered.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Focused / Toggle unselected | Icon button outlined focused icon color - toggle (unselected) | md.comp.icon-button.outlined.unselected.focused.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Pressed | Icon button outlined pressed state layer opacity | md.comp.icon-button.outlined.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| Icon button - Color - Outlined | Hovered / Toggle unselected | Icon button outlined hovered icon color - toggle (unselected) | md.comp.icon-button.outlined.unselected.hovered.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Focused / Toggle selected | Icon button outlined focused icon color - toggle (selected) | md.comp.icon-button.outlined.selected.focused.icon.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Pressed | Icon button outlined pressed icon color | md.comp.icon-button.outlined.pressed.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Hovered / Toggle selected | Icon button outlined hovered icon color - toggle (selected) | md.comp.icon-button.outlined.selected.hovered.icon.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |
| Icon button - Color - Outlined | Pressed / Toggle unselected | Icon button outlined pressed icon color - toggle (unselected) | md.comp.icon-button.outlined.unselected.pressed.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Outlined | Pressed / Toggle selected | Icon button outlined pressed icon color - toggle (selected) | md.comp.icon-button.outlined.selected.pressed.icon.color | md.sys.color.inverse-on-surface | #F5EFF7 |  |

### Icon button - Color - Standard

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Color - Standard | Disabled | Icon button disabled icon color | md.comp.icon-button.standard.disabled.icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Icon button - Color - Standard | Enabled | Icon button icon color | md.comp.icon-button.standard.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Hovered | Icon button hovered state layer color | md.comp.icon-button.standard.hovered.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Focused | Icon button focused state layer color | md.comp.icon-button.standard.focused.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Pressed | Icon button pressed state layer color | md.comp.icon-button.standard.pressed.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Disabled | Icon button disabled opacity | md.comp.icon-button.standard.disabled.icon.opacity |  | 0.38 |  |
| Icon button - Color - Standard | Hovered / Toggle unselected | Icon button hovered state layer color - toggle (unselected) | md.comp.icon-button.standard.unselected.hovered.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Focused / Toggle unselected | Icon button focused state layer color - toggle (unselected) | md.comp.icon-button.standard.unselected.focused.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Enabled / Toggle unselected | Icon button icon color - toggle (unselected) | md.comp.icon-button.standard.unselected.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Hovered / Toggle selected | Icon button hovered state layer color - toggle (selected) | md.comp.icon-button.standard.selected.hovered.state-layer.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Focused / Toggle selected | Icon button focused state layer color - toggle (selected) | md.comp.icon-button.standard.selected.focused.state-layer.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Pressed / Toggle unselected | Icon button pressed state layer color - toggle (unselected) | md.comp.icon-button.standard.unselected.pressed.state-layer.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Enabled / Toggle selected | Icon button icon color - toggle (selected) | md.comp.icon-button.standard.selected.icon.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Focused | Icon button focused state layer opacity | md.comp.icon-button.standard.focused.state-layer.opacity | md.sys.state.focus.state-layer-opacity | 0.1 |  |
| Icon button - Color - Standard | Hovered | Icon button hovered state layer opacity | md.comp.icon-button.standard.hovered.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Icon button - Color - Standard | Pressed / Toggle selected | Icon button pressed state layer color - toggle (selected) | md.comp.icon-button.standard.selected.pressed.state-layer.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Pressed | Icon button pressed state layer opacity | md.comp.icon-button.standard.pressed.state-layer.opacity | md.sys.state.pressed.state-layer-opacity | 0.1 |  |
| Icon button - Color - Standard | Focused | Icon button focused icon color | md.comp.icon-button.standard.focused.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Hovered | Icon button hovered icon color | md.comp.icon-button.standard.hovered.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Pressed | Icon button pressed icon color | md.comp.icon-button.standard.pressed.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Hovered / Toggle unselected | Icon button hovered icon color - toggle (unselected) | md.comp.icon-button.standard.unselected.hovered.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Focused / Toggle unselected | Icon button focused icon color - toggle (unselected) | md.comp.icon-button.standard.unselected.focused.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Hovered / Toggle selected | Icon button hovered icon color - toggle (selected) | md.comp.icon-button.standard.selected.hovered.icon.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Focused / Toggle selected | Icon button focused icon color - toggle (selected) | md.comp.icon-button.standard.selected.focused.icon.color | md.sys.color.primary | #6750A4 |  |
| Icon button - Color - Standard | Pressed / Toggle unselected | Icon button pressed icon color - toggle (unselected) | md.comp.icon-button.standard.unselected.pressed.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Icon button - Color - Standard | Pressed / Toggle selected | Icon button pressed icon color - toggle (selected) | md.comp.icon-button.standard.selected.pressed.icon.color | md.sys.color.primary | #6750A4 |  |

### Icon button - Size - Xsmall

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Size - Xsmall | Layout | Icon button xsmall container height | md.comp.icon-button.xsmall.container.height |  | 32dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall icon size | md.comp.icon-button.xsmall.icon.size |  | 20dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall narrow leading space | md.comp.icon-button.xsmall.narrow.leading-space |  | 4dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall narrow trailing space | md.comp.icon-button.xsmall.narrow.trailing-space |  | 4dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall default leading space | md.comp.icon-button.xsmall.default.leading-space |  | 6dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall default trailing space | md.comp.icon-button.xsmall.default.trailing-space |  | 6dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall wide leading space | md.comp.icon-button.xsmall.wide.leading-space |  | 10dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall wide trailing space | md.comp.icon-button.xsmall.wide.trailing-space |  | 10dp |  |
| Icon button - Size - Xsmall | Shape | Icon button xsmall container shape round | md.comp.icon-button.xsmall.container.shape.round | md.sys.shape.corner.full | Circular | Resolved from the token payload as a circular shape. |
| Icon button - Size - Xsmall | Shape | Icon button xsmall container shape square | md.comp.icon-button.xsmall.container.shape.square | md.sys.shape.corner.medium | 12dp |  |
| Icon button - Size - Xsmall | Layout | Icon button xsmall outline width | md.comp.icon-button.xsmall.outlined.outline.width |  | 1dp |  |
| Icon button - Size - Xsmall | Shape (pressed) | Icon button xsmall shape pressed morph | md.comp.icon-button.xsmall.pressed.container.shape | md.sys.shape.corner.small | 8dp |  |
| Icon button - Size - Xsmall | Motion | Icon button xsmall shape spring animation damping | md.comp.icon-button.xsmall.pressed.container.corner-size.motion.spring.damping | md.sys.motion.spring.fast.spatial.damping | 0.9 |  |
| Icon button - Size - Xsmall | Motion | Icon button xsmall shape spring animation stiffness | md.comp.icon-button.xsmall.pressed.container.corner-size.motion.spring.stiffness | md.sys.motion.spring.fast.spatial.stiffness | 1400 |  |
| Icon button - Size - Xsmall | Shape (selected) | Icon button xsmall selected container shape round | md.comp.icon-button.xsmall.selected.container.shape.round | md.sys.shape.corner.medium | 12dp |  |
| Icon button - Size - Xsmall | Shape (selected) | Icon button xsmall selected container shape square | md.comp.icon-button.xsmall.selected.container.shape.square | md.sys.shape.corner.full | Circular | Selected square variant resolves to the inverse resting circular shape in the token payload. |

### Icon button - Size - Small

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Size - Small | Layout | Icon button small container height | md.comp.icon-button.small.container.height |  | 40dp |  |
| Icon button - Size - Small | Layout | Icon button small icon size | md.comp.icon-button.small.icon.size |  | 24dp |  |
| Icon button - Size - Small | Layout | Icon button small narrow leading space | md.comp.icon-button.small.narrow.leading-space |  | 4dp |  |
| Icon button - Size - Small | Layout | Icon button small narrow trailing space | md.comp.icon-button.small.narrow.trailing-space |  | 4dp |  |
| Icon button - Size - Small | Layout | Icon button small default leading space | md.comp.icon-button.small.default.leading-space |  | 8dp |  |
| Icon button - Size - Small | Layout | Icon button small default trailing space | md.comp.icon-button.small.default.trailing-space |  | 8dp |  |
| Icon button - Size - Small | Layout | Icon button small wide leading space | md.comp.icon-button.small.wide.leading-space |  | 14dp |  |
| Icon button - Size - Small | Layout | Icon button small wide trailing space | md.comp.icon-button.small.wide.trailing-space |  | 14dp |  |
| Icon button - Size - Small | Shape | Icon button small container shape round | md.comp.icon-button.small.container.shape.round | md.sys.shape.corner.full | Circular | Resolved from the token payload as a circular shape. |
| Icon button - Size - Small | Shape | Icon button small container shape square | md.comp.icon-button.small.container.shape.square | md.sys.shape.corner.medium | 12dp |  |
| Icon button - Size - Small | Layout | Icon button small outline width | md.comp.icon-button.small.outlined.outline.width |  | 1dp |  |
| Icon button - Size - Small | Shape (pressed) | Icon button small shape pressed morph | md.comp.icon-button.small.pressed.container.shape | md.sys.shape.corner.small | 8dp |  |
| Icon button - Size - Small | Motion | Icon button small shape spring animation damping | md.comp.icon-button.small.pressed.container.corner-size.motion.spring.damping | md.sys.motion.spring.fast.spatial.damping | 0.9 |  |
| Icon button - Size - Small | Motion | Icon button small shape spring animation stiffness | md.comp.icon-button.small.pressed.container.corner-size.motion.spring.stiffness | md.sys.motion.spring.fast.spatial.stiffness | 1400 |  |
| Icon button - Size - Small | Shape (selected) | Icon button small selected container shape round | md.comp.icon-button.small.selected.container.shape.round | md.sys.shape.corner.medium | 12dp |  |
| Icon button - Size - Small | Shape (selected) | Icon button small selected container shape square | md.comp.icon-button.small.selected.container.shape.square | md.sys.shape.corner.full | Circular | Selected square variant resolves to the inverse resting circular shape in the token payload. |

### Icon button - Size - Medium

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Size - Medium | Layout | Icon button medium container height | md.comp.icon-button.medium.container.height |  | 56dp |  |
| Icon button - Size - Medium | Layout | Icon button medium icon size | md.comp.icon-button.medium.icon.size |  | 24dp |  |
| Icon button - Size - Medium | Layout | Icon button medium narrow leading space | md.comp.icon-button.medium.narrow.leading-space |  | 12dp |  |
| Icon button - Size - Medium | Layout | Icon button medium narrow trailing space | md.comp.icon-button.medium.narrow.trailing-space |  | 12dp |  |
| Icon button - Size - Medium | Layout | Icon button medium default leading space | md.comp.icon-button.medium.default.leading-space |  | 16dp |  |
| Icon button - Size - Medium | Layout | Icon button medium default trailing space | md.comp.icon-button.medium.default.trailing-space |  | 16dp |  |
| Icon button - Size - Medium | Layout | Icon button medium wide leading space | md.comp.icon-button.medium.wide.leading-space |  | 24dp |  |
| Icon button - Size - Medium | Layout | Icon button medium wide trailing space | md.comp.icon-button.medium.wide.trailing-space |  | 24dp |  |
| Icon button - Size - Medium | Shape | Icon button medium container shape round | md.comp.icon-button.medium.container.shape.round | md.sys.shape.corner.full | Circular | Resolved from the token payload as a circular shape. |
| Icon button - Size - Medium | Shape | Icon button medium container shape square | md.comp.icon-button.medium.container.shape.square | md.sys.shape.corner.large | 16dp |  |
| Icon button - Size - Medium | Layout | Icon button medium outline width | md.comp.icon-button.medium.outlined.outline.width |  | 1dp |  |
| Icon button - Size - Medium | Shape (pressed) | Icon button medium shape pressed morph | md.comp.icon-button.medium.pressed.container.shape | md.sys.shape.corner.medium | 12dp |  |
| Icon button - Size - Medium | Motion | Icon button medium shape spring animation damping | md.comp.icon-button.medium.pressed.container.corner-size.motion.spring.damping | md.sys.motion.spring.fast.spatial.damping | 0.9 |  |
| Icon button - Size - Medium | Motion | Icon button medium shape spring animation stiffness | md.comp.icon-button.medium.pressed.container.corner-size.motion.spring.stiffness | md.sys.motion.spring.fast.spatial.stiffness | 1400 |  |
| Icon button - Size - Medium | Shape (selected) | Icon button medium selected container shape round | md.comp.icon-button.medium.selected.container.shape.round | md.sys.shape.corner.large | 16dp |  |
| Icon button - Size - Medium | Shape (selected) | Icon button medium selected container shape square | md.comp.icon-button.medium.selected.container.shape.square | md.sys.shape.corner.full | Circular | Selected square variant resolves to the inverse resting circular shape in the token payload. |

### Icon button - Size - Large

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Size - Large | Layout | Icon button large container height | md.comp.icon-button.large.container.height |  | 96dp |  |
| Icon button - Size - Large | Layout | Icon button large icon size | md.comp.icon-button.large.icon.size |  | 32dp |  |
| Icon button - Size - Large | Layout | Icon button large narrow leading space | md.comp.icon-button.large.narrow.leading-space |  | 16dp |  |
| Icon button - Size - Large | Layout | Icon button large narrow trailing space | md.comp.icon-button.large.narrow.trailing-space |  | 16dp |  |
| Icon button - Size - Large | Layout | Icon button large default leading space | md.comp.icon-button.large.default.leading-space |  | 32dp |  |
| Icon button - Size - Large | Layout | Icon button large default trailing space | md.comp.icon-button.large.default.trailing-space |  | 32dp |  |
| Icon button - Size - Large | Layout | Icon button large wide leading space | md.comp.icon-button.large.wide.leading-space |  | 48dp |  |
| Icon button - Size - Large | Layout | Icon button large wide trailing space | md.comp.icon-button.large.wide.trailing-space |  | 48dp |  |
| Icon button - Size - Large | Shape | Icon button large container shape round | md.comp.icon-button.large.container.shape.round | md.sys.shape.corner.full | Circular | Resolved from the token payload as a circular shape. |
| Icon button - Size - Large | Shape | Icon button large container shape square | md.comp.icon-button.large.container.shape.square | md.sys.shape.corner.extra-large | 28dp |  |
| Icon button - Size - Large | Layout | Icon button large outline width | md.comp.icon-button.large.outlined.outline.width |  | 2dp |  |
| Icon button - Size - Large | Shape (pressed) | Icon button large shape pressed morph | md.comp.icon-button.large.pressed.container.shape | md.sys.shape.corner.large | 16dp |  |
| Icon button - Size - Large | Motion | Icon button large shape spring animation damping | md.comp.icon-button.large.pressed.container.corner-size.motion.spring.damping | md.sys.motion.spring.fast.spatial.damping | 0.9 |  |
| Icon button - Size - Large | Motion | Icon button large shape spring animation stiffness | md.comp.icon-button.large.pressed.container.corner-size.motion.spring.stiffness | md.sys.motion.spring.fast.spatial.stiffness | 1400 |  |
| Icon button - Size - Large | Shape (selected) | Icon button large selected container shape round | md.comp.icon-button.large.selected.container.shape.round | md.sys.shape.corner.extra-large | 28dp |  |
| Icon button - Size - Large | Shape (selected) | Icon button large selected container shape square | md.comp.icon-button.large.selected.container.shape.square | md.sys.shape.corner.full | Circular | Selected square variant resolves to the inverse resting circular shape in the token payload. |

### Icon button - Size - Xlarge

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Icon button - Size - Xlarge | Layout | Icon button xlarge container height | md.comp.icon-button.xlarge.container.height |  | 136dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge icon size | md.comp.icon-button.xlarge.icon.size |  | 40dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge narrow leading space | md.comp.icon-button.xlarge.narrow.leading-space |  | 32dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge narrow trailing space | md.comp.icon-button.xlarge.narrow.trailing-space |  | 32dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge default leading space | md.comp.icon-button.xlarge.default.leading-space |  | 48dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge default trailing space | md.comp.icon-button.xlarge.default.trailing-space |  | 48dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge wide leading space | md.comp.icon-button.xlarge.wide.leading-space |  | 72dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge wide trailing space | md.comp.icon-button.xlarge.wide.trailing-space |  | 72dp |  |
| Icon button - Size - Xlarge | Shape | Icon button xlarge container shape round | md.comp.icon-button.xlarge.container.shape.round | md.sys.shape.corner.full | Circular | Resolved from the token payload as a circular shape. |
| Icon button - Size - Xlarge | Shape | Icon button xlarge container shape square | md.comp.icon-button.xlarge.container.shape.square | md.sys.shape.corner.extra-large | 28dp |  |
| Icon button - Size - Xlarge | Layout | Icon button xlarge outline width | md.comp.icon-button.xlarge.outlined.outline.width |  | 3dp |  |
| Icon button - Size - Xlarge | Shape (pressed) | Icon button xlarge shape pressed morph | md.comp.icon-button.xlarge.pressed.container.shape | md.sys.shape.corner.large | 16dp |  |
| Icon button - Size - Xlarge | Motion | Icon button xlarge shape spring animation damping | md.comp.icon-button.xlarge.pressed.container.corner-size.motion.spring.damping | md.sys.motion.spring.fast.spatial.damping | 0.9 |  |
| Icon button - Size - Xlarge | Motion | Icon button xlarge shape spring animation stiffness | md.comp.icon-button.xlarge.pressed.container.corner-size.motion.spring.stiffness | md.sys.motion.spring.fast.spatial.stiffness | 1400 |  |
| Icon button - Size - Xlarge | Shape (selected) | Icon button xlarge selected container shape round | md.comp.icon-button.xlarge.selected.container.shape.round | md.sys.shape.corner.extra-large | 28dp |  |
| Icon button - Size - Xlarge | Shape (selected) | Icon button xlarge selected container shape square | md.comp.icon-button.xlarge.selected.container.shape.square | md.sys.shape.corner.full | Circular | Selected square variant resolves to the inverse resting circular shape in the token payload. |
