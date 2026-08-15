# Navigation Rail MD3 Specs

Source: <https://m3.material.io/components/navigation-rail/specs>
Collected: 2026-07-08

## Summary

- Two modern variants: **Collapsed** (96 dp wide, vertical items) and **Expanded** (220–360 dp, horizontal items)
- Items use a fully-rounded active indicator (`md.sys.shape.corner.full`)
- Container is flat (`md.sys.elevation.level0`); expanded modal overlay uses `md.sys.elevation.level2` (3 dp)
- Collapsed container: 96 dp wide (narrow: 80 dp); top space 44 dp; items spaced 4 dp vertically
- Expanded container: 220–360 dp wide; top space 44 dp; items 0 dp apart; 20 dp trailing vertical space
- Item container height: 64 dp standard, 56 dp short; icon size 24 dp
- Vertical active indicator: 32 dp × 56 dp; horizontal active indicator: 56 dp tall, 16 dp leading/trailing
- Label text: Label Medium (vertical layout) and Label Large (horizontal layout)
- **Baseline navigation rail is deprecated** — replace with the collapsed navigation rail
- The baseline token set prefix is `md.comp.navigation-rail`; new token set prefixes are `md.comp.nav-rail.*`

---

## Tokens & Specs

### Token sets discovered

| Token set                  | Token set name                     | Notes                                                               |
|----------------------------|------------------------------------|---------------------------------------------------------------------|
| Nav rail - Common          | `md.comp.nav-rail`                 | Color and state-layer tokens shared by collapsed and expanded items |
| Nav rail - Collapsed       | `md.comp.nav-rail.collapsed`       | Size, shape, color, and elevation for the collapsed rail            |
| Nav rail - Expanded        | `md.comp.nav-rail.expanded`        | Size, shape, color, and elevation for the expanded rail             |
| Nav rail item - Common     | `md.comp.nav-rail.item`            | Shape, size, and spacing shared by all nav items                    |
| Nav rail item - Vertical   | `md.comp.nav-rail.item.vertical`   | Indicator size, spacing, and typography for vertical layout         |
| Nav rail item - Horizontal | `md.comp.nav-rail.item.horizontal` | Indicator height, spacing, and typography for horizontal layout     |
| Navigation rail (baseline) | `md.comp.navigation-rail`          | **Deprecated.** 71 tokens for the legacy baseline rail              |

---

### Extracted tokens — Nav rail - Common

Context: Default, Light

| Token set         | Group   | Label                                            | Token                                                      | Source token                               | Value   | Notes                |
|-------------------|---------|--------------------------------------------------|------------------------------------------------------------|--------------------------------------------|---------|----------------------|
| Nav rail - Common | Enabled | Nav rail item active indicator color             | `md.comp.nav-rail.item.active.indicator.color`             | `md.sys.color.secondary-container`         | #E8DEF8 |                      |
| Nav rail - Common | Enabled | Nav rail item active label text color            | `md.comp.nav-rail.item.active.label-text.color`            | `md.sys.color.secondary`                   | #625B71 |                      |
| Nav rail - Common | Enabled | Nav rail item inactive label text color          | `md.comp.nav-rail.item.inactive.label-text.color`          | `md.sys.color.on-surface-variant`          | #49454F |                      |
| Nav rail - Common | Enabled | Nav rail item active icon color                  | `md.comp.nav-rail.item.active.icon.color`                  | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Enabled | Nav rail item inactive icon color                | `md.comp.nav-rail.item.inactive.icon.color`                | `md.sys.color.on-surface-variant`          | #49454F |                      |
| Nav rail - Common | Hovered | Nav rail item active hovered state layer color   | `md.comp.nav-rail.item.active.hovered.state-layer.color`   | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Hovered | Nav rail item active hovered state layer opacity | `md.comp.nav-rail.item.active.hovered.state-layer.opacity` | `md.sys.state.hover.state-layer-opacity`   | 0.08    | Shared with inactive |
| Nav rail - Common | Hovered | Nav rail item inactive hovered state layer color | `md.comp.nav-rail.item.inactive.hovered.state-layer.color` | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Focused | Nav rail item active focused state layer color   | `md.comp.nav-rail.item.active.focused.state-layer.color`   | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Focused | Nav rail item active focused state layer opacity | `md.comp.nav-rail.item.active.focused.state-layer.opacity` | `md.sys.state.focus.state-layer-opacity`   | 0.1     | Shared with inactive |
| Nav rail - Common | Focused | Nav rail item inactive focused state layer color | `md.comp.nav-rail.item.inactive.focused.state-layer.color` | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Pressed | Nav rail item active pressed state layer color   | `md.comp.nav-rail.item.active.pressed.state-layer.color`   | `md.sys.color.on-secondary-container`      | #4A4458 |                      |
| Nav rail - Common | Pressed | Nav rail item active pressed state layer opacity | `md.comp.nav-rail.item.active.pressed.state-layer.opacity` | `md.sys.state.pressed.state-layer-opacity` | 0.1     | Shared with inactive |
| Nav rail - Common | Pressed | Nav rail item inactive pressed state layer color | `md.comp.nav-rail.item.inactive.pressed.state-layer.color` | `md.sys.color.on-secondary-container`      | #4A4458 |                      |

---

### Extracted tokens — Nav rail - Collapsed

| Token set            | Group | Label                                     | Token                                               | Source token               | Value       | Notes               |
|----------------------|-------|-------------------------------------------|-----------------------------------------------------|----------------------------|-------------|---------------------|
| Nav rail - Collapsed |       | Nav rail collapsed container width        | `md.comp.nav-rail.collapsed.container.width`        |                            | 96 dp       |                     |
| Nav rail - Collapsed |       | Nav rail collapsed narrow container width | `md.comp.nav-rail.collapsed.narrow.container.width` |                            | 80 dp       |                     |
| Nav rail - Collapsed |       | Nav rail collapsed container elevation    | `md.comp.nav-rail.collapsed.container.elevation`    | `md.sys.elevation.level0`  | 0           | Flat, no shadow     |
| Nav rail - Collapsed |       | Nav rail collapsed container shape        | `md.comp.nav-rail.collapsed.container.shape`        | `md.sys.shape.corner.none` | No rounding |                     |
| Nav rail - Collapsed |       | Nav rail collapsed container color        | `md.comp.nav-rail.collapsed.container.color`        | `md.sys.color.surface`     | #FEF7FF     |                     |
| Nav rail - Collapsed |       | Nav rail collapsed item vertical space    | `md.comp.nav-rail.collapsed.item.vertical-space`    |                            | 4 dp        | Space between items |
| Nav rail - Collapsed |       | Nav rail collapsed top space              | `md.comp.nav-rail.collapsed.top-space`              |                            | 44 dp       |                     |

---

### Extracted tokens — Nav rail - Expanded

| Token set           | Group | Label                                       | Token                                                 | Source token                     | Value                  | Notes                |
|---------------------|-------|---------------------------------------------|-------------------------------------------------------|----------------------------------|------------------------|----------------------|
| Nav rail - Expanded |       | Nav rail expanded container width minimum   | `md.comp.nav-rail.expanded.container.width.minimum`   |                                  | 220 dp                 |                      |
| Nav rail - Expanded |       | Nav rail expanded container width maximum   | `md.comp.nav-rail.expanded.container.width.maximum`   |                                  | 360 dp                 |                      |
| Nav rail - Expanded |       | Nav rail expanded top space                 | `md.comp.nav-rail.expanded.top-space`                 |                                  | 44 dp                  |                      |
| Nav rail - Expanded |       | Nav rail expanded container elevation       | `md.comp.nav-rail.expanded.container.elevation`       | `md.sys.elevation.level0`        | 0                      | Standard (docked)    |
| Nav rail - Expanded |       | Nav rail expanded modal container elevation | `md.comp.nav-rail.expanded.modal.container.elevation` | `md.sys.elevation.level2`        | 3 dp                   | Modal overlay        |
| Nav rail - Expanded |       | Nav rail expanded container color           | `md.comp.nav-rail.expanded.container.color`           | `md.sys.color.surface`           | #FEF7FF                |                      |
| Nav rail - Expanded |       | Nav rail expanded modal container color     | `md.comp.nav-rail.expanded.modal.container.color`     | `md.sys.color.surface-container` | #F3EDF7                |                      |
| Nav rail - Expanded |       | Nav rail expanded container shape           | `md.comp.nav-rail.expanded.container.shape`           | `md.sys.shape.corner.none`       | No rounding            |                      |
| Nav rail - Expanded |       | Nav rail expanded modal container shape     | `md.comp.nav-rail.expanded.modal.container.shape`     | `md.sys.shape.corner.large`      | Large rounding (16 dp) |                      |
| Nav rail - Expanded |       | Nav rail expanded between item space        | `md.comp.nav-rail.expanded.between-item-space`        |                                  | 0                      | No gap between items |
| Nav rail - Expanded |       | Nav rail expanded vertical trailing space   | `md.comp.nav-rail.expanded.vertical.trailing-space`   |                                  | 20 dp                  |                      |

---

### Extracted tokens — Nav rail item - Common

| Token set              | Group | Label                                           | Token                                                     | Source token               | Value         | Notes                       |
|------------------------|-------|-------------------------------------------------|-----------------------------------------------------------|----------------------------|---------------|-----------------------------|
| Nav rail item - Common |       | Nav rail item icon size                         | `md.comp.nav-rail.item.icon.size`                         |                            | 24 dp         |                             |
| Nav rail item - Common |       | Nav rail item active indicator shape            | `md.comp.nav-rail.item.active-indicator.shape`            | `md.sys.shape.corner.full` | Fully rounded | Pill/stadium shape          |
| Nav rail item - Common |       | Nav rail item active indicator leading space    | `md.comp.nav-rail.item.active-indicator.leading-space`    |                            | 16 dp         |                             |
| Nav rail item - Common |       | Nav rail item active indicator icon–label space | `md.comp.nav-rail.item.active-indicator.icon-label-space` |                            | 8 dp          | Between icon and label text |
| Nav rail item - Common |       | Nav rail item active indicator trailing space   | `md.comp.nav-rail.item.active-indicator.trailing-space`   |                            | 16 dp         |                             |
| Nav rail item - Common |       | Nav rail item container height                  | `md.comp.nav-rail.item.container.height`                  |                            | 64 dp         | Standard                    |
| Nav rail item - Common |       | Nav rail item short container height            | `md.comp.nav-rail.item.short.container.height`            |                            | 56 dp         | Short variant               |
| Nav rail item - Common |       | Nav rail item container shape                   | `md.comp.nav-rail.item.container.shape`                   |                            | No rounding   |                             |
| Nav rail item - Common |       | Nav rail item container vertical space          | `md.comp.nav-rail.item.container.vertical-space`          |                            | 6 dp          |                             |
| Nav rail item - Common |       | Nav rail item header space minimum              | `md.comp.nav-rail.item.header-space-minimum`              |                            | 40 dp         |                             |

---

### Extracted tokens — Nav rail item - Vertical

| Token set                | Group | Label                                          | Token                                                    | Source token            | Value        | Notes                                                                                                |
|--------------------------|-------|------------------------------------------------|----------------------------------------------------------|-------------------------|--------------|------------------------------------------------------------------------------------------------------|
| Nav rail item - Vertical |       | Nav rail item vertical active indicator height | `md.comp.nav-rail.item.vertical.active-indicator.height` |                         | 32 dp        |                                                                                                      |
| Nav rail item - Vertical |       | Nav rail item vertical active indicator width  | `md.comp.nav-rail.item.vertical.active-indicator.width`  |                         | 56 dp        |                                                                                                      |
| Nav rail item - Vertical |       | Nav rail item vertical label text              | `md.comp.nav-rail.item.vertical.label-text.font`         | `md.ref.typeface.plain` | Label Medium | Roboto 500, 12 pt, 0.5 pt tracking, 16 pt line-height; source scale: `md.sys.typescale.label-medium` |
| Nav rail item - Vertical |       | Nav rail item vertical icon–label space        | `md.comp.nav-rail.item.vertical.icon-label-space`        |                         | 4 dp         |                                                                                                      |
| Nav rail item - Vertical |       | Nav rail item vertical leading space           | `md.comp.nav-rail.item.vertical.leading-space`           |                         | 16 dp        |                                                                                                      |
| Nav rail item - Vertical |       | Nav rail item vertical trailing space          | `md.comp.nav-rail.item.vertical.trailing-space`          |                         | 16 dp        |                                                                                                      |

---

### Extracted tokens — Nav rail item - Horizontal

| Token set                  | Group | Label                                              | Token                                                        | Source token            | Value       | Notes                                                                                               |
|----------------------------|-------|----------------------------------------------------|--------------------------------------------------------------|-------------------------|-------------|-----------------------------------------------------------------------------------------------------|
| Nav rail item - Horizontal |       | Nav rail item horizontal label text                | `md.comp.nav-rail.item.horizontal.label-text.font`           | `md.ref.typeface.plain` | Label Large | Roboto 500, 14 pt, 0.1 pt tracking, 20 pt line-height; source scale: `md.sys.typescale.label-large` |
| Nav rail item - Horizontal |       | Nav rail item horizontal active indicator height   | `md.comp.nav-rail.item.horizontal.active-indicator.height`   |                         | 56 dp       | Full row height                                                                                     |
| Nav rail item - Horizontal |       | Nav rail item horizontal full-width leading space  | `md.comp.nav-rail.item.horizontal.full-width.leading-space`  |                         | 16 dp       |                                                                                                     |
| Nav rail item - Horizontal |       | Nav rail item horizontal full-width trailing space | `md.comp.nav-rail.item.horizontal.full-width.trailing-space` |                         | 16 dp       |                                                                                                     |
| Nav rail item - Horizontal |       | Nav rail item horizontal icon–label space          | `md.comp.nav-rail.item.horizontal.icon-label-space`          |                         | 8 dp        |                                                                                                     |

---

### Extracted tokens — Navigation rail (baseline) — DEPRECATED

> **The baseline navigation rail is no longer recommended.** Use the collapsed navigation rail instead. These tokens use the `md.comp.navigation-rail` prefix.

| Token set                  | Group                                    | Label                                       | Token                                                        | Source token                                     | Value        | Notes                           |
|----------------------------|------------------------------------------|---------------------------------------------|--------------------------------------------------------------|--------------------------------------------------|--------------|---------------------------------|
| Navigation rail (baseline) | Enabled / Container                      | Nav rail container color                    | `md.comp.navigation-rail.container.color`                    | `md.sys.color.surface`                           |              |                                 |
| Navigation rail (baseline) | Enabled / Container                      | Nav rail container elevation                | `md.comp.navigation-rail.container.elevation`                | `md.sys.elevation.level0`                        |              |                                 |
| Navigation rail (baseline) | Enabled / Container                      | Nav rail container shape                    | `md.comp.navigation-rail.container.shape`                    | `md.sys.shape.corner.none`                       |              |                                 |
| Navigation rail (baseline) | Enabled / Container                      | Nav rail container width                    | `md.comp.navigation-rail.container.width`                    |                                                  | 80 dp        | From measurement figure         |
| Navigation rail (baseline) | Enabled / Icon                           | Nav rail icon size                          | `md.comp.navigation-rail.icon.size`                          |                                                  | 24 dp        | From measurement figure         |
| Navigation rail (baseline) | Enabled / Icon                           | Nav rail inactive icon color                | `md.comp.navigation-rail.inactive.icon.color`                | `md.sys.color.on-surface-variant`                |              |                                 |
| Navigation rail (baseline) | Enabled / Icon                           | Nav rail active icon color                  | `md.comp.navigation-rail.active.icon.color`                  | `md.sys.color.on-secondary-container`            |              |                                 |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail active indicator color             | `md.comp.navigation-rail.active-indicator.color`             | `md.sys.color.secondary-container`               |              |                                 |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail active indicator shape             | `md.comp.navigation-rail.active-indicator.shape`             | `md.sys.shape.corner.full`                       |              |                                 |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail no-label active indicator shape    | `md.comp.navigation-rail.no-label.active-indicator.shape`    | `md.sys.shape.corner.full`                       |              |                                 |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail active indicator width             | `md.comp.navigation-rail.active-indicator.width`             |                                                  | 56 dp        | From measurement figure         |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail active indicator height            | `md.comp.navigation-rail.active-indicator.height`            |                                                  | 32 dp        | From measurement figure         |
| Navigation rail (baseline) | Enabled / Active indicator               | Nav rail no-label active indicator height   | `md.comp.navigation-rail.no-label.active-indicator.height`   |                                                  |              | visual-only in figure           |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label text type                    | `md.comp.navigation-rail.label-text.type`                    |                                                  | Label Medium | `md.sys.typescale.label-medium` |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label font                         | `md.comp.navigation-rail.label-text.font`                    | `md.sys.typescale.label-medium.font`             |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label weight                       | `md.comp.navigation-rail.label-text.weight`                  | `md.sys.typescale.label-medium.weight`           |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail active label weight                | `md.comp.navigation-rail.active.label-text.weight`           | `md.sys.typescale.label-medium.weight.prominent` |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label size                         | `md.comp.navigation-rail.label-text.size`                    | `md.sys.typescale.label-medium.size`             |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label line height                  | `md.comp.navigation-rail.label-text.line-height`             | `md.sys.typescale.label-medium.line-height`      |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail label tracking                     | `md.comp.navigation-rail.label-text.tracking`                | `md.sys.typescale.label-medium.tracking`         |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail inactive label text color          | `md.comp.navigation-rail.inactive.label-text.color`          | `md.sys.color.on-surface-variant`                |              |                                 |
| Navigation rail (baseline) | Enabled / Label text                     | Nav rail active label text color            | `md.comp.navigation-rail.active.label-text.color`            | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Badge             | Nav rail badge color                        | `md.comp.navigation-rail.badge.color`                        | `md.sys.color.error`                             |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Badge             | Nav rail badge shape                        | `md.comp.navigation-rail.badge.shape`                        |                                                  |              | visual-only                     |
| Navigation rail (baseline) | Enabled / [Deprecated] Badge             | Nav rail badge size                         | `md.comp.navigation-rail.badge.size`                         |                                                  |              | visual-only                     |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge       | Nav rail large badge color                  | `md.comp.navigation-rail.large-badge.color`                  | `md.sys.color.error`                             |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge       | Nav rail large badge shape                  | `md.comp.navigation-rail.large-badge.shape`                  |                                                  |              | visual-only                     |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge       | Nav rail large badge size                   | `md.comp.navigation-rail.large-badge.size`                   |                                                  |              | visual-only                     |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label color            | `md.comp.navigation-rail.large-badge-label.color`            | `md.sys.color.on-error`                          |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label font             | `md.comp.navigation-rail.large-badge-label.font`             | `md.sys.typescale.label-small.font`              |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label weight           | `md.comp.navigation-rail.large-badge-label.weight`           | `md.sys.typescale.label-small.weight`            |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label size             | `md.comp.navigation-rail.large-badge-label.size`             | `md.sys.typescale.label-small.size`              |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label line height      | `md.comp.navigation-rail.large-badge-label.line-height`      | `md.sys.typescale.label-small.line-height`       |              |                                 |
| Navigation rail (baseline) | Enabled / [Deprecated] Large badge label | Nav rail large badge label tracking         | `md.comp.navigation-rail.large-badge-label.tracking`         | `md.sys.typescale.label-small.tracking`          |              |                                 |
| Navigation rail (baseline) | Enabled / Menu icon                      | Nav rail menu icon size                     | `md.comp.navigation-rail.menu.icon.size`                     |                                                  | 24 dp        | From measurement figure         |
| Navigation rail (baseline) | Enabled / Menu icon                      | Nav rail menu icon color                    | `md.comp.navigation-rail.menu.icon.color`                    | `md.sys.color.on-surface-variant`                |              |                                 |
| Navigation rail (baseline) | Hovered / Icon                           | Nav rail active hover icon color            | `md.comp.navigation-rail.active.hover.icon.color`            | `md.sys.color.on-secondary-container`            |              |                                 |
| Navigation rail (baseline) | Hovered / Icon                           | Nav rail inactive hover icon color          | `md.comp.navigation-rail.inactive.hover.icon.color`          | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Hovered / Label text                     | Nav rail active hover label text color      | `md.comp.navigation-rail.active.hover.label-text.color`      | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Hovered / Label text                     | Nav rail inactive hover label text color    | `md.comp.navigation-rail.inactive.hover.label-text.color`    | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Hovered / State layer                    | Nav rail hover state layer opacity          | `md.comp.navigation-rail.hover.state-layer.opacity`          | `md.sys.state.hover.state-layer-opacity`         |              |                                 |
| Navigation rail (baseline) | Hovered / State layer                    | Nav rail active hover state layer color     | `md.comp.navigation-rail.active.hover.state-layer.color`     | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Hovered / State layer                    | Nav rail inactive hover state layer color   | `md.comp.navigation-rail.inactive.hover.state-layer.color`   | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Focused / Icon                           | Nav rail active focus icon color            | `md.comp.navigation-rail.active.focus.icon.color`            | `md.sys.color.on-secondary-container`            |              |                                 |
| Navigation rail (baseline) | Focused / Icon                           | Nav rail inactive focus icon color          | `md.comp.navigation-rail.inactive.focus.icon.color`          | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Focused / Label text                     | Nav rail focus label text color             | `md.comp.navigation-rail.active.focus.label-text.color`      | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Focused / Label text                     | Nav rail inactive focus label text color    | `md.comp.navigation-rail.inactive.focus.label-text.color`    | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Focused / State layer                    | Nav rail focus state layer opacity          | `md.comp.navigation-rail.focus.state-layer.opacity`          | `md.sys.state.focus.state-layer-opacity`         |              |                                 |
| Navigation rail (baseline) | Focused / State layer                    | Nav rail active focus state layer color     | `md.comp.navigation-rail.active.focus.state-layer.color`     | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Focused / State layer                    | Nav rail inactive focus state layer color   | `md.comp.navigation-rail.inactive.focus.state-layer.color`   | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / Icon                  | Nav rail active pressed icon color          | `md.comp.navigation-rail.active.pressed.icon.color`          | `md.sys.color.on-secondary-container`            |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / Icon                  | Nav rail inactive pressed icon color        | `md.comp.navigation-rail.inactive.pressed.icon.color`        | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / Label text            | Nav rail active pressed label text color    | `md.comp.navigation-rail.active.pressed.label-text.color`    | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / Label text            | Nav rail inactive pressed label text color  | `md.comp.navigation-rail.inactive.pressed.label-text.color`  | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / State layer           | Nav rail pressed state layer opacity        | `md.comp.navigation-rail.pressed.state-layer.opacity`        | `md.sys.state.pressed.state-layer-opacity`       |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / State layer           | Nav rail active pressed state layer color   | `md.comp.navigation-rail.active.pressed.state-layer.color`   | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Pressed (ripple) / State layer           | Nav rail inactive pressed state layer color | `md.comp.navigation-rail.inactive.pressed.state-layer.color` | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Hover                             | Nav rail menu hover icon color              | `md.comp.navigation-rail.menu.hover.icon.color`              | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Hover                             | Nav rail menu hover state layer opacity     | `md.comp.navigation-rail.menu.hover.state-layer.opacity`     | `md.sys.state.hover.state-layer-opacity`         |              |                                 |
| Navigation rail (baseline) | Menu / Hover                             | Nav rail menu hover state layer color       | `md.comp.navigation-rail.menu.hover.state-layer.color`       | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Focus                             | Nav rail menu focus icon color              | `md.comp.navigation-rail.menu.focus.icon.color`              | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Focus                             | Nav rail menu focus state layer opacity     | `md.comp.navigation-rail.menu.focus.state-layer.opacity`     | `md.sys.state.focus.state-layer-opacity`         |              |                                 |
| Navigation rail (baseline) | Menu / Focus                             | Nav rail menu focus state layer color       | `md.comp.navigation-rail.menu.focus.state-layer.color`       | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Press                             | Nav rail menu pressed icon color            | `md.comp.navigation-rail.menu.pressed.icon.color`            | `md.sys.color.on-surface`                        |              |                                 |
| Navigation rail (baseline) | Menu / Press                             | Nav rail menu pressed state layer opacity   | `md.comp.navigation-rail.menu.pressed.state-layer.opacity`   | `md.sys.state.pressed.state-layer-opacity`       |              |                                 |
| Navigation rail (baseline) | Menu / Press                             | Nav rail menu pressed state layer color     | `md.comp.navigation-rail.menu.pressed.state-layer.color`     | `md.sys.color.on-surface`                        |              |                                 |

---

## Measurements

### Collapsed navigation rail

| Category         | Item                           | Value         | Notes                                                     |
|------------------|--------------------------------|---------------|-----------------------------------------------------------|
| Container        | Width (standard)               | 96 dp         | `md.comp.nav-rail.collapsed.container.width`              |
| Container        | Width (narrow)                 | 80 dp         | `md.comp.nav-rail.collapsed.narrow.container.width`       |
| Container        | Top space                      | 44 dp         | `md.comp.nav-rail.collapsed.top-space`                    |
| Container        | Elevation                      | 0             | `md.sys.elevation.level0`                                 |
| Container        | Shape                          | No rounding   | `md.sys.shape.corner.none`                                |
| Item             | Vertical spacing between items | 4 dp          | `md.comp.nav-rail.collapsed.item.vertical-space`          |
| Item             | Container height (standard)    | 64 dp         | `md.comp.nav-rail.item.container.height`                  |
| Item             | Container height (short)       | 56 dp         | `md.comp.nav-rail.item.short.container.height`            |
| Item             | Container vertical space       | 6 dp          | `md.comp.nav-rail.item.container.vertical-space`          |
| Item             | Header space minimum           | 40 dp         | `md.comp.nav-rail.item.header-space-minimum`              |
| Icon             | Size                           | 24 dp         | `md.comp.nav-rail.item.icon.size`                         |
| Active indicator | Height                         | 32 dp         | `md.comp.nav-rail.item.vertical.active-indicator.height`  |
| Active indicator | Width                          | 56 dp         | `md.comp.nav-rail.item.vertical.active-indicator.width`   |
| Active indicator | Shape                          | Fully rounded | `md.sys.shape.corner.full`                                |
| Active indicator | Leading space                  | 16 dp         | `md.comp.nav-rail.item.active-indicator.leading-space`    |
| Active indicator | Trailing space                 | 16 dp         | `md.comp.nav-rail.item.active-indicator.trailing-space`   |
| Active indicator | Icon–label space               | 8 dp          | `md.comp.nav-rail.item.active-indicator.icon-label-space` |
| Label text       | Vertical leading space         | 16 dp         | `md.comp.nav-rail.item.vertical.leading-space`            |
| Label text       | Vertical trailing space        | 16 dp         | `md.comp.nav-rail.item.vertical.trailing-space`           |
| Label text       | Vertical icon–label gap        | 4 dp          | `md.comp.nav-rail.item.vertical.icon-label-space`         |
| Label text       | Type style                     | Label Medium  | Roboto 500, 12 pt, 0.5 pt tracking, 16 pt line-height     |

### Expanded navigation rail

| Category         | Item                          | Value                  | Notes                                                                |
|------------------|-------------------------------|------------------------|----------------------------------------------------------------------|
| Container        | Width (minimum)               | 220 dp                 | `md.comp.nav-rail.expanded.container.width.minimum`                  |
| Container        | Width (maximum)               | 360 dp                 | `md.comp.nav-rail.expanded.container.width.maximum`                  |
| Container        | Top space                     | 44 dp                  | `md.comp.nav-rail.expanded.top-space`                                |
| Container        | Elevation (standard)          | 0                      | `md.sys.elevation.level0`                                            |
| Container        | Elevation (modal)             | 3 dp                   | `md.sys.elevation.level2`                                            |
| Container        | Shape (standard)              | No rounding            | `md.sys.shape.corner.none`                                           |
| Container        | Shape (modal)                 | Large rounding (16 dp) | `md.sys.shape.corner.large`                                          |
| Container        | Vertical trailing space       | 20 dp                  | `md.comp.nav-rail.expanded.vertical.trailing-space`                  |
| Item             | Between items                 | 0 dp                   | `md.comp.nav-rail.expanded.between-item-space`                       |
| Item             | Section header top padding    | 12 dp                  | From measurement figure                                              |
| Item             | Section header bottom padding | 8 dp                   | From measurement figure                                              |
| Active indicator | Height                        | 56 dp                  | Full row; `md.comp.nav-rail.item.horizontal.active-indicator.height` |
| Active indicator | Leading space                 | 16 dp                  | `md.comp.nav-rail.item.horizontal.full-width.leading-space`          |
| Active indicator | Trailing space                | 16 dp                  | `md.comp.nav-rail.item.horizontal.full-width.trailing-space`         |
| Active indicator | Icon–label space              | 8 dp                   | `md.comp.nav-rail.item.horizontal.icon-label-space`                  |
| Icon             | Size                          | 24 dp                  | `md.comp.nav-rail.item.icon.size`                                    |
| Label text       | Type style                    | Label Large            | Roboto 500, 14 pt, 0.1 pt tracking, 20 pt line-height                |

### Baseline navigation rail (deprecated)

Measured from figure: "Baseline nav rail size measurements" and "Baseline nav rail padding and margin measurements".

| Category         | Item                    | Value             | Notes                                                                      |
|------------------|-------------------------|-------------------|----------------------------------------------------------------------------|
| Container        | Width                   | 80 dp             | `md.comp.navigation-rail.container.width`                                  |
| Container        | Elevation               | 0                 | `md.sys.elevation.level0`                                                  |
| Container        | Shape                   | No rounding       | `md.sys.shape.corner.none`                                                 |
| Active indicator | Width                   | 56 dp             | `md.comp.navigation-rail.active-indicator.width`; from measurement figure  |
| Active indicator | Height (with label)     | 32 dp             | `md.comp.navigation-rail.active-indicator.height`; from measurement figure |
| Active indicator | Shape                   | Fully rounded     | `md.sys.shape.corner.full`                                                 |
| Active indicator | Horizontal padding      | 12 dp (each side) | From padding figure                                                        |
| Item             | Container height        | 56 dp             | From measurement figure                                                    |
| Item             | Vertical spacing        | 4 dp              | From padding figure                                                        |
| Item             | Space below active item | 12 dp             | From padding figure                                                        |
| Icon             | Size                    | 24 dp             | `md.comp.navigation-rail.icon.size`                                        |
| Menu icon        | Size                    | 24 dp             | `md.comp.navigation-rail.menu.icon.size`                                   |

---

## Implementation Notes

- The new collapsed rail (`md.comp.nav-rail.collapsed`) replaces the baseline rail (`md.comp.navigation-rail`). Width is 96 dp (standard) or 80 dp (narrow), vs. 80 dp fixed for baseline.
- Use **vertical layout** (`md.comp.nav-rail.item.vertical.*`) in the collapsed rail; use **horizontal layout** (`md.comp.nav-rail.item.horizontal.*`) in the expanded rail.
- Active indicator is always fully rounded (`md.sys.shape.corner.full`). The indicator stretches to a 32×56 dp pill in vertical layout and fills the full row (56 dp tall) in horizontal layout.
- The **expanded modal** variant uses `md.sys.elevation.level2` (3 dp) and large rounded corners on the right edge (`md.sys.shape.corner.large`), while the docked expanded variant is flat with no rounding.
- Both active and inactive items share the same state-layer opacity values: hover=0.08, focus=0.1, press=0.1.
- Inactive state-layer color is the same token as active (`md.sys.color.on-secondary-container`) except for inactive icon/label colors which use `md.sys.color.on-surface-variant`.
- Typography: vertical items use `md.sys.typescale.label-medium` (12 pt), horizontal items use `md.sys.typescale.label-large` (14 pt).
- Token values above are resolved for **Default, Light** context.
