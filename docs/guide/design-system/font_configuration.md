# Font Configuration

nuiitivet uses system-installed fonts by default. This guide covers how to
load custom font files and reference them by family name throughout your
application.

## System fonts

`set_default_font_family()` sets the global fallback used when no
`font_family` is specified:

```python
import nuiitivet

# macOS
nuiitivet.set_default_font_family("Hiragino Sans")
# Windows
# nuiitivet.set_default_font_family("Yu Gothic")
```

Pass `None` to reset to locale-based automatic detection.

## Bundled fonts with `register_font()`

When distributing an application with bundled `.ttf` / `.otf` files, use
`register_font()` to make them available by name.

```python
import nuiitivet

# Call once at startup, before any UI is created.
nuiitivet.register_font("assets/fonts/NotoSansJP.ttf", family_name="NotoSansJP")
```

After registration the family name can be used anywhere a `font_family` is
accepted:

```python
from nuiitivet.material import Text, Icon
from nuiitivet.material.styles import TextStyle

# Text widget
Text("Hello", style=TextStyle(font_family="NotoSansJP"))

# Icon widget with a custom icon font
from nuiitivet.material.styles import IconStyle
nuiitivet.register_font("assets/fonts/MyIcons.ttf", family_name="MyIcons")
Icon("star", style=IconStyle(custom_font_family="MyIcons"))
```

### Notes

- `register_font()` only stores the mapping; the font file is loaded lazily
  on first use and cached for the lifetime of the process.
- Call `register_font()` **before** any widget is rendered. Calling it after
  rendering has started may produce stale cache results because resolved
  typefaces are cached per family name.
- Relative paths are resolved relative to the working directory at call time.
  Use `pathlib.Path(__file__).parent / "..."` for paths relative to your
  source files.

```python
from pathlib import Path
import nuiitivet

_ASSETS = Path(__file__).parent / "assets" / "fonts"
nuiitivet.register_font(str(_ASSETS / "NotoSansJP.ttf"), family_name="NotoSansJP")
```
