<!-- markdownlint-disable MD060 -->

# Progress Indicators MD3 Specs

Source: <https://m3.material.io/components/progress-indicators/specs>
Collected: 2026-03-12

## Summary

- The primary token viewer exposes three non-deprecated token sets: shared common tokens plus linear and circular variant-specific baseline tokens.
- Shared common tokens provide current color values and shape previews; the shape rows render as circular previews but do not expose textual numeric values.
- Linear baseline geometry centers on a 4dp track, 10dp wavy height, 3dp wave amplitude, and 40dp wave wavelength, with a 20dp wavelength for indeterminate waves.
- Circular baseline geometry centers on a 40dp size, 48dp wavy size, 4dp track thickness, 1.6dp wave amplitude, and 15dp wave wavelength.
- The Measurements section explicitly states a 4dp screen-edge inset for linear indicators and defines amplitude and wavelength, but its remaining figure callouts are image-only in accessible text.

## Tokens & Specs

### Token sets discovered

| Token set                     | Notes                                                                                                                                                             |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Progress Indicator - Common   | Context shown in the viewer: Default, Light. Non-deprecated groups: Color, Shape. Deprecated legacy thickness/spacing subgroup also appears in the shared viewer. |
| Progress indicator - Linear   | Context shown in the viewer: Default, Light. Non-deprecated group: Linear - baseline. Deprecated thick subgroup also appears.                                     |
| Progress indicator - Circular | Context shown in the viewer: Default, Light. Non-deprecated group: Circular - baseline. Deprecated thick subgroup also appears.                                   |

### Extracted tokens

#### Progress Indicator - Common

| Token set                   | Group | Label                                     | Token                                             | Value                                | Notes                                                                                   |
|-----------------------------|-------|-------------------------------------------|---------------------------------------------------|--------------------------------------|-----------------------------------------------------------------------------------------|
| Progress Indicator - Common | Color | Progress indicator active indicator color | md.comp.progress-indicator.active-indicator.color | #6750A4                              |                                                                                         |
| Progress Indicator - Common | Color | Progress indicator track color            | md.comp.progress-indicator.track.color            | #E8DEF8                              |                                                                                         |
| Progress Indicator - Common | Color | Progress indicator stop indicator color   | md.comp.progress-indicator.stop-indicator.color   | #6750A4                              |                                                                                         |
| Progress Indicator - Common | Shape | Progress indicator active indicator shape | md.comp.progress-indicator.active-indicator.shape | visual-only (circular-shape preview) | No textual value exposed inline; row selection did not expose additional popup details. |
| Progress Indicator - Common | Shape | Progress indicator track shape            | md.comp.progress-indicator.track.shape            | visual-only (circular-shape preview) | No textual value exposed inline; row selection did not expose additional popup details. |
| Progress Indicator - Common | Shape | Progress indicator stop indicator shape   | md.comp.progress-indicator.stop-indicator.shape   | visual-only (circular-shape preview) | No textual value exposed inline; row selection did not expose additional popup details. |

#### Progress indicator - Linear

| Token set                   | Group             | Label                                                   | Token                                                                            | Value | Notes                                                    |
|-----------------------------|-------------------|---------------------------------------------------------|----------------------------------------------------------------------------------|-------|----------------------------------------------------------|
| Progress indicator - Linear | Linear - baseline | Progress indicator linear height                        | md.comp.progress-indicator.linear.height                                         | 4dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear with wave height              | md.comp.progress-indicator.linear.with-wave.height                               | 10dp  |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear active indicator thickness    | md.comp.progress-indicator.linear.active-indicator.thickness                     | 4dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear track thickness               | md.comp.progress-indicator.linear.track.thickness                                | 4dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear stop indicator size           | md.comp.progress-indicator.linear.stop-indicator.size                            | 4dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear track active indicator space  | md.comp.progress-indicator.linear.track-active-indicator-space                   | 4dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear stop indicator trailing space | md.comp.progress-indicator.linear.stop-indicator.trailing-space                  | 0     |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear wave amplitude                | md.comp.progress-indicator.linear.active-indicator.wave.amplitude                | 3dp   |                                                          |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear wave wavelenght               | md.comp.progress-indicator.linear.active-indicator.wave.wavelength               | 40dp  | Display label on the page is misspelled as "wavelenght". |
| Progress indicator - Linear | Linear - baseline | Progress indicator linear indeterminate wave wavelenght | md.comp.progress-indicator.linear.indeterminate.active-indicator.wave.wavelength | 20dp  | Display label on the page is misspelled as "wavelenght". |

#### Progress indicator - Circular

| Token set                     | Group               | Label                                                        | Token                                                                | Value | Notes |
|-------------------------------|---------------------|--------------------------------------------------------------|----------------------------------------------------------------------|-------|-------|
| Progress indicator - Circular | Circular - baseline | Progress indicator circular size                             | md.comp.progress-indicator.circular.size                             | 40dp  |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular size with wave                   | md.comp.progress-indicator.circular.with-wave.size                   | 48dp  |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular active indicator thickness       | md.comp.progress-indicator.circular.active-indicator.thickness       | 4dp   |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular track thickness                  | md.comp.progress-indicator.circular.track.thickness                  | 4dp   |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular track active indicator space     | md.comp.progress-indicator.circular.track-active-indicator-space     | 4dp   |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular active indicator wave amplitude  | md.comp.progress-indicator.circular.active-indicator.wave.amplitude  | 1.6dp |       |
| Progress indicator - Circular | Circular - baseline | Progress indicator circular active indicator wave wavelength | md.comp.progress-indicator.circular.active-indicator.wave.wavelength | 15dp  |       |

## Measurements

| Category             | Item                          | Value                                                    | Notes                                                                                      |
|----------------------|-------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Wave terminology     | Amplitude                     | Center of the resting position to the center of the peak | Explicit prose definition in Measurements.                                                 |
| Wave terminology     | Wavelength                    | Distance between two adjacent peaks                      | Explicit prose definition in Measurements.                                                 |
| Linear               | Default track thickness       | 4dp                                                      | Configurations lists fixed 4dp thickness; the linear baseline token set matches it.        |
| Linear               | Wavy height                   | 10dp                                                     | From md.comp.progress-indicator.linear.with-wave.height.                                   |
| Linear               | Active indicator thickness    | 4dp                                                      | From md.comp.progress-indicator.linear.active-indicator.thickness.                         |
| Linear               | Track thickness               | 4dp                                                      | From md.comp.progress-indicator.linear.track.thickness.                                    |
| Linear               | Stop indicator size           | 4dp                                                      | From md.comp.progress-indicator.linear.stop-indicator.size.                                |
| Linear               | Track-active space            | 4dp                                                      | From md.comp.progress-indicator.linear.track-active-indicator-space.                       |
| Linear               | Stop indicator trailing space | 0                                                        | From md.comp.progress-indicator.linear.stop-indicator.trailing-space.                      |
| Linear               | Wave amplitude                | 3dp                                                      | From md.comp.progress-indicator.linear.active-indicator.wave.amplitude.                    |
| Linear               | Wave wavelength               | 40dp                                                     | From md.comp.progress-indicator.linear.active-indicator.wave.wavelength.                   |
| Linear indeterminate | Wave wavelength               | 20dp                                                     | From md.comp.progress-indicator.linear.indeterminate.active-indicator.wave.wavelength.     |
| Linear               | Screen-edge inset             | 4dp                                                      | Explicit prose in Measurements: the indicator is inset from the edge of the screen by 4dp. |
| Circular             | Default size                  | 40dp                                                     | From md.comp.progress-indicator.circular.size.                                             |
| Circular             | Wavy size                     | 48dp                                                     | From md.comp.progress-indicator.circular.with-wave.size.                                   |
| Circular             | Active indicator thickness    | 4dp                                                      | From md.comp.progress-indicator.circular.active-indicator.thickness.                       |
| Circular             | Track thickness               | 4dp                                                      | From md.comp.progress-indicator.circular.track.thickness.                                  |
| Circular             | Track-active space            | 4dp                                                      | From md.comp.progress-indicator.circular.track-active-indicator-space.                     |
| Circular             | Wave amplitude                | 1.6dp                                                    | From md.comp.progress-indicator.circular.active-indicator.wave.amplitude.                  |
| Circular             | Wave wavelength               | 15dp                                                     | From md.comp.progress-indicator.circular.active-indicator.wave.wavelength.                 |

## Implementation Notes

- Model shared colors separately from variant-specific geometry. Linear and circular sizing is not encoded in the common token set.
- Treat the shared shape tokens as fully rounded/circular until another source exposes a resolved radius token; the rendered token previews use a circular-shape class and no numeric text.
- Support both flat and wavy linear indicators; expressive linear geometry depends on wave height, amplitude, and wavelength tokens rather than only track thickness.
- Keep deprecated thick token groups out of default implementation paths unless you intentionally need archived compatibility behavior.
