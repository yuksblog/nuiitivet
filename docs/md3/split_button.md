<!-- markdownlint-disable MD060 -->

# Split Button MD3 Specs

Source: <https://m3.material.io/components/split-button/specs>
Collected: 2026-04-07

## Summary

- Tokens and specs expose five non-deprecated size token sets in order: Xsmall, Small, Medium, Large, Xlarge.
- Each size set keeps `between-space` at 2dp and uses a fully rounded outer shape with size-specific inner corner behavior.
- Inner corner sizes scale by size and increase for hovered/pressed states; selected trailing-button inner corner stays 50% across all sizes.
- Measurements explicitly define unselected menu icon offset by size (XS/S -1dp, M -2dp, L -3dp, XL -6dp).
- Measurements also state that split-button inner spacing should always be 2dp and that inner corner sizing varies by button size.

## Tokens & Specs

### Token sets discovered

| Token set                    | Notes                                                    |
|------------------------------|----------------------------------------------------------|
| Split button - Size - Xsmall | Non-deprecated size token set under Tokens & specs menu. |
| Split button - Size - Small  | Non-deprecated size token set under Tokens & specs menu. |
| Split button - Size - Medium | Non-deprecated size token set under Tokens & specs menu. |
| Split button - Size - Large  | Non-deprecated size token set under Tokens & specs menu. |
| Split button - Size - Xlarge | Non-deprecated size token set under Tokens & specs menu. |

### Extracted tokens

| Token set                    | Group       | Label                                                          | Token                                                                         | Value                       | Notes                                                   |
|------------------------------|-------------|----------------------------------------------------------------|-------------------------------------------------------------------------------|-----------------------------|---------------------------------------------------------|
| Split button - Size - Xsmall | Size        | Split button xsmall container height                           | md.comp.split-button.xsmall.container.height                                  | 32dp                        |                                                         |
| Split button - Size - Xsmall | Size        | Split button xsmall between space                              | md.comp.split-button.xsmall.between-space                                     | 2dp                         |                                                         |
| Split button - Size - Xsmall | Shape       | Split button xsmall container shape                            | md.comp.split-button.xsmall.container.shape                                   | visual-only (shape preview) | No textual value exposed inline or via row interaction. |
| Split button - Size - Xsmall | Shape       | Split button xsmall inner corner size                          | md.comp.split-button.xsmall.inner-corner.corner-size                          | 4dp                         |                                                         |
| Split button - Size - Xsmall | Shape       | Split button xsmall outer corner size                          | md.comp.split-button.xsmall.outer-corner.corner-size                          | 50%                         | Present only in Xsmall token set on this page.          |
| Split button - Size - Xsmall | Spacing     | Split button xsmall leading button leading space               | md.comp.split-button.xsmall.leading-button.leading-space                      | 12dp                        |                                                         |
| Split button - Size - Xsmall | Spacing     | Split button xsmall leading button trailing space              | md.comp.split-button.xsmall.leading-button.trailing-space                     | 10dp                        |                                                         |
| Split button - Size - Xsmall | Icon        | Split button xsmall trailing button icon size                  | md.comp.split-button.xsmall.trailing-button.icon.size                         | 22dp                        |                                                         |
| Split button - Size - Xsmall | Spacing     | Split button xsmall trailing button leading space              | md.comp.split-button.xsmall.trailing-button.leading-space                     | 13dp                        |                                                         |
| Split button - Size - Xsmall | Spacing     | Split button xsmall trailing button trailing space             | md.comp.split-button.xsmall.trailing-button.trailing-space                    | 13dp                        |                                                         |
| Split button - Size - Xsmall | State shape | Split button xsmall inner corner hovered size                  | md.comp.split-button.xsmall.inner-corner.hovered.corner-size                  | 8dp                         |                                                         |
| Split button - Size - Xsmall | State shape | Split button xsmall inner corner pressed size                  | md.comp.split-button.xsmall.inner-corner.pressed.corner-size                  | 8dp                         |                                                         |
| Split button - Size - Xsmall | State shape | Split button xsmall trailing button inner corner selected size | md.comp.split-button.xsmall.trailing-button.inner-corner.selected.corner-size | 50%                         |                                                         |
| Split button - Size - Small  | Size        | Split button small container height                            | md.comp.split-button.small.container.height                                   | 40dp                        |                                                         |
| Split button - Size - Small  | Size        | Split button small between space                               | md.comp.split-button.small.between-space                                      | 2dp                         |                                                         |
| Split button - Size - Small  | Shape       | Split button small container shape                             | md.comp.split-button.small.container.shape                                    | visual-only (shape preview) | No textual value exposed inline or via row interaction. |
| Split button - Size - Small  | Shape       | Split button small inner corner size                           | md.comp.split-button.small.inner-corner.corner-size                           | 4dp                         |                                                         |
| Split button - Size - Small  | Spacing     | Split button small leading button leading space                | md.comp.split-button.small.leading-button.leading-space                       | 16dp                        |                                                         |
| Split button - Size - Small  | Spacing     | Split button small leading button trailing space               | md.comp.split-button.small.leading-button.trailing-space                      | 12dp                        |                                                         |
| Split button - Size - Small  | Icon        | Split button small trailing button icon size                   | md.comp.split-button.small.trailing-button.icon.size                          | 22dp                        |                                                         |
| Split button - Size - Small  | Spacing     | Split button small trailing button leading space               | md.comp.split-button.small.trailing-button.leading-space                      | 13dp                        |                                                         |
| Split button - Size - Small  | Spacing     | Split button small trailing button trailing space              | md.comp.split-button.small.trailing-button.trailing-space                     | 13dp                        |                                                         |
| Split button - Size - Small  | State shape | Split button small inner corner hovered size                   | md.comp.split-button.small.inner-corner.hovered.corner-size                   | 12dp                        |                                                         |
| Split button - Size - Small  | State shape | Split button small inner corner pressed size                   | md.comp.split-button.small.inner-corner.pressed.corner-size                   | 12dp                        |                                                         |
| Split button - Size - Small  | State shape | Split button small trailing button inner corner selected size  | md.comp.split-button.small.trailing-button.inner-corner.selected.corner-size  | 50%                         |                                                         |
| Split button - Size - Medium | Size        | Split button medium container height                           | md.comp.split-button.medium.container.height                                  | 56dp                        |                                                         |
| Split button - Size - Medium | Size        | Split button medium between space                              | md.comp.split-button.medium.between-space                                     | 2dp                         |                                                         |
| Split button - Size - Medium | Shape       | Split button medium container shape                            | md.comp.split-button.medium.container.shape                                   | visual-only (shape preview) | No textual value exposed inline or via row interaction. |
| Split button - Size - Medium | Shape       | Split button medium inner corner size                          | md.comp.split-button.medium.inner-corner.corner-size                          | 4dp                         |                                                         |
| Split button - Size - Medium | Spacing     | Split button medium leading button leading space               | md.comp.split-button.medium.leading-button.leading-space                      | 24dp                        |                                                         |
| Split button - Size - Medium | Spacing     | Split button medium leading button trailing space              | md.comp.split-button.medium.leading-button.trailing-space                     | 24dp                        |                                                         |
| Split button - Size - Medium | Icon        | Split button medium trailing button icon size                  | md.comp.split-button.medium.trailing-button.icon.size                         | 26dp                        |                                                         |
| Split button - Size - Medium | Spacing     | Split button medium trailing button leading space              | md.comp.split-button.medium.trailing-button.leading-space                     | 15dp                        |                                                         |
| Split button - Size - Medium | Spacing     | Split button medium trailing button trailing space             | md.comp.split-button.medium.trailing-button.trailing-space                    | 15dp                        |                                                         |
| Split button - Size - Medium | State shape | Split button medium inner corner hovered size                  | md.comp.split-button.medium.inner-corner.hovered.corner-size                  | 12dp                        |                                                         |
| Split button - Size - Medium | State shape | Split button medium inner corner pressed size                  | md.comp.split-button.medium.inner-corner.pressed.corner-size                  | 12dp                        |                                                         |
| Split button - Size - Medium | State shape | Split button medium trailing button inner corner selected size | md.comp.split-button.medium.trailing-button.inner-corner.selected.corner-size | 50%                         |                                                         |
| Split button - Size - Large  | Size        | Split button large container height                            | md.comp.split-button.large.container.height                                   | 96dp                        |                                                         |
| Split button - Size - Large  | Size        | Split button large between space                               | md.comp.split-button.large.between-space                                      | 2dp                         |                                                         |
| Split button - Size - Large  | Shape       | Split button large container shape                             | md.comp.split-button.large.container.shape                                    | visual-only (shape preview) | No textual value exposed inline or via row interaction. |
| Split button - Size - Large  | Shape       | Split button large inner corner size                           | md.comp.split-button.large.inner-corner.corner-size                           | 8dp                         |                                                         |
| Split button - Size - Large  | Spacing     | Split button large leading button leading space                | md.comp.split-button.large.leading-button.leading-space                       | 48dp                        |                                                         |
| Split button - Size - Large  | Spacing     | Split button large leading button trailing space               | md.comp.split-button.large.leading-button.trailing-space                      | 48dp                        |                                                         |
| Split button - Size - Large  | Icon        | Split button large trailing button icon size                   | md.comp.split-button.large.trailing-button.icon.size                          | 38dp                        |                                                         |
| Split button - Size - Large  | Spacing     | Split button large trailing button leading space               | md.comp.split-button.large.trailing-button.leading-space                      | 29dp                        |                                                         |
| Split button - Size - Large  | Spacing     | Split button large trailing button trailing space              | md.comp.split-button.large.trailing-button.trailing-space                     | 29dp                        |                                                         |
| Split button - Size - Large  | State shape | Split button large inner corner hovered size                   | md.comp.split-button.large.inner-corner.hovered.corner-size                   | 20dp                        |                                                         |
| Split button - Size - Large  | State shape | Split button large inner corner pressed size                   | md.comp.split-button.large.inner-corner.pressed.corner-size                   | 20dp                        |                                                         |
| Split button - Size - Large  | State shape | Split button large trailing button inner corner selected size  | md.comp.split-button.large.trailing-button.inner-corner.selected.corner-size  | 50%                         |                                                         |
| Split button - Size - Xlarge | Size        | Split button xlarge container height                           | md.comp.split-button.xlarge.container.height                                  | 136dp                       |                                                         |
| Split button - Size - Xlarge | Size        | Split button xlarge between space                              | md.comp.split-button.xlarge.between-space                                     | 2dp                         |                                                         |
| Split button - Size - Xlarge | Shape       | Split button xlarge container shape                            | md.comp.split-button.xlarge.container.shape                                   | visual-only (shape preview) | No textual value exposed inline or via row interaction. |
| Split button - Size - Xlarge | Shape       | Split button xlarge inner corner size                          | md.comp.split-button.xlarge.inner-corner.corner-size                          | 12dp                        |                                                         |
| Split button - Size - Xlarge | Spacing     | Split button xlarge leading button leading space               | md.comp.split-button.xlarge.leading-button.leading-space                      | 64dp                        |                                                         |
| Split button - Size - Xlarge | Spacing     | Split button xlarge leading button trailing space              | md.comp.split-button.xlarge.leading-button.trailing-space                     | 64dp                        |                                                         |
| Split button - Size - Xlarge | Icon        | Split button xlarge trailing button icon size                  | md.comp.split-button.xlarge.trailing-button.icon.size                         | 50dp                        |                                                         |
| Split button - Size - Xlarge | Spacing     | Split button xlarge trailing button leading space              | md.comp.split-button.xlarge.trailing-button.leading-space                     | 43dp                        |                                                         |
| Split button - Size - Xlarge | Spacing     | Split button xlarge trailing button trailing space             | md.comp.split-button.xlarge.trailing-button.trailing-space                    | 43dp                        |                                                         |
| Split button - Size - Xlarge | State shape | Split button xlarge inner corner hovered size                  | md.comp.split-button.xlarge.inner-corner.hovered.corner-size                  | 20dp                        |                                                         |
| Split button - Size - Xlarge | State shape | Split button xlarge inner corner pressed size                  | md.comp.split-button.xlarge.inner-corner.pressed.corner-size                  | 20dp                        |                                                         |
| Split button - Size - Xlarge | State shape | Split button xlarge trailing button inner corner selected size | md.comp.split-button.xlarge.trailing-button.inner-corner.selected.corner-size | 50%                         |                                                         |

## Measurements

| Category       | Item                              | Value                             | Notes                                       |
|----------------|-----------------------------------|-----------------------------------|---------------------------------------------|
| Configurations | Size configurations               | XS, S, M, L, XL                   | Listed in Configurations section.           |
| Configurations | Color configurations              | Elevated, filled, tonal, outlined | Listed in Configurations section.           |
| Measurements   | Menu icon offset (unselected, XS) | -1dp from center                  | Figure callout text.                        |
| Measurements   | Menu icon offset (unselected, S)  | -1dp from center                  | Figure callout text.                        |
| Measurements   | Menu icon offset (unselected, M)  | -2dp from center                  | Figure callout text.                        |
| Measurements   | Menu icon offset (unselected, L)  | -3dp from center                  | Figure callout text.                        |
| Measurements   | Menu icon offset (unselected, XL) | -6dp from center                  | Figure callout text.                        |
| Measurements   | Inner spacing                     | 2dp                               | Explicit prose: space should always be 2dp. |
| Measurements   | Inner corner size (extra small)   | 4dp                               | Figure callout text.                        |
| Measurements   | Inner corner size (small)         | 4dp                               | Figure callout text.                        |
| Measurements   | Inner corner size (medium)        | 4dp                               | Figure callout text.                        |
| Measurements   | Inner corner size (large)         | 8dp                               | Figure callout text.                        |
| Measurements   | Inner corner size (extra large)   | 12dp                              | Figure callout text.                        |

## Implementation Notes

- Drive split-button geometry from the size token set first (`xsmall` through `xlarge`), with a constant `between-space` of 2dp.
- Keep leading/trailing horizontal spacing size-specific; those values increase significantly at Large and Xlarge and should not be derived from a simple linear scale.
- Preserve state-specific inner corner transitions (`hovered` and `pressed`) and trailing-button selected inner corner (50%) for correct split-joint appearance.
- Treat `container.shape` as preview-driven in this source; use concrete corner-size tokens where provided (`inner-corner` and Xsmall `outer-corner`) for implementation math.
- Keep split-button color behavior aligned with standard button specs; selected state applies a state layer without changing the base color role.
