# Material Widgets

`nuiitivet.material` implements Material Design 3 widgets, with more on the way. This page showcases the available widgets — each with a screenshot and a link to the API reference. Overlay-based widgets (Dialog, BottomSheet, SideSheet, Loading) are covered in [Material Overlay](material_overlay.md).

!!! note "Import convention"
    All widgets shown below are exported from `nuiitivet.material`:

    ```python
    from nuiitivet.material import Button, Card, TextField  # etc.
    ```

---

## Text

Typography component for rendering text with theme-aware styles.

![Text](../assets/material_widgets_text.png)

[API Reference](../api/material.md#nuiitivet.material.Text)

---

## Icon

Material Symbols icon component. Specify a symbol name and an optional size.

![Icon](../assets/material_widgets_icon.png)

[API Reference](../api/material.md#nuiitivet.material.Icon)

---

## Button

Five M3 button styles — Filled, Tonal, Elevated, Outlined, and Text — plus icon support and disabled state.

![Button](../assets/material_widgets_button.png)

[API Reference](../api/material.md#nuiitivet.material.Button)

---

## ToggleButton

Two-state button with selected / unselected appearance. Available in Filled and Outlined styles.

![ToggleButton](../assets/material_widgets_toggle_button.png)

[API Reference](../api/material.md#nuiitivet.material.ToggleButton)

---

## IconButton

Compact icon-only buttons in the standard M3 styles, plus a toggle variant.

![IconButton](../assets/material_widgets_icon_button.png)

[API Reference](../api/material.md#nuiitivet.material.IconButton)

---

## Fab (Floating Action Button)

Prominent action button. Multiple color variants and three sizes (small / medium / large).

![Fab](../assets/material_widgets_fab.png)

[API Reference](../api/material.md#nuiitivet.material.Fab)

---

## ExtendedFab

FAB with a label beside the icon. Toggle its `expanded` observable to morph between the extended pill and a circular FAB. Available in tonal and solid color variants across all three sizes.

![ExtendedFab](../assets/material_widgets_extended_fab.png)

[API Reference](../api/material.md#nuiitivet.material.ExtendedFab)

---

## FabMenu

M3 Expressive FAB menu. A single `is_open` observable morphs the FAB between its `add` and `close` icons and reveals a stack of labelled `FabMenuItem` actions, dismissed by tapping outside or selecting an action.

![FabMenu](../assets/material_widgets_fab_menu.png)

API References: [FabMenu](../api/material.md#nuiitivet.material.FabMenu) ・ [FabMenuItem](../api/material.md#nuiitivet.material.FabMenuItem)

---

## SplitButton

M3 Expressive split button — a leading action button joined to a trailing button that opens a menu. Available in Filled, Tonal, Elevated, and Outlined styles across sizes XS–L.

![SplitButton](../assets/material_widgets_split_button.png)

[API Reference](../api/material.md#nuiitivet.material.SplitButton)

---

## ButtonGroup

Group related actions. `StandardButtonGroup` keeps spacing between buttons; `ConnectedButtonGroup` connects them as a single segmented control.

![ButtonGroup](../assets/material_widgets_button_group.png)

[API Reference](../api/material.md#nuiitivet.material.StandardButtonGroup)

---

## Selection Controls

`Checkbox`, `RadioButton` (typically grouped via `RadioGroup`), and `Switch` for boolean / single-select input.

![Selection Controls](../assets/material_widgets_selection_controls.png)

API References: [Checkbox](../api/material.md#nuiitivet.material.Checkbox) ・ [RadioButton](../api/material.md#nuiitivet.material.RadioButton) ・ [Switch](../api/material.md#nuiitivet.material.Switch)

---

## Slider

Numeric input, split by axis. `HorizontalSlider` / `VerticalSlider` select a value in a range, the `*CenteredSlider` variants are anchored at zero, and the `*RangeSlider` variants select a min/max pair. Horizontal variants are sized with `width`; vertical variants with `height`.

![Slider](../assets/material_widgets_slider.png)

API References: [HorizontalSlider](../api/material.md#nuiitivet.material.HorizontalSlider) ・ [VerticalSlider](../api/material.md#nuiitivet.material.VerticalSlider) ・ [HorizontalCenteredSlider](../api/material.md#nuiitivet.material.HorizontalCenteredSlider) ・ [VerticalCenteredSlider](../api/material.md#nuiitivet.material.VerticalCenteredSlider) ・ [HorizontalRangeSlider](../api/material.md#nuiitivet.material.HorizontalRangeSlider) ・ [VerticalRangeSlider](../api/material.md#nuiitivet.material.VerticalRangeSlider)

---

## TextField

Text input. Available as `FilledTextField` and `OutlinedTextField`, with leading icons, supporting text, and error states.

![TextField](../assets/material_widgets_text_field.png)

[API Reference](../api/material.md#nuiitivet.material.TextField)

---

## Card

Container for grouped content. Three variants — Filled, Outlined, Elevated.

![Card](../assets/material_widgets_card.png)

[API Reference](../api/material.md#nuiitivet.material.Card)

---

## Chip

Compact actions and choices: `AssistChip`, `FilterChip`, `InputChip`, `SuggestionChip`.

![Chip](../assets/material_widgets_chip.png)

API References: [AssistChip](../api/material.md#nuiitivet.material.AssistChip) ・ [FilterChip](../api/material.md#nuiitivet.material.FilterChip) ・ [InputChip](../api/material.md#nuiitivet.material.InputChip) ・ [SuggestionChip](../api/material.md#nuiitivet.material.SuggestionChip)

---

## Badge

Small status indicator that decorates other widgets via a modifier. `SmallBadge` is a dot; `LargeBadge` shows a count.

![Badge](../assets/material_widgets_badge.png)

API References: [SmallBadge](../api/material.md#nuiitivet.material.SmallBadge) ・ [LargeBadge](../api/material.md#nuiitivet.material.LargeBadge)

---

## Divider

Separator line, split by axis. `HorizontalDivider` draws a full-width line (sized with `width`); `VerticalDivider` draws a full-height line (sized with `height`). The cross-axis thickness comes from the style.

![Divider](../assets/material_widgets_divider.png)

API References: [HorizontalDivider](../api/material.md#nuiitivet.material.HorizontalDivider) ・ [VerticalDivider](../api/material.md#nuiitivet.material.VerticalDivider)

---

## Progress Indicators

Linear and circular progress, in determinate and indeterminate variants. `LoadingIndicator` is the M3 Expressive shape-morphing indicator.

![Progress Indicators](../assets/material_widgets_progress.png)

API References: [LinearProgressIndicator](../api/material.md#nuiitivet.material.LinearProgressIndicator) ・ [CircularProgressIndicator](../api/material.md#nuiitivet.material.CircularProgressIndicator) ・ [LoadingIndicator](../api/material.md#nuiitivet.material.LoadingIndicator)

---

## NavigationRail

Vertical navigation bar with collapsed / expanded states, badges, and an optional menu button. Pairs with [Material Navigator](material_navigator.md) for routing.

![NavigationRail](../assets/material_widgets_navigation_rail.png)

[API Reference](../api/material.md#nuiitivet.material.NavigationRail)

---

## Toolbar

Action bar of icon buttons. `DockedToolbar` stretches to its container; `HorizontalFloatingToolbar` / `VerticalFloatingToolbar` are pill-shaped overlays laid out along their respective axis.

![Toolbar](../assets/material_widgets_toolbar.png)

API References: [DockedToolbar](../api/material.md#nuiitivet.material.DockedToolbar) ・ [HorizontalFloatingToolbar](../api/material.md#nuiitivet.material.HorizontalFloatingToolbar) ・ [VerticalFloatingToolbar](../api/material.md#nuiitivet.material.VerticalFloatingToolbar)

---

## Menu

Vertical list of `MenuItem`s. Supports leading icons, trailing shortcut/affordance text, dividers, and disabled items.

![Menu](../assets/material_widgets_menu.png)

[API Reference](../api/material.md#nuiitivet.material.Menu)

---

## Tooltip

Contextual hint shown next to a target. `Tooltip` is a plain text label; `RichTooltip` supports a title, body, and action buttons.

![Tooltip](../assets/material_widgets_tooltip.png)

API References: [Tooltip](../api/material.md#nuiitivet.material.Tooltip) ・ [RichTooltip](../api/material.md#nuiitivet.material.RichTooltip)

---

## StandardSideSheet

Docked side panel that sits beside the main content area. Unlike the modal `SideSheet`, it is a permanent part of the layout. Wrap it in `Collapsible` (with `axis="horizontal"`) to animate it open and closed without any additional API on the sheet itself.

```python
Collapsible(
    StandardSideSheet(
        panel_content,
        headline="Filters",
        on_close=vm.close_panel,
    ),
    opened=vm.panel_open,
    axis="horizontal",
    alignment="top_right",
)
```

![StandardSideSheet](../assets/material_widgets_standard_side_sheet.png)

[API Reference](../api/material.md#nuiitivet.material.StandardSideSheet)

---

## DockedDatePicker

Inline calendar that always stays visible (not a dialog). It writes the selected `datetime.date` back to a shared observable and supports `min_date` / `max_date` bounds.

![DockedDatePicker](../assets/material_widgets_date_picker.png)

[API Reference](../api/material.md#nuiitivet.material.DockedDatePicker)

---

## Image

`Image` is a primitive widget that is not part of Material Design. Displays a raster image from in-memory bytes. Supports `contain`, `cover`, `fill`, and `none` fit modes.

![Image](../assets/material_widgets_image.png)

[API Reference](../api/widgets.md#nuiitivet.widgets.image.Image)
