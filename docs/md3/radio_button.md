<!-- markdownlint-disable MD060 -->

# Radio button MD3 Specs

Source: <https://m3.material.io/components/radio-button/specs>
Collected: 2026-05-26

## Summary

- Radio button exposes one active token set in the live viewer: `Radio Button` with `Default, Light` context chips.
- The control uses a 20dp icon inside a 40dp state layer and a 48dp target size.
- Selected icon and selected hover or focus state-layer treatments use `md.sys.color.primary`, while the enabled unselected icon stays on `md.sys.color.on-surface-variant`.
- Hover, focus, and pressed state layers reuse the shared MD3 state-opacity ladder of 0.08 for hover and 0.1 for focus and pressed.
- Disabled selected and unselected icons both use `md.sys.color.on-surface` at 0.38 opacity.
- Adjacent text labels stay on the `on surface` color role regardless of whether the radio button is selected or being interacted with.

## Tokens & Specs

### Token sets discovered

| Token set    | Status | Notes                                                                                                                      |
|--------------|--------|----------------------------------------------------------------------------------------------------------------------------|
| Radio Button | Active | Viewer context chips show `Default, Light`. Includes enabled, disabled, hovered, focused, and pressed radio-button states. |

### Radio Button

| Token set    | Group                          | Label                                               | Token                                                         | Source token                               | Value   | Notes                                                                         |
|--------------|--------------------------------|-----------------------------------------------------|---------------------------------------------------------------|--------------------------------------------|---------|-------------------------------------------------------------------------------|
| Radio Button | Enabled / Icon                 | Radio button icon selected color                    | `md.comp.radio-button.selected.icon.color`                    | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Enabled / Icon                 | Radio button icon unselected color                  | `md.comp.radio-button.unselected.icon.color`                  | `md.sys.color.on-surface-variant`          | #49454F |                                                                               |
| Radio Button | Enabled / Icon                 | Radio button icon size                              | `md.comp.radio-button.icon.size`                              |                                            | 20dp    |                                                                               |
| Radio Button | Enabled / State layer          | Radio button state layer size                       | `md.comp.radio-button.state-layer.size`                       |                                            | 40dp    |                                                                               |
| Radio Button | Disabled / Icon                | Radio button disabled selected icon color           | `md.comp.radio-button.disabled.selected.icon.color`           | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Disabled / Icon                | Radio button disabled selected icon opacity         | `md.comp.radio-button.disabled.selected.icon.opacity`         |                                            | 0.38    | Viewer resolves this directly rather than exposing a semantic upstream token. |
| Radio Button | Disabled / Icon                | Radio button disabled unselected icon color         | `md.comp.radio-button.disabled.unselected.icon.color`         | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Disabled / Icon                | Radio button disabled unselected icon opacity       | `md.comp.radio-button.disabled.unselected.icon.opacity`       |                                            | 0.38    | Viewer resolves this directly rather than exposing a semantic upstream token. |
| Radio Button | Hovered / State layer          | Radio button selected hover state layer color       | `md.comp.radio-button.selected.hover.state-layer.color`       | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Hovered / State layer          | Radio button selected hover state layer opacity     | `md.comp.radio-button.selected.hover.state-layer.opacity`     | `md.sys.state.hover.state-layer-opacity`   | 0.08    |                                                                               |
| Radio Button | Hovered / State layer          | Radio button unselected hover state layer color     | `md.comp.radio-button.unselected.hover.state-layer.color`     | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Hovered / State layer          | Radio button unselected hover state layer opacity   | `md.comp.radio-button.unselected.hover.state-layer.opacity`   | `md.sys.state.hover.state-layer-opacity`   | 0.08    |                                                                               |
| Radio Button | Hovered / Icon                 | Radio button selected hover icon color              | `md.comp.radio-button.selected.hover.icon.color`              | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Hovered / Icon                 | Radio button unselected hover icon color            | `md.comp.radio-button.unselected.hover.icon.color`            | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Focused / State layer          | Radio button selected focus state layer color       | `md.comp.radio-button.selected.focus.state-layer.color`       | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Focused / State layer          | Radio button selected focus state layer opacity     | `md.comp.radio-button.selected.focus.state-layer.opacity`     | `md.sys.state.focus.state-layer-opacity`   | 0.1     |                                                                               |
| Radio Button | Focused / State layer          | Radio button unselected focus state layer color     | `md.comp.radio-button.unselected.focus.state-layer.color`     | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Focused / State layer          | Radio button unselected focus state layer opacity   | `md.comp.radio-button.unselected.focus.state-layer.opacity`   | `md.sys.state.focus.state-layer-opacity`   | 0.1     |                                                                               |
| Radio Button | Focused / Icon                 | Radio button selected focus icon color              | `md.comp.radio-button.selected.focus.icon.color`              | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Focused / Icon                 | Radio button unselected focus icon color            | `md.comp.radio-button.unselected.focus.icon.color`            | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Pressed (ripple) / State layer | Radio button selected pressed state layer color     | `md.comp.radio-button.selected.pressed.state-layer.color`     | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |
| Radio Button | Pressed (ripple) / State layer | Radio button selected pressed state layer opacity   | `md.comp.radio-button.selected.pressed.state-layer.opacity`   | `md.sys.state.pressed.state-layer-opacity` | 0.1     |                                                                               |
| Radio Button | Pressed (ripple) / State layer | Radio button unselected pressed state layer color   | `md.comp.radio-button.unselected.pressed.state-layer.color`   | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Pressed (ripple) / State layer | Radio button unselected pressed state layer opacity | `md.comp.radio-button.unselected.pressed.state-layer.opacity` | `md.sys.state.pressed.state-layer-opacity` | 0.1     |                                                                               |
| Radio Button | Pressed (ripple) / Icon        | Radio button selected pressed icon color            | `md.comp.radio-button.selected.pressed.icon.color`            | `md.sys.color.primary`                     | #6750A4 |                                                                               |
| Radio Button | Pressed (ripple) / Icon        | Radio button unselected pressed icon color          | `md.comp.radio-button.unselected.pressed.icon.color`          | `md.sys.color.on-surface`                  | #1D1B20 |                                                                               |

## Measurements

| Category    | Item                      | Value      | Notes                                                                                                       |
|-------------|---------------------------|------------|-------------------------------------------------------------------------------------------------------------|
| Icon        | Size                      | 20dp       | Measurements table on the spec page.                                                                        |
| Interaction | State-layer size          | 40dp       | Measurements table on the spec page.                                                                        |
| Interaction | Target size               | 48dp       | Minimum touch target from the measurements table.                                                           |
| Typography  | Adjacent text label color | On surface | The prose color guidance says the label color remains the same whether the radio button is selected or not. |

## Implementation Notes

- Model the radio button as a 20dp visual icon inside a larger 48dp hit target, with a 40dp state layer centered on the control.
- Preserve the enabled unselected icon on `md.sys.color.on-surface-variant`; interaction states promote the unselected hover, focus, and pressed treatments to `md.sys.color.on-surface`.
- Selected icon color stays on `md.sys.color.primary` across enabled, hover, focus, and pressed states; the pressed selected state layer is the only selected interaction state that switches to `md.sys.color.on-surface`.
- The live viewer exposes no separate focus-indicator token family for radio button, so current MD3 spec coverage is limited to icon and state-layer treatments for focus.
- The measurements figure did not expose additional reliably legible numeric values beyond the table entries above.
