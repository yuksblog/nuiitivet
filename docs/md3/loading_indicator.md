<!-- markdownlint-disable MD060 -->

# Loading Indicator MD3 Specs

**Source:** <https://m3.material.io/components/loading-indicator/specs>  
**Collected:** 2026-04-30

## Summary

- The live MD3 token viewer exposes a single active token set, `Loading indicator`, with one shape row, three size rows, and four color rows.
- The token viewer's context selector offers Theme values `Light` and `Dark` plus Contrast values `Default`, `Medium contrast`, and `High contrast`; the resolved values below were collected from the default light context.
- Default loading-indicator colors map the active indicator to `md.sys.color.primary` and the container to `md.sys.color.secondary-container`; contained colors map to `md.sys.color.on-primary-container` and `md.sys.color.primary-container`.
- The Measurements section and token viewer agree on a 48dp overall size and a 38dp shape container width, with the shape rendered as fully rounded.

## Tokens & Specs

### Token sets discovered

| Token Set         | Count | Type  | Status |
|-------------------|-------|-------|--------|
| Loading indicator | 8     | Mixed | Active |

### Extracted tokens

| Token Set         | Group | Label                                              | Token                                                      | Source token                      | Value         | Notes                                                                                         |
|-------------------|-------|----------------------------------------------------|------------------------------------------------------------|-----------------------------------|---------------|-----------------------------------------------------------------------------------------------|
| Loading indicator | Color | Loading indicator active indicator color           | md.comp.loading-indicator.active-indicator.color           | md.sys.color.primary              | #6750A4       | Resolved in the default light context.                                                        |
| Loading indicator | Color | Loading indicator container color                  | md.comp.loading-indicator.container.color                  | md.sys.color.secondary-container  | #E8DEF8       | Color section maps the default container role to Secondary container.                         |
| Loading indicator | Color | Loading indicator contained container color        | md.comp.loading-indicator.contained.container.color        | md.sys.color.primary-container    | #EADDFF       | Color section maps the contained container role to Primary container.                         |
| Loading indicator | Color | Loading indicator contained active indicator color | md.comp.loading-indicator.contained.active-indicator.color | md.sys.color.on-primary-container | #4F378B       | Color section maps the contained active indicator role to On primary container.               |
| Loading indicator | Size  | Loading indicator container width                  | md.comp.loading-indicator.container.width                  |                                   | 38dp          | Matches the Measurements prose for the shape container.                                       |
| Loading indicator | Size  | Loading indicator container height                 | md.comp.loading-indicator.container.height                 |                                   | 48dp          | Matches the Measurements prose for the overall size.                                          |
| Loading indicator | Size  | Loading indicator active indicator size            | md.comp.loading-indicator.active-indicator.size            |                                   | 48dp          | Same resolved size as the outer container height in the default light context.                |
| Loading indicator | Shape | Loading indicator container shape                  | md.comp.loading-indicator.container.shape                  |                                   | Fully rounded | The live viewer exposes a textual shape value, but no numeric radius or upstream shape token. |

## Measurements

| Category | Item                  | Value         | Notes                                                                                                                                               |
|----------|-----------------------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Overall  | Outer size            | 48dp          | Explicit prose: "the size is 48dp"; aligns with `md.comp.loading-indicator.container.height` and `md.comp.loading-indicator.active-indicator.size`. |
| Overall  | Shape container width | 38dp          | Explicit prose: "the shape container is 38dp"; aligns with `md.comp.loading-indicator.container.width`.                                             |
| Shape    | Container shape       | Fully rounded | The token viewer exposes this as a textual shape value rather than a numeric corner size.                                                           |

## Implementation Notes

- Treat default and contained color roles as separate tokens rather than deriving the contained colors from the default pair.
- Use 48dp as the outer loading-indicator footprint and 38dp as the inner shape-container width when reproducing the spec geometry.
- Preserve the fully rounded container shape semantically; the live viewer does not expose a numeric radius to substitute for it.
