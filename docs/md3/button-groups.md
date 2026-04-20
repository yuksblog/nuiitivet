<!-- markdownlint-disable MD060 -->

# Button Groups MD3 Specs

Source: <https://m3.material.io/components/button-groups/specs>
Collected: 2026-04-07

## Summary

- Tokens and specs provide 10 non-deprecated token sets: 5 `standard` sizes and 5 `connected` sizes.
- Standard sets define per-size container height, between-space, and pressed-width motion tokens.
- Connected sets define per-size container height, 2dp between-space, fully rounded container shape, and inner-corner tokens.
- Measurements specify standard inner padding by size and fixed connected padding of 2dp at all sizes.
- XS and S connected groups must keep a 48dp minimum width and 48x48dp target area.

## Tokens & Specs

### Token sets discovered

| Token set                              | Notes                                                 |
|----------------------------------------|-------------------------------------------------------|
| Button group standard - Size - Xsmall  | Non-deprecated token-set option under Tokens & specs. |
| Button group standard - Size - Small   | Non-deprecated token-set option under Tokens & specs. |
| Button group standard - Size - Medium  | Non-deprecated token-set option under Tokens & specs. |
| Button group standard - Size - Large   | Non-deprecated token-set option under Tokens & specs. |
| Button group standard - Size - Xlarge  | Non-deprecated token-set option under Tokens & specs. |
| Button group connected - Size - Xsmall | Non-deprecated token-set option under Tokens & specs. |
| Button group connected - Size - Small  | Non-deprecated token-set option under Tokens & specs. |
| Button group connected - Size - Medium | Non-deprecated token-set option under Tokens & specs. |
| Button group connected - Size - Large  | Non-deprecated token-set option under Tokens & specs. |
| Button group connected - Size - Xlarge | Non-deprecated token-set option under Tokens & specs. |

### Extracted tokens

| Token set                              | Group            | Label                                                    | Token                                                                           | Value         | Notes                    |
|----------------------------------------|------------------|----------------------------------------------------------|---------------------------------------------------------------------------------|---------------|--------------------------|
| Button group standard - Size - Xsmall  | Size             | Button group xsmall container height                     | md.comp.button-group.standard.xsmall.container.height                           | 32dp          |                          |
| Button group standard - Size - Xsmall  | Size             | Button group xsmall between space                        | md.comp.button-group.standard.xsmall.between-space                              | 18dp          |                          |
| Button group standard - Size - Xsmall  | Motion (pressed) | Button group xsmall pressed motion spring dampening      | md.comp.button-group.standard.xsmall.pressed.item.width.motion.spring.dampening | 0.9           |                          |
| Button group standard - Size - Xsmall  | Motion (pressed) | Button group xsmall pressed motion spring stiffness      | md.comp.button-group.standard.xsmall.pressed.item.width.motion.spring.stiffness | 1400          |                          |
| Button group standard - Size - Xsmall  | Size (pressed)   | Button group xsmall pressed width multiplier             | md.comp.button-group.standard.xsmall.pressed.item.width.multiplier              | 15%           |                          |
| Button group standard - Size - Small   | Size             | Button group small container height                      | md.comp.button-group.standard.small.container.height                            | 40dp          |                          |
| Button group standard - Size - Small   | Size             | Button group small between space                         | md.comp.button-group.standard.small.between-space                               | 12dp          |                          |
| Button group standard - Size - Small   | Motion (pressed) | Button group small pressed motion spring dampening       | md.comp.button-group.standard.small.pressed.item.width.motion.spring.dampening  | 0.9           |                          |
| Button group standard - Size - Small   | Motion (pressed) | Button group small pressed motion spring stiffness       | md.comp.button-group.standard.small.pressed.item.width.motion.spring.stiffness  | 1400          |                          |
| Button group standard - Size - Small   | Size (pressed)   | Button group small pressed width multiplier              | md.comp.button-group.standard.small.pressed.item.width.multiplier               | 15%           |                          |
| Button group standard - Size - Medium  | Size             | Button group medium container height                     | md.comp.button-group.standard.medium.container.height                           | 56dp          |                          |
| Button group standard - Size - Medium  | Size             | Button group medium between space                        | md.comp.button-group.standard.medium.between-space                              | 8dp           |                          |
| Button group standard - Size - Medium  | Motion (pressed) | Button group medium pressed motion spring dampening      | md.comp.button-group.standard.medium.pressed.item.width.motion.spring.dampening | 0.9           |                          |
| Button group standard - Size - Medium  | Motion (pressed) | Button group medium pressed motion spring stiffness      | md.comp.button-group.standard.medium.pressed.item.width.motion.spring.stiffness | 1400          |                          |
| Button group standard - Size - Medium  | Size (pressed)   | Button group medium pressed width multiplier             | md.comp.button-group.standard.medium.pressed.item.width.multiplier              | 15%           |                          |
| Button group standard - Size - Large   | Size             | Button group large container height                      | md.comp.button-group.standard.large.container.height                            | 96dp          |                          |
| Button group standard - Size - Large   | Size             | Button group large between space                         | md.comp.button-group.standard.large.between-space                               | 8dp           |                          |
| Button group standard - Size - Large   | Motion (pressed) | Button group large pressed motion spring dampening       | md.comp.button-group.standard.large.pressed.item.width.motion.spring.dampening  | 0.9           |                          |
| Button group standard - Size - Large   | Motion (pressed) | Button group large pressed motion spring stiffness       | md.comp.button-group.standard.large.pressed.item.width.motion.spring.stiffness  | 1400          |                          |
| Button group standard - Size - Large   | Size (pressed)   | Button group large pressed width multiplier              | md.comp.button-group.standard.large.pressed.item.width.multiplier               | 15%           |                          |
| Button group standard - Size - Xlarge  | Size             | Button group xlarge container height                     | md.comp.button-group.standard.xlarge.container.height                           | 136dp         |                          |
| Button group standard - Size - Xlarge  | Size             | Button group xlarge between space                        | md.comp.button-group.standard.xlarge.between-space                              | 8dp           |                          |
| Button group standard - Size - Xlarge  | Motion (pressed) | Button group xlarge pressed motion spring dampening      | md.comp.button-group.standard.xlarge.pressed.item.width.motion.spring.dampening | 0.9           |                          |
| Button group standard - Size - Xlarge  | Motion (pressed) | Button group xlarge pressed motion spring stiffness      | md.comp.button-group.standard.xlarge.pressed.item.width.motion.spring.stiffness | 1400          |                          |
| Button group standard - Size - Xlarge  | Size (pressed)   | Button group xlarge pressed width multiplier             | md.comp.button-group.standard.xlarge.pressed.item.width.multiplier              | 15%           |                          |
| Button group connected - Size - Xsmall | Size             | Button group connected xsmall container height           | md.comp.button-group.connected.xsmall.container.height                          | 32dp          |                          |
| Button group connected - Size - Xsmall | Size             | Button group connected xsmall space between buttons      | md.comp.button-group.connected.xsmall.between-space                             | 2dp           |                          |
| Button group connected - Size - Xsmall | Shape            | Button group connected xsmall container shape            | md.comp.button-group.connected.xsmall.container.shape                           | Fully rounded | Text shown in token row. |
| Button group connected - Size - Xsmall | Shape            | Button group connected xsmall inner corner size          | md.comp.button-group.connected.xsmall.inner-corner.corner-size                  | 8dp           |                          |
| Button group connected - Size - Xsmall | Shape (pressed)  | Button group connected xsmall pressed inner corner size  | md.comp.button-group.connected.xsmall.pressed.inner-corner.corner-size          | 4dp           |                          |
| Button group connected - Size - Xsmall | Shape (selected) | Button group connected xsmall selected inner corner size | md.comp.button-group.connected.xsmall.selected.inner-corner.corner-size         | 50%           |                          |
| Button group connected - Size - Small  | Size             | Button group connected small container height            | md.comp.button-group.connected.small.container.height                           | 40dp          |                          |
| Button group connected - Size - Small  | Size             | Button group connected small space between buttons       | md.comp.button-group.connected.small.between-space                              | 2dp           |                          |
| Button group connected - Size - Small  | Shape            | Button group connected small container shape             | md.comp.button-group.connected.small.container.shape                            | Fully rounded | Text shown in token row. |
| Button group connected - Size - Small  | Shape            | Button group connected small inner corner size           | md.comp.button-group.connected.small.inner-corner.corner-size                   | 8dp           |                          |
| Button group connected - Size - Small  | Shape (pressed)  | Button group connected small pressed inner corner size   | md.comp.button-group.connected.small.pressed.inner-corner.corner-size           | 4dp           |                          |
| Button group connected - Size - Small  | Shape (selected) | Button group connected small selected inner corner size  | md.comp.button-group.connected.small.selected.inner-corner.corner-size          | 50%           |                          |
| Button group connected - Size - Medium | Size             | Button group connected medium container height           | md.comp.button-group.connected.medium.container.height                          | 56dp          |                          |
| Button group connected - Size - Medium | Size             | Button group connected medium space between buttons      | md.comp.button-group.connected.medium.between-space                             | 2dp           |                          |
| Button group connected - Size - Medium | Shape            | Button group connected medium container shape            | md.comp.button-group.connected.medium.container.shape                           | Fully rounded | Text shown in token row. |
| Button group connected - Size - Medium | Shape            | Button group connected medium inner corner size          | md.comp.button-group.connected.medium.inner-corner.corner-size                  | 8dp           |                          |
| Button group connected - Size - Medium | Shape (pressed)  | Button group connected medium pressed inner corner size  | md.comp.button-group.connected.medium.pressed.inner-corner.corner-size          | 4dp           |                          |
| Button group connected - Size - Medium | Shape (selected) | Button group connected medium selected inner corner size | md.comp.button-group.connected.medium.selected.inner-corner.corner-size         | 50%           |                          |
| Button group connected - Size - Large  | Size             | Button group connected large container height            | md.comp.button-group.connected.large.container.height                           | 96dp          |                          |
| Button group connected - Size - Large  | Size             | Button group connected large space between buttons       | md.comp.button-group.connected.large.between-space                              | 2dp           |                          |
| Button group connected - Size - Large  | Shape            | Button group connected large container shape             | md.comp.button-group.connected.large.container.shape                            | Fully rounded | Text shown in token row. |
| Button group connected - Size - Large  | Shape            | Button group connected large inner corner size           | md.comp.button-group.connected.large.inner-corner.corner-size                   | 16dp          |                          |
| Button group connected - Size - Large  | Shape (pressed)  | Button group connected large pressed inner corner size   | md.comp.button-group.connected.large.pressed.inner-corner.corner-size           | 12dp          |                          |
| Button group connected - Size - Large  | Shape (selected) | Button group connected large selected inner corner size  | md.comp.button-group.connected.large.selected.inner-corner.corner-size          | 50%           |                          |
| Button group connected - Size - Xlarge | Size             | Button group connected xlarge container height           | md.comp.button-group.connected.xlarge.container.height                          | 136dp         |                          |
| Button group connected - Size - Xlarge | Size             | Button group connected xlarge space between buttons      | md.comp.button-group.connected.xlarge.between-space                             | 2dp           |                          |
| Button group connected - Size - Xlarge | Shape            | Button group connected xlarge container shape            | md.comp.button-group.connected.xlarge.container.shape                           | Fully rounded | Text shown in token row. |
| Button group connected - Size - Xlarge | Shape            | Button group connected xlarge inner corner size          | md.comp.button-group.connected.xlarge.inner-corner.corner-size                  | 20dp          |                          |
| Button group connected - Size - Xlarge | Shape (pressed)  | Button group connected xlarge pressed inner corner size  | md.comp.button-group.connected.xlarge.pressed.inner-corner.corner-size          | 16dp          |                          |
| Button group connected - Size - Xlarge | Shape (selected) | Button group connected xlarge selected inner corner size | md.comp.button-group.connected.xlarge.selected.inner-corner.corner-size         | 50%           |                          |

## Measurements

| Category                        | Item                           | Value                                           | Notes                                     |
|---------------------------------|--------------------------------|-------------------------------------------------|-------------------------------------------|
| Configurations                  | Sizes                          | XS, S, M, L, XL                                 | Listed in Configurations section.         |
| Configurations                  | Default shape                  | Round, square                                   | Listed in Configurations section.         |
| Configurations                  | Selection modes                | Single-select, multi-select, selection-required | Listed in Configurations section.         |
| Standard button group           | Inner padding XS               | 18dp                                            | Figure callout under Measurements.        |
| Standard button group           | Inner padding S                | 12dp                                            | Figure callout under Measurements.        |
| Standard button group           | Inner padding M                | 8dp                                             | Figure callout under Measurements.        |
| Standard button group           | Inner padding L                | 8dp                                             | Figure callout under Measurements.        |
| Standard button group           | Inner padding XL               | 8dp                                             | Figure callout under Measurements.        |
| Standard button group           | Minimum accessible target size | 48dp                                            | Explicit statement in prose.              |
| Connected button group          | Inner padding (all sizes)      | 2dp                                             | Explicit statement in prose.              |
| Connected button group (round)  | Inner corner XS                | 4dp                                             | Figure callout under Measurements.        |
| Connected button group (round)  | Inner corner S                 | 8dp                                             | Figure callout under Measurements.        |
| Connected button group (round)  | Inner corner M                 | 8dp                                             | Figure callout under Measurements.        |
| Connected button group (round)  | Inner corner L                 | 16dp                                            | Figure callout under Measurements.        |
| Connected button group (round)  | Inner corner XL                | 20dp                                            | Figure callout under Measurements.        |
| Connected button group (square) | Outer corner XS                | 4dp                                             | Figure callout under Measurements.        |
| Connected button group (square) | Outer corner S                 | 8dp                                             | Figure callout under Measurements.        |
| Connected button group (square) | Outer corner M                 | 8dp                                             | Figure callout under Measurements.        |
| Connected button group (square) | Outer corner L                 | 16dp                                            | Figure callout under Measurements.        |
| Connected button group (square) | Outer corner XL                | 20dp                                            | Figure callout under Measurements.        |
| Minimum widths                  | Connected XS minimum width     | 48dp                                            | Explicit statement in prose.              |
| Minimum widths                  | Connected S minimum width      | 48dp                                            | Explicit statement in prose.              |
| Minimum widths                  | Connected XS/S target area     | 48x48dp                                         | Figure + prose in Minimum widths section. |

## Implementation Notes

- Use separate token models for `standard` and `connected` variants; they do not share spacing or corner behavior.
- For standard groups, apply size-specific `between-space` (18/12/8/8/8dp) plus pressed-width animation tokens (`dampening`, `stiffness`, `width.multiplier`).
- For connected groups, enforce 2dp between-space at all sizes, fully rounded outer container shape, and size-driven inner-corner values.
- Preserve selected inner corner value at `50%` across all connected sizes.
- Enforce 48dp minimum width and target area rules for connected XS/S variants.
