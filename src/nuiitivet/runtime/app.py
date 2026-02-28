"""App runner that can render a widget tree to an image using Skia."""

import logging
import os
import sys
import time
import traceback
import warnings
import weakref
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..widgeting.widget import ComposableWidget, Widget
from .pointer import PointerCaptureManager
from nuiitivet.input.pointer import PointerEvent, PointerEventType, PointerType
from ..widgeting.widget_binding import flush_binding_invalidations
from ..widgeting.widget_builder import flush_scope_recompositions

from ..rendering.skia import make_raster_surface, require_skia, rgba_to_skia_color, save_png
from ..theme import manager as theme_manager
from nuiitivet.theme.plain_theme import PlainColorRole, PlainTheme
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec
from ..widgets.interaction import FocusNode, InteractionHostMixin
from nuiitivet.common.logging_once import debug_once, exception_once
from .app_events import (
    dispatch_mouse_motion as _dispatch_mouse_motion_fn,
    dispatch_mouse_press as _dispatch_mouse_press_fn,
    dispatch_mouse_release as _dispatch_mouse_release_fn,
    dispatch_mouse_scroll as _dispatch_mouse_scroll_fn,
)
from .title_bar import TitleBar, DefaultTitleBar, CustomTitleBar, WindowDragArea
from .window import WindowSizingLike, WindowPosition, parse_window_sizing
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container

if TYPE_CHECKING:
    from nuiitivet.navigation.navigator import Navigator
    from nuiitivet.navigation.route import Route
    from nuiitivet.overlay.overlay import Overlay


logger = logging.getLogger(__name__)

NavigatorFactory = Callable[
    ["Route", Mapping[type[Any], Callable[[Any], "Route | Widget"]] | None],
    "Navigator",
]


# NOTE: compatibility wrapper removed. Use `resolve_color_to_rgba` from
# `nuiitivet.theme.resolver` to resolve theme ColorRole/ColorLike values to
# an (r,g,b,a) tuple. The app stores a primitive (RGBA tuple) or a
# backend-specific color object (converted below) in `_background_color`.


class AppProxy:
    """Proxy for interacting with the App instance from the widget tree.

    This class provides a restricted interface to the App instance, primarily
    for dispatching intents.
    """

    def __init__(self, app: "App") -> None:
        self._app = weakref.ref(app)

    def dispatch(self, intent: Any) -> None:
        """Dispatch an intent to the application."""
        app = self._app()
        if app is not None:
            app.dispatch(intent)


class AppScope(Widget):
    """Inherited widget that provides access to the App instance."""

    def __init__(self, app: "App", child: Widget) -> None:
        super().__init__()
        self.app_proxy = AppProxy(app)
        self.add_child(child)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        for child in self.children:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)


class App:
    """Application runner."""

    @staticmethod
    def _resolve_window_sizing(spec: WindowSizingLike, *, preferred: int, fallback: int) -> int:
        sizing = parse_window_sizing(spec)
        if sizing.kind == "fixed":
            value = int(sizing.value)
            if value <= 0:
                raise ValueError("window sizing must be positive")
            return value

        if sizing.kind == "auto":
            resolved = int(preferred) if int(preferred) > 0 else int(fallback)
            return max(1, resolved)

        raise ValueError(f"Unsupported window sizing kind: {sizing.kind!r}")

    @staticmethod
    def of(context: Widget) -> AppProxy:
        """Get the AppProxy for the given context.

        Args:
            context: The widget context.

        Returns:
            The AppProxy instance.

        Raises:
            RuntimeError: If the widget is not attached to an App.
        """
        scope = context.find_ancestor(AppScope)
        if scope is None:
            raise RuntimeError("AppScope not found. Is the widget attached to an App?")
        return scope.app_proxy

    @staticmethod
    def _build_root_navigation_stack(
        *,
        initial: "Route",
        intent_routes: Mapping[type[Any], Callable[[Any], "Route | Widget"]] | None,
        overlay_factory: Callable[[], "Overlay"] | None,
        navigator_factory: NavigatorFactory | None = None,
    ) -> tuple[Widget, Widget | None]:
        from nuiitivet.layout.stack import Stack
        from nuiitivet.navigation import Navigator, Route
        from nuiitivet.overlay import Overlay
        from nuiitivet.rendering.sizing import Sizing

        resolved_overlay_factory = overlay_factory or Overlay
        overlay = resolved_overlay_factory()
        if not isinstance(overlay, Overlay):
            raise TypeError("overlay_factory must return an Overlay instance")
        Overlay.set_root(overlay)

        def _default_navigator_factory(
            initial_route: Route,
            routes: Mapping[type[Any], Callable[[Any], "Route | Widget"]] | None,
        ) -> Navigator:
            return Navigator(routes=[initial_route], intent_routes=routes)

        resolved_navigator_factory = navigator_factory or _default_navigator_factory
        navigator = resolved_navigator_factory(initial, intent_routes)
        if not isinstance(navigator, Navigator):
            raise TypeError("navigator_factory must return a Navigator instance")
        Navigator.set_root(navigator)

        initial_route_widget: Widget | None = None
        try:
            initial_route_widget = navigator._route_widget(initial)  # type: ignore[attr-defined]
        except Exception:
            exception_once(logger, "navigator_route_widget_prime_exc", "Failed to prime initial route widget")

        navigator.width_sizing = Sizing.flex(100)
        navigator.height_sizing = Sizing.flex(100)
        overlay.width_sizing = Sizing.flex(100)
        overlay.height_sizing = Sizing.flex(100)

        root_widget = Stack(children=[navigator, overlay], width="100%", height="100%")
        return root_widget, initial_route_widget

    def _init_common(
        self,
        *,
        root: Widget,
        width: WindowSizingLike,
        height: WindowSizingLike,
        title_bar: Optional[TitleBar],
        background: ColorSpec,
        theme: Optional[Any] = None,
        window_position: WindowPosition | None = None,
        window_auto_size_target: Widget | None = None,
    ) -> None:
        if not isinstance(root, Widget):
            raise TypeError("App.root must be a Widget instance.")

        if theme is None:
            theme = PlainTheme.light()
        theme_manager.set_theme(theme)

        self.root = root

        pref_w = 0
        pref_h = 0
        width_sizing = parse_window_sizing(width)
        height_sizing = parse_window_sizing(height)
        needs_auto_size = width_sizing.kind == "auto" or height_sizing.kind == "auto"
        if window_auto_size_target is not None and needs_auto_size:
            target = window_auto_size_target
            built_for_sizing: Widget | None = None
            if isinstance(target, ComposableWidget):
                try:
                    built = target.evaluate_build()
                    if built is not None and built is not target:
                        target = built
                        built_for_sizing = built
                except Exception:
                    target = window_auto_size_target
            try:
                pref_w, pref_h = target.preferred_size()
            except Exception:
                pref_w, pref_h = 0, 0

            if built_for_sizing is not None:
                try:
                    built_for_sizing.unmount()
                except Exception:
                    pass

        # Include custom title bar preferred height for auto sizing.
        if isinstance(title_bar, CustomTitleBar) and needs_auto_size:
            title_target: Widget = title_bar.content
            built_title_target: Widget | None = None
            if isinstance(title_target, ComposableWidget):
                try:
                    built = title_target.evaluate_build()
                    if built is not None and built is not title_target:
                        title_target = built
                        built_title_target = built
                except Exception:
                    title_target = title_bar.content
            try:
                tw, th = title_target.preferred_size()
            except Exception:
                tw, th = 0, 0
            pref_w = max(int(pref_w), int(tw))
            pref_h = int(pref_h) + int(th)

            if built_title_target is not None:
                try:
                    built_title_target.unmount()
                except Exception:
                    pass

        self.width = self._resolve_window_sizing(width, preferred=int(pref_w), fallback=640)
        self.height = self._resolve_window_sizing(height, preferred=int(pref_h), fallback=480)
        self.window_position = window_position

        if title_bar is None:
            title_bar = DefaultTitleBar()

        self.title_bar = title_bar

        if isinstance(self.title_bar, CustomTitleBar):
            # We need a reference to the drag area to notify it of window moves
            self._window_drag_area: Optional[WindowDragArea] = None

            def on_drag(dx: float, dy: float):
                win = getattr(self, "_window", None)
                if win is not None:
                    try:
                        wx, wy = win.get_location()
                        # Note: We assume dx/dy and get_location/set_location use the same units (logical or physical).
                        # If there is a mismatch (e.g. HiDPI), this might need adjustment.
                        win.set_location(int(wx + dx), int(wy + dy))

                        # Notify the drag area to adjust internal state to prevent jitter
                        if self._window_drag_area:
                            self._window_drag_area.notify_window_moved(dx, dy)
                    except Exception:
                        exception_once(logger, "app_custom_title_bar_drag_exc", "Failed to move window")

            self._window_drag_area = WindowDragArea(
                child=self.title_bar.content,
                on_drag=on_drag,
                width="100%",
            )

            self.root = Column(
                children=[
                    self._window_drag_area,
                    Container(child=self.root, width="100%", height="100%"),
                ],
                width="100%",
                height="100%",
            )

        # Wrap the root widget with AppScope to provide access to the App instance
        self.root = AppScope(app=self, child=self.root)

        self._scale = 1.0
        self._dirty = False
        self._window = None
        self._event_loop: Any = None
        self._preferred_draw_fps: Optional[float] = 30.0
        self._last_hover_target = None
        self._focused_target: Optional[InteractionHostMixin] = None
        self._focused_node: Optional[FocusNode] = None
        self._pointer_capture_manager = PointerCaptureManager()
        self._pointer_capture_manager.set_cancel_callback(self._handle_pointer_cancel)
        self._primary_pointer_id = 1
        self._background_value: ColorSpec = background
        self._background_color: Any = None
        self._theme_subscription: Optional[Callable[[Any], None]] = None
        self._update_background_color()
        self._subscribe_theme_updates()
        self._last_layout_size: Optional[tuple[int, int]] = None
        self._saved_window_rect: Optional[tuple[int, int, int, int]] = None

        def _env_flag(name: str, default: bool = False) -> bool:
            raw = os.environ.get(name)
            if raw is None:
                return default
            value = str(raw).strip().lower()
            if value in ("", "0", "false", "no", "off", "disable", "disabled"):
                return False
            if value in ("1", "true", "yes", "on", "enable", "enabled"):
                return True
            return True

        self._debug_invalidate = _env_flag("NUIITIVET_DEBUG_INVALIDATE", default=False)
        self._invalidate_report_every_s = float(os.environ.get("NUIITIVET_DEBUG_INVALIDATE_EVERY", "1.0"))
        self._invalidate_report_every_s = max(0.1, self._invalidate_report_every_s)
        self._invalidate_interval_counts: dict[str, int] = {}
        self._invalidate_total_counts: dict[str, int] = {}
        self._invalidate_last_report = time.perf_counter()

    def can_handle_back_event(self) -> bool:
        """Return True if a back action would be handled.

        This is a non-mutating check used by backends to decide whether to
        consume the OS/back key or let default handlers run (e.g. ESC-to-exit).
        """

        overlay = None
        try:
            from nuiitivet.overlay import Overlay

            overlay = Overlay.root()
        except Exception:
            exception_once(logger, "app_overlay_root_exc", "Overlay.root() failed")
            overlay = None

        if overlay is not None:
            try:
                if overlay.has_entries():
                    return True
            except Exception:
                exception_once(logger, "app_overlay_has_entries_exc", "overlay.has_entries() failed")

        navigator = None
        try:
            from nuiitivet.navigation import Navigator

            navigator = Navigator.root()
        except Exception:
            exception_once(logger, "app_navigator_root_exc", "Navigator.root() failed")
            navigator = None

        if navigator is not None:
            try:
                return bool(navigator.can_pop())
            except Exception:
                exception_once(logger, "app_navigator_can_pop_exc", "navigator.can_pop() failed")
                return False

        return False

    def handle_back_event(self) -> bool:
        """Handle a user back action (e.g. Esc).

        Priority:
        - Overlay: close topmost entry if any
        - Navigator: pop one route if possible
        """

        overlay = None
        try:
            from nuiitivet.overlay import Overlay

            overlay = Overlay.root()
        except Exception:
            exception_once(logger, "app_overlay_root_handle_back_exc", "Overlay.root() failed (handle_back_event)")
            overlay = None

        if overlay is not None:
            try:
                has_entries = bool(overlay.has_entries())
                if has_entries:
                    overlay.close_topmost()
                    return True
            except Exception:
                exception_once(logger, "app_overlay_close_topmost_exc", "overlay.close_topmost() failed")

        navigator = None
        try:
            from nuiitivet.navigation import Navigator

            navigator = Navigator.root()
        except Exception:
            exception_once(logger, "app_navigator_root_handle_back_exc", "Navigator.root() failed (handle_back_event)")
            navigator = None

        if navigator is not None:
            try:
                request_back = getattr(navigator, "request_back", None)
                if callable(request_back):
                    handled = bool(request_back())
                    return handled
                if navigator.can_pop():
                    navigator.pop()
                    return True
            except Exception:
                exception_once(logger, "app_navigator_back_exc", "Navigator back handling failed")
        return False

    @classmethod
    def navigation(
        cls,
        *,
        routes: Mapping[type[Any], Callable[[Any], "Route | Widget"]],
        initial_route: Any,
        overlay_factory: Callable[[], "Overlay"] | None = None,
        navigator_factory: NavigatorFactory | None = None,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        title_bar: Optional[TitleBar] = None,
        background: ColorSpec = PlainColorRole.SURFACE,
        theme: Optional[Any] = None,
        window_position: WindowPosition | None = None,
    ) -> "App":
        """Create an App with a root Navigator and Overlay.

        This provides the Phase 6 initialization pattern:
        - Navigator.root() / Overlay.root() are set
        - The UI is stacked as [Navigator, Overlay]
        """

        from nuiitivet.navigation import PageRoute, Route

        try:
            factory = routes[type(initial_route)]
        except Exception as exc:
            raise RuntimeError(f"No route is registered for intent: {type(initial_route).__name__}") from exc

        resolved = factory(initial_route)
        if isinstance(resolved, Route):
            initial = resolved
        elif isinstance(resolved, Widget):
            widget = resolved
            initial = PageRoute(builder=lambda: widget)
        else:
            raise TypeError("Route factory must return a Route or Widget.")

        root_widget, initial_route_widget = cls._build_root_navigation_stack(
            initial=initial,
            intent_routes=routes,
            overlay_factory=overlay_factory,
            navigator_factory=navigator_factory,
        )
        self = cls.__new__(cls)
        self._init_common(
            root=root_widget,
            width=width,
            height=height,
            title_bar=title_bar,
            background=background,
            theme=theme,
            window_position=window_position,
            window_auto_size_target=initial_route_widget,
        )
        return self

    def __init__(
        self,
        content: Widget,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        *,
        title_bar: Optional[TitleBar] = None,
        background: ColorSpec = PlainColorRole.SURFACE,
        overlay_factory: Callable[[], "Overlay"] | None = None,
        navigator_factory: NavigatorFactory | None = None,
        theme: Optional[Any] = None,
        window_position: WindowPosition | None = None,
    ):
        """Initialize App with a root Navigator and Overlay."""
        if not isinstance(content, Widget):
            raise TypeError("'content' must be a Widget instance.")

        from nuiitivet.navigation import PageRoute

        from nuiitivet.navigation.transition_spec import Transitions

        initial = PageRoute(builder=lambda: content, transition_spec=Transitions.empty())
        root_widget, initial_route_widget = self._build_root_navigation_stack(
            initial=initial,
            intent_routes=None,
            overlay_factory=overlay_factory,
            navigator_factory=navigator_factory,
        )
        self._init_common(
            root=root_widget,
            width=width,
            height=height,
            title_bar=title_bar,
            background=background,
            theme=theme,
            window_position=window_position,
            window_auto_size_target=initial_route_widget,
        )

    def _debug_record_invalidate(self) -> None:
        if not self._debug_invalidate:
            return

        # Extract a small stack and pick the first meaningful callsite above
        # framework internals. This is intentionally lightweight and best-effort.
        ignore_suffixes = (
            "/nuiitivet/core/app.py",
            "/nuiitivet/widgeting/widget.py",
            "/nuiitivet/widgeting/widget_builder.py",
            "/nuiitivet/widgeting/widget_binding.py",
        )
        try:
            stack = traceback.extract_stack(limit=12)
        except Exception:
            exception_once(logger, "app_debug_extract_stack_exc", "traceback.extract_stack failed")
            return

        callsite = None
        # Walk from the immediate caller outward.
        for frame in reversed(stack[:-1]):
            filename = frame.filename.replace("\\", "/")
            if any(filename.endswith(sfx) for sfx in ignore_suffixes):
                continue
            callsite = f"{filename}:{frame.lineno} {frame.name}"
            break
        if callsite is None:
            fallback_frame = stack[-2] if len(stack) >= 2 else None
            if fallback_frame is None:
                return
            filename = fallback_frame.filename.replace("\\", "/")
            callsite = f"{filename}:{fallback_frame.lineno} {fallback_frame.name}"

        self._invalidate_interval_counts[callsite] = self._invalidate_interval_counts.get(callsite, 0) + 1
        self._invalidate_total_counts[callsite] = self._invalidate_total_counts.get(callsite, 0) + 1

        now = time.perf_counter()
        if now - self._invalidate_last_report < self._invalidate_report_every_s:
            return
        self._invalidate_last_report = now

        items = sorted(self._invalidate_interval_counts.items(), key=lambda kv: kv[1], reverse=True)
        self._invalidate_interval_counts = {}

        if not items:
            return
        top = items[:8]
        msg = ", ".join(f"{count}x {site}" for site, count in top)
        try:
            print(f"[nuiitivet] invalidate top: {msg}", file=sys.stderr, flush=True)
        except Exception:
            exception_once(logger, "app_invalidate_top_print_exc", "Failed to print invalidate top stats")

    def __del__(self):  # pragma: no cover - best-effort leak guard
        try:
            self._unsubscribe_theme_updates()
        except Exception:
            exception_once(logger, "app_del_unsubscribe_theme_exc", "_unsubscribe_theme_updates raised in __del__")

    def render_to_png(self, path: str):
        img = self._render_snapshot(scale=1.0)
        save_png(img, path)

    def _background_uses_theme(self) -> bool:
        from nuiitivet.theme.types import ColorToken

        val = self._background_value
        if isinstance(val, ColorToken):
            return True
        if isinstance(val, tuple) and len(val) >= 1:
            return isinstance(val[0], ColorToken)
        return False

    def _update_background_color(self) -> None:
        if self._background_value is None:
            raise ValueError("App background color could not be resolved")
        try:
            rgba = resolve_color_to_rgba(self._background_value, theme=theme_manager.current)
        except Exception as exc:
            raise ValueError("App background color could not be resolved") from exc
        if rgba is None:
            raise ValueError("App background color could not be resolved")

        self._background_color = rgba

    def _background_clear_color(self):
        if self._background_color is None:
            self._update_background_color()
        return self._background_color

    def _subscribe_theme_updates(self) -> None:
        if not self._background_uses_theme():
            return
        if self._theme_subscription is not None:
            return
        app_ref = weakref.ref(self)

        def _on_theme(_theme):
            app = app_ref()
            if app is None:
                try:
                    theme_manager.unsubscribe(_on_theme)
                except Exception:
                    exception_once(logger, "app_theme_unsubscribe_dead_exc", "ThemeManager.unsubscribe raised")
                return
            app._update_background_color()
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "app_theme_invalidate_exc", "App.invalidate raised in theme callback")

        try:
            theme_manager.subscribe(_on_theme)
            self._theme_subscription = _on_theme
        except Exception:
            exception_once(logger, "app_theme_subscribe_exc", "ThemeManager.subscribe raised")
            self._theme_subscription = None

    def _unsubscribe_theme_updates(self) -> None:
        callback = getattr(self, "_theme_subscription", None)
        if callback is None:
            return
        try:
            theme_manager.unsubscribe(callback)
        except Exception:
            exception_once(logger, "app_theme_unsubscribe_exc", "ThemeManager.unsubscribe raised")
        self._theme_subscription = None

    def _mount_paint_unmount(self, canvas, x: int, y: int, w: int, h: int) -> None:
        """Temporarily mount the root widget, paint it, then unmount.

        All exceptions are converted to warnings to avoid crashing render
        paths while preserving debugging information.
        """
        if not self.root:
            return

        # Check if already mounted (e.g. running in App.run)
        is_mounted = getattr(self.root, "_app", None) is not None

        if not is_mounted:
            try:
                self.root.mount(self)
            except Exception as e:
                warnings.warn(f"root.mount() failed: {e}", RuntimeWarning, stacklevel=2)

        try:
            needs_layout = getattr(self.root, "needs_layout", True)
            last_size = getattr(self, "_last_layout_size", None)
            current_size = (w, h)

            if needs_layout or last_size != current_size:
                self.root.layout(w, h)
                self._last_layout_size = current_size
                try:
                    self.root.clear_needs_layout()
                except Exception as e:
                    warnings.warn(f"root.clear_needs_layout() failed: {e}", RuntimeWarning, stacklevel=2)
        except Exception as e:
            warnings.warn(f"root.layout() failed: {e}", RuntimeWarning, stacklevel=2)

        try:
            self.root.paint(canvas, x, y, w, h)
        except Exception as e:
            warnings.warn(f"root.paint() failed: {e}", RuntimeWarning, stacklevel=2)

        if not is_mounted:
            try:
                self.root.unmount()
            except Exception as e:
                warnings.warn(f"root.unmount() failed: {e}", RuntimeWarning, stacklevel=2)

    # --- Window / interactive runtime ---------------------------------
    def invalidate(self, immediate: bool = False):
        """Request that the next frame be redrawn.

        This sets an internal dirty flag which the render loop checks to
        decide whether to re-render the UI.

        Args:
            immediate: If True and running in pyglet, bypass FPS throttle for next draw
        """
        self._dirty = True
        self._debug_record_invalidate()
        loop = self._event_loop
        if loop is not None:
            try:
                loop.request_draw(immediate=immediate)
            except Exception:
                exception_once(logger, "app_request_draw_exc", "Event loop request_draw raised")

    def _render_to_png_bytes(self) -> bytes:
        """Render the root widget to PNG bytes (raster surface).

        Uses `self._scale` when available to generate a high-DPI image.
        """
        scale = max(1.0, float(getattr(self, "_scale", 1.0)))
        img = self._render_snapshot(scale=scale)
        data = img.encodeToData()
        if data is None:
            raise RuntimeError("encodeToData() returned None (failed to encode image)")
        return bytes(data)

    def _render_snapshot(self, scale: float = 1.0):
        """Create a Skia image snapshot for the current root at given scale.

        Returns an image object. Raises RuntimeError if Skia is missing or
        snapshot/encoding fails.
        """
        try:
            flush_binding_invalidations()
        except Exception:
            exception_once(logger, "app_snapshot_flush_binding_invalidations_exc", "flush_binding_invalidations failed")
        try:
            flush_scope_recompositions()
        except Exception:
            exception_once(logger, "app_snapshot_flush_scope_recompositions_exc", "flush_scope_recompositions failed")
        require_skia()

        phys_w = max(1, int(self.width * scale))
        phys_h = max(1, int(self.height * scale))

        surface = make_raster_surface(phys_w, phys_h)
        canvas = surface.getCanvas()

        # Map logical coordinates to device pixels
        if scale != 1.0:
            canvas.scale(scale, scale)

        # Clear with configured background (already normalized by
        # `_update_background_color` to either a backend color or an
        # (r,g,b,a) tuple).
        canvas.clear(rgba_to_skia_color(self._background_clear_color()))

        # Normalize root and paint using shared helpers.
        if isinstance(self.root, ComposableWidget):
            try:
                built = self.root.evaluate_build()
                if built is not None:
                    self.root = built
            except Exception:
                exception_once(logger, "app_snapshot_evaluate_build_exc", "root.evaluate_build raised")

        try:
            self._mount_paint_unmount(canvas, 0, 0, self.width, self.height)
        except Exception:
            exception_once(logger, "app_snapshot_mount_paint_unmount_exc", "_mount_paint_unmount raised")

        img = surface.makeImageSnapshot()
        if img is None:
            raise RuntimeError("makeImageSnapshot() returned None")
        return img

    def _dispatch_mouse_motion(self, x: int, y: int):
        _dispatch_mouse_motion_fn(self, x, y)

    # --- Keyboard / focus helpers ---------------------------------
    def request_focus(self, node: FocusNode) -> None:
        """Set focus to the given FocusNode."""
        if self._focused_node is node:
            return

        # Blur previous node
        if self._focused_node:
            self._focused_node._set_focused(False)

        # Focus new node
        self._focused_node = node
        if node:
            node._set_focused(True)
            # Also update legacy target if the node belongs to a widget
            if node.region:
                self._focused_target = node.region

    def _collect_focus_nodes(self) -> list[FocusNode]:
        """Return a list of FocusNodes in tree order."""
        res = []

        def walk(w):
            try:
                # skip disabled widgets
                if getattr(w, "_disabled", False):
                    return

                # Check for FocusNode
                if isinstance(w, InteractionHostMixin):
                    node = w.get_node(FocusNode)
                    if node and isinstance(node, FocusNode):
                        res.append(node)
            except Exception:
                exception_once(logger, "app_collect_focus_nodes_walk_exc", "Collecting FocusNodes raised")
            try:
                for c in w.children_snapshot():
                    walk(c)
            except Exception:
                exception_once(logger, "app_collect_focus_nodes_children_exc", "Traversing children_snapshot raised")

            # Also traverse built child (for widgets that use build() but don't add to children_store)
            try:
                built = getattr(w, "built_child", None)
                if built is not None and built is not w:
                    walk(built)
            except Exception:
                exception_once(logger, "app_collect_focus_nodes_built_child_exc", "Traversing built_child raised")

        try:
            if self.root is not None:
                walk(self.root)
        except Exception:
            exception_once(logger, "app_collect_focus_nodes_root_exc", "Collecting FocusNodes from root raised")
        return res

    def _dispatch_key_press(self, key, modifiers=0):
        """Handle key presses for focus navigation and activation.

        Accepts simple string names: 'tab', 'space', 'enter'. Returns True if handled.
        """
        kname = None
        try:
            if isinstance(key, str):
                kname = key.lower()
        except Exception:
            debug_once(logger, "app_key_name_lower_exc", "Failed to normalize key name")
            kname = None

        if kname == "escape":
            return self.handle_back_event()

        if kname == "tab":
            # 1. Try FocusNode traversal (New System)
            nodes = self._collect_focus_nodes()
            if nodes:
                try:
                    cur = self._focused_node
                    # If current focus is not in the list (e.g. detached), start from beginning
                    if cur not in nodes:
                        cur = None

                    if cur is None:
                        self.request_focus(nodes[0])
                        return True

                    # Allow composite widgets to consume Tab internally
                    # (e.g. RangeSlider switching between handles).
                    if cur.wants_tab(modifiers):
                        return cur.handle_key_event("tab", modifiers)

                    idx = nodes.index(cur)

                    # Treat bit0 as shift (matches pyglet MOD_SHIFT in practice).
                    go_back = bool(int(modifiers) & 1)

                    if go_back:
                        next_idx = (idx - 1) % len(nodes)
                    else:
                        next_idx = (idx + 1) % len(nodes)
                    self.request_focus(nodes[next_idx])
                    return True
                except Exception:
                    exception_once(logger, "app_dispatch_tab_traversal_exc", "Tab focus traversal raised")

            return False

        # 2. Try FocusNode bubbling (New System)
        if self._focused_node:
            try:
                if self._focused_node.handle_key_event(kname or str(key), modifiers):
                    return True
            except Exception:
                exception_once(logger, "app_focused_node_handle_key_exc", "Focused node handle_key_event raised")

        return False

    def _dispatch_text(self, text: str) -> bool:
        """Handle text input events."""
        if self._focused_node:
            try:
                if self._focused_node.handle_text_event(text):
                    return True
            except Exception:
                exception_once(logger, "app_focused_node_handle_text_exc", "Focused node handle_text_event raised")
        return False

    def _dispatch_text_motion(self, motion: int, select: bool = False) -> bool:
        """Handle text motion events (arrow keys, home/end, etc)."""
        if self._focused_node:
            try:
                if self._focused_node.handle_text_motion_event(motion, select):
                    return True
            except Exception:
                exception_once(
                    logger,
                    "app_focused_node_handle_text_motion_exc",
                    "Focused node handle_text_motion_event raised",
                )
        return False

    def _dispatch_ime_composition(self, text: str, start: int, length: int) -> bool:
        """Handle IME composition events."""
        if self._focused_node:
            try:
                if hasattr(self._focused_node, "handle_ime_composition_event"):
                    if self._focused_node.handle_ime_composition_event(text, start, length):
                        return True
            except Exception:
                exception_once(
                    logger,
                    "app_focused_node_handle_ime_composition_exc",
                    "Focused node handle_ime_composition_event raised",
                )
        return False

    def _dispatch_mouse_press(self, x: int, y: int):
        _dispatch_mouse_press_fn(self, x, y)

    def _dispatch_mouse_release(self, x: int, y: int):
        _dispatch_mouse_release_fn(self, x, y)

    def _dispatch_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float):
        _dispatch_mouse_scroll_fn(self, x, y, scroll_x, scroll_y)

    def _handle_pointer_cancel(
        self,
        pointer_id: int,
        widget: Optional[Widget],
        last_event: Optional[PointerEvent],
    ) -> None:
        if widget is None:
            return
        pivot = last_event or PointerEvent(
            id=pointer_id,
            type=PointerEventType.CANCEL,
            x=0.0,
            y=0.0,
            pointer_type=PointerType.UNKNOWN,
            timestamp=time.time(),
        )
        cancel_event = PointerEvent(
            id=pointer_id,
            type=PointerEventType.CANCEL,
            x=pivot.x,
            y=pivot.y,
            pointer_type=pivot.pointer_type,
            button=pivot.button,
            timestamp=time.time(),
            modifiers=pivot.modifiers,
        )
        try:
            widget.dispatch_pointer_event(cancel_event)
        except Exception:
            exception_once(logger, "app_pointer_cancel_dispatch_exc", "dispatch_pointer_event(CANCEL) raised")

    def _render_frame(self, dt: float) -> None:
        """Render a frame via the pyglet window using current draw callbacks."""
        window = self._window
        if window is None or getattr(window, "has_exit", False):
            return
        try:
            flush_binding_invalidations()
        except Exception:
            exception_once(logger, "app_flush_binding_invalidations_pre_exc", "flush_binding_invalidations failed")
        try:
            flush_scope_recompositions()
        except Exception:
            exception_once(logger, "app_flush_scope_recompositions_pre_exc", "flush_scope_recompositions failed")
        try:
            flush_binding_invalidations()
        except Exception:
            exception_once(logger, "app_flush_binding_invalidations_post_exc", "flush_binding_invalidations failed")
        try:
            flush_scope_recompositions()
        except Exception:
            exception_once(logger, "app_flush_scope_recompositions_post_exc", "flush_scope_recompositions failed")
        try:
            window.switch_to()
            window.dispatch_event("on_draw")
            window.flip()
        except Exception:
            exception_once(logger, "app_window_draw_flip_exc", "Window draw/flip raised")

    def set_draw_fps(self, fps: Optional[float]) -> None:
        """Update the preferred draw FPS for the interactive loop."""
        if fps is not None:
            try:
                fps = float(fps)
            except Exception:
                raise ValueError("fps must be convertible to float or None") from None
            if fps <= 0:
                fps = None
        self._preferred_draw_fps = fps
        loop = self._event_loop
        if loop is not None:
            try:
                loop.set_draw_fps(fps)
            except Exception:
                exception_once(logger, "app_set_draw_fps_exc", "Event loop set_draw_fps raised")

    def run(self, draw_fps: Optional[float] = None):
        """Run an interactive window using the pyglet backend."""

        from ..backends.pyglet.runner import run_app

        run_app(self, draw_fps=draw_fps)

    def exit(self, exit_code: int = 0) -> None:
        """Exit the application."""
        try:
            import pyglet

            pyglet.app.exit()
        except ImportError:
            pass
        except Exception:
            exception_once(logger, "app_exit_exc", "Failed to exit application")

    def dispatch(self, intent: Any) -> None:
        """Dispatch an intent to the application."""
        from nuiitivet.runtime.intents import (
            ExitAppIntent,
            CenterWindowIntent,
            MaximizeWindowIntent,
            MinimizeWindowIntent,
            RestoreWindowIntent,
            FullScreenIntent,
            CloseWindowIntent,
            MoveWindowIntent,
            ResizeWindowIntent,
        )

        if isinstance(intent, ExitAppIntent):
            self.exit(intent.exit_code)
            return

        # Window management
        window = getattr(self, "_window", None)
        if window is not None:
            if isinstance(intent, CenterWindowIntent):
                try:
                    screen = window.screen
                    if screen:
                        x = (screen.width - window.width) // 2
                        y = (screen.height - window.height) // 2
                        window.set_location(x, y)
                except Exception:
                    exception_once(logger, "app_dispatch_center_window_exc", "CenterWindowIntent failed")
                return

            if isinstance(intent, MaximizeWindowIntent):
                try:
                    # Save current window rect before maximizing
                    try:
                        wx, wy = window.get_location()
                        ww, wh = window.width, window.height
                        self._saved_window_rect = (wx, wy, ww, wh)
                    except Exception:
                        self._saved_window_rect = None

                    import sys

                    if sys.platform == "darwin":
                        try:
                            import ctypes
                            from pyglet.libs.darwin import cocoapy
                            from pyglet.libs.darwin.cocoapy import cocoatypes

                            ns_window = window._nswindow
                            screen = ns_window.screen()
                            # visibleFrame returns NSRect
                            visible_frame = cocoapy.send_message(screen, "visibleFrame", restype=cocoatypes.NSRect)
                            # setFrame:display:
                            # void setFrame:(NSRect)frameRect display:(BOOL)flag
                            cocoapy.send_message(
                                ns_window,
                                "setFrame:display:",
                                visible_frame,
                                True,
                                argtypes=[cocoatypes.NSRect, ctypes.c_bool],
                            )
                        except Exception:
                            # Fallback if something goes wrong (e.g. older pyglet)
                            window.maximize()
                    else:
                        window.maximize()
                except Exception:
                    exception_once(logger, "app_dispatch_maximize_window_exc", "MaximizeWindowIntent failed")
                return

            if isinstance(intent, MinimizeWindowIntent):
                try:
                    window.minimize()
                except Exception:
                    exception_once(logger, "app_dispatch_minimize_window_exc", "MinimizeWindowIntent failed")
                return

            if isinstance(intent, RestoreWindowIntent):
                try:
                    if window.fullscreen:
                        window.set_fullscreen(False)
                        return

                    # Try to activate (restore from minimize on some platforms)
                    if hasattr(window, "activate"):
                        window.activate()

                    # Restore from maximize if we have saved state
                    if self._saved_window_rect is not None:
                        try:
                            rx, ry, rw, rh = self._saved_window_rect
                            window.set_location(rx, ry)
                            window.set_size(rw, rh)
                            self._saved_window_rect = None
                        except Exception:
                            exception_once(logger, "app_dispatch_restore_rect_exc", "Failed to restore window rect")

                    # Note: Pyglet doesn't have a direct 'unmaximize' or 'restore' from maximize
                    # that is consistent across platforms.
                except Exception:
                    exception_once(logger, "app_dispatch_restore_window_exc", "RestoreWindowIntent failed")
                return

            if isinstance(intent, FullScreenIntent):
                try:
                    # API: FullScreenIntent requests fullscreen (no toggle)
                    window.set_fullscreen(True)
                except Exception:
                    exception_once(logger, "app_dispatch_fullscreen_exc", "FullScreenIntent failed")
                return

            if isinstance(intent, CloseWindowIntent):
                try:
                    window.close()
                except Exception:
                    exception_once(logger, "app_dispatch_close_window_exc", "CloseWindowIntent failed")
                return

            if isinstance(intent, MoveWindowIntent):
                try:
                    window.set_location(intent.x, intent.y)
                except Exception:
                    exception_once(logger, "app_dispatch_move_window_exc", "MoveWindowIntent failed")
                return

            if isinstance(intent, ResizeWindowIntent):
                try:
                    window.set_size(intent.width, intent.height)
                except Exception:
                    exception_once(logger, "app_dispatch_resize_window_exc", "ResizeWindowIntent failed")
                return

    def _dispatch_close(self):
        """Unmount root and cleanup app-owned resources."""
        try:
            self._unsubscribe_theme_updates()
        except Exception:
            exception_once(logger, "app_close_unsubscribe_theme_exc", "_unsubscribe_theme_updates raised")
        try:
            if self.root is not None:
                self.root.unmount()
        except Exception:
            exception_once(logger, "app_close_root_unmount_exc", "root.unmount raised")
