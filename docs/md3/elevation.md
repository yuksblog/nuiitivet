<!-- markdownlint-disable MD060 -->

# Elevation MD3 Specs

Source: <https://github.com/material-components/material-web/blob/main/elevation/internal/_elevation.scss>
Collected: 2026-09-03

## Summary

- MD3 renders elevation as **two** stacked box-shadow layers per level: a tight, darker
  *key* shadow and a wide, softer *ambient* shadow. A single layer cannot reproduce it.
- The key layer is drawn at `opacity: 0.3`, the ambient layer at `opacity: 0.15`.
  Both use `md.sys.color.shadow` (`#000000` in the baseline palette).
- The ambient layer carries a **spread** from level 1 upward. Spread inflates the shadow
  rect outward on all sides before blurring, which is what makes low levels visible at
  all — without it the opaque container paints over everything but the blur tail.
- The level number is *not* the dp value. `md.sys.elevation.level*` maps to
  1 / 3 / 6 / 8 / 12 dp, and neither the offsets nor the blurs track that dp value
  linearly, so no formula substitutes for the table.

## Tokens & Specs

### Key shadow — `opacity: 0.3`

| Level | offset-x | offset-y | blur | spread | box-shadow           |
|-------|----------|----------|------|--------|----------------------|
| 0     | 0px      | 0px      | 0px  | 0px    | `0px 0px 0px 0px`    |
| 1     | 0px      | 1px      | 2px  | 0px    | `0px 1px 2px 0px`    |
| 2     | 0px      | 1px      | 2px  | 0px    | `0px 1px 2px 0px`    |
| 3     | 0px      | 1px      | 3px  | 0px    | `0px 1px 3px 0px`    |
| 4     | 0px      | 2px      | 3px  | 0px    | `0px 2px 3px 0px`    |
| 5     | 0px      | 4px      | 4px  | 0px    | `0px 4px 4px 0px`    |

### Ambient shadow — `opacity: 0.15`

| Level | offset-x | offset-y | blur | spread | box-shadow           |
|-------|----------|----------|------|--------|----------------------|
| 0     | 0px      | 0px      | 0px  | 0px    | `0px 0px 0px 0px`    |
| 1     | 0px      | 1px      | 3px  | 1px    | `0px 1px 3px 1px`    |
| 2     | 0px      | 2px      | 6px  | 2px    | `0px 2px 6px 2px`    |
| 3     | 0px      | 4px      | 8px  | 3px    | `0px 4px 8px 3px`    |
| 4     | 0px      | 6px      | 10px | 4px    | `0px 6px 10px 4px`   |
| 5     | 0px      | 8px      | 12px | 6px    | `0px 8px 12px 6px`   |

### Level → dp

The dp values below come from the component specs (see `cards.md`), and are recorded
here only to document that they do **not** drive the shadow geometry above.

| Level | dp   |
|-------|------|
| 0     | 0dp  |
| 1     | 1dp  |
| 2     | 3dp  |
| 3     | 6dp  |
| 4     | 8dp  |
| 5     | 12dp |

## Notes

- CSS `blur-radius` is twice the Gaussian sigma a renderer applies, so a Skia-level
  translation uses `sigma = blur / 2`.
- Upstream implements the two layers as `::before` / `::after` pseudo-elements whose
  values are derived from a single `--_level` custom property via clamped `calc()`,
  which is how it interpolates between levels. The discrete per-level results are the
  table values above.
- These per-level box-shadow tokens are not published in the m3.material.io spec viewer;
  the viewer only exposes `md.sys.elevation.level*` as a dp value. Material Web's
  implementation is the authoritative source for the shadow geometry.
