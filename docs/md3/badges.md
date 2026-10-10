<!-- markdownlint-disable MD060 -->

# Badges MD3 Specs

Source: <https://m3.material.io/components/badges/specs>
Collected: 2026-05-25

## Summary

- The live badge token viewer exposes a single `Badges` token set with one enabled container group and one enabled label-text group.
- Resolved values below use the viewer's Default / Light context; the selector also exposes Dark plus Default, Medium contrast, and High contrast variants.
- Small badges use the error role on a 6dp full-shape dot; large badges use the same error container color with on-error label text on a 16dp full-shape pill.
- Large badge typography resolves to `md.sys.typescale.label-small`: Google Sans Text, 500 weight, 11pt size, 16pt line height, and 0.1pt tracking.
- Measurement diagrams place the small badge 6x6dp from the top trailing icon corner and the large badge 14x12dp from that corner, with 4dp padding around large badge text.

## Tokens & Specs

### Token sets discovered

| Token set | Status | Notes                                                                                                                                                                             |
|-----------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Badges    | Active | Context shown in the viewer: Default, Light. Enabled subgroups: Container and Label text. Context selector chips expose Light, Dark, Default, Medium contrast, and High contrast. |

### Badges

| Token set | Group                | Label                              | Token                                      | Source token                             | Value                                                 | Notes                                                                                                |
|-----------|----------------------|------------------------------------|--------------------------------------------|------------------------------------------|-------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| Badges    | Enabled / Container  | Badge color                        | md.comp.badge.color                        | md.sys.color.error                       | #B3261E                                               |                                                                                                      |
| Badges    | Enabled / Container  | Badge shape                        | md.comp.badge.shape                        | md.sys.shape.corner.full                 | full                                                  | Full shape on the 6dp badge yields a 3dp corner radius in the measurements table.                    |
| Badges    | Enabled / Container  | Badge size                         | md.comp.badge.size                         |                                          | 6dp                                                   |                                                                                                      |
| Badges    | Enabled / Container  | Badge large color                  | md.comp.badge.large.color                  | md.sys.color.error                       | #B3261E                                               |                                                                                                      |
| Badges    | Enabled / Container  | Badge large shape                  | md.comp.badge.large.shape                  | md.sys.shape.corner.full                 | full                                                  | Full shape on the 16dp large badge yields an 8dp corner radius in the measurements table.            |
| Badges    | Enabled / Container  | Badge large size                   | md.comp.badge.large.size                   |                                          | 16dp                                                  |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text color       | md.comp.badge.large.label-text.color       | md.sys.color.on-error                    | #FFFFFF                                               |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text font        | md.comp.badge.large.label-text.font        | md.sys.typescale.label-small.font        | Google Sans Text                                      |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text line height | md.comp.badge.large.label-text.line-height | md.sys.typescale.label-small.line-height | 16pt                                                  |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text size        | md.comp.badge.large.label-text.size        | md.sys.typescale.label-small.size        | 11pt                                                  |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text tracking    | md.comp.badge.large.label-text.tracking    | md.sys.typescale.label-small.tracking    | 0.1pt                                                 |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text weight      | md.comp.badge.large.label-text.weight      | md.sys.typescale.label-small.weight      | 500                                                   |                                                                                                      |
| Badges    | Enabled / Label text | Badge large label text type        | md.comp.badge.large.label-text.type        | md.sys.typescale.label-small             | Google Sans Text / 500 / 11pt / 16pt / tracking 0.1pt | Composite shorthand built from the label-small font, weight, size, line-height, and tracking tokens. |

## Measurements

| Category  | Item                                                 | Value             | Notes                                                                          |
|-----------|------------------------------------------------------|-------------------|--------------------------------------------------------------------------------|
| Container | Small badge shape                                    | 3dp corner radius | Matches the 6dp full-shape small badge token.                                  |
| Container | Small badge size (H x W)                             | 6dp               | The small badge is a circular dot.                                             |
| Container | Large badge shape                                    | 8dp corner radius | Matches the 16dp full-shape large badge token.                                 |
| Container | Large badge one digit size (H x W)                   | 16dp              | Single-digit large badge container.                                            |
| Container | Large badge max character count size (H x W)         | 16x34dp           | Max-count badge width for capped count labels.                                 |
| Placement | Small badge corner offset (H x W)                    | 6x6dp             | Distance from the top trailing icon corner to the bottom leading badge corner. |
| Placement | Large badge corner offset (H x W)                    | 14x12dp           | Distance from the top trailing icon corner to the bottom leading badge corner. |
| Spacing   | Large badge padding between badge and text container | 4dp               | Horizontal padding around the large badge label.                               |

## Implementation Notes

- Resolve badge colors from the error / on-error roles rather than primary-toned roles; the spec uses badges as alert-count surfaces.
- Large badge text can reuse the repository's `label-small` typography treatment directly.
- Both small and large badges use full shape. The effective radius comes from the component height: 3dp on the 6dp small badge and 8dp on the 16dp large badge.
- The configuration diagrams show the three implementation-relevant badge variants: small dot, large numeric badge, and large max-character-count badge, applied to both navigation bars and navigation rails.
- The current token viewer exposes only enabled badge rows; no hover, focus, pressed, or disabled badge token groups are documented on this spec page.
