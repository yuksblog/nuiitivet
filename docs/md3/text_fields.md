<!-- markdownlint-disable MD060 -->

# Text Fields MD3 Specs

**Source:** <https://m3.material.io/components/text-fields/specs>  
**Collected:** 2026-04-27

## Summary

- Material Design 3 text field specifications covering filled and outlined fields plus current select and autocomplete variants exposed in the live token viewer.
- Five interactive states are represented across the current token sets: Enabled, Disabled, Hovered, Focused, and Error.
- Values were resolved from the Material token table using the Light + Default + Expressive context when available, with Light + Default as fallback.

## Tokens & Specs

### Token Sets Discovered

| Token Set | Count | Type | Status |
|---|---:|---|---|
| Text field - Filled | 89 | Component | Active |
| Text field - Outlined | 84 | Component | Active |
| Text field - Select, outlined | 105 | Component | Active |
| Text field - Select, filled | 107 | Component | Active |
| Text field - Autocomplete, filled | 103 | Component | Active |
| Text field - Autocomplete, outlined | 101 | Component | Active |

### Text field - Filled

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Filled | Enabled | Filled text field active indicator color | md.comp.filled-text-field.active-indicator.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field active indicator height | md.comp.filled-text-field.active-indicator.height |  | 1dp |  |
| Text field - Filled | Enabled | Filled text field caret color | md.comp.filled-text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Filled | Enabled | Filled text field container color | md.comp.filled-text-field.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Filled | Layout | Filled text field container height | md.comp.filled-text-field.container.height |  | 56dp |  |
| Text field - Filled | Shape | Filled text field container shape | md.comp.filled-text-field.container.shape | md.sys.shape.corner.extra-small.top | Rounded Corners | Resolved as rounded corners. |
| Text field - Filled | Disabled | Filled text field disabled active indicator color | md.comp.filled-text-field.disabled.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled active indicator height | md.comp.filled-text-field.disabled.active-indicator.height |  | 1dp |  |
| Text field - Filled | Disabled | Filled text field disabled active indicator opacity | md.comp.filled-text-field.disabled.active-indicator.opacity |  | 0.38 |  |
| Text field - Filled | Disabled | Filled text field disabled container color | md.comp.filled-text-field.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled container opacity | md.comp.filled-text-field.disabled.container.opacity |  | 0.04 |  |
| Text field - Filled | Disabled | Filled text field disabled input text color | md.comp.filled-text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled input text opacity | md.comp.filled-text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Filled | Disabled | Filled text field disabled label text color | md.comp.filled-text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled label text opacity | md.comp.filled-text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Filled | Disabled | Filled text field disabled leading icon color | md.comp.filled-text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled leading icon opacity | md.comp.filled-text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Filled | Disabled | Filled text field disabled supporting text color | md.comp.filled-text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled supporting text opacity | md.comp.filled-text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Filled | Disabled | Filled text field disabled trailing icon color | md.comp.filled-text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Disabled | Filled text field disabled trailing icon opacity | md.comp.filled-text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Filled | Error | Filled text field error active indicator color | md.comp.filled-text-field.error.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Focused | Filled text field error focus active indicator color | md.comp.filled-text-field.error.focus.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Focused | Filled text field error focus caret color | md.comp.filled-text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Focused | Filled text field error focus input text color | md.comp.filled-text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Error / Focused | Filled text field error focus label text color | md.comp.filled-text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Focused | Filled text field error focus leading icon color | md.comp.filled-text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Error / Focused | Filled text field error focus supporting text color | md.comp.filled-text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Focused | Filled text field error focus trailing icon color | md.comp.filled-text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Hovered | Filled text field error hover active indicator color | md.comp.filled-text-field.error.hover.active-indicator.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Filled | Error / Hovered | Filled text field error hover input text color | md.comp.filled-text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Error / Hovered | Filled text field error hover label text color | md.comp.filled-text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Filled | Error / Hovered | Filled text field error hover leading icon color | md.comp.filled-text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Error / Hovered | Filled text field error hover state layer color | md.comp.filled-text-field.error.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Error / Hovered | Filled text field error hover state layer opacity | md.comp.filled-text-field.error.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Filled | Error / Hovered | Filled text field error hover supporting text color | md.comp.filled-text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error / Hovered | Filled text field error hover trailing icon color | md.comp.filled-text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Filled | Error | Filled text field error input text color | md.comp.filled-text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Error | Filled text field error label text color | md.comp.filled-text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error | Filled text field error leading icon color | md.comp.filled-text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Error | Filled text field error supporting text color | md.comp.filled-text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Error | Filled text field error trailing icon color | md.comp.filled-text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Filled | Focused | Filled text field focus active indicator color | md.comp.filled-text-field.focus.active-indicator.color | md.sys.color.primary | #6750A4 |  |
| Text field - Filled | Focused | Filled text field focus active indicator height | md.comp.filled-text-field.focus.active-indicator.height |  | 2dp |  |
| Text field - Filled | Focused | Filled text field focus active indicator thickness | md.comp.filled-text-field.focus.active-indicator.thickness | md.sys.state.focus-indicator.thickness | 3dp |  |
| Text field - Filled | Focused | Filled text field focus input text color | md.comp.filled-text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Focused | Filled text field focus label text color | md.comp.filled-text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Filled | Focused | Filled text field focus leading icon color | md.comp.filled-text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Focused | Filled text field focus supporting text color | md.comp.filled-text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Focused | Filled text field focus trailing icon color | md.comp.filled-text-field.focus.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Hovered | Filled text field hover active indicator color | md.comp.filled-text-field.hover.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Hovered | Filled text field hover active indicator height | md.comp.filled-text-field.hover.active-indicator.height |  | 1dp |  |
| Text field - Filled | Hovered | Filled text field hover input text color | md.comp.filled-text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Hovered | Filled text field hover label text color | md.comp.filled-text-field.hover.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Hovered | Filled text field hover leading icon color | md.comp.filled-text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Hovered | Filled text field hover state layer color | md.comp.filled-text-field.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Hovered | Filled text field hover state layer opacity | md.comp.filled-text-field.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Filled | Hovered | Filled text field hover supporting text color | md.comp.filled-text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Hovered | Filled text field hover trailing icon color | md.comp.filled-text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field input text color | md.comp.filled-text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Filled | Enabled | Filled text field input text font | md.comp.filled-text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Filled | Enabled | Filled text field input text line height | md.comp.filled-text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Filled | Enabled | Filled text field input text placeholder color | md.comp.filled-text-field.input-text.placeholder.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field input text prefix color | md.comp.filled-text-field.input-text.prefix.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field input text size | md.comp.filled-text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Filled | Enabled | Filled text field input text suffix color | md.comp.filled-text-field.input-text.suffix.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field input text tracking | md.comp.filled-text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Filled | Enabled | Filled text field input text type | md.comp.filled-text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Filled | Enabled | Filled text field input text weight | md.comp.filled-text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Filled | Enabled | Filled text field label text color | md.comp.filled-text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field label text font | md.comp.filled-text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Filled | Enabled | Filled text field label text line height | md.comp.filled-text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Filled | Enabled | Filled text field label text populated line height | md.comp.filled-text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Filled | Enabled | Filled text field label text populated size | md.comp.filled-text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Filled | Enabled | Filled text field label text size | md.comp.filled-text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Filled | Enabled | Filled text field label text tracking | md.comp.filled-text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Filled | Enabled | Filled text field label text type | md.comp.filled-text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Filled | Enabled | Filled text field label text weight | md.comp.filled-text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Filled | Enabled | Filled text field leading icon color | md.comp.filled-text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field leading icon size | md.comp.filled-text-field.leading-icon.size |  | 24dp |  |
| Text field - Filled | Enabled | Filled text field supporting text color | md.comp.filled-text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field supporting text font | md.comp.filled-text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Filled | Enabled | Filled text field supporting text line height | md.comp.filled-text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Filled | Enabled | Filled text field supporting text size | md.comp.filled-text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Filled | Enabled | Filled text field supporting text tracking | md.comp.filled-text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Filled | Enabled | Filled text field supporting text type | md.comp.filled-text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Filled | Enabled | Filled text field supporting text weight | md.comp.filled-text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Filled | Enabled | Filled text field trailing icon color | md.comp.filled-text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Filled | Enabled | Filled text field trailing icon size | md.comp.filled-text-field.trailing-icon.size |  | 24dp |  |

### Text field - Outlined

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Outlined | Enabled | Outlined text field caret color | md.comp.outlined-text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Outlined | Layout | Outlined text field container height | md.comp.outlined-text-field.container.height |  | 56dp |  |
| Text field - Outlined | Shape | Outlined text field container shape | md.comp.outlined-text-field.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Outlined | Disabled | Outlined text field disabled input text color | md.comp.outlined-text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled input text opacity | md.comp.outlined-text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Outlined | Disabled | Outlined text field disabled label text color | md.comp.outlined-text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled label text opacity | md.comp.outlined-text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Outlined | Disabled | Outlined text field disabled leading icon color | md.comp.outlined-text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled leading icon opacity | md.comp.outlined-text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Outlined | Disabled | Outlined text field disabled outline color | md.comp.outlined-text-field.disabled.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled outline opacity | md.comp.outlined-text-field.disabled.outline.opacity |  | 0.12 |  |
| Text field - Outlined | Disabled | Outlined text field disabled outline width | md.comp.outlined-text-field.disabled.outline.width |  | 1dp |  |
| Text field - Outlined | Disabled | Outlined text field disabled supporting text color | md.comp.outlined-text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled supporting text opacity | md.comp.outlined-text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Outlined | Disabled | Outlined text field disabled trailing-icon color | md.comp.outlined-text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Disabled | Outlined text field disabled trailing-icon opacity | md.comp.outlined-text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus caret color | md.comp.outlined-text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Focused | Outlined text field focus indicator color - error | md.comp.outlined-text-field.error.focus.indicator.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus input text color | md.comp.outlined-text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus label text color | md.comp.outlined-text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus leading icon color | md.comp.outlined-text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus outline color | md.comp.outlined-text-field.error.focus.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus supporting text color | md.comp.outlined-text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Focused | Outlined text field error focus trailing icon color | md.comp.outlined-text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover input text color | md.comp.outlined-text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover label text color | md.comp.outlined-text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover leading icon color | md.comp.outlined-text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover outline color | md.comp.outlined-text-field.error.hover.outline.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover supporting text color | md.comp.outlined-text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error / Hovered | Outlined text field error hover trailing icon color | md.comp.outlined-text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Outlined | Error | Outlined text field error input text color | md.comp.outlined-text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Error | Outlined text field error label text color | md.comp.outlined-text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error | Outlined text field error leading icon color | md.comp.outlined-text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Error | Outlined text field error outline color | md.comp.outlined-text-field.error.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error | Outlined text field error supporting text color | md.comp.outlined-text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Error | Outlined text field error trailing icon color | md.comp.outlined-text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Outlined | Focused | Outlined text field focus indicator color | md.comp.outlined-text-field.focus.indicator.outline.color | md.sys.color.secondary | #625B71 |  |
| Text field - Outlined | Focused | Outlined text field focus indicator thickness | md.comp.outlined-text-field.focus.indicator.outline.thickness | md.sys.state.focus-indicator.thickness | 3dp |  |
| Text field - Outlined | Focused | Outlined text field focus input text color | md.comp.outlined-text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Focused | Outlined text field focus label text color | md.comp.outlined-text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Outlined | Focused | Outlined text field focus leading icon color | md.comp.outlined-text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Focused | Outlined text field focus outline color | md.comp.outlined-text-field.focus.outline.color | md.sys.color.primary | #6750A4 |  |
| Text field - Outlined | Focused | Outlined text field focus outline width | md.comp.outlined-text-field.focus.outline.width |  | 3dp |  |
| Text field - Outlined | Focused | Outlined text field focus supporting text color | md.comp.outlined-text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Focused | Outlined text field focus trailing icon color | md.comp.outlined-text-field.focus.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Hovered | Outlined text field hover input text color | md.comp.outlined-text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Hovered | Outlined text field hover label text color | md.comp.outlined-text-field.hover.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Hovered | Outlined text field hover leading icon color | md.comp.outlined-text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Hovered | Outlined text field hover outline color | md.comp.outlined-text-field.hover.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Hovered | Outlined text field hover outline width | md.comp.outlined-text-field.hover.outline.width |  | 1dp |  |
| Text field - Outlined | Hovered | Outlined text field hover supporting text color | md.comp.outlined-text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Hovered | Outlined text field hover trailing icon color | md.comp.outlined-text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field input text color | md.comp.outlined-text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Outlined | Enabled | Outlined text field input text font | md.comp.outlined-text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Outlined | Enabled | Outlined text field input text line height | md.comp.outlined-text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Outlined | Enabled | Outlined text field input text placeholder color | md.comp.outlined-text-field.input-text.placeholder.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field input text prefix color | md.comp.outlined-text-field.input-text.prefix.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field input text size | md.comp.outlined-text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Outlined | Enabled | Outlined text field input text suffix color | md.comp.outlined-text-field.input-text.suffix.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field input text tracking | md.comp.outlined-text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Outlined | Enabled | Outlined text field input text type | md.comp.outlined-text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Outlined | Enabled | Outlined text field input text weight | md.comp.outlined-text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Outlined | Enabled | Outlined text field label text color | md.comp.outlined-text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field label text font | md.comp.outlined-text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Outlined | Enabled | Outlined text field label text line height | md.comp.outlined-text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Outlined | Enabled | Outlined text field label text populated line height | md.comp.outlined-text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Outlined | Enabled | Outlined text field label text populated size | md.comp.outlined-text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Outlined | Enabled | Outlined text field label text size | md.comp.outlined-text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Outlined | Enabled | Outlined text field label text tracking | md.comp.outlined-text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Outlined | Enabled | Outlined text field label text type | md.comp.outlined-text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Outlined | Enabled | Outlined text field label text weight | md.comp.outlined-text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Outlined | Enabled | Outlined text field leading icon color | md.comp.outlined-text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field leading icon size | md.comp.outlined-text-field.leading-icon.size |  | 24dp |  |
| Text field - Outlined | Enabled | Outlined text field outline color | md.comp.outlined-text-field.outline.color | md.sys.color.outline | #79747E |  |
| Text field - Outlined | Layout | Outlined text field outline width | md.comp.outlined-text-field.outline.width |  | 1dp |  |
| Text field - Outlined | Enabled | Outlined text field supporting text color | md.comp.outlined-text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field supporting text font | md.comp.outlined-text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Outlined | Enabled | Outlined text field supporting text line height | md.comp.outlined-text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Outlined | Enabled | Outlined text field supporting text size | md.comp.outlined-text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Outlined | Enabled | Outlined text field supporting text tracking | md.comp.outlined-text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Outlined | Enabled | Outlined text field supporting text type | md.comp.outlined-text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Outlined | Enabled | Outlined text field supporting text weight | md.comp.outlined-text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Outlined | Enabled | Outlined text field trailing icon color | md.comp.outlined-text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Outlined | Enabled | Outlined text field trailing icon size | md.comp.outlined-text-field.trailing-icon.size |  | 24dp |  |

### Text field - Select, outlined

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Select, outlined | Enabled | Outlined select menu cascading menu indicator icon color | md.comp.outlined-select.menu.cascading-menu-indicator.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Layout | Outlined select menu cascading menu indicator icon size | md.comp.outlined-select.menu.cascading-menu-indicator.icon.size |  | 24dp |  |
| Text field - Select, outlined | Enabled | Outlined select menu container color | md.comp.outlined-select.menu.container.color | md.sys.color.surface-container | #F3EDF7 |  |
| Text field - Select, outlined | Enabled | Outlined select menu container elevation | md.comp.outlined-select.menu.container.elevation | md.sys.elevation.level2 | 3dp |  |
| Text field - Select, outlined | Enabled | Outlined select menu container shadow color | md.comp.outlined-select.menu.container.shadow-color | md.sys.color.shadow | #000000 |  |
| Text field - Select, outlined | Shape | Outlined select menu container shape | md.comp.outlined-select.menu.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Select, outlined | Enabled | Outlined select menu container surface tint layer color | md.comp.outlined-select.menu.container.surface-tint-layer.color | md.sys.color.surface-tint | #6750A4 |  |
| Text field - Select, outlined | Enabled | Outlined select menu divider color | md.comp.outlined-select.menu.divider.color | md.sys.color.surface-variant | #E7E0EC |  |
| Text field - Select, outlined | Enabled | Outlined select menu divider height | md.comp.outlined-select.menu.divider.height |  | 1dp |  |
| Text field - Select, outlined | Layout | Outlined select menu list item container height | md.comp.outlined-select.menu.list-item.container.height |  | 48dp |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text color | md.comp.outlined-select.menu.list-item.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text font | md.comp.outlined-select.menu.list-item.label-text.font | md.sys.typescale.label-large.font | Roboto |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text line height | md.comp.outlined-select.menu.list-item.label-text.line-height | md.sys.typescale.label-large.line-height | 20pt |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text size | md.comp.outlined-select.menu.list-item.label-text.size | md.sys.typescale.label-large.size | 14pt |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text tracking | md.comp.outlined-select.menu.list-item.label-text.tracking | md.sys.typescale.label-large.tracking | 0.1pt |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text type style | md.comp.outlined-select.menu.list-item.label-text.type | md.sys.typescale.label-large.font | Roboto / 500 / 14pt / 0.1pt / 20pt |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item label text weight | md.comp.outlined-select.menu.list-item.label-text.weight | md.sys.typescale.label-large.weight | 700 |  |
| Text field - Select, outlined | Enabled / Toggle selected | Outlined select menu list item selected container color | md.comp.outlined-select.menu.list-item.selected.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item with leading icon leading icon color | md.comp.outlined-select.menu.list-item.with-leading-icon.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item with leading icon leading icon size | md.comp.outlined-select.menu.list-item.with-leading-icon.leading-icon.size |  | 24dp |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item with trailing icon trailing icon color | md.comp.outlined-select.menu.list-item.with-trailing-icon.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select menu list item with trailing icon trailing icon size | md.comp.outlined-select.menu.list-item.with-trailing-icon.trailing-icon.size |  | 24dp |  |
| Text field - Select, outlined | Enabled | Outlined select text field caret color | md.comp.outlined-select.text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, outlined | Enabled | Outlined select text field container color | md.comp.outlined-select.text-field.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Select, outlined | Layout | Outlined select text field container height | md.comp.outlined-select.text-field.container.height |  | 56dp |  |
| Text field - Select, outlined | Shape | Outlined select text field container shape | md.comp.outlined-select.text-field.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Select, outlined | Disabled | Outlined select text field disabled input text color | md.comp.outlined-select.text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled input text opacity | md.comp.outlined-select.text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled label text color | md.comp.outlined-select.text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled label text opacity | md.comp.outlined-select.text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled leading icon color | md.comp.outlined-select.text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled leading icon opacity | md.comp.outlined-select.text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled outline color | md.comp.outlined-select.text-field.disabled.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled outline opacity | md.comp.outlined-select.text-field.disabled.outline.opacity |  | 0.12 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled outline width | md.comp.outlined-select.text-field.disabled.outline.width |  | 1dp |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled supporting text color | md.comp.outlined-select.text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled supporting text opacity | md.comp.outlined-select.text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled trailing icon color | md.comp.outlined-select.text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Disabled | Outlined select text field disabled trailing icon opacity | md.comp.outlined-select.text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus caret color | md.comp.outlined-select.text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus input text color | md.comp.outlined-select.text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus label text color | md.comp.outlined-select.text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus leading icon color | md.comp.outlined-select.text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus outline color | md.comp.outlined-select.text-field.error.focus.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus supporting text color | md.comp.outlined-select.text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Focused | Outlined select text field error focus trailing icon color | md.comp.outlined-select.text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover input text color | md.comp.outlined-select.text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover label text color | md.comp.outlined-select.text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover leading icon color | md.comp.outlined-select.text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover outline color | md.comp.outlined-select.text-field.error.hover.outline.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover state layer color | md.comp.outlined-select.text-field.error.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover state layer opacity | md.comp.outlined-select.text-field.error.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover supporting text color | md.comp.outlined-select.text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error / Hovered | Outlined select text field error hover trailing icon color | md.comp.outlined-select.text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, outlined | Error | Outlined select text field error input text color | md.comp.outlined-select.text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Error | Outlined select text field error label text color | md.comp.outlined-select.text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error | Outlined select text field error leading icon color | md.comp.outlined-select.text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Error | Outlined select text field error outline color | md.comp.outlined-select.text-field.error.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error | Outlined select text field error supporting text color | md.comp.outlined-select.text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Error | Outlined select text field error trailing icon color | md.comp.outlined-select.text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Select, outlined | Focused | Outlined select text field focus input text color | md.comp.outlined-select.text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Focused | Outlined select text field focus label text color | md.comp.outlined-select.text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, outlined | Focused | Outlined select text field focus leading icon color | md.comp.outlined-select.text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Focused | Outlined select text field focus outline color | md.comp.outlined-select.text-field.focus.outline.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, outlined | Focused | Outlined select text field focus outline width | md.comp.outlined-select.text-field.focus.outline.width | md.sys.state.focus-indicator.thickness | 3dp |  |
| Text field - Select, outlined | Focused | Outlined select text field focus supporting text color | md.comp.outlined-select.text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Focused | Outlined select text field focus trailing icon color | md.comp.outlined-select.text-field.focus.trailing-icon.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover input text color | md.comp.outlined-select.text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover label text color | md.comp.outlined-select.text-field.hover.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover leading icon color | md.comp.outlined-select.text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover outline color | md.comp.outlined-select.text-field.hover.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover outline width | md.comp.outlined-select.text-field.hover.outline.width |  | 1dp |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover state layer color | md.comp.outlined-select.text-field.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover state layer opacity | md.comp.outlined-select.text-field.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover supporting text color | md.comp.outlined-select.text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Hovered | Outlined select text field hover trailing icon color | md.comp.outlined-select.text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text color | md.comp.outlined-select.text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text font | md.comp.outlined-select.text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text line height | md.comp.outlined-select.text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text size | md.comp.outlined-select.text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text tracking | md.comp.outlined-select.text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text type style | md.comp.outlined-select.text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field input text weight | md.comp.outlined-select.text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text color | md.comp.outlined-select.text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text font | md.comp.outlined-select.text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text line height | md.comp.outlined-select.text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text populated line height | md.comp.outlined-select.text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text populated size | md.comp.outlined-select.text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text size | md.comp.outlined-select.text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text tracking | md.comp.outlined-select.text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text type style | md.comp.outlined-select.text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field label text weight | md.comp.outlined-select.text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Select, outlined | Enabled | Outlined select text field leading icon color | md.comp.outlined-select.text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select text field leading icon size | md.comp.outlined-select.text-field.leading-icon.size |  | 24dp |  |
| Text field - Select, outlined | Enabled | Outlined select text field outline color | md.comp.outlined-select.text-field.outline.color | md.sys.color.outline | #79747E |  |
| Text field - Select, outlined | Layout | Outlined select text field outline width | md.comp.outlined-select.text-field.outline.width |  | 1dp |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text color | md.comp.outlined-select.text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text font | md.comp.outlined-select.text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text line height | md.comp.outlined-select.text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text size | md.comp.outlined-select.text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text tracking | md.comp.outlined-select.text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text type style | md.comp.outlined-select.text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Select, outlined | Enabled | Outlined select text field supporting text weight | md.comp.outlined-select.text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Select, outlined | Enabled | Outlined select text field trailing icon color | md.comp.outlined-select.text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, outlined | Enabled | Outlined select text field trailing icon size | md.comp.outlined-select.text-field.trailing-icon.size |  | 24dp |  |

### Text field - Select, filled

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Select, filled | Enabled | Filled select menu cascading menu indicator icon color | md.comp.filled-select.menu.cascading-menu-indicator.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Layout | Filled select menu cascading menu indicator icon size | md.comp.filled-select.menu.cascading-menu-indicator.icon.size |  | 24dp |  |
| Text field - Select, filled | Enabled | Filled select menu container color | md.comp.filled-select.menu.container.color | md.sys.color.surface-container | #F3EDF7 |  |
| Text field - Select, filled | Enabled | Filled select menu container elevation | md.comp.filled-select.menu.container.elevation | md.sys.elevation.level2 | 3dp |  |
| Text field - Select, filled | Enabled | Filled select menu container shadow color | md.comp.filled-select.menu.container.shadow-color | md.sys.color.shadow | #000000 |  |
| Text field - Select, filled | Shape | Filled select menu container shape | md.comp.filled-select.menu.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Select, filled | Enabled | Filled select menu container surface tint layer color | md.comp.filled-select.menu.container.surface-tint-layer.color | md.sys.color.surface-tint | #6750A4 |  |
| Text field - Select, filled | Enabled | Filled select menu divider color | md.comp.filled-select.menu.divider.color | md.sys.color.surface-variant | #E7E0EC |  |
| Text field - Select, filled | Enabled | Filled select menu divider height | md.comp.filled-select.menu.divider.height |  | 1dp |  |
| Text field - Select, filled | Layout | Filled select menu list item container height | md.comp.filled-select.menu.list-item.container.height |  | 48dp |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text color | md.comp.filled-select.menu.list-item.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text font | md.comp.filled-select.menu.list-item.label-text.font | md.sys.typescale.label-large.font | Roboto |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text line height | md.comp.filled-select.menu.list-item.label-text.line-height | md.sys.typescale.label-large.line-height | 20pt |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text size | md.comp.filled-select.menu.list-item.label-text.size | md.sys.typescale.label-large.size | 14pt |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text tracking | md.comp.filled-select.menu.list-item.label-text.tracking | md.sys.typescale.label-large.tracking | 0.1pt |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text type style | md.comp.filled-select.menu.list-item.label-text.type | md.sys.typescale.label-large.font | Roboto / 500 / 14pt / 0.1pt / 20pt |  |
| Text field - Select, filled | Enabled | Filled select menu list item label text weight | md.comp.filled-select.menu.list-item.label-text.weight | md.sys.typescale.label-large.weight | 700 |  |
| Text field - Select, filled | Enabled / Toggle selected | Filled select menu list item selected container color | md.comp.filled-select.menu.list-item.selected.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Select, filled | Enabled | Filled select menu list item with leading icon leading icon color | md.comp.filled-select.menu.list-item.with-leading-icon.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select menu list item with leading icon leading icon size | md.comp.filled-select.menu.list-item.with-leading-icon.leading-icon.size |  | 24dp |  |
| Text field - Select, filled | Enabled | Filled select menu list item with trailing icon trailing icon color | md.comp.filled-select.menu.list-item.with-trailing-icon.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select menu list item with trailing icon trailing icon size | md.comp.filled-select.menu.list-item.with-trailing-icon.trailing-icon.size |  | 24dp |  |
| Text field - Select, filled | Enabled | Filled select text field active indicator color | md.comp.filled-select.text-field.active-indicator.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field active indicator height | md.comp.filled-select.text-field.active-indicator.height |  | 1dp |  |
| Text field - Select, filled | Enabled | Filled select text field caret color | md.comp.filled-select.text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, filled | Enabled | Filled select text field container color | md.comp.filled-select.text-field.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Select, filled | Layout | Filled select text field container height | md.comp.filled-select.text-field.container.height |  | 56dp |  |
| Text field - Select, filled | Shape | Filled select text field container shape | md.comp.filled-select.text-field.container.shape | md.sys.shape.corner.extra-small.top | Rounded Corners | Resolved as rounded corners. |
| Text field - Select, filled | Disabled | Filled select text field disabled active indicator color | md.comp.filled-select.text-field.disabled.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled active indicator height | md.comp.filled-select.text-field.disabled.active-indicator.height |  | 1dp |  |
| Text field - Select, filled | Disabled | Filled select text field disabled active indicator opacity | md.comp.filled-select.text-field.disabled.active-indicator.opacity |  | 0.38 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled container color | md.comp.filled-select.text-field.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled container opacity | md.comp.filled-select.text-field.disabled.container.opacity |  | 0.04 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled input text color | md.comp.filled-select.text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled input text opacity | md.comp.filled-select.text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled label text color | md.comp.filled-select.text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled label text opacity | md.comp.filled-select.text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled leading icon color | md.comp.filled-select.text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled leading icon opacity | md.comp.filled-select.text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled supporting text color | md.comp.filled-select.text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled supporting text opacity | md.comp.filled-select.text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled trailing icon color | md.comp.filled-select.text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Disabled | Filled select text field disabled trailing icon opacity | md.comp.filled-select.text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Select, filled | Error | Filled select text field error active indicator color | md.comp.filled-select.text-field.error.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus active indicator color | md.comp.filled-select.text-field.error.focus.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus caret color | md.comp.filled-select.text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus input text color | md.comp.filled-select.text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus label text color | md.comp.filled-select.text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus leading icon color | md.comp.filled-select.text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus supporting text color | md.comp.filled-select.text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Focused | Filled select text field error focus trailing icon color | md.comp.filled-select.text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover active indicator color | md.comp.filled-select.text-field.error.hover.active-indicator.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover input text color | md.comp.filled-select.text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover label text color | md.comp.filled-select.text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover leading icon color | md.comp.filled-select.text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover state layer color | md.comp.filled-select.text-field.error.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover state layer opacity | md.comp.filled-select.text-field.error.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover supporting text color | md.comp.filled-select.text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error / Hovered | Filled select text field error hover trailing icon color | md.comp.filled-select.text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Select, filled | Error | Filled select text field error input text color | md.comp.filled-select.text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Error | Filled select text field error label text color | md.comp.filled-select.text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error | Filled select text field error leading icon color | md.comp.filled-select.text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Error | Filled select text field error supporting text color | md.comp.filled-select.text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Error | Filled select text field error trailing icon color | md.comp.filled-select.text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Select, filled | Focused | Filled select text field focus active indicator color | md.comp.filled-select.text-field.focus.active-indicator.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, filled | Focused | Filled select text field focus active indicator height | md.comp.filled-select.text-field.focus.active-indicator.height |  | 2dp |  |
| Text field - Select, filled | Focused | Filled select text field focus input text color | md.comp.filled-select.text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Focused | Filled select text field focus label text color | md.comp.filled-select.text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, filled | Focused | Filled select text field focus leading icon color | md.comp.filled-select.text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Focused | Filled select text field focus supporting text color | md.comp.filled-select.text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Focused | Filled select text field focus trailing icon color | md.comp.filled-select.text-field.focus.trailing-icon.color | md.sys.color.primary | #6750A4 |  |
| Text field - Select, filled | Hovered | Filled select text field hover active indicator color | md.comp.filled-select.text-field.hover.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Hovered | Filled select text field hover active indicator height | md.comp.filled-select.text-field.hover.active-indicator.height |  | 1dp |  |
| Text field - Select, filled | Hovered | Filled select text field hover input text color | md.comp.filled-select.text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Hovered | Filled select text field hover label text color | md.comp.filled-select.text-field.hover.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Hovered | Filled select text field hover leading icon color | md.comp.filled-select.text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Hovered | Filled select text field hover state layer color | md.comp.filled-select.text-field.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Hovered | Filled select text field hover state layer opacity | md.comp.filled-select.text-field.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Select, filled | Hovered | Filled select text field hover supporting text color | md.comp.filled-select.text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Hovered | Filled select text field hover trailing icon color | md.comp.filled-select.text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field input text color | md.comp.filled-select.text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Select, filled | Enabled | Filled select text field input text font | md.comp.filled-select.text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Select, filled | Enabled | Filled select text field input text line height | md.comp.filled-select.text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Select, filled | Enabled | Filled select text field input text size | md.comp.filled-select.text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Select, filled | Enabled | Filled select text field input text tracking | md.comp.filled-select.text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Select, filled | Enabled | Filled select text field input text type style | md.comp.filled-select.text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Select, filled | Enabled | Filled select text field input text weight | md.comp.filled-select.text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Select, filled | Enabled | Filled select text field label text color | md.comp.filled-select.text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field label text font | md.comp.filled-select.text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Select, filled | Enabled | Filled select text field label text line height | md.comp.filled-select.text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text populated line height | md.comp.filled-select.text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text populated size | md.comp.filled-select.text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text size | md.comp.filled-select.text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text tracking | md.comp.filled-select.text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text type style | md.comp.filled-select.text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Select, filled | Enabled | Filled select text field label text weight | md.comp.filled-select.text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Select, filled | Enabled | Filled select text field leading icon color | md.comp.filled-select.text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field leading icon size | md.comp.filled-select.text-field.leading-icon.size |  | 24dp |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text color | md.comp.filled-select.text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text font | md.comp.filled-select.text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text line height | md.comp.filled-select.text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text size | md.comp.filled-select.text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text tracking | md.comp.filled-select.text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text type style | md.comp.filled-select.text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Select, filled | Enabled | Filled select text field supporting text weight | md.comp.filled-select.text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Select, filled | Enabled | Filled select text field trailing icon color | md.comp.filled-select.text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Select, filled | Enabled | Filled select text field trailing icon size | md.comp.filled-select.text-field.trailing-icon.size |  | 24dp |  |

### Text field - Autocomplete, filled

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu cascading menu indicator icon color | md.comp.filled-autocomplete.menu.cascading-menu-indicator.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Layout | Filled autocomplete menu cascading menu indicator icon size | md.comp.filled-autocomplete.menu.cascading-menu-indicator.icon.size |  | 24dp |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu container color | md.comp.filled-autocomplete.menu.container.color | md.sys.color.surface-container | #F3EDF7 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu container elevation | md.comp.filled-autocomplete.menu.container.elevation | md.sys.elevation.level2 | 3dp |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu container shadow color | md.comp.filled-autocomplete.menu.container.shadow-color | md.sys.color.shadow | #000000 |  |
| Text field - Autocomplete, filled | Shape | Filled autocomplete menu container shape | md.comp.filled-autocomplete.menu.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu container surface tint layer color | md.comp.filled-autocomplete.menu.container.surface-tint-layer.color | md.sys.color.surface-tint | #6750A4 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu divider color | md.comp.filled-autocomplete.menu.divider.color | md.sys.color.surface-variant | #E7E0EC |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu divider height | md.comp.filled-autocomplete.menu.divider.height |  | 1dp |  |
| Text field - Autocomplete, filled | Layout | Filled autocomplete menu list item container height | md.comp.filled-autocomplete.menu.list-item.container.height |  | 48dp |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text color | md.comp.filled-autocomplete.menu.list-item.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text font | md.comp.filled-autocomplete.menu.list-item.label-text.font | md.sys.typescale.label-large.font | Roboto |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text line height | md.comp.filled-autocomplete.menu.list-item.label-text.line-height | md.sys.typescale.label-large.line-height | 20pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text size | md.comp.filled-autocomplete.menu.list-item.label-text.size | md.sys.typescale.label-large.size | 14pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text tracking | md.comp.filled-autocomplete.menu.list-item.label-text.tracking | md.sys.typescale.label-large.tracking | 0.1pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text type style | md.comp.filled-autocomplete.menu.list-item.label-text.type | md.sys.typescale.label-large.font | Roboto / 500 / 14pt / 0.1pt / 20pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete menu list item label text weight | md.comp.filled-autocomplete.menu.list-item.label-text.weight | md.sys.typescale.label-large.weight | 700 |  |
| Text field - Autocomplete, filled | Enabled / Toggle selected | Filled autocomplete menu list item selected container color | md.comp.filled-autocomplete.menu.list-item.selected.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field active indicator color | md.comp.filled-autocomplete.text-field.active-indicator.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field active indicator height | md.comp.filled-autocomplete.text-field.active-indicator.height |  | 1dp |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field caret color | md.comp.filled-autocomplete.text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field container color | md.comp.filled-autocomplete.text-field.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Autocomplete, filled | Layout | Filled autocomplete text field container height | md.comp.filled-autocomplete.text-field.container.height |  | 56dp |  |
| Text field - Autocomplete, filled | Shape | Filled autocomplete text field container shape | md.comp.filled-autocomplete.text-field.container.shape | md.sys.shape.corner.extra-small.top | Rounded Corners | Resolved as rounded corners. |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled active indicator color | md.comp.filled-autocomplete.text-field.disabled.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled active indicator height | md.comp.filled-autocomplete.text-field.disabled.active-indicator.height |  | 1dp |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled active indicator opacity | md.comp.filled-autocomplete.text-field.disabled.active-indicator.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled container color | md.comp.filled-autocomplete.text-field.disabled.container.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled container opacity | md.comp.filled-autocomplete.text-field.disabled.container.opacity |  | 0.04 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled input text color | md.comp.filled-autocomplete.text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled input text opacity | md.comp.filled-autocomplete.text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled label text color | md.comp.filled-autocomplete.text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled label text opacity | md.comp.filled-autocomplete.text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled leading icon color | md.comp.filled-autocomplete.text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled leading icon opacity | md.comp.filled-autocomplete.text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled supporting text color | md.comp.filled-autocomplete.text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled supporting text opacity | md.comp.filled-autocomplete.text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled trailing icon color | md.comp.filled-autocomplete.text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Disabled | Filled autocomplete text field disabled trailing icon opacity | md.comp.filled-autocomplete.text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error active indicator color | md.comp.filled-autocomplete.text-field.error.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus active indicator color | md.comp.filled-autocomplete.text-field.error.focus.active-indicator.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Focused | error.Filled focus caret color | md.comp.filled-autocomplete.text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus input text color | md.comp.filled-autocomplete.text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus label text color | md.comp.filled-autocomplete.text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus leading icon color | md.comp.filled-autocomplete.text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus supporting text color | md.comp.filled-autocomplete.text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Focused | Filled autocomplete text field error focus trailing icon color | md.comp.filled-autocomplete.text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover active indicator color | md.comp.filled-autocomplete.text-field.error.hover.active-indicator.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover input text color | md.comp.filled-autocomplete.text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover label text color | md.comp.filled-autocomplete.text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover leading icon color | md.comp.filled-autocomplete.text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover state layer color | md.comp.filled-autocomplete.text-field.error.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover state layer opacity | md.comp.filled-autocomplete.text-field.error.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover supporting text color | md.comp.filled-autocomplete.text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error / Hovered | Filled autocomplete text field error hover trailing icon color | md.comp.filled-autocomplete.text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error input text color | md.comp.filled-autocomplete.text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error label text color | md.comp.filled-autocomplete.text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error leading icon color | md.comp.filled-autocomplete.text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error supporting text color | md.comp.filled-autocomplete.text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Error | Filled autocomplete text field error trailing icon color | md.comp.filled-autocomplete.text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus active indicator color | md.comp.filled-autocomplete.text-field.focus.active-indicator.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus active indicator height | md.comp.filled-autocomplete.text-field.focus.active-indicator.height |  | 2dp |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus input text color | md.comp.filled-autocomplete.text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus label text color | md.comp.filled-autocomplete.text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus leading icon color | md.comp.filled-autocomplete.text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus supporting text color | md.comp.filled-autocomplete.text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Focused | Filled autocomplete text field focus trailing icon color | md.comp.filled-autocomplete.text-field.focus.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover active indicator color | md.comp.filled-autocomplete.text-field.hover.active-indicator.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover active indicator height | md.comp.filled-autocomplete.text-field.hover.active-indicator.height |  | 1dp |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover input text color | md.comp.filled-autocomplete.text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover label text color | md.comp.filled-autocomplete.text-field.hover.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover leading icon color | md.comp.filled-autocomplete.text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover state layer color | md.comp.filled-autocomplete.text-field.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover state layer opacity | md.comp.filled-autocomplete.text-field.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover supporting text color | md.comp.filled-autocomplete.text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Hovered | Filled autocomplete text field hover trailing icon color | md.comp.filled-autocomplete.text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text color | md.comp.filled-autocomplete.text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text font | md.comp.filled-autocomplete.text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text line height | md.comp.filled-autocomplete.text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text size | md.comp.filled-autocomplete.text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text tracking | md.comp.filled-autocomplete.text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text type styl | md.comp.filled-autocomplete.text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field input text weight | md.comp.filled-autocomplete.text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text color | md.comp.filled-autocomplete.text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text font | md.comp.filled-autocomplete.text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text line height | md.comp.filled-autocomplete.text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text populated line height | md.comp.filled-autocomplete.text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text populated size | md.comp.filled-autocomplete.text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text size | md.comp.filled-autocomplete.text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text tracking | md.comp.filled-autocomplete.text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text type style | md.comp.filled-autocomplete.text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field label text weight | md.comp.filled-autocomplete.text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field leading icon color | md.comp.filled-autocomplete.text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field leading icon size | md.comp.filled-autocomplete.text-field.leading-icon.size |  | 20dp |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text color | md.comp.filled-autocomplete.text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text font | md.comp.filled-autocomplete.text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text line height | md.comp.filled-autocomplete.text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text size | md.comp.filled-autocomplete.text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text tracking | md.comp.filled-autocomplete.text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text type style | md.comp.filled-autocomplete.text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field supporting text weight | md.comp.filled-autocomplete.text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field trailing icon color | md.comp.filled-autocomplete.text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, filled | Enabled | Filled autocomplete text field trailing icon size | md.comp.filled-autocomplete.text-field.trailing-icon.size |  | 24dp |  |

### Text field - Autocomplete, outlined

| Token Set | Group | Label | Token | Source token | Value | Notes |
|---|---|---|---|---|---|---|
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu cascading menu indicator icon color | md.comp.outlined-autocomplete.menu.cascading-menu-indicator.icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Layout | Outlined autocomplete menu cascading menu indicator icon size | md.comp.outlined-autocomplete.menu.cascading-menu-indicator.icon.size |  | 24dp |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu container color | md.comp.outlined-autocomplete.menu.container.color | md.sys.color.surface-container | #F3EDF7 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu container elevation | md.comp.outlined-autocomplete.menu.container.elevation | md.sys.elevation.level2 | 3dp |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu container shadow color | md.comp.outlined-autocomplete.menu.container.shadow-color | md.sys.color.shadow | #000000 |  |
| Text field - Autocomplete, outlined | Shape | Outlined autocomplete menu container shape | md.comp.outlined-autocomplete.menu.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu container surface tint layer color | md.comp.outlined-autocomplete.menu.container.surface-tint-layer.color | md.sys.color.surface-tint | #6750A4 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu divider color | md.comp.outlined-autocomplete.menu.divider.color | md.sys.color.surface-variant | #E7E0EC |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu divider height | md.comp.outlined-autocomplete.menu.divider.height |  | 1dp |  |
| Text field - Autocomplete, outlined | Layout | Outlined autocomplete menu list item container height | md.comp.outlined-autocomplete.menu.list-item.container.height |  | 48dp |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text color | md.comp.outlined-autocomplete.menu.list-item.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text font | md.comp.outlined-autocomplete.menu.list-item.label-text.font | md.sys.typescale.label-large.font | Roboto |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text line height | md.comp.outlined-autocomplete.menu.list-item.label-text.line-height | md.sys.typescale.label-large.line-height | 20pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text size | md.comp.outlined-autocomplete.menu.list-item.label-text.size | md.sys.typescale.label-large.size | 14pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text tracking | md.comp.outlined-autocomplete.menu.list-item.label-text.tracking | md.sys.typescale.label-large.tracking | 0.1pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text type style | md.comp.outlined-autocomplete.menu.list-item.label-text.type | md.sys.typescale.label-large.font | Roboto / 500 / 14pt / 0.1pt / 20pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete menu list item label text weight | md.comp.outlined-autocomplete.menu.list-item.label-text.weight | md.sys.typescale.label-large.weight | 700 |  |
| Text field - Autocomplete, outlined | Enabled / Toggle selected | Outlined autocomplete menu list item selected container color | md.comp.outlined-autocomplete.menu.list-item.selected.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field caret color | md.comp.outlined-autocomplete.text-field.caret.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field container color | md.comp.outlined-autocomplete.text-field.container.color | md.sys.color.surface-container-highest | #E6E0E9 |  |
| Text field - Autocomplete, outlined | Layout | Outlined autocomplete text field container height | md.comp.outlined-autocomplete.text-field.container.height |  | 56dp |  |
| Text field - Autocomplete, outlined | Shape | Outlined autocomplete text field container shape | md.comp.outlined-autocomplete.text-field.container.shape | md.sys.shape.corner.extra-small | 4dp | Resolved as rounded corners. |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled input text color | md.comp.outlined-autocomplete.text-field.disabled.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled input text opacity | md.comp.outlined-autocomplete.text-field.disabled.input-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled label text color | md.comp.outlined-autocomplete.text-field.disabled.label-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled label text opacity | md.comp.outlined-autocomplete.text-field.disabled.label-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled leading icon color | md.comp.outlined-autocomplete.text-field.disabled.leading-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled leading icon opacity | md.comp.outlined-autocomplete.text-field.disabled.leading-icon.opacity |  | 0.38 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled outline color | md.comp.outlined-autocomplete.text-field.disabled.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled outline opacity | md.comp.outlined-autocomplete.text-field.disabled.outline.opacity |  | 0.12 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled outline width | md.comp.outlined-autocomplete.text-field.disabled.outline.width |  | 1dp |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled supporting text color | md.comp.outlined-autocomplete.text-field.disabled.supporting-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled supporting text opacity | md.comp.outlined-autocomplete.text-field.disabled.supporting-text.opacity |  | 0.38 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled trailing icon color | md.comp.outlined-autocomplete.text-field.disabled.trailing-icon.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Disabled | Outlined autocomplete text field disabled trailing icon opacity | md.comp.outlined-autocomplete.text-field.disabled.trailing-icon.opacity |  | 0.38 |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus caret color | md.comp.outlined-autocomplete.text-field.error.focus.caret.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus input text color | md.comp.outlined-autocomplete.text-field.error.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus label text color | md.comp.outlined-autocomplete.text-field.error.focus.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus leading icon color | md.comp.outlined-autocomplete.text-field.error.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus outline color | md.comp.outlined-autocomplete.text-field.error.focus.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlined autocomplete text field error focus supporting text color | md.comp.outlined-autocomplete.text-field.error.focus.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Focused | Outlinedfield error focus trailing icon color | md.comp.outlined-autocomplete.text-field.error.focus.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover input text color | md.comp.outlined-autocomplete.text-field.error.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover label text color | md.comp.outlined-autocomplete.text-field.error.hover.label-text.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover leading icon color | md.comp.outlined-autocomplete.text-field.error.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover outline color | md.comp.outlined-autocomplete.text-field.error.hover.outline.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover state layer color | md.comp.outlined-autocomplete.text-field.error.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover state layer opacity | md.comp.outlined-autocomplete.text-field.error.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover supporting text color | md.comp.outlined-autocomplete.text-field.error.hover.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error / Hovered | Outlined autocomplete text field error hover trailing icon color | md.comp.outlined-autocomplete.text-field.error.hover.trailing-icon.color | md.sys.color.on-error-container | #8C1D18 |  |
| Text field - Autocomplete, outlined | Error | Outlined autocomplete text field error input text color | md.comp.outlined-autocomplete.text-field.error.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Error | Outlined autocomplete text field error label text color | md.comp.outlined-autocomplete.text-field.error.label-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error | Outlined autocomplete text field error leading icon color | md.comp.outlined-autocomplete.text-field.error.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Error | text field error outline color | md.comp.outlined-autocomplete.text-field.error.outline.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error | Outlined autocomplete text field error supporting text color | md.comp.outlined-autocomplete.text-field.error.supporting-text.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Error | Outlined autocomplete text field error trailing icon color | md.comp.outlined-autocomplete.text-field.error.trailing-icon.color | md.sys.color.error | #B3261E |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus input text color | md.comp.outlined-autocomplete.text-field.focus.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus label text color | md.comp.outlined-autocomplete.text-field.focus.label-text.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus leading icon color | md.comp.outlined-autocomplete.text-field.focus.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus outline color | md.comp.outlined-autocomplete.text-field.focus.outline.color | md.sys.color.primary | #6750A4 |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus outline width | md.comp.outlined-autocomplete.text-field.focus.outline.width |  | 2dp |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus supporting text color | md.comp.outlined-autocomplete.text-field.focus.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Focused | Outlined autocomplete text field focus trailing icon color | md.comp.outlined-autocomplete.text-field.focus.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover input text color | md.comp.outlined-autocomplete.text-field.hover.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover label text color | md.comp.outlined-autocomplete.text-field.hover.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover leading icon color | md.comp.outlined-autocomplete.text-field.hover.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover outline color | md.comp.outlined-autocomplete.text-field.hover.outline.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover outline width | md.comp.outlined-autocomplete.text-field.hover.outline.width |  | 1dp |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover state layer color | md.comp.outlined-autocomplete.text-field.hover.state-layer.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover state layer opacity | md.comp.outlined-autocomplete.text-field.hover.state-layer.opacity | md.sys.state.hover.state-layer-opacity | 0.08 |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover supporting text color | md.comp.outlined-autocomplete.text-field.hover.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Hovered | Outlined autocomplete text field hover trailing icon color | md.comp.outlined-autocomplete.text-field.hover.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text color | md.comp.outlined-autocomplete.text-field.input-text.color | md.sys.color.on-surface | #1D1B20 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text font | md.comp.outlined-autocomplete.text-field.input-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text line height | md.comp.outlined-autocomplete.text-field.input-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text size | md.comp.outlined-autocomplete.text-field.input-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text tracking | md.comp.outlined-autocomplete.text-field.input-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text type style | md.comp.outlined-autocomplete.text-field.input-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field input text weight | md.comp.outlined-autocomplete.text-field.input-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text color | md.comp.outlined-autocomplete.text-field.label-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text font | md.comp.outlined-autocomplete.text-field.label-text.font | md.sys.typescale.body-large.font | Roboto |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text line height | md.comp.outlined-autocomplete.text-field.label-text.line-height | md.sys.typescale.body-large.line-height | 24pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text populated line height | md.comp.outlined-autocomplete.text-field.label-text.populated.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text populated size | md.comp.outlined-autocomplete.text-field.label-text.populated.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text size | md.comp.outlined-autocomplete.text-field.label-text.size | md.sys.typescale.body-large.size | 16pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text tracking | md.comp.outlined-autocomplete.text-field.label-text.tracking | md.sys.typescale.body-large.tracking | 0.5pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text type style | md.comp.outlined-autocomplete.text-field.label-text.type | md.sys.typescale.body-large.font | Roboto / 400 / 16pt / 0.5pt / 24pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field label text weight | md.comp.outlined-autocomplete.text-field.label-text.weight | md.sys.typescale.body-large.weight | 400 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field leading icon color | md.comp.outlined-autocomplete.text-field.leading-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field leading icon size | md.comp.outlined-autocomplete.text-field.leading-icon.size |  | 24dp |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field outline color | md.comp.outlined-autocomplete.text-field.outline.color | md.sys.color.outline | #79747E |  |
| Text field - Autocomplete, outlined | Layout | Outlined autocomplete text field outline width | md.comp.outlined-autocomplete.text-field.outline.width |  | 1dp |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text color | md.comp.outlined-autocomplete.text-field.supporting-text.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text font | md.comp.outlined-autocomplete.text-field.supporting-text.font | md.sys.typescale.body-small.font | Roboto |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text line height | md.comp.outlined-autocomplete.text-field.supporting-text.line-height | md.sys.typescale.body-small.line-height | 16pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text size | md.comp.outlined-autocomplete.text-field.supporting-text.size | md.sys.typescale.body-small.size | 12pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text tracking | md.comp.outlined-autocomplete.text-field.supporting-text.tracking | md.sys.typescale.body-small.tracking | 0.4pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text type style | md.comp.outlined-autocomplete.text-field.supporting-text.type | md.sys.typescale.body-small.font | Roboto / 400 / 12pt / 0.4pt / 16pt |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field supporting text weight | md.comp.outlined-autocomplete.text-field.supporting-text.weight | md.sys.typescale.body-small.weight | 400 |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field trailing icon color | md.comp.outlined-autocomplete.text-field.trailing-icon.color | md.sys.color.on-surface-variant | #49454F |  |
| Text field - Autocomplete, outlined | Enabled | Outlined autocomplete text field trailing icon size | md.comp.outlined-autocomplete.text-field.trailing-icon.size |  | 24dp |  |
