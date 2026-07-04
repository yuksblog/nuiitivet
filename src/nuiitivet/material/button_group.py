"""Material Design 3 ButtonGroup components.

This module provides:
- ``GroupButton``: A single interactive segment, shared by both group types.
- ``_ButtonGroupBase``: Internal base class with shared validation and mount logic.
- ``StandardButtonGroup``: Action-oriented group; adjacent shape animation ON.
- ``ConnectedButtonGroup``: Option-selector group; manages single / multi-select.
- ``ButtonGroupPosition``: Literal type for segment position within a group.
"""

from __future__ import annotations

import logging
from typing import (
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    cast,
)

from nuiitivet.animation import Animatable
from nuiitivet.animation.converter import VectorConverter
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.layout.layout_utils import expand_layout_children
from nuiitivet.layout.metrics import align_offset
from nuiitivet.layout.row import Row
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.motion import EXPRESSIVE_FAST_SPATIAL, STANDARD_BUTTON_GROUP_WIDTH
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.callbacks import invoke_event_handler, BoolCallback
from nuiitivet.widgets.box import Box

if TYPE_CHECKING:
    from nuiitivet.material.styles.button_group_style import (
        ButtonGroupStyle,
        ConnectedButtonGroupStyle,
        StandardButtonGroupStyle,
    )
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public type alias
# ---------------------------------------------------------------------------

ButtonGroupPosition = Literal["start", "middle", "end", "only"]
"""Position of a segment within a ButtonGroup."""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Maps position → (tl_kind, tr_kind, br_kind, bl_kind)
# Tuple order follows Box.corner_radius convention: (tl, tr, br, bl).
# Each entry is either "outer" (group edge) or "inner" (junction).
_CORNER_KIND: dict[str, Tuple[str, str, str, str]] = {
    "start": ("outer", "inner", "inner", "outer"),
    "middle": ("inner", "inner", "inner", "inner"),
    "end": ("inner", "outer", "outer", "inner"),
    "only": ("outer", "outer", "outer", "outer"),
}


class _CornerTupleConverter(VectorConverter[Tuple[float, float, float, float]]):
    """Animation vector converter for a 4-float corner-radius tuple."""

    def to_vector(self, v: Tuple[float, float, float, float]) -> List[float]:
        return [float(v[0]), float(v[1]), float(v[2]), float(v[3])]

    def from_vector(self, vector: List[float]) -> Tuple[float, float, float, float]:
        return (vector[0], vector[1], vector[2], vector[3])


_CORNER_CONVERTER = _CornerTupleConverter()

# ---------------------------------------------------------------------------
# GroupButton
# ---------------------------------------------------------------------------


class GroupButton(InteractiveWidget):
    """A single interactive segment in a ButtonGroup (Standard or Connected).

    Handles position-aware corner-radius shape morphing via ``EXPRESSIVE_FAST_SPATIAL``
    motion on press / release.  ``set_position()`` is called exclusively by the
    containing ``_ButtonGroupBase`` during ``on_mount``; it is not part of the
    public user API.

    Args:
        label: Optional text label.  Can be a plain ``str`` or a
            ``ReadOnlyObservableProtocol[str]`` for dynamic text.
        icon: Optional icon.  Accepts a ``Symbol``, ``str`` icon name, or
            ``ReadOnlyObservableProtocol`` wrapping either.
        selected: Initial selected (toggle) state.  Pass an
            ``ObservableProtocol[bool]`` to bind to external state.
        on_change: Callback fired with the new ``bool`` selected state after each
            toggle.  In ``ConnectedButtonGroup`` this callback is composed with
            the group-level selection logic.
        disabled: Whether the item ignores pointer events.
        width: Optional width sizing.  ``ConnectedButtonGroup`` overrides this to
            ``Sizing.flex(1)`` to achieve equal-width segments.
        style: Optional style override.  If omitted the ``filled`` preset is used.
    """

    def __init__(
        self,
        label: "str | ReadOnlyObservableProtocol[str] | None" = None,
        icon: "Symbol | str | ReadOnlyObservableProtocol | None" = None,
        *,
        selected: "bool | ObservableProtocol[bool]" = False,
        on_change: Optional[BoolCallback] = None,
        disabled: "bool | ObservableProtocol[bool]" = False,
        width: SizingLike = None,
        style: "Optional[ButtonGroupStyle]" = None,
    ) -> None:
        """Initialize GroupButton.

        Args:
            label: Text label, or an observable string.
            icon: Icon symbol, string name, or observable icon.
            selected: Initial selected state, or an observable bool.
            on_change: Toggle-state change callback.
            disabled: Disable interaction.
            width: Width sizing spec.
            style: Visual style override.
        """
        from nuiitivet.material.styles.button_group_style import StandardButtonGroupStyle

        if label is None and icon is None:
            raise ValueError("GroupButton requires at least one of label or icon")

        self._has_user_style = style is not None
        self._style: "ButtonGroupStyle" = style or StandardButtonGroupStyle.filled()
        self._label = label
        self._icon = icon

        # on_change is interceptable by the containing group
        self._on_change: Optional[BoolCallback] = on_change

        # Selected state
        self._selected_external: "Optional[ObservableProtocol[bool]]" = None
        if hasattr(selected, "subscribe") and hasattr(selected, "value"):
            self._selected_external = cast("ObservableProtocol[bool]", selected)
            self._selected: bool = bool(self._selected_external.value)
        else:
            self._selected = bool(selected)

        # Corner animation state
        self._position: ButtonGroupPosition = "only"
        self._adjacent_animation: bool = True
        self._persistent_selected_pressed_shape: bool = False
        self._connected_inner_press_only: bool = False
        self._own_pressed: bool = False

        # Adjacent width-interaction state (Standard groups only).  Each item
        # exposes only a 0..1 "active" progress and its natural content-fit
        # width; the parent group layout (``_ButtonGroupRow``) reads these in a
        # single measure pass to grow the active item and compress its direct
        # neighbors, keeping the group width conserved (mirrors M3 Compose's
        # ButtonGroup, which avoids per-child layout jitter).  The width is NOT
        # animated per item here.
        self._base_width: float = float(self._style.min_item_width)

        # Store child widget refs for colour updates
        self._text_widget: "Optional[Widget]" = None
        self._icon_widget_ref: "Optional[Widget]" = None

        # Compute initial effective colours
        bg, fg, bc, bw = self._effective_colors()

        # Build content child (stores text/icon refs)
        content = self._build_content(fg)

        # Initialize corner animation (no motion yet; motion is enabled in
        # set_position() so the initial position snap is immediate)
        initial_corners = self._compute_raw_idle_corners(
            self._style.outer_corner_radius,
            self._style.outer_corner_radius,  # "only" position: all outer
        )
        self._corner_anim: "Animatable[Tuple[float, float, float, float]]" = Animatable.vector(
            initial_value=initial_corners,
            converter=_CORNER_CONVERTER,
            motion=None,  # Enabled after first set_position()
        )

        # Active progress 0..1 (motion enabled in set_position()).  Drives the
        # parent-computed width interaction; ticks only request a re-layout.
        self._press_progress: "Animatable[float]" = Animatable(0.0, motion=None)

        super().__init__(
            child=content,
            on_click=self._handle_click,
            on_press=self._handle_press_down,
            on_release=self._handle_press_up,
            disabled=disabled,
            width=width,
            height=self._style.container_height,
            # No box padding: the leading/trailing space is reserved via
            # ``preferred_size`` and rendered by *centering* the content (see
            # ``_side_space``).  This keeps the icon/label centred so the
            # pressed-width interaction compresses neighbours symmetrically.
            padding=0,
            alignment="center",
            background_color=bg,
            border_color=bc,
            border_width=bw,
            corner_radius=initial_corners,
            state_layer_color=self._style.overlay_color or ColorRole.ON_SURFACE,
        )

        # Override state-layer opacities from style
        self._PRESS_OPACITY = self._style.overlay_alpha
        self._HOVER_OPACITY = self._style.overlay_alpha * 2 / 3

    # ------------------------------------------------------------------
    # Preferred size
    # ------------------------------------------------------------------

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size.

        Connected groups enforce a visual minimum width (M3: 48dp for XS/S
        segments).  Standard groups are content-fit: their 48dp spec value is an
        accessible **tap-target** requirement, not a visual width floor, so it
        is intentionally not applied to the rendered width here.

        Args:
            max_width: Available width constraint.
            max_height: Available height constraint.

        Returns:
            ``(width, height)`` in pixels.
        """
        # Content is centred with zero box padding, so ``super`` returns the
        # bare content width; add the reserved leading + trailing space here so
        # the idle width still equals content + 2 × side-space.
        w, _h = super().preferred_size(max_width=max_width, max_height=max_height)
        w += 2 * self._side_space()
        if not self._adjacent_animation:  # Connected groups only
            w = max(w, self._style.min_item_width)
        return (int(w), self._style.container_height)

    def _side_space(self) -> int:
        """Return the per-side leading/trailing space reserved around the content.

        Sourced from the style's ``inner_padding`` (the MD3 button
        leading/trailing-space token).  Connected styles do not expose it; fall
        back to the historical fixed value so their layout is unchanged.

        This space is *not* applied as box padding — it is reserved width that
        centring turns into symmetric left/right margins, so the content stays
        centred while neighbours compress during the pressed-width interaction.
        """
        return int(getattr(self._style, "inner_padding", 12))

    # ------------------------------------------------------------------
    # Position injection (called by container on_mount)
    # ------------------------------------------------------------------

    def set_position(
        self,
        position: ButtonGroupPosition,
        adjacent_animation: bool = True,
    ) -> None:
        """Configure this item's position within its group.

        Called exclusively by ``_ButtonGroupBase.on_mount()``.  Snaps the
        corner radius to the idle value for the given position without
        animation, then arms the ``EXPRESSIVE_FAST_SPATIAL`` motion for
        subsequent press interactions.

        Args:
            position: One of ``"start"``, ``"middle"``, ``"end"``, ``"only"``.
            adjacent_animation: ``True`` for Standard groups (the active item's
                width grows and neighbors compress); ``False`` for Connected.
        """
        self._position = position
        self._adjacent_animation = adjacent_animation
        self._own_pressed = False

        # Capture the natural content-fit width (the parent layout grows/
        # compresses around this base).  Arm the MD3-spec spring on the active
        # progress so press/select transitions are smooth.
        self._base_width = float(self.preferred_size()[0])
        self._press_progress.snap_to(0.0)
        self._press_progress.set_motion(STANDARD_BUTTON_GROUP_WIDTH)

        idle = self._compute_target_corners(False)

        # Snap the animation to idle (no motion for position init)
        self._corner_anim.stop()
        # Directly set internal observable to avoid a spurious animation tick
        self._corner_anim._value.value = idle  # type: ignore[attr-defined]
        self._corner_anim._target = idle  # type: ignore[attr-defined]
        if self._corner_anim._state is not None:  # type: ignore[attr-defined]
            v = _CORNER_CONVERTER.to_vector(idle)
            state = self._corner_anim._state  # type: ignore[attr-defined]
            state.value = v.copy()
            state.start = v.copy()
            state.target = v.copy()

        # Enable expressive motion for future press interactions
        self._corner_anim._motion = EXPRESSIVE_FAST_SPATIAL  # type: ignore[attr-defined]
        v0 = _CORNER_CONVERTER.to_vector(idle)
        self._corner_anim._state = EXPRESSIVE_FAST_SPATIAL.create_state(v0, v0)  # type: ignore[attr-defined]

        # Apply immediately to Box's corner_radius (invalidates paint cache)
        self.corner_radius = idle

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Subscribe to corner animation and external selected observable."""
        super().on_mount()

        # Subscribe to corner animation ticks
        self.bind(self._corner_anim.subscribe(self._on_corner_value_changed))

        # Subscribe to active-progress ticks: request a parent re-layout so the
        # group recomputes all widths in a single coordinated pass.
        self.bind(self._press_progress.subscribe(self._on_progress_changed))

        # Subscribe to external selected observable if provided
        if self._selected_external is not None:
            sub = self._selected_external.subscribe(lambda v: self._set_selected(bool(v)))
            self.bind(sub)

    # ------------------------------------------------------------------
    # Interaction handlers (pointer events)
    # ------------------------------------------------------------------

    def _handle_press_down(self, event: PointerEvent) -> None:
        """Start own press shape animation and drive the adjacent width interaction.

        Only this item's own shape morphs on press; neighbors respond by
        adjusting their **width** (not their corners), per the MD3 spec.
        """
        self._own_pressed = True
        self._update_corner_target()
        self._update_active_progress()

    def _handle_press_up(self, event: PointerEvent) -> None:
        """Restore own shape animation on release and refresh the width interaction."""
        self._own_pressed = False
        self._update_corner_target()
        self._update_active_progress()

    def _handle_click(self) -> None:
        """Toggle selected state, fire change and click callbacks."""
        if self.disabled:
            return
        new_selected = not self._selected
        self._set_selected(new_selected)
        if self._on_change is not None:
            invoke_event_handler(
                self._on_change,
                new_selected,
                error_key="group_button_on_change",
                error_msg="GroupButton on_change raised",
                owner_name=type(self).__name__,
            )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_selected(self, value: bool) -> None:
        """Update selected state and refresh visual colours.

        Does NOT call ``_on_change``; callers must do so explicitly when needed.

        Args:
            value: New selected state.
        """
        self._selected = bool(value)

        # Write back to external observable if mutable
        if self._selected_external is not None:
            ext = self._selected_external
            if hasattr(ext, "value") and not isinstance(ext, ReadOnlyObservableProtocol):
                try:
                    ext.value = bool(value)  # type: ignore[assignment]
                except AttributeError:
                    pass

        bg, fg, bc, _bw = self._effective_colors()
        self.bgcolor = bg
        self.border_color = bc
        self._apply_foreground(fg)
        self.state.selected = bool(value)
        self._update_corner_target()
        self._update_active_progress()
        self.invalidate()

    # ------------------------------------------------------------------
    # Corner animation helpers
    # ------------------------------------------------------------------

    def _update_corner_target(self) -> None:
        """Recompute and apply the corner animation target."""
        target = self._compute_target_corners(self._own_pressed)
        self._corner_anim.target = target

    def _compute_target_corners(
        self,
        own_pressed: bool,
    ) -> Tuple[float, float, float, float]:
        """Compute the 4-corner radius tuple for the given interaction state.

        Corner-tuple order: ``(tl, tr, br, bl)``.  Only this item's own
        interaction state drives its corners; a neighbor's press never alters
        them (the MD3 adjacent interaction adjusts neighbor **width**, not
        shape — see ``_ButtonGroupRow``).

        Args:
            own_pressed: Whether this item is currently pressed.

        Returns:
            Target ``(tl, tr, br, bl)`` corner radii in logical pixels.
        """
        s = self._style
        kinds = _CORNER_KIND[self._position]  # (tl, tr, br, bl) kinds

        def resolve(kind: str, own: bool) -> float:
            if own:
                if self._connected_inner_press_only:
                    # Connected groups: keep outer corners stable while pressed.
                    # When selected, preserve fully rounded inner corners to avoid
                    # a temporary rectangular-looking intermediate shape.
                    if kind == "outer":
                        return s.outer_corner_radius
                    if self._selected:
                        sel = s.selected_inner_corner_radius
                        return sel if sel > 0 else s.outer_corner_radius
                    return s.pressed_inner_corner_radius
                return s.pressed_outer_corner_radius if kind == "outer" else s.pressed_inner_corner_radius
            # Standard groups: keep the pressed (squared) shape on selection.
            # The MD3 button-group spec defines no separate selected shape for
            # standard groups, and the official demo shows the selected segment
            # at the same roundness as a pressed one — so selection reuses the
            # pressed corners (selection is otherwise conveyed by colour).
            if self._selected and self._persistent_selected_pressed_shape:
                return s.pressed_outer_corner_radius if kind == "outer" else s.pressed_inner_corner_radius
            # Selected inner corner: fully rounded on inner edges (Connected groups only).
            if kind == "inner" and self._selected and not self._adjacent_animation:
                sel = s.selected_inner_corner_radius
                return sel if sel > 0 else s.outer_corner_radius
            return s.outer_corner_radius if kind == "outer" else s.inner_corner_radius

        tl = resolve(kinds[0], own_pressed)
        tr = resolve(kinds[1], own_pressed)
        br = resolve(kinds[2], own_pressed)
        bl = resolve(kinds[3], own_pressed)
        return (tl, tr, br, bl)

    @staticmethod
    def _compute_raw_idle_corners(outer: float, inner: float) -> Tuple[float, float, float, float]:
        """Return idle corners for the ``"only"`` position (all outer).

        Args:
            outer: Outer corner radius.
            inner: Inner corner radius (unused for ``"only"``; kept for symmetry).

        Returns:
            ``(outer, outer, outer, outer)``
        """
        return (outer, outer, outer, outer)

    def _on_corner_value_changed(self, v: Tuple[float, float, float, float]) -> None:
        """Animation tick callback: apply animated corners to the Box."""
        # Use Box's setter so paint cache is invalidated with every shape update.
        self.corner_radius = v
        self.invalidate()

    # ------------------------------------------------------------------
    # Adjacent width interaction (Standard groups)
    # ------------------------------------------------------------------

    def _update_active_progress(self) -> None:
        """Retarget the 0..1 active progress; the parent layout reads the value.

        The width expansion is a **transient press** effect (MD3: the only
        width token is ``pressed``): the item grows to the 15% peak while held
        and returns to its idle width on release.  Selection is conveyed by
        colour and corner shape, not by a persistent width change.

        Only Standard groups (``adjacent_animation=True``) participate; for
        Connected groups this is a no-op so their flex layout is preserved.
        """
        if not self._adjacent_animation:
            return
        self._press_progress.target = 1.0 if self._own_pressed else 0.0

    def _on_progress_changed(self, _value: float) -> None:
        """Active-progress tick: re-layout the group and force a repaint.

        ``mark_needs_layout`` flags the tree as needing layout, but it only
        schedules a repaint on the first dirtying call (the node stays dirty
        afterwards, so its guarded ``invalidate`` is skipped).  An animation
        ticks every frame, so we must invalidate explicitly each tick — mirroring
        the corner animation — otherwise only the first frame would repaint and
        the width would appear frozen.
        """
        self.mark_needs_layout()
        self.invalidate()

    # ------------------------------------------------------------------
    # Visual helpers
    # ------------------------------------------------------------------

    def _effective_colors(
        self,
    ) -> Tuple[Optional[ColorSpec], ColorSpec, Optional[ColorSpec], float]:
        """Return ``(background, foreground, border_color, border_width)`` for current state.

        Returns:
            Tuple of effective colour specs for the current selected state.
        """
        s = self._style
        if self._selected:
            bg: Optional[ColorSpec] = s.selected_background or s.background
            fg: ColorSpec = s.selected_foreground or s.foreground or ColorRole.ON_SURFACE
            bc: Optional[ColorSpec] = s.selected_border_color or s.border_color
        else:
            bg = s.background
            fg = s.foreground or ColorRole.ON_SURFACE
            bc = s.border_color
        return bg, fg, bc, s.border_width

    def _build_content(self, foreground: ColorSpec) -> "Widget":
        """Build the content child widget (icon + label composition).

        Stores references to the text and icon widgets for later colour updates.

        Args:
            foreground: Initial foreground colour for icon and text.

        Returns:
            A widget representing the item content.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.text import Text
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle
        from nuiitivet.theme.type_scale import TypeScaleToken
        from nuiitivet.layout.row import Row

        # Icon / label / spacing scale with the group size (MD3 button tokens).
        icon_size = self._style.icon_size
        label_size = self._style.label_size
        icon_label_space = self._style.icon_label_space

        icon_w: "Optional[Widget]" = None
        text_w: "Optional[Widget]" = None

        if self._icon is not None:
            icon_w = Icon(self._icon, size=icon_size, style=IconStyle(color=foreground))
            self._icon_widget_ref = icon_w

        if self._label is not None:
            text_w = Text(
                self._label,
                style=TextStyle(color=foreground),
                type_scale=TypeScaleToken.from_size(label_size),
                alignment="center",
            )
            self._text_widget = text_w

        if icon_w is not None and text_w is None:
            return icon_w
        if text_w is not None and icon_w is None:
            return text_w
        assert icon_w is not None and text_w is not None
        return Row([icon_w, text_w], gap=icon_label_space, cross_alignment="center")

    def _rebuild_content(self) -> None:
        """Rebuild the content child from the current style.

        Content metrics (icon size, label size, icon/label spacing) are baked
        into the Icon/Text widgets at build time, so when the containing group
        assigns a sized style the content must be regenerated to pick up the
        new sizes.  Called by ``_ButtonGroupBase.on_mount`` before layout.
        """
        _bg, fg, _bc, _bw = self._effective_colors()
        content = self._build_content(fg)
        self.clear_children()
        self.add_child(content)
        self.mark_needs_layout()

    def _apply_foreground(self, foreground: ColorSpec) -> None:
        """Update the colour of child text and icon widgets.

        Args:
            foreground: New foreground colour.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle

        if self._text_widget is not None:
            current = getattr(self._text_widget, "_style", None)
            if current is not None:
                self._text_widget._style = current.copy_with(color=foreground)  # type: ignore[attr-defined]
            else:
                # Typography (type_scale) and alignment already live on the
                # widget from build time; only the color needs refreshing.
                self._text_widget._style = TextStyle(color=foreground)  # type: ignore[attr-defined]
            self._text_widget.invalidate()

        if self._icon_widget_ref is not None and isinstance(self._icon_widget_ref, Icon):
            current_icon = getattr(self._icon_widget_ref, "_style", None)
            if current_icon is not None:
                self._icon_widget_ref._style = current_icon.copy_with(color=foreground)
            else:
                self._icon_widget_ref._style = IconStyle(color=foreground)
            self._icon_widget_ref.invalidate()


# ---------------------------------------------------------------------------
# _ButtonGroupRow
# ---------------------------------------------------------------------------


class _ButtonGroupRow(Row):
    """Row that runs the M3 Standard button-group width interaction.

    In a single layout pass it reads each child's 0..1 active progress and its
    natural base width, grows each active item and compresses its direct
    neighbors (bounded by the neighbor's padding so content never clips), then
    places the children using rounded *boundary* positions.  Computing all
    widths together in one pass — rather than animating each item's width
    independently — keeps the group width conserved and prevents the rightmost
    item from accumulating per-frame rounding jitter.  This mirrors M3 Compose's
    ``ButtonGroup`` measure policy.
    """

    def layout(self, width: int, height: int) -> None:
        """Lay out children, applying the active/neighbor width interaction."""
        super().layout(width, height)  # establish own geometry + default pass
        items = [c for c in expand_layout_children(self.children_snapshot()) if isinstance(c, GroupButton)]
        if len(items) < 2:
            return

        widths = self._interaction_widths(items)

        l, t, _r, _b = self.padding
        gap = max(0, int(self.gap))
        ch = max(0, height - t - _b)

        # Round boundary positions (not individual widths) so cumulative offsets
        # never drift: each child width is the gap between rounded boundaries.
        x = float(l)
        for i, item in enumerate(items):
            start_edge = round(x)
            x += widths[i]
            end_edge = round(x)
            w = max(0, end_edge - start_edge)
            ih = self._item_height(item, ch)
            y = t + align_offset(ch, ih, "center")
            item.layout(w, ih)
            item.set_layout_rect(start_edge, y, w, ih)
            x += gap

    def _interaction_widths(self, items: List["GroupButton"]) -> List[float]:
        """Return the per-item widths after applying grow/compress (float, conserved)."""
        bases = [float(it._base_width) for it in items]
        widths = list(bases)
        n = len(items)
        for i, it in enumerate(items):
            if not it._adjacent_animation:
                continue
            p = it._press_progress.value
            if p <= 0.0:
                continue
            p = min(1.0, p)  # clamp any motion overshoot so content never clips
            ratio = float(getattr(it._style, "pressed_width_multiplier", 0.0))
            half = ratio * bases[i] / 2.0
            # Each side's growth is bounded by the *neighbor's* padding, so a
            # compressed neighbor never loses more than its padding (content
            # stays intact).  Edge items grow on their single available side.
            if i > 0:
                gl = min(half, self._pad(items[i - 1])) * p
                widths[i] += gl
                widths[i - 1] -= gl
            if i < n - 1:
                gr = min(half, self._pad(items[i + 1])) * p
                widths[i] += gr
                widths[i + 1] -= gr
        return widths

    @staticmethod
    def _item_height(item: "GroupButton", content_height: int) -> int:
        dim = item.height_sizing
        if dim is not None and dim.kind == "fixed":
            return int(dim.value)
        return content_height

    @staticmethod
    def _pad(item: "GroupButton") -> float:
        """Horizontal inner padding = the maximum a neighbor may be compressed by."""
        return float(getattr(item._style, "inner_padding", 12))


# ---------------------------------------------------------------------------
# _ButtonGroupBase
# ---------------------------------------------------------------------------


class _ButtonGroupBase(Box):
    """Internal base for StandardButtonGroup and ConnectedButtonGroup.

    Validates items, builds the Row layout, and calls ``set_position()`` on
    each item during ``on_mount()``.
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        adjacent_animation: bool,
        persistent_selected_pressed_shape: bool,
        connected_inner_press_only: bool,
        group_width: SizingLike,
        style: "ButtonGroupStyle",
    ) -> None:
        """Initialize the shared button group layout.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            adjacent_animation: ``True`` to enable neighbor corner animation
                (Standard); ``False`` to disable it (Connected).
            persistent_selected_pressed_shape: ``True`` to keep a squarer
                shape on selected items after release (Standard groups).
            connected_inner_press_only: ``True`` to keep outer corners
                stable while pressed, animating only inner corners
                (Connected groups).
            group_width: Width sizing passed to the inner ``Row`` and outer
                ``Box``.  ``None`` for content-fit; ``"100%"`` for full-width.
            style: Resolved ``ButtonGroupStyle`` for this group.
        """
        _validate_items(items)

        self._items: List[GroupButton] = list(items)
        self._style = style
        self._adjacent_animation = adjacent_animation
        self._persistent_selected_pressed_shape = persistent_selected_pressed_shape
        self._connected_inner_press_only = connected_inner_press_only

        # Standard groups use the interaction-aware row (active grows / neighbors
        # compress in one coordinated pass); Connected groups use a plain Row.
        row_cls = _ButtonGroupRow if adjacent_animation else Row
        row = row_cls(
            list(items),
            gap=style.item_gap,
            cross_alignment="center",
            width=group_width,
            height=style.container_height,
        )

        super().__init__(child=row, width=group_width)

        # Propagate the group's sized style to items now, so the tree measures
        # correctly even before mount.  Window auto-sizing calls preferred_size
        # on the *unmounted* content tree; without this each item would still
        # carry its default style and report too small a width (the height comes
        # from the group container_height, so only width is affected).
        self._apply_item_sizing()

    def _apply_item_sizing(self) -> None:
        """Propagate the group's sized style + content metrics to every item.

        Covers only the properties that affect measurement (style, fixed item
        height, rebuilt icon/label content, padding) so it is safe to run before
        mount.  Idempotent: ``on_mount`` calls it again before wiring colours,
        positions and corner animation.
        """
        size_tokens = self._item_size_tokens()
        for item in self._items:
            # Items without a user-provided style inherit the full group style;
            # items with a custom style only receive size tokens so they keep
            # their custom colours.
            if not item._has_user_style:
                item._style = self._style
            else:
                item._style = item._style.copy_with(**size_tokens)
            item.height_sizing = Sizing.fixed(self._style.container_height)
            # Rebuild content so icon/label sizes reflect the assigned style.
            item._rebuild_content()
            # Leading/trailing space is reserved via preferred_size + centring,
            # not box padding (see GroupButton._side_space).
            item.padding = 0

    def _item_size_tokens(self) -> dict[str, int | float]:
        """Return size tokens to propagate to items with user-provided styles.

        Subclasses override to include only field names valid for their
        concrete style type (e.g. ``inner_corner_radius`` is a field only
        on ``ConnectedButtonGroupStyle``).
        """
        return {
            "container_height": self._style.container_height,
            "icon_size": self._style.icon_size,
            "label_size": self._style.label_size,
            "icon_label_space": self._style.icon_label_space,
            "outer_corner_radius": self._style.outer_corner_radius,
            "pressed_outer_corner_radius": self._style.pressed_outer_corner_radius,
            "pressed_inner_corner_radius": self._style.pressed_inner_corner_radius,
        }

    def on_mount(self) -> None:
        """Assign positions, sync size-layout tokens, and set neighbors for all items."""
        super().on_mount()
        # Re-sync style + content (also done at construction) so any change is
        # reflected, then wire up the mount-only visuals and interaction state.
        self._apply_item_sizing()
        n = len(self._items)
        for i, item in enumerate(self._items):
            if n == 1:
                pos: ButtonGroupPosition = "only"
            elif i == 0:
                pos = "start"
            elif i == n - 1:
                pos = "end"
            else:
                pos = "middle"

            # Refresh visual properties that were baked in during __init__.
            bg, fg, bc, bw = item._effective_colors()
            item.bgcolor = bg
            item.border_color = bc
            item.border_width = bw
            item.state_layer_color = item._style.overlay_color or ColorRole.ON_SURFACE
            item._PRESS_OPACITY = item._style.overlay_alpha
            item._HOVER_OPACITY = item._style.overlay_alpha * 2 / 3
            item.mark_needs_layout()
            item._persistent_selected_pressed_shape = self._persistent_selected_pressed_shape
            item._connected_inner_press_only = self._connected_inner_press_only

            item.set_position(pos, adjacent_animation=self._adjacent_animation)


def _validate_items(items: Sequence[object]) -> None:
    """Raise if items fail the ButtonGroup constraints.

    Args:
        items: Sequence to validate.

    Raises:
        ValueError: If the number of items is outside [2, 5].
        TypeError: If any element is not a ``GroupButton``.
    """
    if len(items) < 2:
        raise ValueError(f"ButtonGroup requires at least 2 items, got {len(items)}")
    if len(items) > 5:
        raise ValueError(f"ButtonGroup requires at most 5 items, got {len(items)}")
    for item in items:
        if not isinstance(item, GroupButton):
            raise TypeError(f"All items must be GroupButton instances, got {type(item).__name__}")


# ---------------------------------------------------------------------------
# StandardButtonGroup
# ---------------------------------------------------------------------------


class StandardButtonGroup(_ButtonGroupBase):
    """A ButtonGroup that organises action or toggle segments horizontally.

    Width fits the combined item widths.  When a segment is activated (pressed)
    or selected, the MD3 adjacent interaction runs: the active segment animates
    its **width**, **shape**, and (via centered content) **padding**, while its
    direct neighbors shrink to compensate so the group's overall width stays
    stable.  All transitions use M3 Expressive (``EXPRESSIVE_FAST_SPATIAL``)
    motion.  Item selected states are independent — no group-level enforcement.

    Args:
        items: Between 2 and 5 ``GroupButton`` instances.
        style: Visual style.  Use ``StandardButtonGroupStyle.filled()``,
            ``.tonal()``, or ``.outlined()``, optionally passing a size
            (e.g. ``StandardButtonGroupStyle.filled("m")``).
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        style: "Optional[StandardButtonGroupStyle]" = None,
    ) -> None:
        """Initialize StandardButtonGroup.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            style: Visual style override.  Defaults to
                ``StandardButtonGroupStyle.filled()`` (size ``"s"``).
        """
        from nuiitivet.material.styles.button_group_style import (
            StandardButtonGroupStyle as _Std,
        )

        eff_style = style if style is not None else _Std.filled()
        super().__init__(
            items,
            adjacent_animation=True,
            persistent_selected_pressed_shape=True,
            connected_inner_press_only=False,
            group_width=None,  # Fits content
            style=eff_style,
        )

    def _item_size_tokens(self) -> dict[str, int | float]:
        """Include ``inner_padding`` (a real field on Standard style)."""
        tokens = super()._item_size_tokens()
        style = cast("StandardButtonGroupStyle", self._style)
        tokens["inner_padding"] = style.inner_padding
        return tokens


# ---------------------------------------------------------------------------
# ConnectedButtonGroup
# ---------------------------------------------------------------------------


class ConnectedButtonGroup(_ButtonGroupBase):
    """A ButtonGroup that functions as an option selector / view switcher.

    Width expands to fill the containing widget (``width="100%"``).  Items
    share space equally (``Sizing.flex(1)``).  Only corner shapes animate on
    press — adjacent segment corners are unaffected.  Selection is always
    enforced by the group.

    Args:
        items: Between 2 and 5 ``GroupButton`` instances.
        select_mode: ``"single"`` ensures at most one item is selected;
            ``"multi"`` allows any combination.
        style: Visual style.  Use ``ConnectedButtonGroupStyle.filled()``,
            ``.tonal()``, or ``.outlined()``, optionally passing a size
            (e.g. ``ConnectedButtonGroupStyle.filled("m")``).
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        select_mode: Literal["single", "multi"] = "single",
        style: "Optional[ConnectedButtonGroupStyle]" = None,
    ) -> None:
        """Initialize ConnectedButtonGroup.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            select_mode: ``"single"`` or ``"multi"`` selection enforcement.
            style: Visual style override.  Defaults to
                ``ConnectedButtonGroupStyle.filled()`` (size ``"s"``).
        """
        from nuiitivet.material.styles.button_group_style import (
            ConnectedButtonGroupStyle as _Con,
        )

        eff_style = style if style is not None else _Con.filled()
        self._select_mode = select_mode

        super().__init__(
            items,
            adjacent_animation=False,
            persistent_selected_pressed_shape=False,
            connected_inner_press_only=True,
            group_width="100%",
            style=eff_style,
        )

    def _item_size_tokens(self) -> dict[str, int | float]:
        """Include ``inner_corner_radius`` (a real field on Connected style)."""
        tokens = super()._item_size_tokens()
        tokens["inner_corner_radius"] = self._style.inner_corner_radius
        return tokens

    def on_mount(self) -> None:
        """Assign positions, set flex widths, and wire group selection logic."""
        super().on_mount()  # Calls _ButtonGroupBase.on_mount → set_position()

        # Equal-width distribution for connected layout
        for item in self._items:
            item.width_sizing = Sizing.flex(1)
            item.mark_needs_layout()

        # Intercept each item's on_change to apply group selection logic
        for i, item in enumerate(self._items):
            original_on_change = item._on_change

            def _make_wrapper(
                item_idx: int,
                orig_cb: Optional[BoolCallback],
            ) -> BoolCallback:
                def _wrapper(selected: bool) -> None:
                    # 1. Item-level callback fires first
                    if orig_cb is not None:
                        invoke_event_handler(
                            orig_cb,
                            selected,
                            error_key="group_button_item_on_change",
                            error_msg="GroupButton item on_change raised",
                            owner_name=type(item).__name__,
                        )
                    # 2. Group selection logic
                    self._handle_group_selection_change(item_idx, selected)

                return _wrapper

            item._on_change = _make_wrapper(i, original_on_change)

    def _handle_group_selection_change(self, changed_idx: int, selected: bool) -> None:
        """Apply select_mode logic.

        Args:
            changed_idx: Index of the item whose state just changed.
            selected: New selected state of the changed item.
        """
        if self._select_mode == "single" and selected:
            for i, item in enumerate(self._items):
                if i != changed_idx and item._selected:
                    item._set_selected(False)


__all__ = [
    "GroupButton",
    "ButtonGroupPosition",
    "StandardButtonGroup",
    "ConnectedButtonGroup",
]
