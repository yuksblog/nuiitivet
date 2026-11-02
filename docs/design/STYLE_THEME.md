# Style and Theme

A widget's look is a style, one dataclass per widget. A theme supplies the
colours a style names. A design system may put another default style in the
theme. How a widget reads the theme is in
[THEME_CONSUMPTION.md](THEME_CONSUMPTION.md).

## Overview

Three groups of modules take part.

### Structure

```mermaid
flowchart LR
    theme[The Theme]
    material[The Material Theme]
    styles[The Styles]
    widgets[the Material widgets]
    generic[the generic widgets]
    app[the app]

    app -- "MaterialThemeFactory.from_seed(seed, mode, variant, contrast_level, form_factor)" --> material
    app -- "App(theme=...) · set_theme(theme)" --> theme
    material -- "Theme(mode, extensions, name) · ThemeExtension" --> theme
    widgets -- "Theme.of(self) · theme.extension(MaterialThemeData)" --> theme
    widgets -- "Style.from_theme(theme) · style.copy_with(...) · ColorSpec fields" --> styles
    styles -- "resolve_color_to_rgba(spec, theme)" --> theme
    generic -- "theme.extension(ScrollbarThemeData) · theme.extension(MenuBarThemeData)" --> theme
```

| Module | Role |
| --- | --- |
| The Theme | the design-agnostic container, the colour resolver and the manager |
| The Material Theme | the palette from a seed, the form factor and the per-variant style overrides |
| The Styles | one dataclass per widget |
| the Material widgets | read a style ([MATERIAL_INTERACTION.md](MATERIAL_INTERACTION.md)) |
| the generic widgets | the scrollbar and the menu bar, each with a palette extension of its own ([MENU_BAR.md](MENU_BAR.md)) |
| the app | builds a theme and installs it |

### Promises

- Everything design-specific lives in a `ThemeExtension`.
- A generic widget never reads a Material colour role.
- The app-wide palette lives in a `ThemeExtension`. A per-instance override
  lives in the nullable `ColorSpec` fields of the widget's style. The shape
  lives in the style.

## The Theme

`Theme` is the container every design system fills.

### Structure

```mermaid
flowchart LR
    theme[theme/theme.py]
    types[theme/types.py]
    resolver[theme/resolver.py]
    manager[theme/manager.py]
    plain[theme/plain_theme.py]
    appscope[runtime/app.py]
    styles[the styles]

    theme -- "is a: ThemeExtension, each extension" --> types
    resolver -- "token.resolve(theme)" --> types
    styles -- "resolve_color_to_rgba(spec, theme)" --> resolver
    appscope -- "ThemeManager(initial) · current · generation · on_change" --> manager
    manager -- "the current Theme" --> theme
    plain -- "Theme(mode, [PlainThemeData, ScrollbarThemeData, MenuBarThemeData])" --> theme
```

| Module | Role |
| --- | --- |
| `theme/theme.py` | the container and `Theme.of` |
| `theme/types.py` | the colour spec vocabulary, a token, a literal or either with an alpha, and the extension protocol |
| `theme/resolver.py` | turns a `ColorSpec` into RGBA against a theme |
| `theme/manager.py` | holds the current theme for one owner |
| `theme/plain_theme.py` | `PlainTheme`, the design system with no Material ([THEME_CONSUMPTION.md](THEME_CONSUMPTION.md)) |
| `runtime/app.py` | the `AppScope` that owns the manager ([APP_WINDOW.md](APP_WINDOW.md)) |
| the styles | the colour fields resolved (The Styles) |

### Promises

- A colour token resolves at paint, against the theme current then.
- A theme holds at most one extension per type.
- The manager notifies one owner.

## The Material Theme

`MaterialThemeData` is the Material extension of a theme.

### Structure

```mermaid
flowchart LR
    data[material/theme/theme_data.py]
    factory[material/theme/material_theme.py]
    palette[material/theme/palette.py]
    role[material/theme/color_role.py]
    form[material/theme/form_factor.py]
    styles[material/styles/]
    scrollbar[scrolling/scrollbar_theme_data.py]
    menubar[menubar/theme_data.py]
    widgets[the Material widgets]

    factory -- "palette.from_seed(seed, dark, variant, contrast_level)" --> palette
    palette -- "the ColorRole to colour map" --> data
    factory -- "MaterialThemeData(roles, form_factor) · ScrollbarThemeData(...) · MenuBarThemeData(...)" --> data & scrollbar & menubar
    role -- "resolve(theme)" --> data
    data -- "_shared_default(Style.variant), when the slot is empty" --> styles
    styles -- "theme_data.<variant>_style" --> data
    widgets -- "form_factor_of(context) · min_extent(explicit, container, context)" --> form
    form -- "theme.extension(MaterialThemeData).form_factor" --> data
```

| Module | Role |
| --- | --- |
| `material/theme/theme_data.py` | `MaterialThemeData`: the roles, the form factor, one nullable slot per widget variant falling through to a shared default |
| `material/theme/material_theme.py` | `MaterialThemeFactory`: a theme from a seed, with the Material, scrollbar and menu bar extensions |
| `material/theme/palette.py` | derives the roles from a seed, a scheme variant and a contrast level |
| `material/theme/color_role.py` | `ColorRole`, a token resolving through the Material extension |
| `material/theme/form_factor.py` | `FormFactor`, the component sizes of one kind of device |
| `material/styles/` | the defaults the slots fall through to (The Styles) |
| `scrolling/scrollbar_theme_data.py` | the scrollbar's palette |
| `menubar/theme_data.py` | the menu bar's palette ([MENU_BAR.md](MENU_BAR.md)) |
| the Material widgets | measure and paint by the form factor |

### Sequence

#### A widget resolves its style

```mermaid
sequenceDiagram
    participant W as the Material widgets
    participant S as material/styles/
    participant D as material/theme/theme_data.py

    alt the caller passed a style, or a host derived one
        W->>W: that style
    else
    W->>S: Style.from_theme(theme)
    S->>S: theme.extension(MaterialThemeData)
    alt a Material theme is installed
        S->>D: the variant's slot
        alt the slot is set
            D-->>S: the override
        else
            D-->>S: the shared default
        end
    else
        S->>S: Style.default()
    end
    end
```

### Promises

- An empty slot falls through to one shared frozen preset.
- A style keeps the MD3 baseline numbers under every form factor. The widget
  applies the form factor where it measures and paints.
- A style's own `density` wins over the theme's step.

## The Styles

Each widget has its own style class.

### Structure

```mermaid
flowchart LR
    styles[material/styles/]
    widgets[the Material widgets]
    data[material/theme/theme_data.py]
    resolver[theme/resolver.py]
    app[the app]

    app -- "ButtonStyle.filled(size) · CardStyle.elevated() · style.copy_with(...)" --> styles
    app -- "Button(style=...)" --> widgets
    widgets -- "Style.from_theme(theme) · Style.default() · style.resolve(theme)" --> styles
    styles -- "theme_data.<variant>_style" --> data
    styles -- "resolve_color_to_rgba(spec, theme), per colour field" --> resolver
```

| Module | Role |
| --- | --- |
| `material/styles/` | one frozen dataclass per widget: the `ColorSpec` fields, the MD3 shape and size tokens, the variant factories, `default()`, `from_theme()` |
| the Material widgets | hold the caller's style, and one a hosting widget such as a toolbar derives for them |
| `material/theme/theme_data.py` | the overrides (The Material Theme) |
| `theme/resolver.py` | the colour resolution (The Theme) |
| the app | passes a style or a variant |

### Promises

- A style is frozen. A variation is a `copy_with`, never a mutation.
- No style class inherits from another.
- Every style class with presets has `default()`.
