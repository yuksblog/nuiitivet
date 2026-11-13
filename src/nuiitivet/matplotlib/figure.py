"""A matplotlib ``Figure`` shown as a widget, drawn at the widget's device size in the theme's colors."""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, TypeVar

from nuiitivet.common.logging_once import exception_once
from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT, MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.matplotlib.theme_data import MatplotlibFigureThemeData
from nuiitivet.observable.protocols import StateBase
from nuiitivet.rendering.padding import PaddingLike
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import make_paint, make_rect
from nuiitivet.theme.dependency import theme_generation
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.theme import Theme
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgets.interaction import FocusNode, FocusSource, InteractionHostMixin, PointerListenerNode
from nuiitivet.widgets.raster_surface import RasterSurface

if TYPE_CHECKING:
    from matplotlib.figure import Figure


logger = logging.getLogger(__name__)

T = TypeVar("T")
_FigureWidget = TypeVar("_FigureWidget", bound="MatplotlibFigure")

#: Points per logical pixel: a 10pt label is 10pt on screen, as in the rest of the app.
_LOGICAL_DPI = 96.0

_TRANSPARENT = (0.0, 0.0, 0.0, 0.0)

#: The zoom rectangle's fill: the rubberband color at a state layer's opacity, under a one pixel outline.
_RUBBERBAND_FILL_ALPHA = 31

#: matplotlib's button numbers for the framework's button codes.
_BUTTONS = {BUTTON_LEFT: 1, BUTTON_MIDDLE: 2, BUTTON_RIGHT: 3}

#: Modifier names in the order matplotlib prefixes them to a key: ``ctrl+alt+shift+super+k``.
_MODIFIERS = ((MOD_CTRL, "ctrl"), (MOD_ALT, "alt"), (MOD_SHIFT, "shift"), (MOD_META, "super"))

#: The framework's key names that matplotlib spells differently.
_KEY_NAMES = {
    "space": " ",
    "return": "enter",
    "capslock": "caps_lock",
    "lshift": "shift",
    "rshift": "shift",
    "lctrl": "control",
    "rctrl": "control",
    "lalt": "alt",
    "ralt": "alt",
    "loption": "alt",
    "roption": "alt",
    "meta": "super",
    "lmeta": "super",
    "rmeta": "super",
    "lcommand": "super",
    "rcommand": "super",
    "lwindows": "super",
    "rwindows": "super",
    "minus": "-",
    "equal": "=",
    "plus": "+",
    "comma": ",",
    "period": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "grave": "`",
    "bracketleft": "[",
    "bracketright": "]",
}

#: A modifier pressed on its own is not its own prefix: ``shift``, never ``shift+shift``.
_MODIFIER_KEYS = {"shift": "shift", "control": "ctrl", "alt": "alt", "super": "super"}


class MatplotlibFigure(InteractionHostMixin, RasterSurface):
    """A matplotlib ``Figure`` as a widget, in the colors of the theme's :class:`MatplotlibFigureThemeData`.

    The figure is drawn with the Agg renderer at the widget's device size, so
    text and lines stay crisp on any display; the widget takes over the
    figure's canvas, size and dpi.

    With ``themed`` the figure follows the app's theme and switches with it:
    the figure and axes backgrounds become transparent, and text, ticks,
    spines and the series take the palette's colors, resolved against the
    theme on each draw. A series drawn in one of matplotlib's stock cycle
    colors takes the palette's series colors in turn; a color set by hand
    stays. The palette is the extension the theme's design system registered;
    a theme without one draws the neutral defaults. From a data source:
    :meth:`plot`.

    The figure takes the pointer, and the keyboard after a click on it, as
    matplotlib events: a handler connected with ``mpl_connect`` runs with the
    event in the figure's pixels and data coordinates, ``picker`` artists
    fire ``pick_event``, and the wheel arrives as ``scroll_event`` instead of
    scrolling the page behind. A key the figure does not consume goes on to
    the app's shortcuts. ``draw_idle()`` on the canvas redraws the figure on
    the next frame, once however often it is called. A
    :class:`MatplotlibController` made for the figure adds pan, zoom and the
    view history, driven from the app's own buttons.
    """

    def __init__(
        self,
        figure: "Figure",
        *,
        themed: bool = True,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> None:
        """Initialize a MatplotlibFigure showing *figure* as it is.

        Args:
            figure: The figure to show, drawn already.
            themed: Whether the figure takes the app theme's colors.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the figure.
            key: Stable widget identity for dev-bridge targeting and hot reload.

        Raises:
            ImportError: matplotlib is not installed; ``pip install nuiitivet[matplotlib]``.
        """
        try:
            import matplotlib.backends.backend_agg  # noqa: F401
        except ImportError as error:
            raise ImportError(
                "MatplotlibFigure needs matplotlib: install the extra with `pip install nuiitivet[matplotlib]`"
            ) from error
        super().__init__(self._render_figure, width=width, height=height, padding=padding, key=key)
        self._figure = figure
        self._canvas = _canvas_class()(figure)
        self._canvas.on_draw_idle = self._on_draw_idle
        self._drawing = False
        self._themed = bool(themed)
        self._theme_gen: Optional[int] = None
        self._applied_series: list[str] = []
        self._plot_fn: Optional[Callable[["Figure", Any], None]] = None
        self._pending_value: Any = None
        self._plot_pending = False
        # Where the pointer last was, in figure pixels: a key event carries it.
        self._pointer_px: tuple[float, float] = (0.0, 0.0)
        # The zoom rectangle being dragged, in figure pixels, or None.
        self._rubberband: Optional[tuple[float, float, float, float]] = None
        from nuiitivet.matplotlib.controller import MatplotlibController

        MatplotlibController._shown(figure, self)
        self._focus_node = FocusNode(traversable=False, on_key=self._on_key, on_key_up=self._on_key_up)
        self.add_node(self._focus_node)
        self.add_node(
            PointerListenerNode(
                on_press=self._on_press,
                on_move=self._on_move,
                on_release=self._on_release,
                on_enter=self._on_enter,
                on_leave=self._on_leave,
                on_scroll=self._on_scroll,
            )
        )

    @classmethod
    def plot(
        cls: type[_FigureWidget],
        figure: "Figure",
        data: StateBase[T],
        plot: Callable[["Figure", T], None],
        *,
        themed: bool = True,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> _FigureWidget:
        """Create a widget replotted from *data* on every change.

        Args:
            figure: The figure *plot* draws into.
            plot: Called as ``plot(figure, value)`` with the current value
                before the figure is drawn, whenever the value changes.
            data: The State the plot is made from.
            themed: Whether the figure takes the app theme's colors.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the figure.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        widget = cls(figure, themed=themed, width=width, height=height, padding=padding, key=key)
        widget._plot_fn = plot
        widget.observe(data, widget._on_data)
        return widget

    @property
    def figure(self) -> "Figure":
        """The figure shown."""
        return self._figure

    def layout(self, width: int, height: int) -> None:
        """Lay out, and queue a redraw when the theme changed since the last one."""
        super().layout(width, height)
        if self._themed and self._theme_gen is not None and theme_generation(self) != self._theme_gen:
            self.request_render()

    def _on_data(self, value: Any) -> None:
        self._pending_value = value
        self._plot_pending = True
        self.request_render()

    def _render_figure(self, width_px: int, height_px: int) -> Any:
        self._drawing = True
        try:
            return self._draw_figure(width_px, height_px)
        finally:
            self._drawing = False

    def _draw_figure(self, width_px: int, height_px: int) -> Any:
        figure = self._figure
        if self._plot_pending and self._plot_fn is not None:
            self._plot_pending = False
            try:
                self._plot_fn(figure, self._pending_value)
            except Exception:
                exception_once(logger, "matplotlib_figure_plot_exc", "MatplotlibFigure plot function raised")
        if self._themed:
            self._apply_theme()
        dpi = _LOGICAL_DPI * self.pixel_ratio
        figure.set_dpi(dpi)
        # Agg truncates the figure's size in pixels to an int; half a pixel
        # keeps a rounding error below the requested size from losing a row.
        figure.set_size_inches((width_px + 0.5) / dpi, (height_px + 0.5) / dpi, forward=False)
        self._canvas.draw()
        got = tuple(int(v) for v in self._canvas.get_width_height())
        if got != (width_px, height_px):
            exception_once(
                logger,
                "matplotlib_figure_size_exc",
                "matplotlib drew %s for a %s request",
                got,
                (width_px, height_px),
            )
            return None
        return self._canvas.buffer_rgba()

    def _on_draw_idle(self) -> None:
        # A draw_idle from inside a draw (a draw_event handler, the plot function) is already answered.
        if not self._drawing:
            self.request_render()

    # --- Rubberband ------------------------------------------------------------

    def _set_rubberband(self, rect: Optional[tuple[float, float, float, float]]) -> None:
        """Show the zoom rectangle *rect*, two corners in figure pixels, or none."""
        if rect != self._rubberband:
            self._rubberband = rect
            self.invalidate()

    @replay_safe
    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        """Paint the figure, and the zoom rectangle while one is dragged."""
        super().paint(canvas, x, y, width, height)
        if canvas is None or self._rubberband is None:
            return
        cx, cy, _cw, _ch = self.content_rect(x, y, width, height)
        ratio = self.pixel_ratio
        figure_height = float(self._figure.bbox.height)
        x0, y0, x1, y1 = self._rubberband
        left = cx + min(x0, x1) / ratio
        right = cx + max(x0, x1) / ratio
        top = cy + (figure_height - max(y0, y1)) / ratio
        bottom = cy + (figure_height - min(y0, y1)) / ratio
        rect = make_rect(left, top, right - left, bottom - top)
        if rect is None:
            return
        theme = Theme.of(self)
        colors = _palette(theme)
        spec = colors.rubberband if colors.rubberband is not None else colors.text
        r, g, b, _a = resolve_color_to_rgba(spec, theme=theme)
        fill = make_paint(color=(r, g, b, _RUBBERBAND_FILL_ALPHA), style="fill")
        outline = make_paint(color=(r, g, b, 255), style="stroke", stroke_width=1.0)
        try:
            if fill is not None:
                canvas.drawRect(rect, fill)
            if outline is not None:
                canvas.drawRect(rect, outline)
        except Exception:
            exception_once(logger, "matplotlib_figure_rubberband_exc", "the zoom rectangle could not be painted")

    # --- Events ----------------------------------------------------------------

    def _figure_xy(self, event: PointerEvent) -> tuple[float, float]:
        """The pointer in the figure's pixels: device pixels from its bottom-left corner."""
        left, top, _right, _bottom = self.padding
        ratio = self.pixel_ratio
        x = (event.local_x - left) * ratio
        y = float(self._figure.bbox.height) - (event.local_y - top) * ratio
        return x, y

    def _deliver(self, event: Any) -> None:
        try:
            event._process()
        except Exception:
            exception_once(logger, "matplotlib_figure_handler_exc", "a matplotlib event handler raised")

    def _mouse(
        self,
        name: str,
        event: PointerEvent,
        *,
        button: Optional[int] = None,
        step: float = 0,
        buttons: Optional[frozenset[int]] = None,
    ) -> None:
        from matplotlib.backend_bases import MouseButton, MouseEvent

        x, y = self._figure_xy(event)
        self._pointer_px = (x, y)
        self._deliver(
            MouseEvent(
                name,
                self._canvas,
                int(x),
                int(y),
                button=None if button is None else MouseButton(button),
                step=step,
                buttons=None if buttons is None else [MouseButton(number) for number in buttons],
                modifiers=_mpl_modifiers(event.modifier_keys),
            )
        )

    def _location(self, name: str, event: PointerEvent) -> None:
        from matplotlib.backend_bases import LocationEvent

        x, y = self._figure_xy(event)
        self._pointer_px = (x, y)
        self._deliver(
            LocationEvent(name, self._canvas, int(x), int(y), modifiers=_mpl_modifiers(event.modifier_keys))
        )

    def _on_press(self, event: PointerEvent) -> None:
        self._focus_node.request_focus(FocusSource.POINTER)
        self._mouse("button_press_event", event, button=_mpl_button(event.button))

    def _on_move(self, event: PointerEvent) -> None:
        self._mouse("motion_notify_event", event, buttons=_mpl_buttons(event.buttons))

    def _on_release(self, event: PointerEvent) -> None:
        self._mouse("button_release_event", event, button=_mpl_button(event.button))

    def _on_scroll(self, event: PointerEvent) -> None:
        # The framework counts a wheel step toward the user as positive; matplotlib counts it as "down".
        step = -float(event.scroll_y)
        if step != 0:
            self._mouse("scroll_event", event, step=step)

    def _on_enter(self, event: PointerEvent) -> None:
        self._location("figure_enter_event", event)

    def _on_leave(self, event: PointerEvent) -> None:
        self._location("figure_leave_event", event)

    def _on_key(self, key: str, modifier_keys: int) -> bool:
        self._key("key_press_event", key, modifier_keys)
        return False

    def _on_key_up(self, key: str, modifier_keys: int) -> bool:
        self._key("key_release_event", key, modifier_keys)
        return False

    def _key(self, name: str, key: str, modifier_keys: int) -> None:
        from matplotlib.backend_bases import KeyEvent

        x, y = self._pointer_px
        self._deliver(KeyEvent(name, self._canvas, _mpl_key(key, modifier_keys), int(x), int(y)))

    # --- Theme ---------------------------------------------------------------

    def _apply_theme(self) -> None:
        theme = Theme.of(self)
        self._theme_gen = theme_generation(self)
        colors = _palette(theme)
        on_surface = _hex(colors.text, theme)
        on_surface_variant = _hex(colors.ticks, theme)
        outline_variant = _hex(colors.outline, theme)
        series = [_hex(spec, theme) for spec in colors.series]
        recolor = _series_mapping(self._applied_series, series)
        self._applied_series = series

        figure = self._figure
        figure.patch.set_facecolor(_TRANSPARENT)
        for text in figure.texts:
            text.set_color(on_surface)
        for ax in figure.axes:
            ax.set_facecolor(_TRANSPARENT)
            for spine in ax.spines.values():
                spine.set_color(outline_variant)
            ax.tick_params(axis="both", which="both", colors=on_surface_variant, labelcolor=on_surface_variant)
            ax.xaxis.label.set_color(on_surface)
            ax.yaxis.label.set_color(on_surface)
            ax.title.set_color(on_surface)
            for gridline in ax.get_xgridlines() + ax.get_ygridlines():
                gridline.set_color(outline_variant)
            _recolor_artists(ax.get_lines(), recolor)
            _recolor_artists(ax.patches, recolor)
            _recolor_collections(ax.collections, recolor)
            legend = ax.get_legend()
            if legend is not None:
                if colors.legend is not None:
                    legend.get_frame().set_facecolor(_hex(colors.legend, theme))
                legend.get_frame().set_edgecolor(outline_variant)
                for text in legend.get_texts():
                    text.set_color(on_surface)
                _recolor_artists(getattr(legend, "legend_handles", ()), recolor)
            if series:
                ax.set_prop_cycle(color=series)


@functools.lru_cache(maxsize=1)
def _canvas_class() -> Any:
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    class WidgetCanvas(FigureCanvasAgg):
        """An Agg canvas whose ``draw_idle`` is answered by the widget on the next frame."""

        on_draw_idle: Optional[Callable[[], None]] = None

        def draw_idle(self, *args: Any, **kwargs: Any) -> None:
            if self.on_draw_idle is not None:
                self.on_draw_idle()

    return WidgetCanvas


def _mpl_button(button: Optional[int]) -> Optional[int]:
    """matplotlib's number for a button code; a synthetic press without one is the left button."""
    if button is None:
        return 1
    return _BUTTONS.get(button)


def _mpl_buttons(mask: int) -> frozenset[int]:
    return frozenset(number for code, number in _BUTTONS.items() if mask & code)


def _mpl_modifiers(modifier_keys: int) -> frozenset[str]:
    return frozenset(name for mask, name in _MODIFIERS if modifier_keys & mask)


def _mpl_key(key: str, modifier_keys: int) -> str:
    """matplotlib's name for a key press: modifiers first, a shifted letter as its capital."""
    name = key.strip().lower()
    if len(name) == 2 and name[0] == "_" and name[1].isdigit():
        name = name[1]
    name = _KEY_NAMES.get(name, name)
    mods = [label for mask, label in _MODIFIERS if modifier_keys & mask]
    own = _MODIFIER_KEYS.get(name)
    if own in mods:
        mods.remove(own)
    if len(name) == 1 and name.isalpha():
        if "shift" in mods:
            mods.remove("shift")
            name = name.upper()
    return "+".join(mods + [name])


def _palette(theme: Theme) -> MatplotlibFigureThemeData:
    """The figure palette *theme*'s design system registered, else the neutral defaults."""
    palette = theme.extension(MatplotlibFigureThemeData)
    return palette if palette is not None else MatplotlibFigureThemeData()


def _hex(spec: ColorSpec, theme: Theme) -> str:
    r, g, b, _a = resolve_color_to_rgba(spec, theme=theme)
    return f"#{r:02x}{g:02x}{b:02x}"


def _series_mapping(previous: list[str], current: list[str]) -> dict[str, str]:
    """Which colors a series may hold that mean "the n-th theme color": the stock cycle, and the last theme's."""
    import matplotlib
    from matplotlib.colors import to_hex

    if not current:
        return {}
    stock = [to_hex(c).lower() for c in matplotlib.rcParamsDefault["axes.prop_cycle"].by_key()["color"]]
    mapping = {color: current[i % len(current)] for i, color in enumerate(stock)}
    mapping.update({color: current[i % len(current)] for i, color in enumerate(previous)})
    return mapping


def _mapped(color: Any, recolor: dict[str, str]) -> Optional[str]:
    from matplotlib.colors import to_hex

    try:
        return recolor.get(to_hex(color).lower())
    except (ValueError, TypeError):
        return None


def _recolor_artists(artists: Iterable[Any], recolor: dict[str, str]) -> None:
    for artist in artists:
        if hasattr(artist, "get_color") and hasattr(artist, "set_color"):
            mapped = _mapped(artist.get_color(), recolor)
            if mapped is not None:
                artist.set_color(mapped)
            continue
        if hasattr(artist, "get_facecolor"):
            mapped = _mapped(artist.get_facecolor(), recolor)
            if mapped is not None:
                artist.set_facecolor(mapped)
        if hasattr(artist, "get_edgecolor"):
            mapped = _mapped(artist.get_edgecolor(), recolor)
            if mapped is not None:
                artist.set_edgecolor(mapped)


def _recolor_collections(collections: Iterable[Any], recolor: dict[str, str]) -> None:
    for collection in collections:
        for getter, setter in (("get_facecolor", "set_facecolor"), ("get_edgecolor", "set_edgecolor")):
            colors = getattr(collection, getter)()
            if len(colors) == 0:
                continue
            mapped = [_mapped(color, recolor) for color in colors]
            if any(m is not None for m in mapped):
                getattr(collection, setter)([m if m is not None else tuple(c) for m, c in zip(mapped, colors)])


__all__ = ["MatplotlibFigure"]
