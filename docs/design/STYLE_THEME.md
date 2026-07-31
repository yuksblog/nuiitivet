# Style & Theme System Proposal

## Design Philosophy

### Core Principles

1. **Widget-specific Styles**: Each widget has its own style class (e.g., `ButtonStyle`, `CheckboxStyle`, `IconStyle`)
2. **Theme holds defaults**: `Theme` contains default style instances for all widgets
3. **Immutable with override**: Styles are frozen dataclasses, use `dataclasses.replace()` for customization
4. **ColorRole-first**: Colors default to `ColorRole` for theme reactivity; concrete values allowed
5. **No inheritance hierarchy**: Flat style classes, no complex inheritance

## Architecture

```text
Theme
├── color roles (ColorRole → hex)
├── text_theme: TextTheme
├── button_style: ButtonStyle
├── checkbox_style: CheckboxStyle
├── icon_style: IconStyle
└── ...other widget styles

Widget(style: Optional[WidgetStyle])
├── If style=None → use Theme.current.widget_style
├── If style provided → merge with Theme defaults
└── Resolve colors at paint time via ColorRole
```

## Implementation Structure

### 1. Base Style Protocol (Optional)

```python
# src/nuiitivet/ui/styles/protocol.py
from typing import Protocol, TypeVar, Dict, Any

T = TypeVar('T')

class Style(Protocol):
    """Base protocol for widget styles (no runtime overhead)."""
    
    def resolve(self) -> Dict[str, Any]:
        """Resolve ColorRole and dynamic values to concrete paint values."""
        ...
```

### 2. Widget Style Classes

```python
# src/nuiitivet/ui/styles/button.py
from dataclasses import dataclass, replace
from typing import Optional, Tuple
from ...theme import ColorRole

@dataclass(frozen=True)
class ButtonStyle:
    """Immutable style for Button widgets."""
    
    background: Optional[str | ColorRole] = None
    foreground: Optional[str | ColorRole] = None
    elevation: float = 0.0
    border_color: Optional[str | ColorRole] = None
    border_width: float = 0.0
    corner_radius: int = 12
    padding: int = 16
    min_size: Tuple[int, int] = (160, 48)
    overlay: Optional[Tuple[str, float]] = None
    
    def copy_with(self, **changes) -> "ButtonStyle":
        """Create a new instance with specified fields changed."""
        return replace(self, **changes)
    
    def resolve(self) -> dict:
        """Resolve ColorRole to concrete values."""
        from ...rendering.skia import resolve_color
        return {
            "background": resolve_color(self.background),
            "foreground": resolve_color(self.foreground),
            "border_color": resolve_color(self.border_color),
            "corner_radius": self.corner_radius,
            "padding": self.padding,
            "min_size": self.min_size,
            "overlay": self.overlay,
        }

# src/nuiitivet/ui/styles/checkbox.py
@dataclass(frozen=True)
class CheckboxStyle:
    """Immutable style for Checkbox widgets."""
    
    size: int = 40
    icon_size_ratio: float = 18.0 / 48.0  # Icon size relative to touch target
    corner_radius_ratio: float = 0.111    # Corner radius relative to icon size
    stroke_width_ratio: float = 0.11      # Stroke width relative to icon size
    
    # Colors
    stroke_color: Optional[str | ColorRole] = ColorRole.ON_SURFACE
    stroke_alpha: float = 0.54
    checked_background: Optional[str | ColorRole] = ColorRole.PRIMARY
    checked_foreground: Optional[str | ColorRole] = ColorRole.ON_PRIMARY
    
    # State layer
    state_layer_ratio: float = 40.0 / 48.0
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12
    
    # Focus indicator
    focus_stroke: float = 3.0
    focus_offset: float = 2.0
    focus_alpha: float = 0.12
    focus_color: Optional[str | ColorRole] = ColorRole.PRIMARY
    
    def copy_with(self, **changes) -> "CheckboxStyle":
        return replace(self, **changes)
    
    def resolve(self) -> dict:
        from ...rendering.skia import resolve_color
        return {
            "size": self.size,
            "icon_size_ratio": self.icon_size_ratio,
            "corner_radius_ratio": self.corner_radius_ratio,
            "stroke_width_ratio": self.stroke_width_ratio,
            "stroke_color": resolve_color(self.stroke_color),
            "stroke_alpha": self.stroke_alpha,
            "checked_background": resolve_color(self.checked_background),
            "checked_foreground": resolve_color(self.checked_foreground),
            "state_layer_ratio": self.state_layer_ratio,
            "hover_alpha": self.hover_alpha,
            "pressed_alpha": self.pressed_alpha,
            "focus_stroke": self.focus_stroke,
            "focus_offset": self.focus_offset,
            "focus_alpha": self.focus_alpha,
            "focus_color": resolve_color(self.focus_color),
        }

# src/nuiitivet/ui/styles/icon.py
@dataclass(frozen=True)
class IconStyle:
    """Immutable style for Icon widgets."""
    
    default_size: int = 24
    default_color: Optional[str | ColorRole] = ColorRole.ON_SURFACE
    font_family_priority: Tuple[str, ...] = (
        "Material Symbols Outlined",
        "Material Icons",
    )
    
    def copy_with(self, **changes) -> "IconStyle":
        return replace(self, **changes)
    
    def resolve(self) -> dict:
        from ...rendering.skia import resolve_color
        return {
            "default_size": self.default_size,
            "default_color": resolve_color(self.default_color),
            "font_family_priority": self.font_family_priority,
        }
```

### 3. Theme Integration

```python
# src/nuiitivet/theme/theme.py
from dataclasses import dataclass, field
from typing import Mapping
from .color_role import ColorRole
from ..ui.styles import ButtonStyle, CheckboxStyle, IconStyle, TextTheme

@dataclass(frozen=True)
class Theme:
    """Theme holds color roles and default widget styles."""
    
    mode: str  # 'light' | 'dark'
    roles: Mapping[ColorRole, str]
    name: str = ""
    
    # Widget styles
    text_theme: TextTheme = field(default_factory=lambda: TextTheme())
    button_style: ButtonStyle = field(default_factory=lambda: ButtonStyle(
        background=ColorRole.PRIMARY,
        foreground=ColorRole.ON_PRIMARY,
        elevation=0.0,
        corner_radius=12,
        padding=16,
        min_size=(160, 48),
        overlay=(ColorRole.ON_PRIMARY, 0.12),
    ))
    checkbox_style: CheckboxStyle = field(default_factory=lambda: CheckboxStyle())
    icon_style: IconStyle = field(default_factory=lambda: IconStyle())
    
    # ... other styles
    
    def get(self, role: ColorRole) -> str:
        """Return color hex for role."""
        return self.roles[role]
    
    @classmethod
    def from_seed(cls, seed_hex: str, name: str = "") -> Tuple["Theme", "Theme"]:
        """Create light/dark themes from seed."""
        from .palette import from_seed as palette_from_seed
        light_roles = palette_from_seed(seed_hex)
        dark_roles = palette_from_seed(seed_hex, dark=True)
        
        # Create Material 3 button variants
        filled_btn = ButtonStyle(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            elevation=0.0,
            corner_radius=12,
            padding=16,
            min_size=(160, 48),
            overlay=(ColorRole.ON_PRIMARY, 0.12),
        )
        
        light = cls(
            name=name,
            mode="light",
            roles=light_roles,
            button_style=filled_btn,
            checkbox_style=CheckboxStyle(),
            icon_style=IconStyle(),
        )
        
        dark = cls(
            name=name,
            mode="dark",
            roles=dark_roles,
            button_style=filled_btn,
            checkbox_style=CheckboxStyle(),
            icon_style=IconStyle(),
        )
        
        return light, dark
```

### 4. Widget Usage Pattern

```python
from nuiitivet.material import ButtonStyle
# User code - use theme defaults
button = Button("Click", on_click=handler, style=ButtonStyle.filled())

# User code - customize specific properties
button = Button(
    "Click",
    style=manager.current.button_style.copy_with(
        corner_radius=20,
        padding=20,
    ),
)

# User code - completely custom style
custom_style = ButtonStyle(
    background="#FF5722",
    foreground="#FFFFFF",
    corner_radius=24,
    elevation=4.0,
)
button = Button("Custom", style=custom_style)

# Widget implementation
class Button(BaseButton, style=ButtonStyle.filled()):
    def __init__(
        self,
        text: str,
        on_click: Optional[Callable[[], None]] = None,
        style: Optional[ButtonStyle] = None,
        **kwargs
    ):
        # Merge: user style > theme default
        if style is None:
            style = manager.current.button_style
        
        # Create child with style properties
        super().__init__(
            child=Text(text, color=style.foreground),
            on_click=on_click,
            style=style,
            **kwargs,
        )
```

### 4.1 When may a widget read the theme?

> This section describes **current behaviour**. The rules below still require the
> author to choose between pulling and pushing, which is the root of #464, #473
> and #476. `docs/design/THEME_CONSUMPTION.md` proposes removing that choice:
> a read registers a dependency, the framework owns the invalidation, and nobody
> subscribes. Read that document before adding a new theme-aware widget.

The theme is an input to **layout and paint**, never to construction. It carries
typography and shape as well as colour, so it is consumed twice: once while
measuring, and again while painting.

| Call site | Verdict |
| --- | --- |
| `preferred_size()` / `layout()` | Yes — the layout phase needs typography and shape |
| `paint()` | Yes — the paint phase needs colour |
| `build()` | Yes — the result feeds both phases |
| `on_mount()` | Not to resolve a value. Only to subscribe, and only in the cases below |
| `__init__()` | Never — there is no parent yet, so the value is frozen wrong |

`Theme.of` resolves by walking `_parent` upward, so it can only answer once the
widget is attached. A value read in `__init__` is the light default forever.

#### Writing a widget: the default is to do nothing

**Read the theme where you use it. Do not resolve it in `__init__`, and do not
reach for a subscription.**

1. Most widgets need no theme code at all. `Box` already resolves background,
   border and shadow at paint time, so anything built on it follows the theme
   for free.
2. If the widget uses a colour or a typeface of its own, read `Theme.of(self)`
   at the point of use — inside `paint()`, or while measuring. `Text` does
   exactly this: its `style` property resolves on every access and holds nothing.
3. Only subscribe when you have no choice (below).

**The authoritative path is a pull at the point of use.** A widget must be able
to answer "what is my style?" *at any time*, including before it is mounted:
`App` measures the content tree to size an `auto` window, and although it mounts
the tree first (see below), a widget measured outside an App must still resolve
its own chain rather than look detached.

#### What a subscription is actually for

A `ThemeManager` subscription plays one of two roles, and only the second one
carries a value:

- **Invalidation.** `Box` subscribes purely to drop a cached paint —
  `_handle_theme_change` calls `invalidate_paint_cache()` and nothing else. The
  colour is still pulled on the next paint. This is the cheap, safe form.
- **Projection.** `Card` and the chips resolve the style and write it onto
  stored `Box` properties (`bgcolor`, `corner_radius`, …), because `Box` paints
  from its own fields and cannot pull on their behalf. Buttons do the same to
  feed concrete endpoints to their colour animations.

Projection is the exception, not the pattern. A widget that projects must:

1. fall back to a pull while it is unmounted, and
2. keep the subscription paired with `on_unmount` — `ThemeManager` holds
   subscribers strongly, so a missed unsubscribe pins the widget.

**A push is a cache over the pull, never a replacement for it.** Adopting at
mount *without* subscribing is exactly as broken as reading in `__init__`, only
harder to notice: the value stops following the theme.

#### The framework's side of the contract

Widgets can only honour the rule if the chain they walk is intact:

- A composable parents its build result **when it builds**, not when it mounts
  (`BuilderHostMixin._adopt_built`), so a pre-mount measurement resolves
  ancestors instead of dead-ending.
- A `ChildrenStore` clears a child's `_parent` only while it still points at
  that store's owner, so re-parenting a child before the old owner drops it does
  not orphan it.
- `App` installs the `AppScope` and **mounts the tree before it measures**
  anything. Measuring first would resolve every lookup against the default light
  theme and size the window for a theme the app never installed.

Together these make `Theme.of`'s premature-lookup warning trustworthy: it fires
only for a genuine `__init__` call, while a deliberately detached widget falls
back to the light default silently. See issues #464, #473 and #476.

#### A theme change repaints; it does not relayout

Light/dark switching — and switching between themes built from different seed
colours — changes only the colour roles. Every size-affecting field
(`text_style`, the card and chip styles) is identical across the pair, so the
theme subscription requests a repaint and deliberately does not invalidate
layout.

### 5. Directory Structure

```text
src/nuiitivet/
├── theme/
│   ├── __init__.py
│   ├── color_role.py
│   ├── theme.py          # Theme with style fields
│   ├── manager.py
│   └── palette.py
├── ui/
│   ├── styles/
│   │   ├── __init__.py
│   │   ├── button.py     # ButtonStyle
│   │   ├── checkbox.py   # CheckboxStyle
│   │   ├── icon.py       # IconStyle
│   │   ├── text.py       # TextTheme (existing)
│   │   └── ...
│   └── widgets/
│       ├── buttons/
│       │   ├── base.py
│       │   ├── filled.py
│       │   └── ...
│       ├── checkbox.py
│       ├── icon.py
│       └── ...
```

## Migration Strategy

### Phase 1: Create style classes

- Extract hardcoded values from `Checkbox` → `CheckboxStyle`
- Extract hardcoded values from `Icon` → `IconStyle`
- Move existing `ButtonStyle` to `ui/styles/`

### Phase 2: Integrate into Theme

- Add style fields to `Theme` dataclass
- Update `Theme.from_seed()` to create default styles
- Add M3 variant factories (filled, outlined, text, etc.)

### Phase 3: Update widgets

- Remove hardcoded values from widget constructors
- Accept optional `style` parameter
- Fall back to `manager.current.{widget}_style`

### Phase 4: Public API

- Export all styles from `nuiitivet.ui.styles`
- Document style customization patterns
- Provide examples in samples/

## Benefits

✅ **Consistency**: All widgets follow the same style pattern
✅ **Themeable**: Styles live in Theme, hot-swappable
✅ **Type-safe**: Dataclasses with explicit types
✅ **Flexible**: Easy to override individual properties
✅ **Discoverable**: IDE autocomplete for all style options
✅ **Testable**: Pure data objects, easy to test
✅ **No breaking changes**: Widgets remain backward compatible

## Comparison with Other Frameworks

### Flutter

- Uses immutable `ThemeData` with widget-specific sub-themes (`ButtonThemeData`, etc.)
- Our approach mirrors Flutter's structure

### SwiftUI

- Uses environment values + `.buttonStyle()` modifiers
- We use direct style parameters (more explicit, less magic)

### Material Design 3

- Defines component tokens (container, label, etc.)
- Our `Style` classes map directly to M3 component tokens

## Example: Button Style Presets (Factory-Driven)

Button styles are not stored as separate fields in `Theme`. Instead, `ButtonStyle` provides factory methods that generate M3-compliant presets, and the optional size variant is passed as an argument:

```python
# Filled button (M3 default)
style = ButtonStyle.filled()

# Text button
style = ButtonStyle.text()

# Outlined button
style = ButtonStyle.outlined()

# Size variant (e.g., small)
style = ButtonStyle.filled("s")
```

Usage at the call site:

```python
Button("OK", on_click=handler, style=ButtonStyle.filled())
Button("Cancel", on_click=handler, style=ButtonStyle.text())
```

> **Historical note**: An earlier proposal stored per-variant fields (`filled_button_style`, `text_button_style`, `outlined_button_style`) directly on `Theme` and provided a `button_style_for(variant)` helper. This approach was replaced by the factory-driven design above to keep `Theme` focused on color/typography tokens.
