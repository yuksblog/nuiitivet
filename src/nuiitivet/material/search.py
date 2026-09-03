"""Material Design 3 Search.

Two widgets, both the *contained* (expressive) variant:

- :class:`SearchBar` — the search bar container on its own.
- :class:`DockedSearchBar` — the bar plus a docked container, anchored 2dp
  below it.

MD3 reference: ``md.comp.search-bar.*`` and ``md.comp.search-view.contained.*``
(``docs/md3/search.md``).

Deliberate omissions
--------------------

*The baseline / Divided variant is not implemented.* It is deprecated, so every
``Layout and Text / Divided (baseline)`` token is a non-target — and so are the
Color-group tokens that belong to it: ``search-*.container.elevation``,
``search-*.container.surface-tint-layer.color`` and
``search-view.divider.color``. Neither widget casts a shadow or draws a divider;
the contained variant separates by surface role and by the 2dp bar-to-results
gap instead.

*There is no full-screen search widget.* MD3's third container — the screen a
full-screen search takes over — is the application's to lay out; place a
:class:`SearchBar` in your own screen. The bar still animates its own margin
(below), so what the app supplies is the screen, not the inset.

*No avatar and no multiple trailing actions.* ``search-bar.avatar.*`` and
``search-bar.contained.trailing-actions.*`` are unimplemented; the bar carries a
single generic ``trailing_icon``.

*No disabled state.* The ``Search - Bar`` colour group specifies Enabled,
Hovered, Pressed and Focused only, so there are no tokens to render one.

The animated margin
-------------------

``width`` names the **box**, not the bar: the bar is drawn inset inside it by
24dp, animating to 12dp while focused
(``md.comp.search-bar.contained.leading-margin`` ->
``md.comp.search-view.contained.leading-margin``). Sizing the box rather than
the bar keeps the widget's own footprint stable, so focusing a search bar does
not reflow its siblings.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union

from nuiitivet.animation import Animatable
from nuiitivet.common.logging_once import exception_once
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.motion import SEARCH_BAR_FOCUS_MARGIN
from nuiitivet.material.styles.search_bar_style import DockedSearchBarStyle, SearchBarStyle
from nuiitivet.modifiers.popup import popup
from nuiitivet.observable import Observable, ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import (
    draw_round_rect,
    get_default_font_fallbacks,
    get_typeface,
    make_font,
    make_paint,
    make_rect,
    make_text_blob,
)
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.callbacks import invoke_event_handler
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.interaction import FocusChangeCallback, FocusSource
from nuiitivet.widgets.input_filter import InputFilterLike

# The "decorative Icon vs tappable IconButton" rule is identical for a search
# bar and a text field, so the helper is shared rather than restated. Importing
# it leaves TextField untouched; moving it to a shared module would be a
# refactor of text_fields.py, which is out of scope here.
from nuiitivet.material.text_fields import _build_text_field_icon

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.theme.theme import Theme
    from nuiitivet.widgeting.widget_kernel import WidgetKernel


_logger = logging.getLogger(__name__)

IconLike = Union["Symbol", str, ReadOnlyObservableProtocol["Symbol"], ReadOnlyObservableProtocol[str], None]

# A tappable icon occupies a 48dp target. With the contained 4dp outer space
# that puts the 24dp glyph's edge at 16dp from the container edge, which is
# what the MD3 measurements show and what the 16dp ``no-actions`` space matches
# when there is no target to inset.
_ICON_TARGET = 48.0


class _SearchBarCore(InteractiveWidget):
    """The search bar container itself: 56dp tall, fully rounded, no elevation.

    This is the widget the state layer, the focus ring and a docked popup all
    attach to. It is deliberately *not* the public widget: the public one owns
    the animated outer margin, and a state layer painted over that margin would
    extend past the bar.
    """

    def __init__(
        self,
        *,
        value: Union[str, ReadOnlyObservableProtocol[str]] = "",
        placeholder: str | None = None,
        leading_icon: IconLike = None,
        on_tap_leading_icon: Optional[Callable[[], None]] = None,
        trailing_icon: IconLike = None,
        on_tap_trailing_icon: Optional[Callable[[], None]] = None,
        on_change: Optional[Callable[[str], None]] = None,
        on_user_edit: Optional[Callable[[str], None]] = None,
        on_submit: Optional[Callable[[str], None]] = None,
        on_focus_change: Optional[FocusChangeCallback] = None,
        input_filter: Optional[InputFilterLike] = None,
        style: Optional[SearchBarStyle] = None,
    ) -> None:
        self._user_style = style
        resolved = self.style

        super().__init__(
            height=resolved.container_height,
            state_layer_color=resolved.state_layer_color,
            # The focus subject is the inner EditableText; mirroring it here
            # would ping-pong between two FocusNodes on pointer press. Same
            # arrangement as TextField.
            focusable=False,
        )

        self._placeholder = placeholder
        self._on_change = on_change
        self._on_submit = on_submit
        self._on_focus_change = on_focus_change

        # Read by the pane (to drive the margin animation) and by
        # DockedSearchBar (to open the docked container).
        self.focused: Observable[bool] = Observable(False)

        if on_tap_leading_icon is not None and leading_icon is None:
            raise ValueError("on_tap_leading_icon requires leading_icon to be provided")
        if on_tap_trailing_icon is not None and trailing_icon is None:
            raise ValueError("on_tap_trailing_icon requires trailing_icon to be provided")

        self.leading_icon = _build_text_field_icon(leading_icon, arg_name="leading_icon", on_tap=on_tap_leading_icon)
        self.trailing_icon = _build_text_field_icon(
            trailing_icon, arg_name="trailing_icon", on_tap=on_tap_trailing_icon
        )
        if self.leading_icon is not None:
            self.add_child(self.leading_icon)
        if self.trailing_icon is not None:
            self.add_child(self.trailing_icon)

        self._editable = EditableText(
            value=value,
            on_change=self._handle_editable_change,
            # Passed straight through: only a caller that must tell typing
            # apart from its own writes asks for this, so wrapping it here
            # would add nothing.
            on_user_edit=on_user_edit,
            on_focus_change=self._handle_editable_focus_change,
            # EditableText claims Enter only when it has an on_submit, and
            # declines it otherwise so the key can still reach a shortcut.
            on_submit=self._handle_editable_submit if on_submit is not None else None,
            input_filter=input_filter,
            text_color=resolved.input_text_color,
            cursor_color=resolved.cursor_color,
            selection_color=resolved.selection_color,
            font_size=resolved.font_size,
        )
        self.add_child(self._editable)

        self.enable_click(on_press=self._handle_press)

    # ------------------------------------------------------------------
    # Style / theme
    # ------------------------------------------------------------------

    def _resolvable_theme(self) -> "Theme | None":
        """Return the theme, or ``None`` while this widget cannot reach one.

        Before the widget is attached it has no ancestors, so ``Theme.of``
        would fall back to the light default and warn about it. ``None``
        expresses the same fallback without the warning (issue #473).
        """
        from nuiitivet.widgeting.context_lookup import is_premature_lookup

        if is_premature_lookup(self):
            return None

        from nuiitivet.theme.theme import Theme

        return Theme.of(self)

    @property
    def style(self) -> SearchBarStyle:
        """Return the resolved search bar style."""
        if self._user_style is not None:
            return self._user_style

        theme = self._resolvable_theme()
        if theme is None:
            return SearchBarStyle()
        return SearchBarStyle.from_theme(theme)

    # ------------------------------------------------------------------
    # Value / focus
    # ------------------------------------------------------------------

    @property
    def value(self) -> str:
        """Return the current query text."""
        return self._editable.value

    @value.setter
    def value(self, new_text: str) -> None:
        self._editable.value = new_text

    @property
    def should_show_focus_ring(self) -> bool:
        """Show the ring only for keyboard focus, per MD3."""
        return self._editable.state.focused and not self._editable.is_focus_from_pointer

    def focus(self) -> None:
        """Programmatically focus the bar (keyboard-style focus)."""
        self._editable.focus()

    def corner_radii_pixels(self, width: float, height: float) -> Tuple[float, float, float, float]:
        """Fully rounded: ``md.comp.search-bar.container.shape``."""
        r = float(height) / 2.0
        return (r, r, r, r)

    def _handle_press(self, event) -> None:
        # Route focus through the editable's pointer entry point so the ring is
        # suppressed for clicks, per MD3. Tappable icons are IconButton
        # children handling their own press, so they never reach here.
        self._editable.request_focus_from_pointer()

    def _handle_editable_change(self, new_text: str) -> None:
        # The placeholder shows and hides with the text.
        self.invalidate()
        if self._on_change is not None:
            self._on_change(new_text)

    def _handle_editable_submit(self, value: str) -> None:
        if self._on_submit is None:
            return
        try:
            self._on_submit(value)
        except Exception:
            exception_once(_logger, "search_bar_on_submit_exc", "SearchBar on_submit raised")

    def _handle_editable_focus_change(self, focused: bool, source: FocusSource) -> None:
        self.focused.value = bool(focused)
        self.invalidate()
        if self._on_focus_change is not None:
            invoke_event_handler(
                self._on_focus_change,
                focused,
                source,
                error_key="search_bar_on_focus_change",
                error_msg="SearchBar on_focus_change raised",
                owner_name=type(self).__name__,
            )

    # ------------------------------------------------------------------
    # Layout / paint
    # ------------------------------------------------------------------

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """The bar is as wide as it is given and 56dp tall."""
        style = self.style
        width = int(max_width) if max_width is not None else int(style.min_width)
        height = int(style.container_height)
        if max_height is not None:
            height = min(height, int(max_height))
        return (width, height)

    def _slot_bounds(self, width: int) -> Tuple[float, float]:
        """Return the x range available to the input text."""
        style = self.style

        if self.leading_icon is not None:
            text_left = style.leading_space + _ICON_TARGET + style.icon_label_gap
        else:
            # md.comp.search-bar.contained.no-actions.leading-space
            text_left = 16.0

        if self.trailing_icon is not None:
            text_right = width - style.trailing_space - _ICON_TARGET - style.icon_label_gap
        else:
            text_right = width - 16.0

        return (text_left, text_right)

    def layout(self, width: int, height: int) -> None:
        """Place the icons in their 48dp targets and the editable between them."""
        super().layout(width, height)

        style = self.style

        if self.leading_icon is not None:
            lw, lh = self.leading_icon.preferred_size()
            ix = style.leading_space + (_ICON_TARGET - lw) / 2.0
            iy = (height - lh) / 2.0
            self.leading_icon.layout(lw, lh)
            self.leading_icon.set_layout_rect(int(ix), int(iy), int(lw), int(lh))

        if self.trailing_icon is not None:
            tw, th = self.trailing_icon.preferred_size()
            ix = width - style.trailing_space - _ICON_TARGET + (_ICON_TARGET - tw) / 2.0
            iy = (height - th) / 2.0
            self.trailing_icon.layout(tw, th)
            self.trailing_icon.set_layout_rect(int(ix), int(iy), int(tw), int(th))

        text_left, text_right = self._slot_bounds(width)
        text_w = max(0, int(text_right - text_left))
        self._editable.layout(text_w, height)
        self._editable.set_layout_rect(int(text_left), 0, text_w, height)

    def _get_font(self, size: int):
        tf = get_typeface(
            candidate_files=None,
            family_candidates=get_default_font_fallbacks(),
            pkg_font_dir=None,
            fallback_to_default=True,
        )
        return make_font(tf, size)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Draw the container, the state layer, the text and the icons."""
        if canvas is None:
            return

        self.set_last_rect(x, y, width, height)
        style = self.style
        theme = self._resolvable_theme()

        container_color = resolve_color_to_rgba(style.container_color, theme=theme)
        paint_container = make_paint(color=container_color)
        rect = make_rect(x, y, width, height)
        if rect is not None and paint_container is not None:
            draw_round_rect(canvas, rect, list(self.corner_radii_pixels(width, height)), paint_container)

        self.draw_state_layer(canvas, x, y, width, height)

        if self._editable.value:
            self._draw_editable(canvas, x, y)
        else:
            self._draw_placeholder(canvas, x, y, width, height)
            # The cursor still belongs on screen while the bar is focused and
            # empty, so the editable paints underneath the placeholder text.
            if self._editable.state.focused:
                self._draw_editable(canvas, x, y)

        self._draw_icons(canvas, x, y)

        if self.should_show_focus_ring:
            self.draw_focus_indicator(canvas, x, y, width, height)

    def _draw_editable(self, canvas, x: int, y: int) -> None:
        rect = self._editable.layout_rect
        if rect is None:
            return
        rel_x, rel_y, w, h = rect
        self._editable.set_last_rect(x + rel_x, y + rel_y, w, h)
        self._editable.paint(canvas, x + rel_x, y + rel_y, w, h)

    def _draw_placeholder(self, canvas, x: int, y: int, width: int, height: int) -> None:
        if not self._placeholder:
            return

        style = self.style
        font = self._get_font(style.font_size)
        if font is None:
            return

        color = resolve_color_to_rgba(style.supporting_text_color, theme=self._resolvable_theme())
        paint = make_paint(color=color)
        blob = make_text_blob(self._placeholder, font)
        if blob is None or paint is None:
            return

        metrics = font.getMetrics()
        baseline = y + (height - (-metrics.fAscent + metrics.fDescent)) / 2.0 - metrics.fAscent
        text_left, _ = self._slot_bounds(width)
        canvas.drawTextBlob(blob, x + text_left, baseline, paint)

    def _draw_icons(self, canvas, x: int, y: int) -> None:
        for icon in (self.leading_icon, self.trailing_icon):
            if icon is None:
                continue
            rect = icon.layout_rect
            if rect is None:
                continue
            ix, iy, iw, ih = rect
            icon.paint(canvas, x + ix, y + iy, iw, ih)


class _SearchPane(Widget):
    """The box a search bar is given, with the bar inset inside it.

    Owns the 24dp <-> 12dp margin animation. The child is the bar itself, or
    the bar wrapped in a popup modifier — either way it is laid out at the
    inset rect, so a popup anchored to it tracks the animation.
    """

    def __init__(
        self,
        child: Widget,
        *,
        core: _SearchBarCore,
        width: SizingLike = None,
    ) -> None:
        super().__init__(width=width)
        self._child = child
        self._core = core
        self._margin = Animatable(core.style.margin, motion=SEARCH_BAR_FOCUS_MARGIN)
        self.add_child(child)

    def on_mount(self) -> None:
        """Track focus for the margin target, and relayout as it animates."""
        super().on_mount()
        # Bound rather than subscribed bare: a running Animatable is held by
        # the clock, so a bare subscribe keeps every unmounted pane alive.
        self.bind(self._margin.subscribe(lambda _v: self.mark_needs_layout()))
        self.observe(self._core.focused, self._on_focus_changed)

    def _on_focus_changed(self, focused: bool) -> None:
        style = self._core.style
        self._margin.target = style.focused_margin if focused else style.margin

    def _bar_rect(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """Return the bar's rect inside this box: inset, capped, centred.

        The edges are **rounded**, and rounded as edges rather than as an
        origin and a size. Truncating instead turns the spring's settling
        overshoot -- five millionths of a pixel -- into a full-pixel jump on the
        one frame it happens, which reads as a visible twitch at the end of the
        animation. Rounding x and w independently has the same failure in
        slower motion: the two disagree by a pixel and the bar breathes.
        """
        style = self._core.style
        margin = float(self._margin.value)

        bar_w = width - 2.0 * margin
        if bar_w > style.max_width:
            # Cap and centre, rather than growing with the box.
            bar_w = style.max_width
        # ``min_width`` deliberately yields to a narrower box: overflowing the
        # allotted space is a worse failure than a sub-spec bar in a small
        # window.
        bar_w = max(0.0, min(bar_w, float(width)))

        left = (width - bar_w) / 2.0
        x0 = int(round(left))
        x1 = int(round(left + bar_w))
        return (x0, 0, x1 - x0, int(height))

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """As wide as allowed (or as sized), and as tall as the bar."""
        style = self._core.style
        w_dim = self.width_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        elif max_width is not None:
            width = int(max_width)
        else:
            width = int(style.min_width + 2 * style.margin)

        if max_width is not None:
            width = min(width, int(max_width))

        height = int(style.container_height)
        if max_height is not None:
            height = min(height, int(max_height))
        return (width, height)

    def layout(self, width: int, height: int) -> None:
        """Lay the child out at the inset bar rect."""
        super().layout(width, height)
        bx, by, bw, bh = self._bar_rect(width, height)
        self._child.layout(bw, bh)
        self._child.set_layout_rect(bx, by, bw, bh)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the child; the pane's own margins stay empty by design."""
        self.set_last_rect(x, y, width, height)
        rect = self._child.layout_rect
        if rect is None:
            return
        cx, cy, cw, ch = rect
        self._child.paint(canvas, x + cx, y + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        """Only the bar is interactive; the margins are not."""
        hit = self._child.hit_test(x, y)
        if hit is not None:
            return hit
        return None


class _DockedContainer(Widget):
    """The docked container: the surface below the bar.

    ``md.comp.search-view.contained.docked.results.shape`` (medium rounding) on
    ``surface-container-high``, with no elevation.
    """

    def __init__(
        self,
        content: Widget,
        *,
        style: DockedSearchBarStyle,
        bar_rect: Callable[[], Optional[Tuple[float, float, float, float]]],
        viewport_height: Callable[[], Optional[int]],
    ) -> None:
        super().__init__()
        self._content = content
        self._style = style
        self._bar_rect = bar_rect
        self._viewport_height = viewport_height
        self.add_child(content)

    def _resolvable_theme(self) -> "Theme | None":
        from nuiitivet.widgeting.context_lookup import is_premature_lookup

        if is_premature_lookup(self):
            return None

        from nuiitivet.theme.theme import Theme

        return Theme.of(self)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Match the bar's width; size the height to the MD3 range.

        ``min_height`` is a floor, not a preference: the container is never
        shrunk below it, and in a window with less room than that it simply
        overflows. That is the honest failure — a search bar does not belong
        somewhere its container cannot open, and a window too small to show
        them is not a case worth contorting the layout for. Overflowing stays
        harmless because ``popup`` never slides content along the placement
        axis, so an overflowing container cannot end up over the bar.

        The bounds cannot come from ``max_height``:
        ``_AnchoredOverlayPosition.layout`` measures its child through
        ``preferred_size(child)`` with no constraints at all, so an overlay's
        content is always measured unbounded. The viewport is resolved from the
        tree instead.
        """
        style = self._style

        bar = self._bar_rect()
        if bar is not None:
            width = int(bar[2])
        elif max_width is not None:
            width = min(int(max_width), int(style.bar.max_width))
        else:
            width = int(style.bar.min_width)

        viewport = self._viewport_height()
        if viewport is None and max_height is not None:
            viewport = int(max_height)

        _, content_h = self._content.preferred_size(width, viewport)
        height = int(content_h)

        if viewport is not None:
            height = min(height, int(viewport * style.max_height_ratio))
        # The floor is applied last, so it wins over the two-thirds cap in a
        # window short enough for the two to disagree.
        height = max(height, int(style.min_height))

        return (int(width), int(height))

    def layout(self, width: int, height: int) -> None:
        """Fill the container with the app's content widget."""
        super().layout(width, height)
        self._content.layout(width, height)
        self._content.set_layout_rect(0, 0, width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Draw the rounded surface, then the app's content on top."""
        if canvas is None:
            return

        self.set_last_rect(x, y, width, height)
        style = self._style

        color = resolve_color_to_rgba(style.container_color, theme=self._resolvable_theme())
        paint = make_paint(color=color)
        rect = make_rect(x, y, width, height)
        if rect is not None and paint is not None:
            draw_round_rect(canvas, rect, style.corner_radius, paint)

        rel = self._content.layout_rect
        if rel is None:
            return
        cx, cy, cw, ch = rel
        self._content.set_last_rect(x + cx, y + cy, cw, ch)
        self._content.paint(canvas, x + cx, y + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        """Route hits to the app's content first."""
        hit = self._content.hit_test(x, y)
        if hit is not None:
            return hit
        return super().hit_test(x, y)


class SearchBar(ComposableWidget):
    """Material Design 3 search bar (contained variant).

    The bar is drawn inset inside the box this widget is given: 24dp on each
    side, animating to 12dp while focused. ``width`` therefore names the
    **box**, not the bar — which keeps the widget's footprint stable when it is
    focused, instead of reflowing its siblings.

    There is no full-screen search widget. To build one, lay out your own
    screen and place a ``SearchBar`` in it; the bar brings its own margin
    animation with it.

    Args:
        value: Initial query text, or the observable holding it. Edits are
            written back to a writable observable, exactly as for ``TextField``.
        placeholder: Supporting text shown inside the bar while it is empty.
        leading_icon: Icon source (Symbol/str, or an Observable of them).
        on_tap_leading_icon: Makes the leading icon a tappable icon button.
        trailing_icon: Icon source for the trailing slot.
        on_tap_trailing_icon: Makes the trailing icon a tappable icon button.
            The slot is generic — clearing the query is one use of it, not a
            built-in behaviour.
        on_change: Callback invoked with the query as it changes, for a side
            effect of the change. The observable bound to *value* carries the
            same signal without it.
        on_submit: Callback invoked with the query when Enter is pressed.
            Fires on every press, including a repeat on an unchanged query,
            and never on focus loss.
        on_focus_change: Callback invoked as focus arrives and leaves, with
            ``(focused, source)`` -- the same signature as ``focusable()``. It
            can arrive more than once with ``focused=True`` for a single
            acquisition, because the *source* is re-announced when the user
            switches from keyboard to pointer; ``focused=False`` arrives once.
        input_filter: Rule applied to text as the user types it.
        width: Sizing for the **box**, not for the bar drawn inside it. The bar
            is the box minus the margins, so ``width=440`` draws a 392dp bar
            that grows to 416dp when the user clicks into it, while the
            widget's own footprint stays 440dp and nothing beside it moves. The
            bar is capped at 720dp and centred when the box is wider; in a box
            too narrow for the 360dp minimum it shrinks to fit rather than
            overflowing.
        style: Custom style configuration.
    """

    def __init__(
        self,
        value: Union[str, ReadOnlyObservableProtocol[str]] = "",
        *,
        placeholder: str | None = None,
        leading_icon: IconLike = "search",
        on_tap_leading_icon: Optional[Callable[[], None]] = None,
        trailing_icon: IconLike = None,
        on_tap_trailing_icon: Optional[Callable[[], None]] = None,
        on_change: Optional[Callable[[str], None]] = None,
        on_submit: Optional[Callable[[str], None]] = None,
        on_focus_change: Optional[FocusChangeCallback] = None,
        input_filter: Optional[InputFilterLike] = None,
        width: SizingLike = None,
        style: Optional[SearchBarStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        super().__init__(key=key)
        self._width = width
        # Built once and reused across rebuilds so focus and cursor position
        # survive recomposition.
        self._core = _SearchBarCore(
            value=value,
            placeholder=placeholder,
            leading_icon=leading_icon,
            on_tap_leading_icon=on_tap_leading_icon,
            trailing_icon=trailing_icon,
            on_tap_trailing_icon=on_tap_trailing_icon,
            on_change=on_change,
            on_submit=on_submit,
            on_focus_change=on_focus_change,
            input_filter=input_filter,
            style=style,
        )

    @property
    def value(self) -> str:
        """Return the current query text."""
        return self._core.value

    def focus(self) -> None:
        """Programmatically focus the bar."""
        self._core.focus()

    def build(self) -> Widget:
        """Return the pane, with the bar inset inside it."""
        return _SearchPane(self._core, core=self._core, width=self._width)


class DockedSearchBar(ComposableWidget):
    """Material Design 3 docked search (contained variant).

    A :class:`SearchBar` with a container anchored 2dp below it, holding
    whatever the query currently calls for — recent searches, suggestions,
    results, a spinner, "no matches". There is one slot, ``content``, and the
    application swaps what is inside it from its own observables; the widget
    only shows and hides the container. That also means the query pipeline
    keeps running while the container is closed, so gate it yourself if that
    matters.

    **When the container opens and closes.** The state is a single observable,
    writable at any time by the application, that this widget drives from four
    triggers:

    ==================================== ==================================
    Trigger                              Effect
    ==================================== ==================================
    Focus gained                         Open — including on an empty query,
                                         which is where MD3 shows recent
                                         searches
    User edits the text                  Open, even if it was just closed
    Enter                                Close when *close_on_enter*
    Focus lost, or a tap outside         Close
    ==================================== ==================================

    The second one is what makes "Enter closes the panel, results render on
    the page" work: focus never changed, so without it the panel could not
    come back. It counts *user* edits only — assigning to ``value``, or a
    write to the bound observable, does not reopen the container, so filling
    the bar in after a pick stays closed.

    Args:
        value: Initial query text, or the observable holding it.
        content: Widget rendered inside the docked container.
        is_open: Observable holding whether the container is open. Pass one to
            drive or observe it; when omitted an internal one is created and
            exposed as :attr:`is_open`.
        close_on_enter: Whether Enter closes the container. The default suits
            a page that renders its own results; pass ``False`` to keep the
            container up and swap ``content`` to the results instead. The
            close runs before *on_submit*, so a search that wants the
            container to stay up can reopen it from inside its own callback.
        placeholder: Supporting text shown inside the bar while it is empty.
        leading_icon: Icon source for the leading slot.
        on_tap_leading_icon: Makes the leading icon a tappable icon button.
        trailing_icon: Icon source for the trailing slot.
        on_tap_trailing_icon: Makes the trailing icon a tappable icon button.
        on_change: Callback invoked with the query as it changes, for a side
            effect of the change. The observable bound to *value* carries the
            same signal without it.
        on_submit: Callback invoked with the query when Enter is pressed.
            Fires on every press, including a repeat on an unchanged query,
            and never on focus loss.
        on_focus_change: Callback invoked as focus arrives and leaves, with
            ``(focused, source)`` -- the same signature as ``focusable()``. It
            can arrive more than once with ``focused=True`` for a single
            acquisition, because the *source* is re-announced when the user
            switches from keyboard to pointer; ``focused=False`` arrives once.
        input_filter: Rule applied to text as the user types it.
        width: Sizing for the box — see :class:`SearchBar`.
        style: Custom style configuration.
    """

    def __init__(
        self,
        value: Union[str, ReadOnlyObservableProtocol[str]] = "",
        *,
        content: Widget,
        is_open: Optional[Observable[bool]] = None,
        close_on_enter: bool = True,
        placeholder: str | None = None,
        leading_icon: IconLike = "search",
        on_tap_leading_icon: Optional[Callable[[], None]] = None,
        trailing_icon: IconLike = None,
        on_tap_trailing_icon: Optional[Callable[[], None]] = None,
        on_change: Optional[Callable[[str], None]] = None,
        on_submit: Optional[Callable[[str], None]] = None,
        on_focus_change: Optional[FocusChangeCallback] = None,
        input_filter: Optional[InputFilterLike] = None,
        width: SizingLike = None,
        style: Optional[DockedSearchBarStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        super().__init__(key=key)
        self._width = width
        self._style = style if style is not None else DockedSearchBarStyle()
        self._close_on_enter = bool(close_on_enter)
        self._on_submit = on_submit

        # Kept separate from ``core.focused`` so that an outside tap can close
        # the container (popup writes False here) without claiming the bar lost
        # focus.
        self._is_open: Observable[bool] = is_open if is_open is not None else Observable(False)

        # EditableText declines Enter when it has no on_submit, so the key
        # stays available to a shortcut. The wrapper is withheld unless Enter
        # has something to do here -- the app's callback, closing the
        # container, or both.
        wants_enter = on_submit is not None or self._close_on_enter

        self._core = _SearchBarCore(
            value=value,
            placeholder=placeholder,
            leading_icon=leading_icon,
            on_tap_leading_icon=on_tap_leading_icon,
            trailing_icon=trailing_icon,
            on_tap_trailing_icon=on_tap_trailing_icon,
            on_change=on_change,
            on_user_edit=self._handle_user_edit,
            on_submit=self._handle_submit if wants_enter else None,
            on_focus_change=on_focus_change,
            input_filter=input_filter,
            style=self._style.bar,
        )

        self._container = _DockedContainer(
            content,
            style=self._style,
            bar_rect=lambda: self._core.global_visual_rect,
            viewport_height=self._viewport_height,
        )

    def _viewport_height(self) -> Optional[int]:
        """Return the window's height, read from the topmost laid-out ancestor.

        The docked container lives in the overlay, which is measured
        unbounded, so it cannot learn the viewport from its own constraints.
        The bar is in the app's tree, and the root there is laid out at the
        window size.
        """
        node: Optional["WidgetKernel"] = self._core
        height: Optional[int] = None
        seen: set[int] = set()
        while node is not None and id(node) not in seen:
            seen.add(id(node))
            rect = node.layout_rect
            if rect is not None:
                height = int(rect[3])
            node = node.parent
        return height

    @property
    def value(self) -> str:
        """Return the current query text."""
        return self._core.value

    @property
    def is_open(self) -> Observable[bool]:
        """Observable holding whether the docked container is open.

        Writable: setting it opens or closes the container directly. The
        widget writes it too, on the triggers listed in the class docstring.
        """
        return self._is_open

    def focus(self) -> None:
        """Programmatically focus the bar."""
        self._core.focus()

    def on_mount(self) -> None:
        """Open the container whenever the bar takes focus."""
        super().on_mount()
        self.observe(self._core.focused, self._on_focus_changed)

    def _on_focus_changed(self, focused: bool) -> None:
        self._is_open.value = bool(focused)

    def _handle_user_edit(self, _text: str) -> None:
        """Reopen the container for text the user typed.

        Focus does not change when the container was closed by Enter or by the
        application, so this is the only trigger that can bring it back while
        the user keeps working in the bar.
        """
        self._is_open.value = True

    def _handle_submit(self, text: str) -> None:
        """Close the container, then hand the query to the application.

        Closing first lets a search that wants the container to stay up reopen
        it from inside its own callback, and keeps the close from being
        skipped when that callback raises.
        """
        if self._close_on_enter:
            self._is_open.value = False
        if self._on_submit is not None:
            self._on_submit(text)

    def build(self) -> Widget:
        """Return the pane, with a popup anchored to the inset bar.

        The popup's ``offset`` is constant: ``OverlayPosition.anchored``
        re-resolves the anchor rect on every layout pass, so anchoring to the
        bar (rather than to the pane) tracks the margin animation for free.

        ``flip=False`` keeps the container below the bar even when the window
        is too short for it: it overflows downwards rather than opening
        upwards. Opening above would also be correct MD3 — turn it on if that
        is wanted. Either way the bar is never covered, because ``popup`` only
        ever shifts content along the cross axis.
        """
        anchored = self._core.modifier(
            popup(
                self._container,
                is_open=self._is_open,
                target_anchor="bottom-left",
                content_anchor="top-left",
                offset=(0.0, self._style.gap),
                flip=False,
            )
        )
        return _SearchPane(anchored, core=self._core, width=self._width)


__all__ = ["SearchBar", "DockedSearchBar"]
