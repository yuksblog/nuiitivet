"""Material Design 3 Expressive FAB Menu (:class:`FabMenu` / :class:`FabMenuItem`).

A :class:`FabMenu` is a Floating Action Button that expands into a vertical
list of labelled actions and morphs its icon between the closed and open
states.  It is delivered as a single high-level widget so the FAB morph, the
staggered reveal of items, and the dismissal scrim are all driven by one
``is_open`` observable.

The widget reuses existing infrastructure:

- The morphing FAB is an internal :class:`~nuiitivet.material.buttons.Fab`
  whose icon is *bound* to ``is_open`` -- there is no separate toggle state.
- The overlay (scrim, outside-tap dismissal, anchored positioning) comes from
  the existing :func:`~nuiitivet.modifiers.popup.light_dismiss` modifier.

Geometry and colour values follow ``docs/md3/fab-menu.md``: the close button
uses a solid/tonal FAB colour, list items use the matching ``*-container``
colour set, items are 56dp fully-rounded pills with 24/8/24 internal spacing
and a 4dp gap between items, and elevation rises to level-4 on hover and
level-3 on focus/press.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Union

from nuiitivet.animation import Animatable
from nuiitivet.common.logging_once import warning_once
from nuiitivet.layout.measure import preferred_size as _measure_preferred_size
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL
from nuiitivet.material.icon import IconLike
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.material.symbols import Symbols
from nuiitivet.material.text import LabelLike
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.modifiers.popup import light_dismiss
from nuiitivet.modifiers.transform import opacity, translate
from nuiitivet.observable import Observable, ObservableProtocol
from nuiitivet.observable import runtime
from nuiitivet.widgeting.callbacks import VoidCallback, invoke_event_handler
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol


logger = logging.getLogger(__name__)


# Vertical distance (px) each item slides up while fading in.
_ITEM_REVEAL_RISE = 16.0
# Per-item stagger between consecutive reveals (seconds).
_ITEM_REVEAL_STAGGER = 0.05

# The opened FAB-menu close button is always size "s": a 56dp fully-rounded
# circle, regardless of the closed FAB size.  Larger closed FABs therefore
# shrink to this size and align their top edge, leaving a larger bottom margin.
_OPEN_FAB_SIZE = 56.0
_OPEN_FAB_CORNER = 28.0

# md.comp.fab-menu.close-button.between-space: gap between the close button and
# the adjacent menu item.
_CLOSE_BUTTON_BETWEEN_SPACE = 8.0
# md.comp.fab-menu.menu-item.between-space: gap between consecutive menu items.
_MENU_ITEM_BETWEEN_SPACE = 4


@dataclass(frozen=True)
class FabMenuItem:
    """Declarative spec for a single action inside a :class:`FabMenu`.

    Args:
        icon: Leading icon shown in the menu-item pill.
        label: Text label rendered next to the icon.
        on_click: Optional callback invoked when the item is selected.
        disabled: Whether the item is disabled (non-interactive).
    """

    icon: IconLike
    label: LabelLike
    on_click: Optional[VoidCallback] = None
    disabled: Union[bool, ObservableProtocol[bool]] = False


# MD3 only defines FAB-menu colour sets for the primary / secondary / tertiary
# families.  A FAB menu of a given family pairs a *solid* close button with
# *container*-toned list items (e.g. primary uses ``primary`` / ``on-primary``
# for the close button and ``primary-container`` / ``on-primary-container`` for
# the items).

# Recover the colour family from a style background (solid or tonal).
_BACKGROUND_TO_FAMILY: dict = {
    ColorRole.PRIMARY: "primary",
    ColorRole.PRIMARY_CONTAINER: "primary",
    ColorRole.SECONDARY: "secondary",
    ColorRole.SECONDARY_CONTAINER: "secondary",
    ColorRole.TERTIARY: "tertiary",
    ColorRole.TERTIARY_CONTAINER: "tertiary",
}

# Close button (solid) colour set per family: (container colour, foreground).
_CLOSE_BUTTON_COLOR_SETS: dict = {
    "primary": (ColorRole.PRIMARY, ColorRole.ON_PRIMARY),
    "secondary": (ColorRole.SECONDARY, ColorRole.ON_SECONDARY),
    "tertiary": (ColorRole.TERTIARY, ColorRole.ON_TERTIARY),
}

# List item (container) colour set per family: (container colour, foreground).
_LIST_ITEM_COLOR_SETS: dict = {
    "primary": (ColorRole.PRIMARY_CONTAINER, ColorRole.ON_PRIMARY_CONTAINER),
    "secondary": (ColorRole.SECONDARY_CONTAINER, ColorRole.ON_SECONDARY_CONTAINER),
    "tertiary": (ColorRole.TERTIARY_CONTAINER, ColorRole.ON_TERTIARY_CONTAINER),
}


def _color_family(base_style: FabStyle) -> str:
    """Return the MD3 FAB-menu colour family for *base_style*.

    Only primary / secondary / tertiary are defined by the spec.  An
    unsupported style background (e.g. an elevated/outlined or custom style that
    is not a tonal/solid FAB colour) falls back to ``"primary"`` and logs a
    one-time warning, since that almost always signals a misuse.
    """
    family = _BACKGROUND_TO_FAMILY.get(base_style.background)
    if family is None:
        warning_once(
            logger,
            f"fab_menu_unsupported_color_family:{base_style.background}",
            "FabMenu only supports primary/secondary/tertiary colour families; "
            "style background %s is unsupported and falls back to primary.",
            base_style.background,
        )
        return "primary"
    return family


def _close_button_style(base_style: FabStyle) -> FabStyle:
    """Derive the solid close-button FAB style from the chosen colour family.

    Per MD3 the FAB-menu close button is a *solid* FAB (``primary`` /
    ``secondary`` / ``tertiary``), distinct from the tonal list items.
    """
    bg, fg = _CLOSE_BUTTON_COLOR_SETS[_color_family(base_style)]
    return base_style.copy_with(  # type: ignore[return-value]
        background=bg,
        foreground=fg,
        overlay_color=fg,
    )


def _scalar_corner(corner_radius) -> float:
    """Return a scalar corner radius, taking the first value of a tuple."""
    if isinstance(corner_radius, (tuple, list)):
        return float(corner_radius[0]) if corner_radius else 0.0
    return float(corner_radius)


def _list_item_style(base_style: FabStyle) -> FabStyle:
    """Derive the list-item pill style from the FAB's colour family.

    Applies the MD3 FAB-menu list-item geometry (56dp fully-rounded pill,
    title-medium label, 24dp leading / 8dp icon-label / 24dp trailing spacing)
    and the level-0 base / level-4 hover / level-3 focus-press elevation set.
    """
    bg, fg = _LIST_ITEM_COLOR_SETS[_color_family(base_style)]
    return base_style.copy_with(  # type: ignore[return-value]
        background=bg,
        foreground=fg,
        overlay_color=fg,
        corner_radius=28.0,
        container_height=56,
        min_width=56,
        min_height=56,
        label_font_size=16,
        icon_size=24,
        spacing=8,
        padding=(24, 0, 24, 0),
        elevation=0,
        focused_elevation=3,
        hovered_elevation=4,
        pressed_elevation=3,
        focus_opacity=0.1,
        hover_opacity=0.08,
        pressed_opacity=0.1,
    )


def _build_item_row_class() -> type:
    """Build the internal menu-item row class on top of the private FAB base.

    Done lazily inside a function so ``buttons`` (which imports a number of
    Material modules) is only touched at first use, avoiding import cycles.
    """
    from nuiitivet.material.buttons import _FabBase, build_button_child, resolve_button_style_params

    class _Row(_FabBase):
        """Tonal pill row used to render a single FAB menu item."""

        def __init__(self, item: FabMenuItem, *, style: FabStyle, on_select: Callable[[], None]) -> None:
            self._item = item
            self._on_select = on_select
            self._user_style = style
            self._user_padding = None
            self._user_height = style.container_height

            child_widget = build_button_child(
                item.label,
                item.icon,
                foreground=style.foreground,
                button_height=style.container_height,
                icon_position="leading",
                spacing=int(getattr(style, "spacing", 8) or 8),
                style=style,
            )
            params = resolve_button_style_params(style, None, style.container_height, item.disabled)
            super().__init__(
                child=child_widget,
                on_click=self._handle_click,
                width=None,
                disabled=item.disabled,
                **params,
            )
            self._sync_state_tokens(style)

        def _expressive_press_scale(self) -> Tuple[float, float]:
            # Wide pills should not squash; rely on the state layer for feedback.
            return (1.0, 1.0)

        def _handle_click(self) -> None:
            if self._item.on_click is not None:
                invoke_event_handler(
                    self._item.on_click,
                    error_key="fab_menu_item_on_click",
                    error_msg="FabMenuItem on_click handler failed",
                    owner_name="FabMenuItem",
                )
            self._on_select()

    return _Row


def _build_morph_fab_class() -> type:
    """Build the internal morphing FAB class (the FAB-menu close button).

    While closed the FAB shows its normal size and rounded-square shape; while
    open it morphs into the MD3 FAB-menu *close button*: a fixed 56dp (size "s")
    fully-rounded circle, regardless of the closed size.  A single progress
    animation drives both the container size and the corner radius, bound to
    ``is_open``.

    The morph owns the container corner radius and re-asserts it after every
    theme change, since the base FAB resets the corner to the static style value
    whenever the theme is (re)applied.

    Built lazily so ``buttons`` is only imported at first use, avoiding cycles.
    """
    from nuiitivet.material.buttons import Fab

    class _MorphFab(Fab):
        """A :class:`Fab` that morphs to a 56dp close button while open."""

        def __init__(
            self,
            icon: IconLike,
            *,
            on_click: Optional[VoidCallback],
            style: FabStyle,
            is_open: Observable[bool],
            closed_size: float,
            open_size: float,
            closed_corner: float,
            open_corner: float,
        ) -> None:
            self._closed_size = float(closed_size)
            self._open_size = float(open_size)
            self._closed_corner = float(closed_corner)
            self._open_corner = float(open_corner)
            self._morph_corner = float(closed_corner)
            self._is_open_ref = is_open
            # Progress: 0.0 = closed (full size), 1.0 = open (56dp circle).
            self._morph_anim: Animatable = Animatable(0.0, motion=EXPRESSIVE_DEFAULT_SPATIAL)
            super().__init__(icon, on_click=on_click, style=style)

        def on_mount(self) -> None:
            super().on_mount()
            self.bind(self._morph_anim.subscribe(self._on_morph_tick))
            self._on_morph_tick(self._morph_anim.value)
            self.observe(self._is_open_ref, self._retarget)
            self._retarget(bool(self._is_open_ref.value))

        def _retarget(self, is_open_value: bool) -> None:
            self._morph_anim.target = 1.0 if is_open_value else 0.0

        def _morph_size(self) -> int:
            t = max(0.0, min(1.0, float(self._morph_anim.value)))
            size = self._closed_size + (self._open_size - self._closed_size) * t
            return int(round(size))

        def _morph_corner_value(self) -> float:
            t = max(0.0, min(1.0, float(self._morph_anim.value)))
            return self._closed_corner + (self._open_corner - self._closed_corner) * t

        def _on_morph_tick(self, _value: float) -> None:
            self._morph_corner = self._morph_corner_value()
            self.corner_radius = self._morph_corner
            self.mark_needs_layout()
            self.invalidate()

        def preferred_size(
            self,
            max_width: Optional[int] = None,
            max_height: Optional[int] = None,
        ) -> Tuple[int, int]:
            size = self._morph_size()
            if max_width is not None:
                size = min(size, int(max_width))
            if max_height is not None:
                size = min(size, int(max_height))
            return (size, size)

        def _on_theme_change(self, theme) -> None:
            super()._on_theme_change(theme)
            # The base resets corner_radius to the static style value; re-assert
            # the current morph corner so the shape state survives theme changes.
            self.corner_radius = self._morph_corner

    return _MorphFab


class _FabMenuList(Widget):
    """Internal overlay content: a vertical, staggered-reveal list of items.

    The list is mounted by the overlay when the menu opens, which triggers the
    staggered fade/slide-in of each item starting from the row closest to the
    FAB.  On unmount the per-item animations snap back to the hidden state so a
    re-open replays the reveal.
    """

    def __init__(
        self,
        items: List[FabMenuItem],
        *,
        item_style: FabStyle,
        on_select: Callable[[], None],
        stagger: float = _ITEM_REVEAL_STAGGER,
    ) -> None:
        super().__init__()
        from nuiitivet.layout.column import Column

        row_cls = _build_item_row_class()
        self._stagger = float(stagger)
        self._anims: List[Animatable] = []
        self._pending: List[Callable[[float], None]] = []

        rows: List[Widget] = []
        for item in items:
            anim: Animatable = Animatable(0.0, motion=EXPRESSIVE_DEFAULT_SPATIAL)
            self._anims.append(anim)
            row = row_cls(item, style=item_style, on_select=on_select)
            opacity_obs = anim.map(lambda t: max(0.0, min(1.0, float(t))))
            translate_obs = anim.map(lambda t: (0.0, (1.0 - max(0.0, min(1.0, float(t)))) * _ITEM_REVEAL_RISE))
            wrapped = row.modifier(translate(translate_obs)).modifier(opacity(opacity_obs))
            rows.append(wrapped)

        # Right-align items to the FAB's trailing edge; 4dp between-item gap.
        self._column = Column(rows, gap=_MENU_ITEM_BETWEEN_SPACE, cross_alignment="end")
        self.add_child(self._column)

    def on_mount(self) -> None:
        """Replay the staggered reveal each time the overlay is shown."""
        super().on_mount()
        self._cancel_pending()
        count = len(self._anims)
        for idx, anim in enumerate(self._anims):
            anim.snap_to(0.0)
            # The row closest to the FAB (visually bottom) reveals first.
            rank = count - 1 - idx
            delay = rank * self._stagger

            def _reveal(_dt: float, _a: Animatable = anim) -> None:
                _a.target = 1.0

            self._pending.append(_reveal)
            runtime.clock.schedule_once(_reveal, delay)

    def on_unmount(self) -> None:
        """Cancel pending reveals and reset to the hidden state."""
        self._cancel_pending()
        for anim in self._anims:
            anim.snap_to(0.0)
        super().on_unmount()

    def _cancel_pending(self) -> None:
        for cb in self._pending:
            runtime.clock.unschedule(cb)
        self._pending.clear()

    # -- Delegation to the inner column -------------------------------------

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        return _measure_preferred_size(self._column, max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        self._column.layout(width, height)
        self._column.set_layout_rect(0, 0, width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        rect = self._column.layout_rect
        if rect is not None:
            cx, cy, cw, ch = rect
            self._column.paint(canvas, x + cx, y + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        hit = self._column.hit_test(x, y)
        if hit is not None:
            return hit
        return super().hit_test(x, y)


class FabMenu(Widget):
    """Material Design 3 Expressive FAB Menu.

    A Floating Action Button that expands into a vertical list of labelled
    actions.  A single ``is_open`` observable is the source of truth.  On open
    the FAB morphs into the MD3 *close button*: its icon changes (``icon`` ->
    ``close_icon``) and it shrinks from its closed size to a fixed 56dp (size
    "s") fully-rounded circle, regardless of the configured size.  The overlay
    -- scrim, outside-tap dismissal, and anchored positioning -- is driven
    through the same observable via
    :func:`~nuiitivet.modifiers.popup.light_dismiss`.

    The closed-size footprint is reserved for layout stability; the shrinking
    close button aligns to its top-trailing corner, so larger closed FAB sizes
    place the menu higher with a larger margin underneath (40dp for medium, 56dp
    for large per MD3).  The menu expands upward from that top-trailing edge with
    a 4dp gap and a staggered item reveal.  Selecting an item invokes its
    ``on_click`` and, by default, closes the menu.
    """

    def __init__(
        self,
        icon: IconLike,
        items: List[FabMenuItem],
        *,
        is_open: Optional[Observable[bool]] = None,
        auto_close: bool = True,
        close_icon: Union["Symbol", str] = Symbols.close,
        style: Optional[FabStyle] = None,
    ) -> None:
        """Initialize a FabMenu.

        Args:
            icon: FAB icon shown while the menu is closed.
            items: The actions to display when the menu is open.
            is_open: Optional external ``Observable[bool]`` controlling the
                open/close state.  When ``None`` an internal one is created and
                exposed via :attr:`is_open`.
            auto_close: When ``True`` (default), selecting an item closes the
                menu after invoking its ``on_click``.
            close_icon: Icon the FAB morphs to while the menu is open.
                Defaults to ``Symbols.close``.
            style: FAB style preset selecting the colour family and size.
                Defaults to :meth:`FabStyle.primary`.  List items use the
                matching ``*-container`` colour set.
        """
        super().__init__()

        base_style = style if style is not None else FabStyle.primary()
        self._is_open: Observable[bool] = is_open if is_open is not None else Observable(False)
        self._auto_close = bool(auto_close)

        # FAB icon is bound to is_open: there is no separate toggle state.
        def _resolve_icon(is_open_value: bool) -> Union["Symbol", str, IconLike]:
            return close_icon if is_open_value else icon

        icon_source = self._is_open.map(_resolve_icon)

        # The FAB keeps its normal size/shape while closed and morphs into the
        # fixed 56dp circular "close button" while open.  The morph is owned by
        # the FAB and bound to is_open.  The closed footprint is reserved so the
        # surrounding layout stays stable; the shrinking close button aligns to
        # the footprint's top-trailing corner, growing the bottom margin.
        # The close button uses the family's *solid* colour (distinct from the
        # tonal list items) per MD3.
        fab_style = _close_button_style(base_style)
        self._closed_size = float(base_style.container_height)
        morph_fab_cls = _build_morph_fab_class()
        self._fab = morph_fab_cls(
            icon_source,
            on_click=self._toggle,
            style=fab_style,
            is_open=self._is_open,
            closed_size=self._closed_size,
            open_size=_OPEN_FAB_SIZE,
            closed_corner=_scalar_corner(fab_style.corner_radius),
            open_corner=_OPEN_FAB_CORNER,
        )

        self._list = _FabMenuList(
            items,
            item_style=_list_item_style(base_style),
            on_select=self._on_item_selected,
        )

        # Reuse the existing light-dismiss overlay for scrim + outside-tap close.
        self._inner = self._fab.modifier(
            light_dismiss(
                self._list,
                is_open=self._is_open,
                alignment="top-right",
                anchor="bottom-right",
                offset=(0.0, -_CLOSE_BUTTON_BETWEEN_SPACE),
            )
        )
        self.add_child(self._inner)

    @property
    def is_open(self) -> Observable[bool]:
        """Observable that controls (and reflects) the menu's open state."""
        return self._is_open

    def _toggle(self) -> None:
        self._is_open.value = not bool(self._is_open.value)

    def _on_item_selected(self) -> None:
        if self._auto_close:
            self._is_open.value = False

    # -- Layout: reserve the closed footprint, top-trailing align the FAB ---

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        # Always reserve the closed-size footprint so the surrounding layout is
        # stable as the FAB shrinks into the smaller close button.
        size = int(round(self._closed_size))
        if max_width is not None:
            size = min(size, int(max_width))
        if max_height is not None:
            size = min(size, int(max_height))
        return (size, size)

    def _fab_box(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """Return the (x, y, w, h) for the morphing FAB inside the footprint.

        The FAB is aligned to the top-trailing corner, so shrinking it grows the
        margin underneath (and to the leading side).
        """
        fab_w, fab_h = self._inner.preferred_size()
        fab_w = min(int(fab_w), width)
        fab_h = min(int(fab_h), height)
        return (width - fab_w, 0, fab_w, fab_h)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        bx, by, bw, bh = self._fab_box(width, height)
        self._inner.layout(bw, bh)
        self._inner.set_layout_rect(bx, by, bw, bh)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        rect = self._inner.layout_rect
        if rect is not None:
            cx, cy, cw, ch = rect
            self._inner.paint(canvas, x + cx, y + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        hit = self._inner.hit_test(x, y)
        if hit is not None:
            return hit
        return super().hit_test(x, y)


__all__ = ["FabMenu", "FabMenuItem"]
