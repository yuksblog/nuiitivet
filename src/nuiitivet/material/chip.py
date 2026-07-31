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
from nuiitivet.theme.theme import Theme
from nuiitivet.theme.type_scale import TypeScale
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.material.styles.chip_style import ChipStyle
    from nuiitivet.material.symbols import Symbol


def _chip_text(
    label: str | ReadOnlyObservableProtocol[str],
    color: ColorSpec,
) -> Text:
    return Text(
        label,
        style=TextStyle(color=color),
        type_scale=TypeScale.LABEL_LARGE,
        alignment="center",
    )


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
    """Base class for Material Design 3 chip widgets.

    Subclasses hold their own content inputs (label, icons, selection) and
    implement :meth:`_build_content`, which the base calls whenever the
    effective style changes. Content is therefore rebuilt — not merely
    recoloured — when the theme supplies a different chip style.
    """

    _variant: str = "assist"

    def __init__(
        self,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["ChipStyle"] = None,
    ):
        """Initialize base chip.

        Args:
            on_click: Click callback.
            disabled: Disabled flag.
            width: Width sizing.
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        from nuiitivet.material.styles.chip_style import ChipStyle

        self._user_style = style
        # The theme is unreachable until the chip is attached, so resolving it
        # here would pin the light default. Build with the variant preset; the
        # real style is pulled in :attr:`style` once the chip can reach a theme.
        initial_style = style if style is not None else ChipStyle.preset(self._variant)
        self._effective_style: "ChipStyle" = initial_style
        # Chip height is MD3-fixed (container_height token) -> style only.
        content_padding = padding if padding is not None else 0

        super().__init__(
            child=self._build_content(initial_style),
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=int(initial_style.container_height),
            padding=content_padding,
            background_color=initial_style.background,
            border_color=initial_style.border_color,
            border_width=initial_style.border_width,
            corner_radius=initial_style.corner_radius,
            state_layer_color=initial_style.state_layer_color,
        )

        self._HOVER_OPACITY = initial_style.hover_alpha
        self._PRESS_OPACITY = initial_style.pressed_alpha
        self._DRAG_OPACITY = initial_style.drag_alpha
        self._on_style_applied(initial_style)

    # --- Theme integration ----------------------------------------------------
    def _resolve_style(self) -> "ChipStyle":
        """Resolve the style this chip should be showing.

        A chip has no ``build()``, so it reads the theme where the style is
        consumed. The read registers a dependency, so a theme change re-measures
        and repaints this chip and lands back here with the new value.

        Returns:
            The explicit ``style`` when one was given, otherwise the variant's
            style resolved from the current theme.
        """
        if self._user_style is not None:
            return self._user_style
        from nuiitivet.material.styles.chip_style import ChipStyle

        return ChipStyle.from_theme(Theme.of(self), self._variant)

    @property
    def style(self) -> "ChipStyle":
        """Return the style currently in effect, pulled from the theme.

        The container visuals a chip hands to :class:`Box` -- background, border,
        corner radius, fixed height -- and its content subtree are derived from
        the style rather than re-derived on every read, so they are re-applied
        here whenever the resolved style has moved. That makes the pushed
        properties a write-through cache of this pull, never a value that can go
        stale on its own.
        """
        style = self._resolve_style()
        if style != self._effective_style:
            self._apply_chip_style(style)
        return style

    def _refresh_chip_style(self) -> None:
        """Re-apply the resolved style, rebuilding the content.

        Used when something other than the theme changed the visuals -- chiefly
        selection, which :meth:`_on_style_applied` layers over the base style.
        """
        self._apply_chip_style(self._resolve_style())

    def _apply_chip_style(self, style: "ChipStyle") -> None:
        """Push ``style`` onto the container visuals and rebuild the content."""
        from nuiitivet.rendering.sizing import Sizing

        self._effective_style = style
        self.height_sizing = Sizing.fixed(int(style.container_height))
        self.bgcolor = style.background
        self.border_color = style.border_color
        self.border_width = style.border_width
        self.corner_radius = style.corner_radius
        self.state_layer_color = style.state_layer_color
        self._HOVER_OPACITY = style.hover_alpha
        self._PRESS_OPACITY = style.pressed_alpha
        self._DRAG_OPACITY = style.drag_alpha

        content = self._build_content(style)
        self.clear_children()
        self.add_child(content)
        self._on_style_applied(style)
        self.invalidate()

    def _build_content(self, style: "ChipStyle") -> Widget:
        """Build the chip's content subtree for ``style``.

        Called from ``__init__`` (with the preset) and again whenever the
        effective style changes, so it must only read constructor inputs the
        subclass has already stored.
        """
        raise NotImplementedError

    def _on_style_applied(self, style: "ChipStyle") -> None:
        """Hook for subclasses to layer state-dependent visuals over ``style``.

        Runs after every style application, including the initial one.
        """

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
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._label = label
        self._leading_icon = leading_icon

        super().__init__(
            on_click=on_click,
            disabled=disabled,
            width=width,
            padding=padding,
            style=style,
        )

    def _build_content(self, style: "ChipStyle") -> Widget:
        children: list[Widget] = []
        if self._leading_icon is not None:
            children.append(_chip_icon(self._leading_icon, color=style.foreground))
        children.append(_chip_text(self._label, style.foreground))

        return _chip_content(
            children,
            spacing=style.spacing,
            has_icon=self._leading_icon is not None,
            style=style,
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

        super().__init__(
            on_click=self._handle_click,
            disabled=disabled,
            width=width,
            padding=padding,
            style=style,
        )

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
        self._refresh_chip_style()

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
        self._refresh_chip_style()

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

    def _on_style_applied(self, style: "ChipStyle") -> None:
        """Layer the selected-state container colours over the base style."""
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
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._label = label
        self._leading_icon = leading_icon
        self._trailing_icon = trailing_icon
        self._on_trailing_icon_click = on_trailing_icon_click
        self._trailing_icon_widget: Optional[Icon] = None
        self._trailing_icon_tap_target: Optional[Widget] = None

        super().__init__(
            on_click=on_click,
            disabled=disabled,
            width=width,
            padding=padding,
            style=style,
        )

    def _build_content(self, style: "ChipStyle") -> Widget:
        children: list[Widget] = []
        if self._leading_icon is not None:
            children.append(_chip_icon(self._leading_icon, color=style.foreground))
        children.append(_chip_text(self._label, style.foreground))

        trailing_icon_widget = _chip_icon(self._trailing_icon, color=style.foreground)
        self._trailing_icon_widget = trailing_icon_widget
        if self._on_trailing_icon_click is None:
            self._trailing_icon_tap_target = trailing_icon_widget
            children.append(trailing_icon_widget)
        else:
            trailing_icon_button = InteractiveWidget(
                child=trailing_icon_widget,
                on_click=self._on_trailing_icon_click,
                focusable=True,
                padding=0,
                corner_radius=999,
                state_layer_color=style.state_layer_color,
            )
            self._trailing_icon_tap_target = trailing_icon_button
            children.append(trailing_icon_button)

        return _chip_content(children, spacing=style.spacing, has_icon=True, style=style)


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
            padding: External insets around chip widget.
            style: Optional chip style.
        """
        self._label = label
        self._leading_icon = leading_icon

        super().__init__(
            on_click=on_click,
            disabled=disabled,
            width=width,
            padding=padding,
            style=style,
        )

    def _build_content(self, style: "ChipStyle") -> Widget:
        children: list[Widget] = []
        if self._leading_icon is not None:
            children.append(_chip_icon(self._leading_icon, color=style.foreground))
        children.append(_chip_text(self._label, style.foreground))

        return _chip_content(
            children,
            spacing=style.spacing,
            has_icon=self._leading_icon is not None,
            style=style,
        )


__all__ = ["AssistChip", "FilterChip", "InputChip", "SuggestionChip"]
