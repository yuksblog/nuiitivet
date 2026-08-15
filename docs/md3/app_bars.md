<!-- markdownlint-disable MD060 -->

# App Bars MD3 Specs

Source: <https://m3.material.io/components/app-bars/specs>
Collected: 2026-05-25

## Summary

- Current expressive variants are Search, Small, Medium Flexible, and Large Flexible; the baseline Medium and Large app bars remain documented only as legacy fallbacks.
- Shared app-bar tokens use surface-based container colors, on-surface headline and leading-icon color, on-surface-variant subtitle and trailing-icon color, and a 0dp resting elevation that rises to 3dp on scroll.
- Common layout tokens fix 4dp outer app-bar padding, 24dp icon size, 32dp avatar size, and 8dp side padding inside the search container.
- The search app bar uses a 56dp full-shape search container inside a 64dp bar; medium flexible is 112dp or 136dp with subtitle; large flexible is 120dp or 152dp with subtitle.
- Flexible variants keep 48dp action slots and move to larger expressive type ramps than the deprecated baseline medium and large bars.

## Tokens & Specs

### Token sets discovered

| Token set                                        | Status         | Notes                                                                                |
|--------------------------------------------------|----------------|--------------------------------------------------------------------------------------|
| App bar - Common                                 | Active         | Primary shared token set for current app bars.                                       |
| App bar - Size - Small                           | Active         | Small app bar sizing, search-bar sizing, and small typography.                       |
| App bar - Size - Medium Flexible                 | Active         | Recommended replacement for the legacy medium baseline app bar.                      |
| App bar - Size - Large Flexible                  | Active         | Recommended replacement for the legacy large baseline app bar.                       |
| App bar - Size - Medium (baseline)               | Active, legacy | Exposed under the Baseline app bars section; no longer recommended in M3 Expressive. |
| App bar - Size - Large (baseline)                | Active, legacy | Exposed under the Baseline app bars section; no longer recommended in M3 Expressive. |
| [Deprecated] Top app bar - Small                 | Deprecated     | Exposed in the baseline token viewer and intentionally skipped.                      |
| [Deprecated] Top app bar - Medium                | Deprecated     | Exposed in the baseline token viewer and intentionally skipped.                      |
| [Deprecated] Top app bar - Large                 | Deprecated     | Exposed in the baseline token viewer and intentionally skipped.                      |
| [Deprecated] Top app bar - Small, Center-aligned | Deprecated     | Exposed in the baseline token viewer and intentionally skipped.                      |
| Search - View                                    | Referenced     | Separate embedded Search component token viewer; not duplicated here.                |
| Search - Bar                                     | Referenced     | Separate embedded Search component token viewer; not duplicated here.                |

### App bar - Common

| Token Set        | Group   | Label                                 | Token                                            | Source token                           | Value   | Notes                                                                                                                                 |
|------------------|---------|---------------------------------------|--------------------------------------------------|----------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------|
| App bar - Common | Color   | App bar container color               | md.comp.app-bar.container.color                  | md.sys.color.surface                   | #FFFFFF |                                                                                                                                       |
| App bar - Common | Color   | Search container color                | md.comp.app-bar.search.container.color           | md.sys.color.surface-container         | #F0F4F9 |                                                                                                                                       |
| App bar - Common | Color   | Search label color                    | md.comp.app-bar.search.label.color               | md.sys.color.on-surface-variant        | #444746 |                                                                                                                                       |
| App bar - Common | Color   | App bar container color on scroll     | md.comp.app-bar.on-scroll.container.color        | md.sys.color.surface-container         | #F0F4F9 |                                                                                                                                       |
| App bar - Common | Color   | Search container color on scroll      | md.comp.app-bar.search.on-scroll.container.color | md.sys.color.surface-container-highest | #DDE3EA |                                                                                                                                       |
| App bar - Common | Color   | App bar container elevation           | md.comp.app-bar.container.elevation              | md.sys.elevation.level0                | 0dp     | Resolved from elevation token.                                                                                                        |
| App bar - Common | Color   | App bar container elevation on scroll | md.comp.app-bar.on-scroll.container.elevation    | md.sys.elevation.level2                | 3dp     |                                                                                                                                       |
| App bar - Common | Color   | App bar title text                    | md.comp.app-bar.title.color                      | md.sys.color.on-surface                | #1F1F1F |                                                                                                                                       |
| App bar - Common | Color   | App bar subtitle text                 | md.comp.app-bar.subtitle.color                   | md.sys.color.on-surface-variant        | #444746 |                                                                                                                                       |
| App bar - Common | Color   | App bar leading icon                  | md.comp.app-bar.leading-icon.color               | md.sys.color.on-surface                | #1F1F1F |                                                                                                                                       |
| App bar - Common | Color   | App bar trailing icon                 | md.comp.app-bar.trailing-icon.color              | md.sys.color.on-surface-variant        | #444746 |                                                                                                                                       |
| App bar - Common | Shape   | App bar container shape               | md.comp.app-bar.container.shape                  | md.sys.shape.corner.none               | 0dp     | Resolved from shape token.                                                                                                            |
| App bar - Common | Size    | App bar avatar size                   | md.comp.app-bar.avatar.size                      |                                        | 32dp    |                                                                                                                                       |
| App bar - Common | Size    | App bar icon size                     | md.comp.app-bar.icon.size                        |                                        | 24dp    |                                                                                                                                       |
| App bar - Common | Spacing | App bar left padding                  | md.comp.app-bar.leading-space                    |                                        | 4dp     |                                                                                                                                       |
| App bar - Common | Spacing | App bar right padding                 | md.comp.app-bar.trailing-space                   |                                        | 4dp     |                                                                                                                                       |
| App bar - Common | Spacing | App bar icon spacing                  | md.comp.app-bar.icon-button-space                |                                        | 24dp    | Measurement diagrams show 24dp between adjacent trailing action slots; the token payload serialized this row without a numeric value. |
| App bar - Common | Spacing | Search left padding                   | md.comp.app-bar.search.leading-space             |                                        | 8dp     |                                                                                                                                       |
| App bar - Common | Spacing | Search right padding                  | md.comp.app-bar.search.trailing-space            |                                        | 8dp     |                                                                                                                                       |

### App bar - Size - Small

| Token Set              | Group      | Label                          | Token                                         | Source token                  | Value                                                 | Notes                      |
|------------------------|------------|--------------------------------|-----------------------------------------------|-------------------------------|-------------------------------------------------------|----------------------------|
| App bar - Size - Small | Size       | App bar small container height | md.comp.app-bar.small.container.height        |                               | 64dp                                                  |                            |
| App bar - Size - Small | Typography | App bar small title font       | md.comp.app-bar.small.title.font              | md.sys.typescale.title-large  | Google Sans / 400 / 22pt / 28pt                       | Context: Static type ramp. |
| App bar - Size - Small | Typography | App bar small subtitle font    | md.comp.app-bar.small.subtitle.font           | md.sys.typescale.label-medium | Google Sans Text / 500 / 12pt / 16pt / tracking 0.1pt | Context: Static type ramp. |
| App bar - Size - Small | Size       | App bar small icon button size | md.comp.app-bar.small.icon.size               |                               | 24dp                                                  |                            |
| App bar - Size - Small | Size       | Search container height        | md.comp.app-bar.small.search.container.height |                               | 56dp                                                  |                            |
| App bar - Size - Small | Shape      | Search container shape         | md.comp.app-bar.small.search.container.shape  | md.sys.shape.corner.full      | full                                                  | Resolved from shape token. |
| App bar - Size - Small | Typography | Search title font              | md.comp.app-bar.small.search.label-text.font  | md.sys.typescale.body-large   | Google Sans Text / 400 / 16pt / 24pt                  | Context: Static type ramp. |

### App bar - Size - Medium Flexible

| Token Set                        | Group      | Label                                                  | Token                                                          | Source token                     | Value                                | Notes                      |
|----------------------------------|------------|--------------------------------------------------------|----------------------------------------------------------------|----------------------------------|--------------------------------------|----------------------------|
| App bar - Size - Medium Flexible | Size       | App bar medium flexible container height               | md.comp.app-bar.medium-flexible.container.height               |                                  | 112dp                                |                            |
| App bar - Size - Medium Flexible | Size       | App bar medium flexible container height with subtitle | md.comp.app-bar.medium-flexible.with-subtitle.container.height |                                  | 136dp                                |                            |
| App bar - Size - Medium Flexible | Typography | App bar medium title font                              | md.comp.app-bar.medium-flexible.title.font                     | md.sys.typescale.headline-medium | Google Sans / 400 / 28pt / 36pt      | Context: Static type ramp. |
| App bar - Size - Medium Flexible | Typography | App bar medium subtitle font                           | md.comp.app-bar.medium-flexible.subtitle.font                  | md.sys.typescale.label-large     | Google Sans Text / 500 / 14pt / 20pt | Context: Static type ramp. |

### App bar - Size - Large Flexible

| Token Set                       | Group      | Label                                                 | Token                                                         | Source token                   | Value                                | Notes                      |
|---------------------------------|------------|-------------------------------------------------------|---------------------------------------------------------------|--------------------------------|--------------------------------------|----------------------------|
| App bar - Size - Large Flexible | Size       | App bar large flexible container height               | md.comp.app-bar.large-flexible.container.height               |                                | 120dp                                |                            |
| App bar - Size - Large Flexible | Size       | App bar large flexible container height with subtitle | md.comp.app-bar.large-flexible.with-subtitle.container.height |                                | 152dp                                |                            |
| App bar - Size - Large Flexible | Typography | App bar large title font                              | md.comp.app-bar.large-flexible.title.font                     | md.sys.typescale.display-small | Google Sans / 400 / 36pt / 44pt      | Context: Static type ramp. |
| App bar - Size - Large Flexible | Typography | App bar large subtitle font                           | md.comp.app-bar.large-flexible.subtitle.font                  | md.sys.typescale.title-medium  | Google Sans Text / 500 / 16pt / 24pt | Context: Static type ramp. |

### App bar - Size - Medium (baseline)

| Token Set                          | Group      | Label                           | Token                                   | Source token                    | Value                                | Notes                      |
|------------------------------------|------------|---------------------------------|-----------------------------------------|---------------------------------|--------------------------------------|----------------------------|
| App bar - Size - Medium (baseline) | Size       | App bar medium container height | md.comp.app-bar.medium.container.height |                                 | 112dp                                | Legacy baseline size.      |
| App bar - Size - Medium (baseline) | Typography | App bar medium title font       | md.comp.app-bar.medium.title.font       | md.sys.typescale.headline-small | Google Sans / 400 / 24pt / 32pt      | Context: Static type ramp. |
| App bar - Size - Medium (baseline) | Size       | App bar medium icon button size | md.comp.app-bar.medium.icon.size        |                                 | 24dp                                 |                            |
| App bar - Size - Medium (baseline) | Typography | App bar medium subtitle font    | md.comp.app-bar.medium.subtitle.font    | md.sys.typescale.label-large    | Google Sans Text / 500 / 14pt / 20pt | Context: Static type ramp. |

### App bar - Size - Large (baseline)

| Token Set                         | Group      | Label                          | Token                                  | Source token                     | Value                                | Notes                      |
|-----------------------------------|------------|--------------------------------|----------------------------------------|----------------------------------|--------------------------------------|----------------------------|
| App bar - Size - Large (baseline) | Size       | App bar large container height | md.comp.app-bar.large.container.height |                                  | 152dp                                | Legacy baseline size.      |
| App bar - Size - Large (baseline) | Typography | App bar large title font       | md.comp.app-bar.large.title.font       | md.sys.typescale.headline-medium | Google Sans / 400 / 28pt / 36pt      | Context: Static type ramp. |
| App bar - Size - Large (baseline) | Size       | App bar large icon button size | md.comp.app-bar.large.icon.size        |                                  | 24dp                                 |                            |
| App bar - Size - Large (baseline) | Typography | App bar large subtitle font    | md.comp.app-bar.large.subtitle.font    | md.sys.typescale.title-medium    | Google Sans Text / 500 / 16pt / 24pt | Context: Static type ramp. |

## Measurements

| Category                | Item                                            | Value      | Notes                                                                                                                                                    |
|-------------------------|-------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Search app bar          | Overall bar height                              | 64dp       | From the small app-bar size token and the search measurement figure.                                                                                     |
| Search app bar          | Search container height                         | 56dp       | Matches the small search container size token.                                                                                                           |
| Search app bar          | External action slot size                       | 48dp       | Leading and trailing controls occupy 48dp slots in the diagram.                                                                                          |
| Search app bar          | Outer edge padding                              | 4dp        | The figure labels 4dp at both outer edges.                                                                                                               |
| Search app bar          | Gap between leading action and search container | 8dp        | The figure labels 8dp between the leading slot and the search container.                                                                                 |
| Search app bar          | Internal trailing search action slot            | 48dp       | The measurement figure shows a 48dp search-internal trailing action slot.                                                                                |
| Small app bar           | Overall height                                  | 64dp       | From the small size token.                                                                                                                               |
| Small app bar           | Leading and trailing action slot size           | 48dp       | The figure shows 48dp action slots for back, search, calendar, and avatar placements.                                                                    |
| Small app bar           | Edge padding                                    | 4dp        | Labeled 4dp on both outer edges in the icon-button layout.                                                                                               |
| Small app bar           | Title offset from adjacent action area          | 24dp       | The figure labels 24dp between the leading slot and the title area, and between adjacent trailing action slots.                                          |
| Small app bar           | Avatar graphic size                             | 32dp       | The centered-avatar example shows a 32dp avatar inside a 48dp slot.                                                                                      |
| Medium flexible app bar | Overall height                                  | 112dp      | From the size token and confirmed by the measurement figure.                                                                                             |
| Medium flexible app bar | Height with subtitle                            | 136dp      | From the size token.                                                                                                                                     |
| Medium flexible app bar | Leading and trailing action slot size           | 48dp       | The figure shows 48dp action slots.                                                                                                                      |
| Medium flexible app bar | Outer edge padding                              | 4dp        | Labeled at the left and right edges of the top action row.                                                                                               |
| Medium flexible app bar | Trailing action spacing                         | 24dp       | The figure labels 24dp between the trailing action slots.                                                                                                |
| Medium flexible app bar | Title block horizontal inset                    | 16dp       | The figure labels 16dp from the container edge to the text block.                                                                                        |
| Medium flexible app bar | Top inset above action row                      | 8dp        | The figure labels 8dp above the trailing action row.                                                                                                     |
| Medium flexible app bar | Bottom inset below title block                  | 12dp       | The figure labels 12dp below the title block.                                                                                                            |
| Large flexible app bar  | Overall height                                  | 120dp      | From the size token and confirmed by the measurement figure.                                                                                             |
| Large flexible app bar  | Height with subtitle                            | 152dp      | From the size token.                                                                                                                                     |
| Large flexible app bar  | Leading and trailing action slot size           | 48dp       | The figure shows 48dp action slots.                                                                                                                      |
| Large flexible app bar  | Outer edge padding                              | 4dp        | Labeled at the outer edges of the action row.                                                                                                            |
| Large flexible app bar  | Trailing action spacing                         | 24dp       | The figure labels 24dp between the trailing action slots.                                                                                                |
| Large flexible app bar  | Title block horizontal inset                    | 16dp       | The figure labels 16dp from the container edge to the display-small title block.                                                                         |
| Large flexible app bar  | Top inset above action row                      | 8dp        | The figure labels 8dp above the trailing action row.                                                                                                     |
| Large flexible app bar  | Bottom inset below title block                  | 12dp       | The figure labels 12dp below the title block.                                                                                                            |
| Baseline medium app bar | Overall height                                  | 112dp      | From the baseline medium size token.                                                                                                                     |
| Baseline medium app bar | Title block horizontal inset                    | 16dp       | The baseline medium figure labels 16dp at the left and right text edges.                                                                                 |
| Baseline medium app bar | Trailing action spacing                         | 24dp       | The baseline medium figure labels 24dp between trailing action slots.                                                                                    |
| Baseline medium app bar | Top inset above title block                     | 20dp       | Visible in the baseline medium measurement figure.                                                                                                       |
| Baseline medium app bar | Bottom inset below title block                  | 24dp       | Visible in the baseline medium measurement figure.                                                                                                       |
| Baseline large app bar  | Overall height                                  | 152dp      | From the baseline large size token.                                                                                                                      |
| Baseline large app bar  | Additional padding values                       | See figure | The browser-exposed large baseline capture did not expose extra numeric labels cleanly; rely on the size and typography tokens above for implementation. |

## Implementation Notes

- Prefer small, medium-flexible, and large-flexible app bars for new work. The baseline medium and large bars remain useful as migration references but are explicitly not recommended by the spec page.
- Treat on-scroll as a real visual state, not a mere scroll flag: the app-bar container color changes from `surface` to `surface-container`, and the container elevation rises from `level0` to `level2`.
- The shared app-bar container shape is effectively square (`md.sys.shape.corner.none`), while the small search container uses a full shape.
- Search app bars depend partly on the separate embedded Search component viewer. This document captures the app-bar-local search tokens and measurements, but the full `Search - View` and `Search - Bar` token tables belong in a dedicated Search spec document if that component is implemented separately.
