# Menu Widget — API Proposal

> Issue #33 · Branch: `feat/33-menu-widget`

---

## Overview

Material Design 3 **Vertical Menu** (dropdown-style) widget.  
Menus display a list of choices on a temporary elevated surface anchored to a trigger widget.
Vertical menus are the recommended variant for new designs, featuring rounded corners, standard/vibrant color styles, and richer selection states.

> Baseline variant is out of scope — it uses outdated square corners and is not recommended for new products.

Reference: [M3 Menus Specs](https://m3.material.io/components/menus/specs)

---

## Scope

| Target | Description |
|--------|-------------|
| `MenuItem` | Interactive single menu list item |
| `SubMenuItem` | Menu item that reveals a nested submenu |
| `MenuDivider` | Sentinel for group separator |
| `Menu` | Popup surface containing item list |
| `MenuStyle` | Frozen style dataclass |

Out of scope: Tooltip, Baseline variant.

---

## M3 Vertical Menu Measurements

| Property | Value |
|----------|-------|
| Container width | 112 dp min / 280 dp max |
| Corner radius | 12 dp (fully rounded, M3 Expressive) |
| List item height | 48 dp |
| Left/right padding | 12 dp |
| Padding between elements within item | 12 dp |
| Divider top/bottom padding | 8 dp |
| Divider height | 1 dp |
| Icon size (leading/trailing) | 24 dp |

---

## M3 Vertical Menu Color Roles

### Standard

| Element | Token |
|---------|-------|
| Container background | `Surface Container Low` |
| Item label text | `On Surface` |
| Leading/trailing icon | `On Surface Variant` |
| Trailing text | `On Surface Variant` |
| State layer | `On Surface` |
| State layer opacity (hover) | 0.08 |
| State layer opacity (pressed) | 0.12 |
| Selected item background | `Tertiary Container` |
| Selected item foreground | `On Tertiary Container` |
| Divider | `Outline Variant` |

### Vibrant

| Element | Token |
|---------|-------|
| Container background | `Tertiary Container` |
| Item label text | `On Tertiary Container` |
| Leading/trailing icon | `On Tertiary Container` |
| Trailing text | `On Tertiary Container` |
| State layer | `On Tertiary Container` |
| Selected item background | `Tertiary` |
| Selected item foreground | `On Tertiary` |

---

## Class: `MenuStyle`

カラースキームは `standard()` / `vibrant()` クラスメソッドで切り替える（ButtonStyle と同様のパターン）。

```python
@dataclass(frozen=True)
class MenuStyle:
    """Immutable style for Material Design 3 Vertical Menu widgets."""

    # Container
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_LOW
    corner_radius: int = 12
    min_width: int = 112
    max_width: int = 280
    container_vertical_padding: int = 8  # top/bottom inset of the menu surface

    # MenuItem
    item_height: int = 48
    item_horizontal_padding: int = 12   # left / right
    item_spacing: int = 12              # gap between icon and label
    icon_size: int = 24
    label_color: ColorSpec = ColorRole.ON_SURFACE
    icon_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    trailing_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    disabled_color: ColorSpec = ColorRole.ON_SURFACE   # opacity 0.38 applied internally

    # Interaction
    state_layer_color: ColorSpec = ColorRole.ON_SURFACE
    hover_alpha: float = 0.08
    pressed_alpha: float = 0.12

    # Selected state
    selected_background: ColorSpec = ColorRole.TERTIARY_CONTAINER
    selected_foreground: ColorSpec = ColorRole.ON_TERTIARY_CONTAINER

    # Divider (resolved via existing DividerStyle; stored here for Menu to pass)
    divider_color: ColorSpec = ColorRole.OUTLINE_VARIANT
    divider_vertical_padding: int = 8

    def copy_with(self, **changes) -> "MenuStyle": ...

    @classmethod
    def standard(cls) -> "MenuStyle":
        """Standard (surface-based) color scheme."""
        return cls()  # defaults are standard

    @classmethod
    def vibrant(cls) -> "MenuStyle":
        """Vibrant (tertiary-based) color scheme for higher visual emphasis."""
        return cls(
            background=ColorRole.TERTIARY_CONTAINER,
            label_color=ColorRole.ON_TERTIARY_CONTAINER,
            icon_color=ColorRole.ON_TERTIARY_CONTAINER,
            trailing_text_color=ColorRole.ON_TERTIARY_CONTAINER,
            state_layer_color=ColorRole.ON_TERTIARY_CONTAINER,
            selected_background=ColorRole.TERTIARY,
            selected_foreground=ColorRole.ON_TERTIARY,
        )

    @classmethod
    def from_theme(cls, theme: "Theme", variant: str = "standard") -> "MenuStyle": ...
```

---

## Class: `MenuItem`

```python
class MenuItem(InteractiveWidget):
    """Material Design 3 Menu list item.

    A single interactive row within a Menu. Supports an optional leading icon,
    a trailing icon OR trailing text (mutually exclusive), and a disabled state.
    """

    def __init__(
        self,
        label: str,                                    # 1. Content (positional)
        *,
        on_click: Callable[[], None] | None = None,   # 2. Config — handler
        disabled: bool = False,                        # 2. Config — state
        leading_icon: Symbol | str | None = None,      # 2. Config — decoration
        trailing: Symbol | str | None = None,          # 2. Config — Symbol: icon / str: shortcut text
        height: SizingLike = None,                     # 3. Layout
    ) -> None: ...
```

### Notes

- Inherits from `InteractiveWidget` → gets focus ring, state layer, standard key bindings.
- Height defaults to `style.item_height` (48 dp).
- Width fills the containing `Menu` (determined by `Menu`, not `MenuItem`).
  - `width` パラメータは持たない。幅は常に親 `Menu` に委ねる。
- `style` パラメータは持たない。スタイルは親 `Menu` の `MenuStyle` を継承する。
- `leading_icon` is rendered at `style.icon_size` (24 dp).
- `trailing` は `Symbol | str` の Union 型。`Symbol` ならアイコン（24 dp）、`str` ならショートカットヒントなど右寄せテキストとして描画する。
- When `disabled=True`, label and icons are rendered at 38 % opacity; interaction is suppressed.

---

## Class: `Menu`

```python
class Menu(Widget):
    """Material Design 3 Vertical Menu popup surface.

    Renders a list of MenuItem / Divider widgets on a temporary elevated
    surface. Keyboard navigation (Up / Down / Enter / Escape) is handled
    internally. Dismiss is triggered by Escape key or externally via
    on_dismiss.
    """

    def __init__(
        self,
        items: list[MenuItem | SubMenuItem | MenuDivider],  # 1. Content (positional)
        *,
        on_dismiss: Callable[[], None] | None = None,  # 2. Config — handler
        style: MenuStyle | None = None,                # 4. Style
    ) -> None: ...
```

### Notes

- `items` はフラットなリスト。`MenuDivider` を挿入することでグループ区切りを表現する。`SubMenuItem` も混在可能。
- Width は `style.min_width` ～ `style.max_width` で自動決定される。
  - 明示的な `width` パラメータは持たない。幅は children の最大幅をベースに `[min_width, max_width]` でクランプする。
- The surface renders as a `Box` with `corner_radius` and `background`.
- Keyboard navigation moves a focus cursor within the item list; focused item receives standard focus-ring treatment.
- `Escape` key calls `on_dismiss`.

---

## Class: `MenuDivider`

`items` リスト内に置くことで区切り線を表現する軽量 sentinel クラス。Widget ではない。
`Menu` が内部で `Divider` + `divider_vertical_padding` を生成する。

```python
class MenuDivider:
    """Sentinel that renders a horizontal divider inside a Menu.

    Not a Widget. Menu interprets this object and renders a Divider
    with divider_vertical_padding applied on top and bottom.
    """
    pass
```

```python
Menu(items=[
    MenuItem("Cut"),
    MenuItem("Copy"),
    MenuDivider(),
    MenuItem("Paste"),
])
```

---

## Usage Example

```python
from nuiitivet.material import FilledButton, Menu, MenuItem, MenuDivider, SubMenuItem
from nuiitivet.modifiers.popup import light_dismiss
from nuiitivet.observable.value import Observable

is_open: Observable[bool] = Observable(False)

menu = Menu(
    items=[
        MenuItem("New",      on_click=lambda: print("New")),
        MenuItem("Open...",  on_click=lambda: print("Open")),
        MenuDivider(),
        MenuItem("Save",     leading_icon="save", on_click=lambda: print("Save")),
        MenuItem("Save As...", trailing="Shift+Ctrl+S", disabled=True),
        SubMenuItem("Export", items=[
            MenuItem("PNG",  on_click=lambda: print("PNG")),
            MenuItem("SVG",  on_click=lambda: print("SVG")),
        ]),
        MenuDivider(),
        MenuItem("Exit",     on_click=lambda: print("Exit")),
    ],
    on_dismiss=lambda: setattr(is_open, "value", False),
)

trigger = FilledButton(
    "File",
    on_click=lambda: setattr(is_open, "value", not is_open.value),
).modifier(
    light_dismiss(menu, is_open=is_open, alignment="bottom-left", anchor="top-left")
)
```

---

## Class: `SubMenuItem`

```python
class SubMenuItem(InteractiveWidget):
    """Material Design 3 submenu item.

    A menu item that reveals a nested Menu on hover or focus.
    Displays a trailing chevron-right icon automatically.
    Does not accept on_click — interaction is reserved for submenu expansion.
    """

    def __init__(
        self,
        label: str,                                              # 1. Content (positional)
        items: list[MenuItem | SubMenuItem | MenuDivider],       # 1. Content (positional)
        *,
        leading_icon: Symbol | str | None = None,                # 2. Config — decoration
        disabled: bool = False,                                  # 2. Config — state
        height: SizingLike = None,                               # 3. Layout
    ) -> None: ...
```

### Notes

- Trailing に展開矢印アイコン（`chevron_right`）を自動表示する。
- ホバーまたはフォーカス時に `items` から生成した子 `Menu` を右側に `light_dismiss=False` で展開する。
- `disabled=True` の場合は展開しない。
- 子 `Menu` の `on_dismiss` は親 `Menu` の dismiss に連鎖する。
- 再帰的に `SubMenuItem` をネスト可能（多段サブメニュー）。
- `style` パラメータは持たない。スタイルは親 `Menu` の `MenuStyle` を継承する。

---

## File Layout

```
src/nuiitivet/material/
    menu.py                         # MenuItem, SubMenuItem, MenuDivider, Menu
    styles/
        menu_style.py               # MenuStyle

tests/
    test_menu.py                    # Unit tests

src/samples/
    menu_demo.py                    # Interactive sample
```

---

## Exports

`src/nuiitivet/material/__init__.py` additions:

```python
from .menu import Menu, MenuDivider, MenuItem, SubMenuItem
```

`__all__` additions: `"Menu"`, `"MenuDivider"`, `"MenuItem"`, `"SubMenuItem"`

---

## Checklist (aligned with Issue #33)

- [ ] `MenuItem` — interactive list item with leading/trailing icon, trailing text, disabled
- [ ] `SubMenuItem` — menu item with nested submenu expansion
- [ ] `MenuDivider` — sentinel for group separator
- [ ] `Menu` — popup surface with keyboard navigation
- [ ] `MenuStyle` — frozen dataclass with `standard()` / `vibrant()` / `from_theme()`
- [ ] Unit tests (`tests/test_menu.py`)
- [ ] Sample (`src/samples/menu_demo.py`) using `light_dismiss()` modifier
- [ ] Exports in `material/__init__.py`
