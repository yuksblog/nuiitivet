<!-- markdownlint-disable MD060 -->

# Divider MD3 Specs

Source: <https://m3.material.io/components/divider/specs>
Collected: 2026-05-25

## Summary

- Divider exposes one active token set in the live viewer: `Divider` with `Default, Light` context chips.
- The component token surface is intentionally small: a 1dp thickness token and a single color token resolved from `md.sys.color.outline-variant`.
- The measurements spec distinguishes full-width, inset, and middle-inset placements rather than variant-specific token sets.
- Insets are 16dp from the left edge for both inset styles; middle-inset additionally applies a 16dp right inset.
- Supporting-text dividers use a 4dp gap above the text and 8dp right and bottom margins in the illustrated layout.

## Tokens & Specs

### Token sets discovered

| Token set | Status | Notes                                                                                                                                              |
|-----------|--------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Divider   | Active | Viewer context chips show `Default, Light`. The expanded live viewer exposes a single `Enabled / Container` group with thickness and color tokens. |

### Divider

| Token set | Group               | Label             | Token                       | Source token                   | Value   | Notes                                                                                                    |
|-----------|---------------------|-------------------|-----------------------------|--------------------------------|---------|----------------------------------------------------------------------------------------------------------|
| Divider   | Enabled / Container | Divider thickness | `md.comp.divider.thickness` |                                | 1dp     | Expanded live viewer row.                                                                                |
| Divider   | Enabled / Container | Divider color     | `md.comp.divider.color`     | `md.sys.color.outline-variant` | #CAC4D0 | Live viewer default light context. The color section also calls out Outline Variant as the divider role. |

## Measurements

| Category | Item                                      | Value | Notes                                                                            |
|----------|-------------------------------------------|-------|----------------------------------------------------------------------------------|
| Layout   | Divider full-width                        | 100%  | Full-width divider spans the available container width.                          |
| Layout   | Divider inset left margin                 | 16dp  | Standard inset divider starts 16dp from the left edge.                           |
| Layout   | Divider inset right margin                | 0dp   | Standard inset divider runs to the trailing edge.                                |
| Layout   | Divider middle-inset left margin          | 16dp  | Middle-inset divider keeps the same leading inset as the standard inset divider. |
| Layout   | Divider middle-inset right margin         | 16dp  | Middle-inset divider applies symmetrical 16dp side insets.                       |
| Spacing  | Space between divider and supporting text | 4dp   | Applies to the supporting-text layout shown in the measurements diagram.         |
| Spacing  | Divider right margin                      | 8dp   | Measurement table lists this with the supporting-text layout.                    |
| Spacing  | Divider bottom margin                     | 8dp   | Measurement table lists this with the supporting-text layout.                    |

## Implementation Notes

- Model divider rendering as a 1dp rule whose default enabled color comes from `md.sys.color.outline-variant`.
- Keep layout variants separate from token resolution: full-width, inset, and middle-inset are spacing patterns, not distinct token sets.
- Use 16dp leading inset for list-style dividers and add a matching 16dp trailing inset only for middle-inset placements.
- When pairing a divider with supporting text, preserve the 4dp gap above the text and the 8dp right and bottom margins from the measurement spec.
