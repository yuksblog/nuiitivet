"""Material Design 3 Chip widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Tuple, Union, cast

from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material.icon import Icon
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.material.styles.chip_style import ChipStyle
    from nuiitivet.material.symbols import Symbol


def _resolve_fixed_height(height: SizingLike, fallback: int) -> int:
    if isinstance(height, (int, float)):
        return int(height)
    if height is None:
        return int(fallback)
    try:
        from nuiitivet.rendering.sizing import parse_sizing

        parsed = parse_sizing(height, default=None)
        if parsed.kind == "fixed":
            return int(parsed.value)
    except Exception:
        pass
    return int(fallback)


def _chip_text(
    label: str | ReadOnlyObservableProtocol[str],
    color: ColorSpec,
) -> Text:
    return Text(label, style=TextStyle(font_size=14, color=color, text_alignment="center"))


def _chip_icon(
    name: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
    *,
    color: ColorSpec,
) -> Icon:
    return Icon(name, size=18, style=IconStyle(color=color))


def _default_inner_padding(has_icon: bool) -> tuple[int, int, int, int]:
    if has_icon:
        return (8, 0, 8, 0)
    return (16, 0, 16, 0)


def _chip_content(
    children: list[Widget],
    *,
    spacing: int,
    has_icon: bool,
    style: "ChipStyle",
) -> Container:
    row = Row(children, gap=spacing, cross_alignment="center")

    inner_padding: tuple[int, int, int, int]
    if style.padding == (8, 0, 8, 0):
        inner_padding = _default_inner_padding(has_icon)
    else:
        inner_padding = style.padding

    return Container(child=row, padding=inner_padding, alignment="center")


class MaterialChipBase(InteractiveWidget):
    """Base class for Material Design 3 chip widgets."""

    _variant: str = "assist"

    def __init__(
        self,
        child: Widget,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize base chip.

        Args:
            child: Chip content widget.
            on_click: Click callback.
            disabled: Disabled flag.
            width: Width sizing.
            height: Height sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._user_style = style
        effective_style = self.style
        resolved_height = _resolve_fixed_height(height, effective_style.container_height)
        content_padding = padding if padding is not None else 0

        super().__init__(
            child=child,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=resolved_height,
            padding=content_padding,
            background_color=effective_style.background,
            border_color=effective_style.border_color,
            border_width=effective_style.border_width,
            corner_radius=effective_style.corner_radius,
            state_layer_color=effective_style.state_layer_color,
        )

        self._HOVER_OPACITY = effective_style.hover_alpha
        self._PRESS_OPACITY = effective_style.pressed_alpha
        self._DRAG_OPACITY = effective_style.drag_alpha

    @property
    def style(self) -> "ChipStyle":
        """Resolve chip style from explicit style or current theme."""
        if self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.styles.chip_style import ChipStyle

        return ChipStyle.from_theme(manager.current, self._variant)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
        """Return preferred size clamped to style minimum touch-target size."""
        w, h = super().preferred_size(max_width=max_width, max_height=max_height)
        style = self.style

        if getattr(self.width_sizing, "kind", None) != "fixed":
            w = max(int(w), int(style.min_width))
        if getattr(self.height_sizing, "kind", None) != "fixed":
            h = max(int(h), int(style.min_height))

        if max_width is not None:
            w = min(int(w), int(max_width))
        if max_height is not None:
            h = min(int(h), int(max_height))

        return int(w), int(h)


class AssistChip(MaterialChipBase):
    """Material Design 3 Assist Chip widget."""

    _variant = "assist"

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str],
        *,
        leading_icon: (
            "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize AssistChip.

        Args:
            label: Chip label.
            leading_icon: Optional leading icon.
            on_click: Click callback.
            disabled: Disabled flag.
            width: Width sizing.
            height: Height sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        effective_style = style
        if effective_style is None:
            from nuiitivet.theme.manager import manager
            from nuiitivet.material.styles.chip_style import ChipStyle

            effective_style = ChipStyle.from_theme(manager.current, self._variant)

        children: list[Widget] = []
        if leading_icon is not None:
            children.append(_chip_icon(leading_icon, color=effective_style.foreground))
        children.append(_chip_text(label, effective_style.foreground))

        content = _chip_content(
            children,
            spacing=effective_style.spacing,
            has_icon=leading_icon is not None,
            style=effective_style,
        )

        super().__init__(
            child=content,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=effective_style,
        )


class FilterChip(MaterialChipBase):
    """Material Design 3 Filter Chip widget."""

    _variant = "filter"

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str],
        *,
        selected: bool | ObservableProtocol[bool] = False,
        on_selected_change: Optional[Callable[[bool], None]] = None,
        leading_icon: (
            "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize FilterChip.

        Args:
            label: Chip label.
            selected: Selected state source.
            on_selected_change: Callback when selected state changes.
            leading_icon: Optional leading icon in unselected state.
            on_click: Additional click callback.
            disabled: Disabled flag.
            width: Width sizing.
            height: Height sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._selected_external: ObservableProtocol[bool] | None = None
        self._selected = bool(selected)
        self._label = label
        if hasattr(selected, "subscribe") and hasattr(selected, "value"):
            self._selected_external = cast("ObservableProtocol[bool]", selected)
            self._selected = bool(self._selected_external.value)

        self._base_on_click = on_click
        self._on_selected_change = on_selected_change
        self._leading_icon = leading_icon

        effective_style = style
        if effective_style is None:
            from nuiitivet.theme.manager import manager
            from nuiitivet.material.styles.chip_style import ChipStyle

            effective_style = ChipStyle.from_theme(manager.current, self._variant)

        content = self._build_content(effective_style)

        super().__init__(
            child=content,
            on_click=self._handle_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=effective_style,
        )

        self._apply_selected_visuals()

    @property
    def selected(self) -> bool:
        """Return current selected state."""
        return bool(self._selected)

    def on_mount(self) -> None:
        super().on_mount()
        if self._selected_external is not None:
            self.observe(self._selected_external, lambda _value: self._sync_selected_from_external())

    def _sync_selected_from_external(self) -> None:
        if self._selected_external is None:
            return
        next_value = bool(self._selected_external.value)
        if self._selected == next_value:
            return
        self._selected = next_value
        self._rebuild_content()
        self._apply_selected_visuals()

    def _handle_click(self) -> None:
        if self.disabled:
            return

        next_value = not self._selected
        if self._selected_external is not None:
            try:
                self._selected_external.value = next_value
            except Exception:
                pass

        self._selected = next_value
        self._rebuild_content()
        self._apply_selected_visuals()

        if self._on_selected_change is not None:
            self._on_selected_change(next_value)
        if self._base_on_click is not None:
            self._base_on_click()

    def _build_content(self, style: "ChipStyle") -> Container:
        children: list[Widget] = []
        has_icon = False
        if self._selected:
            children.append(_chip_icon("check", color=style.selected_foreground or style.foreground))
            has_icon = True
        elif self._leading_icon is not None:
            children.append(_chip_icon(self._leading_icon, color=style.foreground))
            has_icon = True
        children.append(_chip_text(self._label, style.selected_foreground or style.foreground))
        return _chip_content(children, spacing=style.spacing, has_icon=has_icon, style=style)

    def _rebuild_content(self) -> None:
        style = self.style
        content = self._build_content(style)
        self.clear_children()
        self.add_child(content)
        self.invalidate()

    def _apply_selected_visuals(self) -> None:
        style = self.style
        if self._selected:
            self.bgcolor = style.selected_background or style.background
            self.border_color = style.selected_border_color or style.border_color
        else:
            self.bgcolor = style.background
            self.border_color = style.border_color


class InputChip(MaterialChipBase):
    """Material Design 3 Input Chip widget."""

    _variant = "input"

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str],
        *,
        trailing_icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
        leading_icon: (
            "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        on_trailing_icon_click: Optional[Callable[[], None]] = None,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize InputChip.

        Args:
            label: Chip label.
            trailing_icon: Required trailing icon.
            leading_icon: Optional leading icon.
            on_trailing_icon_click: Callback invoked when trailing icon is pressed.
            on_click: Click callback.
            disabled: Disabled flag.
            width: Width sizing.
            height: Height sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._on_trailing_icon_click = on_trailing_icon_click
        self._trailing_icon_widget: Optional[Icon] = None
        self._trailing_icon_tap_target: Optional[Widget] = None

        effective_style = style
        if effective_style is None:
            from nuiitivet.theme.manager import manager
            from nuiitivet.material.styles.chip_style import ChipStyle

            effective_style = ChipStyle.from_theme(manager.current, self._variant)

        children: list[Widget] = []
        if leading_icon is not None:
            children.append(_chip_icon(leading_icon, color=effective_style.foreground))
        children.append(_chip_text(label, effective_style.foreground))
        trailing_icon_widget = _chip_icon(trailing_icon, color=effective_style.foreground)
        self._trailing_icon_widget = trailing_icon_widget
        if on_trailing_icon_click is None:
            self._trailing_icon_tap_target = trailing_icon_widget
            children.append(trailing_icon_widget)
        else:
            trailing_icon_button = InteractiveWidget(
                child=trailing_icon_widget,
                on_click=on_trailing_icon_click,
                focusable=True,
                padding=0,
                corner_radius=999,
                state_layer_color=effective_style.state_layer_color,
            )
            self._trailing_icon_tap_target = trailing_icon_button
            children.append(trailing_icon_button)

        content = _chip_content(children, spacing=effective_style.spacing, has_icon=True, style=effective_style)

        super().__init__(
            child=content,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=effective_style,
        )


class SuggestionChip(MaterialChipBase):
    """Material Design 3 Suggestion Chip widget."""

    _variant = "suggestion"

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str],
        *,
        leading_icon: (
            "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize SuggestionChip.

        Args:
            label: Chip label.
            leading_icon: Optional leading icon.
            on_click: Click callback.
            disabled: Disabled flag.
            width: Width sizing.
            height: Height sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        effective_style = style
        if effective_style is None:
            from nuiitivet.theme.manager import manager
            from nuiitivet.material.styles.chip_style import ChipStyle

            effective_style = ChipStyle.from_theme(manager.current, self._variant)

        children: list[Widget] = []
        if leading_icon is not None:
            children.append(_chip_icon(leading_icon, color=effective_style.foreground))
        children.append(_chip_text(label, effective_style.foreground))

        content = _chip_content(
            children,
            spacing=effective_style.spacing,
            has_icon=leading_icon is not None,
            style=effective_style,
        )

        super().__init__(
            child=content,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=effective_style,
        )


__all__ = ["AssistChip", "FilterChip", "InputChip", "SuggestionChip"]
