"""App runner that can render a widget tree to an image using Skia."""

import logging
import os
import sys
import time
import traceback
import warnings
import weakref
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Sequence, Tuple

from ..widgeting.callbacks import spawn_task
from ..widgeting.context_lookup import find_provider, raise_if_premature_lookup
from ..widgeting.widget import ComposableWidget, Widget
from .pointer import PointerCaptureManager
from nuiitivet.input.pointer import PointerEvent, PointerEventType, PointerType
from ..widgeting.widget_binding import flush_binding_invalidations
from ..widgeting.widget_builder import flush_scope_recompositions
from ..widgeting.widget_size_change import flush_size_change_callbacks

from ..rendering.skia import make_raster_surface, require_skia, rgba_to_skia_color, save_png
from ..theme.manager import ThemeManager
from nuiitivet.theme.plain_theme import PlainColorRole, PlainTheme
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec
from ..widgets.interaction import (
    FocusNode,
    FocusScope,
    FocusSource,
    FocusTraversalBlocker,
    InteractionHostMixin,
    ShortcutNode,
)
from nuiitivet.input.shortcut import ShortcutBinding, ShortcutScope, produces_text
from .shortcut_dispatch import is_foreground
from nuiitivet.common.logging_once import debug_once, exception_once, warning_once
from .app_events import (
    dispatch_file_drop as _dispatch_file_drop_fn,
    dispatch_mouse_motion as _dispatch_mouse_motion_fn,
    dispatch_mouse_press as _dispatch_mouse_press_fn,
    dispatch_mouse_release as _dispatch_mouse_release_fn,
    dispatch_mouse_scroll as _dispatch_mouse_scroll_fn,
)
from .chrome import OSChrome, CustomChrome
from .title_bar import WindowDragArea
from nuiitivet.observable.protocols import Disposable, ObservableBase
from .window import WindowSizingLike, WindowPosition, parse_window_sizing
from .renderer import RendererMode, parse_renderer_mode
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container

if TYPE_CHECKING:
    from nuiitivet.navigation.navigator import Navigator
    from nuiitivet.overlay.overlay import Overlay
    from nuiitivet.theme.theme import Theme


logger = logging.getLogger(__name__)

_UNSET = object()

# A root factory is any zero-argument callable returning the root Widget. Passing
# a factory (rather than a Widget instance) is what enables hot reload: the dev
# runner re-invokes it to rebuild the tree after a module reload. A bare Widget
# subclass qualifies (``App(content=CounterApp)``), as does a function or lambda.
RootFactory = Callable[[], Widget]


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
    """Inherited widget that provides access to the App instance.

    Also the theme provider: ``Theme.of`` resolves against the nearest one of
    these, and a theme change is turned into invalidation here rather than
    pushed to a list of subscribers.
    """

    def __init__(self, app: "App", child: Widget) -> None:
        super().__init__()
        self.app_proxy = AppProxy(app)
        self.theme_manager = app._theme_manager
        self._app_ref = weakref.ref(app)
        self.theme_manager.on_change = self._on_theme_changed
        self.add_child(child)

    @property
    def app(self) -> Optional["App"]:
        """The App this scope belongs to, or ``None`` once it has been collected.

        The App-scoped half of ``X.of(context)`` resolves through here — see
        :func:`nuiitivet.widgeting.context_lookup.find_app`.
        """
        return self._app_ref()

    def _on_theme_changed(self, _theme: "Theme") -> None:
        """Refresh everything below that read the theme.

        The provider keeps no consumer references, so it does not know who its
        readers are; it walks its own subtree and invalidates the widgets that
        marked themselves while reading. See ``nuiitivet/theme/dependency.py``.
        """
        from nuiitivet.theme.dependency import invalidate_theme_readers

        invalidate_theme_readers(self)
        app = self._app_ref()
        if app is None:
            return
        # The window's clear colour is the App's own, not a widget's, so nothing
        # marked it as a reader; refresh it here when it is token-based. Probed
        # rather than called outright because tests scope a stub app.
        uses_theme = getattr(app, "_background_uses_theme", None)
        update = getattr(app, "_update_background_color", None)
        if callable(uses_theme) and callable(update):
            try:
                if uses_theme():
                    update()
            except Exception:
                exception_once(logger, "app_scope_theme_background_exc", "Background update raised on theme change")
        invalidate = getattr(app, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(logger, "app_scope_theme_invalidate_exc", "App.invalidate raised on theme change")

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        for child in self.children:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)


@dataclass(frozen=True)
class _ContentRoot:
    """A built-but-not-installed content root and the pieces it is made of.

    Built by :meth:`App._build_root_navigation_stack` and installed by
    :meth:`App._commit_content_root`. The navigator and overlay travel with the
    widget so the App can adopt them *at commit time*: a hot reload that builds
    successfully but fails to commit must leave the App pointing at the tree
    that is still on screen, not at an orphan that was never mounted.
    """

    widget: Widget
    navigator: "Navigator"
    overlay: "Overlay"
    initial_route_widget: Widget | None


class App:
    """Application runner."""

    # Set when a CustomChrome is in use (see :meth:`_wrap_with_chrome_and_scope`).
    _window_drag_area: Optional[WindowDragArea] = None

    # The App's own navigation layers, adopted in :meth:`_commit_content_root`.
    # These are what ``Navigator.of`` / ``Overlay.of`` fall back to, so they are
    # per-App state and never a process-wide global.
    _navigator: Optional["Navigator"] = None
    _overlay: Optional["Overlay"] = None

    @property
    def navigator(self) -> "Navigator":
        """This App's root :class:`~nuiitivet.navigation.Navigator`.

        Raises:
            RuntimeError: If the App has no content root yet.
        """
        if self._navigator is None:
            raise RuntimeError("App has no navigator yet; its content root is not built.")
        return self._navigator

    @property
    def overlay(self) -> "Overlay":
        """This App's root :class:`~nuiitivet.overlay.Overlay`.

        Raises:
            RuntimeError: If the App has no content root yet.
        """
        if self._overlay is None:
            raise RuntimeError("App has no overlay yet; its content root is not built.")
        return self._overlay

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
            RuntimeError: If called before ``context`` is mounted (typically from
                ``__init__``), or if the widget is not attached to an App.
        """
        scope = find_provider(context, AppScope)
        if scope is None:
            raise_if_premature_lookup("App.of", context)
            raise RuntimeError("AppScope not found. Is the widget attached to an App?")
        return scope.app_proxy

    @staticmethod
    def _build_root_navigation_stack(
        *,
        navigator: "Navigator",
        overlay_factory: Callable[[], "Overlay"] | None,
    ) -> _ContentRoot:
        """Assemble the Navigator/Overlay layer stack for a content root.

        Building is deliberately free of side effects on the App: the caller
        adopts the result, so a build that is thrown away (a hot reload that
        fails to commit) leaves no trace.
        """
        from nuiitivet.layout.stack import Stack
        from nuiitivet.navigation import Navigator as _Navigator
        from nuiitivet.overlay import Overlay
        from nuiitivet.rendering.sizing import Sizing

        resolved_overlay_factory = overlay_factory or Overlay
        overlay = resolved_overlay_factory()
        if not isinstance(overlay, Overlay):
            raise TypeError("overlay_factory must return an Overlay instance")

        if not isinstance(navigator, _Navigator):
            raise TypeError("navigator must be a Navigator instance")

        initial_route_widget: Widget | None = None
        try:
            top_route = navigator._stack.top()  # type: ignore[attr-defined]
            if top_route is not None:
                initial_route_widget = navigator._route_widget(top_route)  # type: ignore[attr-defined]
        except Exception:
            exception_once(logger, "navigator_route_widget_prime_exc", "Failed to prime initial route widget")

        navigator.width_sizing = Sizing.weight(100)
        navigator.height_sizing = Sizing.weight(100)
        overlay.width_sizing = Sizing.weight(100)
        overlay.height_sizing = Sizing.weight(100)

        root_widget = Stack(children=[navigator, overlay], width="wt", height="wt")
        return _ContentRoot(
            widget=root_widget,
            navigator=navigator,
            overlay=overlay,
            initial_route_widget=initial_route_widget,
        )

    def _wrap_with_chrome_and_scope(self, root: Widget) -> Widget:
        """Wrap a content root with the window chrome and the AppScope.

        Applies the :class:`CustomChrome` header + drag area (when a custom
        chrome is in use) and finally the :class:`AppScope` that exposes the App
        to the widget tree. Reused by both initial construction and hot reload so
        a rebuilt content subtree is wrapped identically. ``self.chrome`` must be
        set before calling.

        Args:
            root: The content root (the Navigator/Overlay stack).

        Returns:
            The wrapped root widget.
        """
        if isinstance(self.chrome, CustomChrome):

            def on_drag(dx: float, dy: float) -> None:
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
                        exception_once(logger, "app_custom_chrome_drag_exc", "Failed to move window")

            self._window_drag_area = WindowDragArea(
                child=self.chrome.header,
                on_drag=on_drag,
                width="wt",
            )

            root = Column(
                children=[
                    self._window_drag_area,
                    Container(child=root, width="wt", height="wt"),
                ],
                width="wt",
                height="wt",
            )

        # Install the root Geometry provider so ``Geometry.of(context)`` resolves
        # even without an explicit wrapper: with no nearer Geometry, a top-level
        # read tracks the window size. The root Geometry needs no special resize
        # plumbing -- it measures the window through the normal layout pass, which
        # the resize path already triggers via ``invalidate`` -> relayout.
        from nuiitivet.geometry import Geometry

        # Wrap the root widget with AppScope to provide access to the App instance
        return AppScope(app=self, child=Geometry(root))

    def _init_common(
        self,
        *,
        root: Widget,
        width: WindowSizingLike,
        height: WindowSizingLike,
        title: "str | None | ObservableBase[str | None]",
        chrome: "OSChrome | CustomChrome | None",
        background: ColorSpec,
        theme: Optional[Any] = None,
        window_position: WindowPosition | None = None,
        window_auto_size_target: Widget | None = None,
        resizable: bool = True,
    ) -> None:
        if not isinstance(root, Widget):
            raise TypeError("App.root must be a Widget instance.")

        if theme is None:
            theme = PlainTheme.light()
        self._theme_manager = ThemeManager(initial=theme)
        self._theme_registry: dict[str, Any] = {}

        self.root = root

        self.chrome: OSChrome | CustomChrome | None = chrome
        # Reset the drag-area reference (class default is None); a CustomChrome
        # rebuilds it in :meth:`_wrap_with_chrome_and_scope`.
        self._window_drag_area = None

        # Apply the chrome decoration and AppScope wrapping. This is factored out
        # so hot reload can re-wrap a freshly rebuilt content subtree with the
        # same (preserved) chrome shell. See :meth:`_rebuild_content_root`.
        #
        # This must precede the auto-size measurement at the end of this method:
        # the AppScope installed here is what ``Theme.of`` resolves against, so a
        # tree measured before it exists is measured against the default theme.
        self.root = self._wrap_with_chrome_and_scope(self.root)

        width_sizing = parse_window_sizing(width)
        height_sizing = parse_window_sizing(height)
        needs_auto_size = width_sizing.kind == "auto" or height_sizing.kind == "auto"

        # Provisional window size. An ``auto`` dimension is resolved at the end
        # of this method, once the tree is mounted and can be measured against
        # the real theme; until then ``on_mount`` code that reads app.width /
        # app.height must still see a number rather than an AttributeError.
        self.width = self._resolve_window_sizing(width, preferred=0, fallback=640)
        self.height = self._resolve_window_sizing(height, preferred=0, fallback=480)
        self.window_position = window_position
        self.resizable = resizable

        self._title_value: str | None | ObservableBase[str | None] = title
        self._title_disposable: Optional[Disposable] = None

        self._scale = 1.0
        self._dirty = False
        # Content dirtiness is distinct from ``_dirty``: ``_dirty`` means "a frame
        # was requested", while ``_paint_dirty`` means "the widget tree changed and
        # must be re-painted". A surface-loss redraw (window show/activate) requests
        # a frame without changing content, letting the GPU path re-blit its cached
        # full frame instead of re-walking the tree. See ``draw_gpu_frame``.
        self._paint_dirty = True
        self._window = None
        self._event_loop: Any = None
        # On-demand drawing by default: a clean tree produces zero frames. A
        # positive value (via `App.run(draw_fps=...)` or `set_draw_fps`) acts as
        # an upper-bound throttle, not a mandate to draw every frame.
        self._preferred_draw_fps: Optional[float] = None
        self._last_hover_target = None
        self._focused_target: Optional[InteractionHostMixin] = None
        self._focused_node: Optional[FocusNode] = None
        # Open blocking overlay entries, innermost last, each paired with the node
        # that held focus when it opened. A modal takes focus with it and hands it
        # back on close; the invoker cannot be looked up from the tree afterwards,
        # because by then the dialog is detached. See :meth:`_sync_overlay_focus_trap`.
        self._overlay_focus_trap: list[Tuple[Widget, Optional[FocusNode]]] = []
        # How the user is driving the app right now. A widget that takes focus on
        # its own (a menu focusing its first item when it opens) inherits it, so a
        # mouse-opened menu does not come up wearing a keyboard focus ring.
        self._last_input_source: FocusSource = FocusSource.KEYBOARD
        self._modifier_keys: int = 0
        # Dev-only observer for the interaction journal (#390). The dev runner
        # attaches an ``InteractionRecorder`` here so the human's coarse UI
        # actions can be recorded for an AI pair to pull; ``None`` -- and zero
        # overhead -- in production.
        self._interaction_recorder: Optional[Any] = None
        # Dev-only designation mode (#591). The dev runner attaches an
        # ``InspectMode`` here so the human can point at a widget for an AI pair
        # to read; ``None`` -- and zero overhead -- in production.
        self._inspect_mode: Optional[Any] = None
        # Last known pointer position / held buttons (screen coords), used to
        # synthesize the pointer event delivered on a modifier-key mask change.
        self._last_pointer_pos: Optional[Tuple[float, float]] = None
        self._last_pointer_buttons: int = 0
        self._pointer_capture_manager = PointerCaptureManager()
        self._pointer_capture_manager.set_cancel_callback(self._handle_pointer_cancel)
        self._primary_pointer_id = 1
        self._background_value: ColorSpec = background
        self._background_color: Any = None
        self._update_background_color()
        self._subscribe_title_updates()
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

        # Mounting comes last, after every attribute a lifecycle hook might touch
        # is initialized: ``mount()`` runs on_mount for the whole tree, and that
        # user code can call straight back into the App (``invalidate()`` reads
        # the debug-instrumentation fields set just above).
        try:
            self.root.mount(self)
        except Exception:
            exception_once(logger, "app_init_root_mount_exc", "root.mount(self) raised during App construction")

        if needs_auto_size:
            self._apply_auto_window_size(
                width=width,
                height=height,
                target=window_auto_size_target,
                chrome=chrome,
            )

    def _apply_auto_window_size(
        self,
        *,
        width: WindowSizingLike,
        height: WindowSizingLike,
        target: Widget | None,
        chrome: "OSChrome | CustomChrome | None",
    ) -> None:
        """Size the window from the content's preferred size.

        Only called when at least one dimension is ``auto``. The tree must
        already be mounted: a widget reaches its theme by walking up to the
        :class:`AppScope`, and that walk only works once the widget is attached.
        Measuring first and mounting afterwards sizes the window against the
        default light theme, ignoring any custom typography or style the app
        installed (#476).

        Args:
            width: The window width specification, as passed to the App.
            height: The window height specification, as passed to the App.
            target: The content widget to measure, or ``None`` to skip.
            chrome: The window chrome; a :class:`CustomChrome` header adds its
                own preferred height to the total.
        """
        pref_w = 0
        pref_h = 0
        if target is not None:
            try:
                pref_w, pref_h = target.preferred_size()
            except Exception:
                exception_once(logger, "app_auto_size_measure_exc", "Auto-size content measurement raised")
                pref_w, pref_h = 0, 0

        if isinstance(chrome, CustomChrome):
            try:
                tw, th = chrome.header.preferred_size()
            except Exception:
                exception_once(logger, "app_auto_size_chrome_measure_exc", "Auto-size chrome measurement raised")
                tw, th = 0, 0
            pref_w = max(int(pref_w), int(tw))
            pref_h = int(pref_h) + int(th)

        self.width = self._resolve_window_sizing(width, preferred=int(pref_w), fallback=640)
        self.height = self._resolve_window_sizing(height, preferred=int(pref_h), fallback=480)

    def can_handle_back_event(self) -> bool:
        """Return True if a back action would be handled.

        This is a non-mutating check used by backends to decide whether to
        consume the OS/back key or let default handlers run (e.g. ESC-to-exit).
        """

        overlay = self._overlay
        if overlay is not None:
            try:
                if overlay.has_entries():
                    return True
            except Exception:
                exception_once(logger, "app_overlay_has_entries_exc", "overlay.has_entries() failed")

        navigator = self._navigator
        if navigator is not None:
            try:
                return bool(navigator.can_pop())
            except Exception:
                exception_once(logger, "app_navigator_can_pop_exc", "navigator.can_pop() failed")
                return False

        return False

    async def handle_back_event(self) -> bool:
        """Handle a user back action (e.g. Esc).

        Priority:
        - Overlay: close topmost entry if any
        - Navigator: pop one route if possible

        A back action never reaches past a blocking layer. If the overlay had
        nothing left to close but is still painting one -- a dialog already
        dismissed and animating out is the case that reaches here -- the event
        stops, rather than popping the screen the user can still see behind it.
        This is the keyboard half of what ``Overlay.hit_test`` does for the
        pointer; a pass-through layer (toast, banner) blocks neither.
        """

        overlay = self._overlay
        if overlay is not None:
            try:
                has_entries = bool(overlay.has_entries())
                if has_entries:
                    handled = bool(await overlay.async_request_close_topmost())
                    if handled:
                        return True
                    if overlay.occluding_content_widget() is not None:
                        return True
            except Exception:
                exception_once(logger, "app_overlay_close_topmost_exc", "overlay.close_topmost() failed")

        navigator = self._navigator
        if navigator is not None:
            try:
                request_back = getattr(navigator, "request_back", None)
                if callable(request_back):
                    handled = bool(await request_back())
                    return handled
                if navigator.can_pop():
                    navigator.pop()
                    return True
            except Exception:
                exception_once(logger, "app_navigator_back_exc", "Navigator back handling failed")
        return False

    def _build_default_navigator(self, content: Widget) -> "Navigator":
        """Wrap ``content`` in a default root Navigator.

        Subclasses (e.g. ``MaterialApp``) can override this to provide a
        framework-specific Navigator (e.g. ``MaterialNavigator``).
        """
        from nuiitivet.navigation import Navigator

        return Navigator(content)

    def __init__(
        self,
        content: "Widget | RootFactory",
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        *,
        title: "str | None | ObservableBase[str | None]" = None,
        chrome: "OSChrome | CustomChrome | None" = _UNSET,  # type: ignore[assignment]
        background: ColorSpec = PlainColorRole.SURFACE,
        overlay_factory: Callable[[], "Overlay"] | None = None,
        theme: Optional[Any] = None,
        window_position: WindowPosition | None = None,
        resizable: bool = True,
    ):
        """Initialize the App.

        Args:
            content: The root content. Accepts either a ready ``Widget`` instance
                or a **root factory** — a zero-argument callable returning the
                root ``Widget`` (e.g. a ``Widget`` subclass ``App(content=Home)``,
                a function, or ``lambda: Home(config)``). Passing a factory is
                what enables hot reload under ``python -m nuiitivet.dev``: the
                runner re-invokes it to rebuild the tree after a module reload.
                Passing a Widget instance still works but the tree cannot be
                rebuilt, so hot reload is inert for that root.

                Whichever form is used, the resulting root may be:
                - A ``Navigator`` (including factory-built variants like
                  ``Navigator.routes(...)`` / ``Navigator.intents(...)``), which
                  is used directly as the root Navigator.
                - Any other ``Widget``, in which case a default root ``Navigator``
                  is created implicitly so ``Navigator.of(context).push(...)``
                  works out of the box.
            width: Window width specification.
            height: Window height specification.
            title: OS window title. Accepts a plain string or a
                :class:`~nuiitivet.observable.protocols.ObservableBase`
                for dynamic updates (e.g. ``Observable("Untitled")``). Pass
                ``None`` for no title.
            chrome: Window decoration. Pass an :class:`OSChrome` instance to
                use OS-managed decorations with an optional style variant,
                :class:`CustomChrome` for an app-drawn header, or ``None`` for
                a bare borderless window. Omitting this parameter (the default)
                is equivalent to ``OSChrome()``.
            background: Window background color.
            overlay_factory: Optional overlay factory.
            theme: Theme to install.
            window_position: Initial window position.
            resizable: Whether the window can be resized.
        """
        # Normalize ``content`` to a root factory. A Widget instance is wrapped in
        # a factory that always returns that same instance (so hot reload is a
        # no-op for it); a callable is stored as-is. ``self._root_factory`` is the
        # single source of truth the reload path re-invokes.
        if callable(content) and not isinstance(content, Widget):
            self._root_factory: RootFactory = content
        elif isinstance(content, Widget):
            instance = content
            self._root_factory = lambda: instance
        else:
            raise TypeError(
                "'content' must be a Widget instance or a callable returning a Widget."
            )
        # Overlay factory is retained so the reload path can rebuild the
        # Navigator/Overlay stack identically. See :meth:`_rebuild_content_root`.
        self._overlay_factory = overlay_factory

        content_root = self._root_factory()
        if not isinstance(content_root, Widget):
            raise TypeError("root factory must return a Widget instance.")

        from nuiitivet.navigation import Navigator

        if isinstance(content_root, Navigator):
            navigator = content_root
        else:
            navigator = self._build_default_navigator(content_root)

        built = self._build_root_navigation_stack(
            navigator=navigator,
            overlay_factory=overlay_factory,
        )
        # Nothing to unmount on the initial path, so adopt straight away; the
        # reload path defers this to :meth:`_commit_content_root`.
        self._navigator = built.navigator
        self._overlay = built.overlay
        resolved_chrome: OSChrome | CustomChrome | None = OSChrome() if chrome is _UNSET else chrome
        self._init_common(
            root=built.widget,
            width=width,
            height=height,
            title=title,
            chrome=resolved_chrome,
            background=background,
            theme=theme,
            window_position=window_position,
            window_auto_size_target=built.initial_route_widget,
            resizable=resizable,
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
            self._unsubscribe_title_updates()
        except Exception:
            exception_once(logger, "app_del_unsubscribe_title_exc", "_unsubscribe_title_updates raised in __del__")

    def render_to_png(self, path: str):
        """Render the current UI to a PNG file.

        Settles first: an interactive app reaches its final layout over the next
        frame or two (see :meth:`_settle_pending_size_changes`), which a single
        render would otherwise never draw.
        """
        img = self._render_snapshot(scale=1.0, settle=True)
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
            rgba = resolve_color_to_rgba(self._background_value, theme=self._theme_manager.current)
        except Exception as exc:
            raise ValueError("App background color could not be resolved") from exc
        if rgba is None:
            raise ValueError("App background color could not be resolved")

        self._background_color = rgba

    def _background_clear_color(self):
        if self._background_color is None:
            self._update_background_color()
        return self._background_color

    def _subscribe_title_updates(self) -> None:
        if not isinstance(self._title_value, ObservableBase):
            return
        app_ref = weakref.ref(self)

        def _on_title(new_title: "str | None") -> None:
            app = app_ref()
            if app is not None:
                app._apply_window_title(new_title)

        try:
            self._title_disposable = self._title_value.subscribe(_on_title)
        except Exception:
            exception_once(logger, "app_title_subscribe_exc", "Observable title subscribe raised")

    @property
    def title(self) -> "str | None":
        """The window title's current value, or ``None`` if unset.

        Resolves the title given at construction: a plain string is returned as
        is; an :class:`~nuiitivet.observable.protocols.ObservableBase` is
        unwrapped to its current value. Exposed for dev tooling -- the dev
        bridge's ``status`` reports it so an assistant can confirm *which* app is
        running -- and never raises: an observable whose read fails reports
        ``None`` rather than propagating.
        """
        value = self._title_value
        if isinstance(value, ObservableBase):
            try:
                value = value.value
            except Exception:
                return None
        return str(value) if value is not None else None

    def _apply_window_title(self, title: "str | None") -> None:
        window = getattr(self, "_window", None)
        if window is not None:
            try:
                window.set_caption(str(title) if title is not None else "")
            except Exception:
                exception_once(logger, "app_title_set_caption_exc", "window.set_caption raised")

    def _unsubscribe_title_updates(self) -> None:
        disp = getattr(self, "_title_disposable", None)
        if disp is None:
            return
        try:
            disp.dispose()
        except Exception:
            exception_once(logger, "app_title_unsubscribe_exc", "title disposable.dispose raised")
        self._title_disposable = None

    # Cap on how many frames' worth of settling a one-shot render simulates. A
    # callback that resizes what it measures would otherwise never converge.
    _MAX_SNAPSHOT_SETTLE_PASSES = 3

    def _settle_pending_size_changes(self, w: int, h: int) -> None:
        """Drive queued size callbacks to completion for a one-shot render.

        Size callbacks are dispatched *between* frames, so an effect one produces
        lands on the frame after the layout that measured it. An interactive app
        simply draws that frame; a single ``render_to_png`` never does and would
        capture the pre-callback state. This runs those frames' worth of work in
        place, while the root is mounted so no queued report is dropped.

        Snapshot-only: the live frame loop must not run user callbacks between
        layout and paint. See :meth:`_render_frame`.
        """
        root = self.root
        if root is None:
            return
        for _ in range(self._MAX_SNAPSHOT_SETTLE_PASSES):
            if not flush_size_change_callbacks():
                return
            flush_binding_invalidations()
            flush_scope_recompositions()
            root.layout(w, h)
            root.clear_needs_layout()

    def _mount_paint_unmount(self, canvas, x: int, y: int, w: int, h: int, *, settle: bool = False) -> None:
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
            if settle:
                self._settle_pending_size_changes(w, h)
        except Exception as e:
            warnings.warn(f"root.layout() failed: {e}", RuntimeWarning, stacklevel=2)

        try:
            self._release_focus_if_blocked()
        except Exception:
            exception_once(logger, "app_release_focus_if_blocked_exc", "_release_focus_if_blocked raised")

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
    def invalidate(self, immediate: bool = False, content: bool = True):
        """Request that the next frame be redrawn.

        This sets an internal dirty flag which the render loop checks to
        decide whether to re-render the UI.

        Args:
            immediate: If True and running in pyglet, bypass FPS throttle for next draw
            content: If True (default), mark the widget tree as changed so the next
                frame is fully re-painted. Pass False for surface-loss redraws
                (window show/activate) where the tree is unchanged and the GPU path
                may re-blit its cached full frame instead of re-walking the tree.
        """
        self._dirty = True
        if content:
            self._paint_dirty = True
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
        img = self._render_snapshot(scale=scale, settle=True)
        data = img.encodeToData()
        if data is None:
            raise RuntimeError("encodeToData() returned None (failed to encode image)")
        return bytes(data)

    def _render_snapshot(self, scale: float = 1.0, *, for_display: bool = False, settle: bool = False):
        """Create a Skia image snapshot for the current root at given scale.

        Returns an image object. Raises RuntimeError if Skia is missing or
        snapshot/encoding fails.

        Args:
            scale: Device-pixel scale factor for the raster surface.
            for_display: When ``True`` this snapshot is being drawn to the live
                on-screen window (the CPU/raster frame path), so the human-only
                dev action overlay is painted over it. Screenshot callers leave
                this ``False`` so the overlay never leaks into ``screenshot``.
            settle: When ``True`` this is a one-shot capture, so run the reactive
                work that the next frames would have done (see
                :meth:`_settle_pending_size_changes`). Live frame paths leave it
                ``False``; there, the next frame does that work as usual.
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
            self._mount_paint_unmount(canvas, 0, 0, self.width, self.height, settle=settle)
        except Exception:
            exception_once(logger, "app_snapshot_mount_paint_unmount_exc", "_mount_paint_unmount raised")

        # Human-only dev action overlay: on-screen frames only, never screenshots.
        if for_display:
            try:
                from nuiitivet.dev import action_overlay

                action_overlay.paint_markers(canvas=canvas, app=self, width=self.width, height=self.height)
            except Exception:
                exception_once(logger, "app_snapshot_dev_action_overlay_exc", "dev action overlay paint raised")

            try:
                from nuiitivet.dev import selection_overlay

                selection_overlay.paint_selection(self, canvas, self.width, self.height)
            except Exception:
                exception_once(
                    logger, "app_snapshot_dev_selection_overlay_exc", "dev selection overlay paint raised"
                )

        img = surface.makeImageSnapshot()
        if img is None:
            raise RuntimeError("makeImageSnapshot() returned None")
        return img

    # Longest-side pixel budget for the blank-frame probe. Small on purpose: it
    # only decides whether the frame is a single uniform color, not what it is.
    _BLANK_PROBE_MAX_DIM = 64

    def _frame_is_blank(self) -> bool:
        """Return whether the current frame is a single uniform color.

        A render that produced nothing -- a build that returned no content, or a
        paint that raised and was swallowed -- leaves the frame filled with only
        the background clear color, so every pixel is identical. Any real content
        paints at least one differing pixel, so "one color everywhere" is a
        reliable "the screen is blank" signal that the widget tree alone cannot
        give (the tree can look right while nothing paints).

        Renders a small downscaled snapshot and reads its raw pixels -- no PNG
        encode, so no image tokens -- returning ``True`` only when the whole
        frame is one color. A splash or demo screen that is *intentionally* one
        solid color reads as blank too, so treat this as a heuristic hint, not a
        hard failure.

        Must be called on the UI thread (it renders the live tree). Never
        raises: if pixels cannot be read on this backend it reports ``False``
        (do not claim blank) rather than propagating.
        """
        longest = max(int(self.width), int(self.height), 1)
        scale = min(1.0, self._BLANK_PROBE_MAX_DIM / longest)
        img = self._render_snapshot(scale=scale)
        tobytes = getattr(img, "tobytes", None)
        if not callable(tobytes):
            return False
        rgba = tobytes()  # 4 bytes/pixel (RGBA); byte order is irrelevant here
        if len(rgba) < 8:
            return False
        # A single uniform color == the buffer equals its first pixel repeated.
        first = rgba[:4]
        return rgba == first * (len(rgba) // 4)

    def _dispatch_mouse_motion(self, x: int, y: int, *, buttons: int = 0, modifier_keys: int = 0):
        _dispatch_mouse_motion_fn(self, x, y, buttons=buttons, modifier_keys=modifier_keys)

    # --- Keyboard / focus helpers ---------------------------------
    def request_focus(self, node: Optional[FocusNode], source: FocusSource = FocusSource.KEYBOARD) -> None:
        """Set focus to the given FocusNode. Pass ``None`` to clear focus."""
        if self._focused_node is node:
            # Same node, possibly a different source: a pointer press on the widget
            # that Tab already focused still has to hide its focus ring.
            if node is not None:
                node.notify_focus_source(source)
            return

        # Blur previous node
        if self._focused_node:
            self._focused_node._set_focused(False)

        # Focus new node
        self._focused_node = node
        if node:
            node._set_focused(True, source)
            # Also update legacy target if the node belongs to a widget
            if node.region:
                self._focused_target = node.region
        else:
            self._focused_target = None

    def _occluding_overlay_content(self) -> Optional[Widget]:
        """Return the content of the topmost input-blocking overlay entry, if any."""
        overlay = self._overlay
        if overlay is None:
            # No App-installed overlay (e.g. a bare widget tree in a test).
            return None
        try:
            return overlay.occluding_content_widget()
        except Exception:
            exception_once(logger, "app_occluding_overlay_content_exc", "occluding_content_widget raised")
            return None

    def _focus_traversal_root(self) -> Optional[Widget]:
        """Return the widget the Tab sequence starts from.

        The app root, normally. While a modal (or any other input-blocking
        overlay entry) is open, the sequence is trapped inside that entry:
        everything behind it is already unreachable to the pointer, and the
        keyboard has to agree — Tab must not walk out of a dialog into controls
        the user cannot see or click.
        """
        occluding = self._occluding_overlay_content()
        return occluding if occluding is not None else self.root

    def _focus_traversal_descendants(self, widget: Widget) -> list[Widget]:
        """Return the widgets one traversal step below ``widget``."""
        try:
            children = list(widget.focus_traversal_children())
        except Exception:
            exception_once(logger, "app_focus_traversal_children_exc", "focus_traversal_children raised")
            children = []

        # Also traverse built child (for widgets that use build() but don't add to children_store)
        try:
            built = getattr(widget, "built_child", None)
            if built is not None and built is not widget:
                children.append(built)
        except Exception:
            exception_once(logger, "app_collect_focus_nodes_built_child_exc", "Traversing built_child raised")
        return children

    def _iter_focus_traversal(self, widget: Widget) -> Iterator[Widget]:
        """Yield ``widget`` and everything Tab can reach below it, in tree order.

        A :class:`FocusTraversalBlocker` that is currently blocking hides its
        whole subtree (a disabled ``Clickable``, a closed
        :class:`~nuiitivet.layout.collapsible.Collapsible`, a hidden
        ``visible()``), so the walk does not descend into it at all. A container
        that keeps content mounted off screen narrows the walk more finely,
        through :meth:`~nuiitivet.widgeting.widget.Widget.focus_traversal_children`.
        """
        try:
            if isinstance(widget, FocusTraversalBlocker) and widget.blocks_focus_traversal:
                return
        except Exception:
            exception_once(logger, "app_focus_traversal_blocker_exc", "blocks_focus_traversal raised")

        yield widget
        for child in self._focus_traversal_descendants(widget):
            yield from self._iter_focus_traversal(child)

    def _collect_focus_nodes(self) -> list[FocusNode]:
        """Return the Tab stops — the traversable FocusNodes — in tree order.

        Nodes marked non-traversable are skipped: they can still hold focus and
        receive keys, but an enclosing :class:`FocusScope` decides when they do,
        not the global Tab sequence.
        """
        res: list[FocusNode] = []
        root = self._focus_traversal_root()
        if root is None:
            return res
        try:
            for widget in self._iter_focus_traversal(root):
                try:
                    if isinstance(widget, InteractionHostMixin):
                        node = widget.get_node(FocusNode)
                        if isinstance(node, FocusNode) and node.traversable:
                            res.append(node)
                except Exception:
                    exception_once(logger, "app_collect_focus_nodes_walk_exc", "Collecting FocusNodes raised")
        except Exception:
            exception_once(logger, "app_collect_focus_nodes_root_exc", "Collecting FocusNodes from root raised")
        return res

    def _is_focus_reachable(self, node: Optional[FocusNode]) -> bool:
        """Return True if ``node``'s widget is still displayed.

        Reachability is the same walk the Tab sequence uses, so "displayed" means
        exactly one thing across the focus system. It is asked of the widget
        rather than of the node because a node may deliberately sit outside the
        Tab sequence (``traversable=False``) while remaining perfectly visible.
        """
        if node is None:
            return False
        owner = node.owner
        if owner is None:
            return False
        root = self._focus_traversal_root()
        if root is None:
            return False
        try:
            return any(widget is owner for widget in self._iter_focus_traversal(root))
        except Exception:
            exception_once(logger, "app_focus_reachable_exc", "Focus reachability walk raised")
            return True

    def _release_focus_if_blocked(self) -> None:
        """Keep focus on something the user can actually see.

        Content stops being displayed outside the focus system — a
        ``Collapsible`` closes, a ``visible()`` flips to ``False``, a ``Deck``
        switches page, a route is pushed over another, a modal opens — so focus
        left behind has to be dealt with here. Run once per frame, this both
        maintains the modal focus trap and drops focus that is no longer
        reachable.
        """
        self._sync_overlay_focus_trap()

        node = self._focused_node
        if node is None:
            return
        if not self._is_focus_reachable(node):
            self.request_focus(None)

    def _sync_overlay_focus_trap(self) -> None:
        """Move focus into a blocking overlay entry, and give it back on close.

        A modal takes focus with it: the user tabs inside the dialog, and when it
        goes away focus returns to whatever invoked it. Neither half can be
        expressed as a traversal rule — on close the dialog is already detached,
        so there is no tree left to reason about — which is why the invoker is
        remembered here, one frame at a time.
        """
        occluding = self._occluding_overlay_content()
        trap = self._overlay_focus_trap

        if occluding is not None:
            if any(widget is occluding for widget, _ in trap):
                # Already trapped here; unwind only the entries closed above it.
                while trap and trap[-1][0] is not occluding:
                    self._restore_focus_to(trap.pop()[1])
                return
            trap.append((occluding, self._focused_node))
            self._focus_first_stop()
            return

        while trap:
            self._restore_focus_to(trap.pop()[1])

    def _focus_first_stop(self) -> None:
        """Focus the first Tab stop of the current traversal root, or clear focus."""
        nodes = self._collect_focus_nodes()
        self.request_focus(nodes[0] if nodes else None, self._last_input_source)

    def _restore_focus_to(self, node: Optional[FocusNode]) -> None:
        """Give focus back to ``node``, or clear it when that widget is gone."""
        self.request_focus(node if self._is_focus_reachable(node) else None, self._last_input_source)

    def _focus_scope_for(self, node: Optional[FocusNode]) -> Optional[FocusScope]:
        """Return the innermost FocusScope enclosing ``node``, if any.

        Walking up from the node means nested scopes resolve inside-out: with a
        submenu open, its scope answers for the focus inside it, not the parent
        menu's.
        """
        if node is None:
            return None

        widget: Optional[Widget] = node.owner
        while widget is not None:
            if isinstance(widget, InteractionHostMixin):
                scope = widget.get_node(FocusScope)
                if isinstance(scope, FocusScope):
                    return scope
            widget = getattr(widget, "_parent", None)
        return None

    def _scope_owner_node(self, scope: Optional[FocusScope], nodes: list[FocusNode]) -> Optional[FocusNode]:
        """Return ``scope``'s own Tab stop — the FocusNode of the widget hosting it."""
        if scope is None:
            return None

        owner = scope.owner
        if not isinstance(owner, InteractionHostMixin):
            return None

        node = owner.get_node(FocusNode)
        if isinstance(node, FocusNode) and node in nodes:
            return node
        return None

    def _focus_traversal_target(self, node: FocusNode, go_back: bool) -> None:
        """Focus ``node`` as a Tab traversal target, entering its scope if it owns one.

        A scope entered from the outside starts at its last member on Shift+Tab
        and at its first otherwise, so Shift+Tab into a range slider lands on the
        far handle rather than walking the whole widget again.
        """
        self.request_focus(node, FocusSource.KEYBOARD)
        try:
            scope = self._focus_scope_for(node)
            if scope is not None:
                scope.on_enter(go_back)
        except Exception:
            exception_once(logger, "app_focus_scope_enter_exc", "Focus scope entry raised")

    def _dispatch_key_press(self, key, modifier_keys=0):
        """Handle key presses for focus navigation and activation.

        Accepts simple string names: 'tab', 'space', 'enter'. Returns True if handled.

        Escape is consumed here but *acts* on release: the press only latches
        intent, so it must not reach the focused node or Tab traversal, while
        :meth:`_dispatch_key_release` is what runs :meth:`handle_back_event`.
        Spawning back navigation from both halves would pop twice for every
        caller that synthesizes a full key tap.
        """
        self._last_input_source = FocusSource.KEYBOARD

        kname = None
        try:
            if isinstance(key, str):
                kname = key.lower()
        except Exception:
            debug_once(logger, "app_key_name_lower_exc", "Failed to normalize key name")
            kname = None

        if kname == "escape":
            # Consume without acting -- the release half runs back navigation.
            return True

        if kname == "tab":
            # Treat bit0 as shift (matches pyglet MOD_SHIFT in practice).
            go_back = bool(int(modifier_keys) & 1)

            # 1. The scope enclosing the focused node decides first. It may rove
            #    between its own members or consume Tab at its boundary (a menu
            #    dismisses itself), and it must get the chance before the global
            #    sequence does — the focused node may not even be a Tab stop.
            scope = None
            try:
                scope = self._focus_scope_for(self._focused_node)
                if scope is not None and scope.handle_tab(go_back):
                    # Roving inside the scope leaves the focused node as it is (a
                    # slider keeps focus while Tab moves between its handles), so
                    # announce that the focus is keyboard-driven again — the user
                    # may have been dragging it a moment ago.
                    if self._focused_node is not None:
                        self._focused_node.notify_focus_source(FocusSource.KEYBOARD)
                    return True
            except Exception:
                exception_once(logger, "app_dispatch_tab_scope_exc", "Focus scope Tab handling raised")

            # 2. Global traversal over the Tab stops.
            nodes = self._collect_focus_nodes()
            if nodes:
                try:
                    cur = self._focused_node
                    if cur not in nodes:
                        # The focused node is no Tab stop (a menu item, say). If Tab
                        # just escaped its scope, resume from the scope's own stop so
                        # the group is left in the direction the user asked for.
                        cur = self._scope_owner_node(scope, nodes)

                    if cur is None:
                        self._focus_traversal_target(nodes[0], go_back)
                        return True

                    idx = nodes.index(cur)
                    next_idx = (idx - 1) % len(nodes) if go_back else (idx + 1) % len(nodes)
                    self._focus_traversal_target(nodes[next_idx], go_back)
                    return True
                except Exception:
                    exception_once(logger, "app_dispatch_tab_traversal_exc", "Tab focus traversal raised")

            return False

        # 2. Try FocusNode bubbling (New System)
        if self._focused_node:
            try:
                if self._focused_node.handle_key_event(kname or str(key), modifier_keys):
                    return True
            except Exception:
                exception_once(logger, "app_focused_node_handle_key_exc", "Focused node handle_key_event raised")

        # 3. Unhandled by the focused widget: offer it to the key_shortcut
        #    bindings, narrowest scope first.
        if self._dispatch_shortcut(kname or str(key), modifier_keys):
            return True

        return False

    def _dispatch_shortcut(self, key: str, modifier_keys: int) -> bool:
        """Offer a key press the focused widget declined to the ``key_shortcut`` bindings.

        The scopes are consulted narrowest first, so whatever is closest to the
        user's attention wins: bindings enclosing the focused node, then bindings
        on the topmost interactable layer, then merely-mounted ones. The first
        scope that matches decides; the rest are not consulted. Returns True if a
        binding was triggered.

        A focused text field declines printable keys on the ``on_key`` route even
        though it is about to insert them as text through ``on_text``, so
        "declined" cannot be taken at face value here: a key the field will type
        is withheld from the bindings outright (see #331).
        """
        if self._text_input_claims(key, modifier_keys):
            return False

        if self._dispatch_focus_scoped_shortcut(key, modifier_keys):
            return True

        nodes = self._collect_shortcut_nodes()
        if self._dispatch_unordered_shortcut(nodes, key, modifier_keys, ShortcutScope.FOREGROUND):
            return True
        return self._dispatch_unordered_shortcut(nodes, key, modifier_keys, ShortcutScope.MOUNT)

    def _text_input_claims(self, key: str, modifier_keys: int) -> bool:
        """Return True if the focused node will consume ``key`` as text input.

        Two questions, both of which must hold: does the focused chain take text
        at all (a fact — it is the chain ``on_text`` is delivered along), and is
        this key one that text input may claim (an approximation, deliberately
        biased toward text; see :func:`produces_text`).
        """
        node = self._focused_node
        if node is None:
            return False
        try:
            if not node.accepts_text_input:
                return False
        except Exception:
            exception_once(logger, "app_accepts_text_input_exc", "FocusNode.accepts_text_input raised")
            return False
        return produces_text(key, modifier_keys)

    def _dispatch_focus_scoped_shortcut(self, key: str, modifier_keys: int) -> bool:
        """Trigger the innermost FOCUS-scoped binding enclosing the focused node."""
        node = self._focused_node
        if node is None:
            return False

        widget: Optional[Widget] = node.owner
        while widget is not None:
            try:
                if isinstance(widget, InteractionHostMixin):
                    shortcut_node = widget.get_node(ShortcutNode)
                    if isinstance(shortcut_node, ShortcutNode):
                        binding = shortcut_node.match(key, modifier_keys, ShortcutScope.FOCUS)
                        if binding is not None:
                            shortcut_node.trigger(binding)
                            return True
            except Exception:
                exception_once(logger, "app_dispatch_focus_shortcut_exc", "Focus-scoped shortcut dispatch raised")
            widget = getattr(widget, "_parent", None)

        return False

    def _dispatch_unordered_shortcut(
        self,
        nodes: list[ShortcutNode],
        key: str,
        modifier_keys: int,
        scope: ShortcutScope,
    ) -> bool:
        """Trigger the one binding matching ``key`` in ``scope``, if it is unambiguous.

        FOREGROUND and MOUNT bindings have no ordering between them — two
        displayed panes can bind the same gesture with nothing to choose between
        them. Rather than picking arbitrarily, an ambiguous match fires nothing
        and warns (as Qt does). ``ShortcutScope.FOCUS`` is the way to express a
        gesture whose target depends on which pane is active.
        """
        matches: list[Tuple[ShortcutNode, ShortcutBinding]] = []
        for node in nodes:
            try:
                if scope is ShortcutScope.FOREGROUND:
                    owner = node.owner
                    if owner is None or not is_foreground(owner):
                        continue
                binding = node.match(key, modifier_keys, scope)
                if binding is not None:
                    matches.append((node, binding))
            except Exception:
                exception_once(logger, "app_dispatch_shortcut_match_exc", "Shortcut match raised")

        if not matches:
            return False

        if len(matches) > 1:
            owners = ", ".join(type(node.owner).__name__ for node, _ in matches)
            warning_once(
                logger,
                f"app_ambiguous_shortcut:{scope.value}:{key}:{modifier_keys}",
                "Ambiguous %s shortcut: %s is bound by %d widgets (%s). Firing none — "
                "use ShortcutScope.FOCUS if the target depends on which one is active.",
                scope.value,
                key,
                len(matches),
                owners,
            )
            return False

        node, binding = matches[0]
        node.trigger(binding)
        return True

    def _collect_shortcut_nodes(self) -> list[ShortcutNode]:
        """Collect every ShortcutNode in the widget tree, in tree order."""
        res: list[ShortcutNode] = []

        def walk(w: Widget) -> None:
            try:
                if isinstance(w, InteractionHostMixin):
                    node = w.get_node(ShortcutNode)
                    if isinstance(node, ShortcutNode):
                        res.append(node)
            except Exception:
                exception_once(logger, "app_collect_shortcut_nodes_walk_exc", "Collecting ShortcutNodes raised")
            try:
                for c in w.children_snapshot():
                    walk(c)
            except Exception:
                exception_once(
                    logger,
                    "app_collect_shortcut_nodes_children_exc",
                    "Traversing children_snapshot raised",
                )
            try:
                built = getattr(w, "built_child", None)
                if built is not None and built is not w:
                    walk(built)
            except Exception:
                exception_once(
                    logger,
                    "app_collect_shortcut_nodes_built_child_exc",
                    "Traversing built_child raised",
                )

        try:
            if self.root is not None:
                walk(self.root)
        except Exception:
            exception_once(logger, "app_collect_shortcut_nodes_root_exc", "Collecting ShortcutNodes from root raised")
        return res

    def _dispatch_key_release(self, key, modifier_keys=0) -> bool:
        """Handle key releases, mirroring :meth:`_dispatch_key_press`.

        Back-navigation keys off the Escape *release* (the press only latches
        intent), so Escape is routed to :meth:`handle_back_event` here rather
        than to the focused node. Every other key is routed to the focused
        :class:`FocusNode` via :meth:`FocusNode.handle_key_release_event`, with
        the same bubbling semantics as key press. Unlike a press there is no Tab
        traversal — traversal is a press-time action. Returns True if handled.
        """
        kname = None
        try:
            if isinstance(key, str):
                kname = key.lower()
        except Exception:
            debug_once(logger, "app_key_release_name_lower_exc", "Failed to normalize key name")
            kname = None

        if kname == "escape":
            spawn_task(self.handle_back_event(), owner_name="App.on_key_release(escape)")
            return True

        if self._focused_node:
            try:
                if self._focused_node.handle_key_release_event(kname or str(key), modifier_keys):
                    return True
            except Exception:
                exception_once(
                    logger,
                    "app_focused_node_handle_key_release_exc",
                    "Focused node handle_key_release_event raised",
                )

        return False

    @property
    def modifier_keys(self) -> int:
        """The keyboard-modifier keys currently held down.

        A bitmask of ``MOD_SHIFT``/``MOD_CTRL``/``MOD_ALT``/``MOD_META``. This is
        the single authoritative source of "which modifier keys are down",
        maintained by the backend on every key press and release and cleared on
        window deactivation. It is exposed for framework internals only and must
        not be treated as mutable application state.
        """
        return self._modifier_keys

    def _set_modifier_keys(self, modifier_keys: int) -> None:
        """Update the authoritative modifier-key mask (framework-internal).

        When the mask actually changes, a synthetic pointer event is delivered
        to the widget under (or capturing) the pointer via
        :meth:`_dispatch_modifier_keys_change` so ``pointer_input`` handlers can
        react to a modifier press/release even while the pointer is stationary.
        """
        try:
            new_mask = int(modifier_keys)
        except Exception:
            debug_once(logger, "app_set_modifier_keys_exc", "Failed to set modifier-key mask")
            new_mask = 0
        if new_mask == self._modifier_keys:
            return
        self._modifier_keys = new_mask
        self._dispatch_modifier_keys_change()

    def _clear_modifier_keys(self) -> None:
        """Clear the authoritative modifier-key mask (framework-internal).

        Called when the window loses focus so that a modifier released while the
        app was inactive cannot leave a permanently stuck mask.
        """
        if self._modifier_keys == 0:
            return
        self._modifier_keys = 0
        self._dispatch_modifier_keys_change()

    def _dispatch_modifier_keys_change(self) -> None:
        """Notify ``pointer_input`` handlers that the modifier-key mask changed.

        The synthetic event is placed at the last known pointer position and
        routed to the widget currently capturing the pointer, or failing that
        the widget under the pointer. Only :class:`PointerListenerNode` instances
        that are inside or captured respond (see
        :meth:`InteractionHostMixin.dispatch_modifier_keys_change`).
        """
        pos = self._last_pointer_pos
        if pos is None:
            return

        manager = self._pointer_capture_manager
        target: Any = None
        if manager is not None:
            target = manager.owner_of(self._primary_pointer_id)
        if target is None:
            target = self._last_hover_target
        if target is None:
            return

        event = PointerEvent.mouse_event(
            self._primary_pointer_id,
            PointerEventType.MOVE,
            pos[0],
            pos[1],
            buttons=self._last_pointer_buttons,
            modifier_keys=self._modifier_keys,
        )

        current = target
        visited: set[int] = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            dispatcher = getattr(current, "dispatch_modifier_keys_change", None)
            if callable(dispatcher):
                try:
                    if dispatcher(event):
                        self.invalidate()
                        return
                except Exception:
                    exception_once(
                        logger,
                        "app_dispatch_modifier_keys_change_exc",
                        "dispatch_modifier_keys_change raised (target=%s)",
                        type(current).__name__,
                    )
            current = getattr(current, "_parent", None)

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

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Optional[int] = None, modifier_keys: int = 0):
        self._last_input_source = FocusSource.POINTER
        _dispatch_mouse_press_fn(self, x, y, button=button, modifier_keys=modifier_keys)

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Optional[int] = None, modifier_keys: int = 0):
        _dispatch_mouse_release_fn(self, x, y, button=button, modifier_keys=modifier_keys)

    def _dispatch_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> Optional[Widget]:
        """Deliver a wheel event; return the widget that consumed it, if any."""
        return _dispatch_mouse_scroll_fn(self, x, y, scroll_x, scroll_y)

    def _dispatch_file_drop(self, x: int, y: int, paths: Sequence[str]) -> Optional[Widget]:
        """Deliver an OS file drop; return the widget that consumed it, if any."""
        return _dispatch_file_drop_fn(self, x, y, paths)

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
            buttons=pivot.buttons,
            timestamp=time.time(),
            modifier_keys=pivot.modifier_keys,
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
        # Size callbacks queued by the previous frame's layout run first, so the
        # Observables they write are picked up by the build flush below and land
        # in this frame. Between frames is the only safe point for them: they are
        # arbitrary user code, and layout must never be re-entered from within.
        try:
            flush_size_change_callbacks()
        except Exception:
            exception_once(logger, "app_flush_size_change_callbacks_exc", "flush_size_change_callbacks failed")
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

    def run(self, draw_fps: Optional[float] = None, *, renderer: RendererMode = "auto"):
        """Run an interactive window using the pyglet backend.

        Args:
            draw_fps: Upper-bound frame-rate throttle. ``None`` (the default)
                draws purely on demand — a clean widget tree produces zero
                frames. A positive value caps the frame rate but still only
                draws when something has invalidated; it is a throttle, not a
                mandate to draw every frame.
            renderer: Renderer selection.

                - ``"auto"`` (default): try the GPU and silently fall back to
                  software (raster) rendering when it is unavailable.
                - ``"gpu"``: require the GPU; raise ``RuntimeError`` if the GPU
                  backend cannot be initialized or a GPU frame fails to render.
                - ``"cpu"``: always render in software; the GPU is never touched.

                For GPU-less, software-GL, or remote environments (with a
                display) prefer ``"cpu"``. Truly headless environments cannot use
                ``run()`` at all — render offscreen via :meth:`render_to_png`.

        When launched under ``python -m nuiitivet.dev`` (hot reload), this method
        does **not** block. It hands the App and its root factory to the active
        dev session and returns; the dev runner then drives the real event loop,
        file watching, and reloads. In production (no dev session) it blocks on
        the pyglet loop as usual.
        """

        resolved_renderer = parse_renderer_mode(renderer)

        # Hot-reload handoff: if the dev runner installed a session, give it the
        # App + factory and return without blocking. See nuiitivet.dev.
        try:
            from nuiitivet.dev import current_dev_session
        except Exception:
            current_dev_session = None  # type: ignore[assignment]
        if current_dev_session is not None:
            session = current_dev_session()
            if session is not None:
                session.attach(
                    app=self,
                    root_factory=self._root_factory,
                    draw_fps=draw_fps,
                    renderer=resolved_renderer,
                )
                return

        from ..backends.pyglet.runner import run_app

        run_app(self, draw_fps=draw_fps, renderer=resolved_renderer)

    def _rebuild_content_root(self, new_factory: "RootFactory | None" = None) -> _ContentRoot:
        """Rebuild the content subtree from the root factory.

        Re-invokes the root factory, rebuilds the Navigator/Overlay stack and
        re-wraps it with the preserved chrome shell and AppScope. The App shell —
        window, chrome, theme — is left untouched, and so is the App's current
        navigator/overlay: the result is **not** mounted, swapped in, or adopted
        until :meth:`_commit_content_root` takes it. Splitting build from commit
        lets the hot-reload orchestrator snapshot old state and restore it into
        the new tree before it is mounted, and keeps a failed commit from leaving
        the App pointing at a tree that never went on screen.

        Args:
            new_factory: Optional replacement factory re-fetched from a reloaded
                module. When given, it becomes the new source of truth (the
                factory captured at construction may reference stale module
                globals after a reload). When ``None``, the current factory is
                reused.

        Returns:
            The freshly built content root, its ``widget`` chrome + AppScope
            wrapped.
        """
        if new_factory is not None:
            self._root_factory = new_factory

        content_root = self._root_factory()
        if not isinstance(content_root, Widget):
            raise TypeError("root factory must return a Widget instance.")

        from nuiitivet.navigation import Navigator

        if isinstance(content_root, Navigator):
            navigator = content_root
        else:
            navigator = self._build_default_navigator(content_root)

        content = self._build_root_navigation_stack(
            navigator=navigator,
            overlay_factory=self._overlay_factory,
        )
        return replace(content, widget=self._wrap_with_chrome_and_scope(content.widget))

    def _commit_content_root(self, content: _ContentRoot) -> None:
        """Swap in a rebuilt content root: unmount the old tree, mount the new.

        The counterpart to :meth:`_rebuild_content_root`. Unmounts the previous
        root, installs the new widget as ``self.root``, adopts its navigator and
        overlay, mounts it against this App, and forces a repaint. Intended for
        the hot-reload path; the App shell and window are preserved across the
        swap.

        Adoption happens here rather than at build time so that a reload which
        builds cleanly but fails on the way in leaves ``self.navigator`` and
        ``self.overlay`` pointing at the tree the user can still see.

        Args:
            content: A content root produced by :meth:`_rebuild_content_root`.
        """
        new_root = content.widget
        old_root = self.root
        if old_root is not None and old_root is not new_root:
            try:
                old_root.unmount()
            except Exception:
                exception_once(logger, "app_reload_unmount_exc", "old root.unmount() raised")

        # Drop interaction state that pointed into the now-unmounted tree.
        # These are strong references (focus/hover/pressed targets), so leaving
        # them set would retain the old tree until the next interaction replaces
        # them — a leak counter to the reload's "no stale old-tree references"
        # goal. Pointer captures are weak but are released too so a subsequent
        # motion/release does not route to a dead capture.
        self._reset_interaction_state()

        self.root = new_root
        self._navigator = content.navigator
        self._overlay = content.overlay
        try:
            new_root.mount(self)
        except Exception:
            exception_once(logger, "app_reload_mount_exc", "new root.mount() raised")

        self._last_layout_size = None
        self._paint_dirty = True
        self.invalidate()

    def _reset_interaction_state(self) -> None:
        """Clear focus/hover/pressed targets and pointer captures.

        Used by the hot-reload swap so no strong reference into the old,
        unmounted tree survives. Safe to call at any time; it only nulls
        App-held references and drops capture records (without dispatching a
        cancel to the — now unmounted — captured widgets).
        """
        self._focused_node = None
        self._focused_target = None
        self._last_hover_target = None
        self._pressed_target = None
        manager = getattr(self, "_pointer_capture_manager", None)
        if manager is not None:
            try:
                for pointer_id in manager.captured_pointer_ids():
                    manager.release(pointer_id)
            except Exception:
                exception_once(logger, "app_reload_capture_release_exc", "pointer capture release raised")

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
        from nuiitivet.theme.intents import ThemeModeIntent, ThemeRegistryIntent

        if isinstance(intent, ThemeRegistryIntent):
            self._theme_registry.update(intent.themes)
            return

        if isinstance(intent, ThemeModeIntent):
            from nuiitivet.theme.theme import Theme

            theme_val = intent.theme
            if isinstance(theme_val, Theme):
                self._theme_manager.set_theme(theme_val)
            else:
                # Look up by name; fall back to light/dark built-ins
                theme_obj = self._theme_registry.get(str(theme_val))
                if theme_obj is None:
                    if str(theme_val) == "dark":
                        theme_obj = PlainTheme.dark()
                    else:
                        theme_obj = PlainTheme.light()
                self._theme_manager.set_theme(theme_obj)
            return

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

                    try:
                        if sys.platform == "win32":
                            import ctypes

                            SW_RESTORE = 9
                            hwnd = getattr(window, "_hwnd", None)
                            if hwnd:
                                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                    except Exception:
                        exception_once(logger, "app_dispatch_restore_win32_exc", "Windows restore fallback failed")

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
            if self.root is not None:
                self.root.unmount()
        except Exception:
            exception_once(logger, "app_close_root_unmount_exc", "root.unmount raised")
