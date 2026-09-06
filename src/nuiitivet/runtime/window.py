"""The ``Window`` type: one OS window, its widget tree, and its services.

A ``Window`` is constructed as a model (no OS window, no mounted tree),
realized by :meth:`Window.open`, and destroyed by :meth:`Window.close` — one
object is one window lifetime. It is also the host object widget trees mount
against: focus, pointer dispatch, rendering, overlay/navigator ownership, and
the menu bar all live here, per window. The application-wide runtime (theme,
event loop, exit policy, app-scoped intents) is
:class:`nuiitivet.runtime.app.App`.
"""

import itertools
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
from nuiitivet.observable import Observable
from nuiitivet.theme.plain_theme import PlainColorRole
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
from nuiitivet.platform.ime import IMEManager
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
from .window_sizing import WindowSizingLike, WindowPosition, parse_window_sizing
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container

if TYPE_CHECKING:
    from nuiitivet.menubar.model import MenuBar
    from nuiitivet.navigation.navigator import Navigator
    from nuiitivet.overlay.overlay import Overlay
    from nuiitivet.runtime.app import App
    from nuiitivet.theme.manager import ThemeManager


logger = logging.getLogger(__name__)

_UNSET = object()

# Source of :attr:`Window.id` values; process-wide so ids stay unique across
# every App an interpreter creates.
_window_ids = itertools.count(1)

# A root factory is any zero-argument callable returning the root Widget. Passing
# a factory (rather than a Widget instance) is what enables hot reload: the dev
# runner re-invokes it to rebuild the tree after a module reload. A bare Widget
# subclass qualifies (``Window(content=CounterApp)``), as does a function or lambda.
RootFactory = Callable[[], Widget]


# NOTE: compatibility wrapper removed. Use `resolve_color_to_rgba` from
# `nuiitivet.theme.resolver` to resolve theme ColorRole/ColorLike values to
# an (r,g,b,a) tuple. The app stores a primitive (RGBA tuple) or a
# backend-specific color object (converted below) in `_background_color`.


class WindowScope(Widget):
    """Inherited widget that provides access to the owning :class:`Window`.

    Every window's root is wrapped in one of these (inside the app-wide
    ``AppScope``), so ``Window.of(context)`` — and the window-scoped fallback
    of ``Overlay.of`` / ``Navigator.of`` — resolves to the window the context
    belongs to, never to a process-wide default.
    """

    def __init__(self, window: "Window", child: Widget, *, key: "str | None" = None) -> None:
        super().__init__(key=key)
        self._window_ref = weakref.ref(window)
        self.add_child(child)

    @property
    def window(self) -> Optional["Window"]:
        """The Window this scope belongs to, or ``None`` once collected."""
        return self._window_ref()

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


class Window:
    """One OS window: its widget tree, services, and lifecycle.

    Construction builds a model only — no OS window, no mounted tree.
    :meth:`open` realizes it (and registers it with the running
    :class:`~nuiitivet.runtime.app.App`); :meth:`close` destroys it. One
    object is one window lifetime: a closed Window is finished, and showing
    the same content again means constructing a new one. State that must
    survive a window lives in app-layer Observables passed into the content.
    """

    # The wrapped, mounted root tree. Assigned by :meth:`open` (and swapped by
    # the hot-reload commit); absent while the window is only constructed.
    root: Widget

    # Set when a CustomChrome is in use (see :meth:`_wrap_with_chrome_and_scope`).
    _window_drag_area: Optional[WindowDragArea] = None

    # Whether this OS window currently holds the OS focus; maintained by the
    # backend through :meth:`_set_os_active`.
    _os_active: bool

    # The Window's own navigation layers, adopted in :meth:`_commit_content_root`.
    # These are what ``Navigator.of`` / ``Overlay.of`` fall back to, so they are
    # per-Window state and never a process-wide global.
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

    @property
    def menu(self) -> "MenuBar | None":
        """The registered application menu bar model, or ``None``.

        Assigning replaces the model wholesale and rebuilds the rendered bar;
        item *properties* (label / enabled / checked) may be Observables and
        propagate live without replacement.
        """
        return self._menubar_controller.model

    @menu.setter
    def menu(self, model: "MenuBar | None") -> None:
        self._menubar_controller.set_model(model)

    def _on_window_created(self) -> None:
        """Backend hook: the OS window exists now.

        Attaches platform integrations that need a live window — today the
        menu bar's platform bridge (the macOS global menu bar, which follows
        the focused window; see ``nuiitivet.menubar.focus``).
        """
        self._menubar_controller.install_platform_bridge()

    @property
    def ime(self) -> IMEManager:
        """This window's IME geometry (cursor rect and window location).

        One instance per window, so two windows never race each other's
        candidate-window positioning.
        """
        return self._ime

    def _set_os_active(self, active: bool) -> None:
        """Backend hook: this OS window gained or lost the OS focus.

        Maintains :attr:`_os_active` and lets the macOS menu bar coordinator
        follow the focus. On focus loss a pending IME composition is committed
        (the backend separately discards the OS-side conversation), so the
        window's text field is settled while another window types. Called from
        the backend's activate/deactivate events, on the UI thread.
        """
        active = bool(active)
        if self._os_active == active:
            return
        self._os_active = active
        if not active:
            self._commit_ime_composition()
        self._menubar_controller.os_focus_changed(active)

    def _commit_ime_composition(self) -> None:
        """Commit a pending IME composition on the focused node, if any.

        The provisional text of a half-converted composition is kept as
        committed text — matching what native fields do when their window
        loses focus — rather than dropped.
        """
        node = self._focused_node
        if node is None:
            return
        handler = getattr(node, "handle_ime_commit_event", None)
        if handler is None:
            return
        try:
            handler()
        except Exception:
            exception_once(
                logger,
                "app_focused_node_ime_commit_exc",
                "Focused node IME commit raised",
            )

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
    def of(context: Widget) -> "Window":
        """Return the Window whose tree contains ``context``.

        The returned object is the same ``Window`` the opener holds — there is
        no proxy type. A ViewModel should receive it typed as
        :class:`~nuiitivet.runtime.protocols.WindowProtocol`. Valid from
        ``on_mount``, not from ``__init__``, like every ``.of()`` lookup.

        Args:
            context: The widget context.

        Returns:
            The owning Window.

        Raises:
            RuntimeError: If called before ``context`` is mounted (typically
                from ``__init__``), or if the widget is not attached to a
                Window.
        """
        scope = find_provider(context, WindowScope)
        window = scope.window if scope is not None else None
        if window is None:
            raise_if_premature_lookup("Window.of", context)
            raise RuntimeError("WindowScope not found. Is the widget attached to a Window?")
        return window

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
        # Default menu bar placement: a slot at the top of the content area,
        # below the chrome. Inserted only when a menu was registered at App
        # construction; the slot itself stays empty whenever a user-placed
        # MenuBarArea is mounted (see nuiitivet/menubar/slots.py).
        menubar_slot: Widget | None = None
        if getattr(self, "_menubar_controller", None) is not None and self._menubar_controller.model is not None:
            from nuiitivet.menubar.slots import DefaultMenuBarSlot

            menubar_slot = DefaultMenuBarSlot()

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

            chrome_children: list[Widget] = [self._window_drag_area]
            if menubar_slot is not None:
                chrome_children.append(menubar_slot)
            chrome_children.append(Container(child=root, width="wt", height="wt"))
            root = Column(children=chrome_children, width="wt", height="wt")
        elif menubar_slot is not None:
            root = Column(
                children=[
                    menubar_slot,
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
        from nuiitivet.layout.geometry import Geometry
        from nuiitivet.runtime.app import AppScope

        # Two scope layers: the app-wide AppScope (theme provider, App access)
        # outside, this window's WindowScope inside, so both App.of and
        # Window.of resolve from anywhere in the tree.
        return AppScope(app=self.app, child=WindowScope(window=self, child=Geometry(root)))

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
        window_position: WindowPosition | None = None,
        resizable: bool = True,
        accepts_first_mouse: bool = True,
        menu: "MenuBar | None" = None,
        parent: "Window | None" = None,
        modal: bool = False,
        close_action: "str | ObservableBase[str]" = "close",
    ):
        """Initialize the Window model. :meth:`open` realizes it.

        Args:
            content: The root content. Accepts either a ready ``Widget``
                instance or a **root factory** — a zero-argument callable
                returning the root ``Widget``. Passing a factory is what
                enables hot reload under ``python -m nuiitivet.dev``: the
                runner re-invokes it to rebuild the tree after a module
                reload. The resulting root may be a ``Navigator`` (used
                directly as the root Navigator) or any other ``Widget``, in
                which case a default root ``Navigator`` is created implicitly.
            width: Window width specification.
            height: Window height specification.
            title: OS window title. Accepts a plain string or an
                :class:`~nuiitivet.observable.protocols.ObservableBase` for
                dynamic updates. Pass ``None`` for no title.
            chrome: Window decoration. Pass an :class:`OSChrome` instance to
                use OS-managed decorations with an optional style variant,
                :class:`CustomChrome` for an app-drawn header, or ``None``
                for a bare borderless window. Omitting this parameter (the
                default) is equivalent to ``OSChrome()``.
            background: Window background color.
            overlay_factory: Optional overlay factory.
            window_position: Initial window position.
            resizable: Whether the window can be resized.
            accepts_first_mouse: macOS only. When ``True`` (default), the
                click that activates this window while it is inactive is
                also delivered to the app, matching Windows/Linux and
                today's platform norm (Finder, Preview). Pass ``False`` to
                restore activate-only behavior for windows where an
                accidental first click could commit something. No effect
                on other platforms — they always deliver the click.
            menu: The menu bar model (:class:`~nuiitivet.menubar.MenuBar`),
                or ``None`` for no menu bar. Replace it wholesale via
                ``window.menu = ...``.
            parent: The parent window, or ``None`` for a top-level window.
                A child stacks with its parent and closes when it closes.
            modal: Whether this window blocks input to its parent chain
                while open (framework modal). Requires ``parent``.
            close_action: What the OS close button does: ``"close"`` (default)
                destroys the window; ``"hide"`` parks it — :meth:`hide` —
                so a tray-resident app can be summoned back. Accepts an
                Observable so the choice can follow live state; the resident
                recipe binds it to ``TrayIcon.installed`` (hide only while
                the tray is actually showing). Programmatic :meth:`close`
                is unaffected.
        """
        # Normalize ``content`` to a root factory. A Widget instance is wrapped
        # in a factory that always returns that same instance (so hot reload is
        # a no-op for it); a callable is stored as-is. ``self._root_factory`` is
        # the single source of truth the reload path re-invokes.
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

        if parent is not None and not isinstance(parent, Window):
            raise TypeError("'parent' must be a Window instance or None.")
        if modal and parent is None:
            raise ValueError("modal=True requires a parent window.")
        self._parent: "Window | None" = parent
        self._modal = bool(modal)

        # Stable per-process identity, used by tooling (the dev bridge's
        # window selector) and useful in logs. Never reused within a process.
        self.id: int = next(_window_ids)

        if not isinstance(close_action, ObservableBase) and close_action not in ("close", "hide"):
            raise ValueError('close_action must be "close", "hide", or an Observable of one.')
        self._close_action: "str | ObservableBase[str]" = close_action

        # Lifecycle: created -> open -> closed, one way. Visibility is
        # orthogonal: a hidden window is still open (and still counts for the
        # App's exit policy).
        self._app_ref: Any = None
        self._lifecycle_state: str = "created"
        self._is_open_obs: Observable[bool] = Observable(False)
        self._visible_obs: Observable[bool] = Observable(True)
        self._closed_event: Any = None
        self._os_active = False
        # Per-window IME geometry (cursor rect, window location). Written by
        # this window's focused text field and its backend window, read by the
        # platform IME hook installed on this OS window. See design doc 8.6.
        self._ime = IMEManager()

        self._width_spec: WindowSizingLike = width
        self._height_spec: WindowSizingLike = height

        self.chrome: OSChrome | CustomChrome | None = OSChrome() if chrome is _UNSET else chrome
        # Reset the drag-area reference (class default is None); a CustomChrome
        # rebuilds it in :meth:`_wrap_with_chrome_and_scope`.
        self._window_drag_area = None

        # Menu bar: the controller owns the registered model and the slots
        # rendering it. The default slot is inserted below the chrome (see
        # :meth:`_wrap_with_chrome_and_scope`) only when a menu was registered
        # at construction; a MenuBarArea in the tree takes over regardless.
        from nuiitivet.menubar.controller import MenuBarController

        self._menubar_controller: MenuBarController = MenuBarController(self, menu)

        # Provisional window size. An ``auto`` dimension is resolved at the end
        # of :meth:`open`, once the tree is mounted and can be measured against
        # the real theme; until then ``on_mount`` code that reads window.width /
        # window.height must still see a number rather than an AttributeError.
        self.width = self._resolve_window_sizing(width, preferred=0, fallback=640)
        self.height = self._resolve_window_sizing(height, preferred=0, fallback=480)
        self.window_position = window_position
        self.resizable = resizable
        self.accepts_first_mouse = bool(accepts_first_mouse)

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
        # Dev-only observer for the interaction journal. The dev runner
        # attaches an ``InteractionRecorder`` here so the human's coarse UI
        # actions can be recorded for an AI pair to pull; ``None`` -- and zero
        # overhead -- in production.
        self._interaction_recorder: Optional[Any] = None
        # Dev-only designation mode. The dev runner attaches an
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
        # Resolved lazily (and re-resolved on theme change): resolution needs
        # the App's theme, which this Window meets at :meth:`open`.
        self._background_color: Any = None
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
        installed.

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

    # --- Lifecycle -----------------------------------------------------

    def _attach_app(self, app: "App") -> None:
        """Bind this window to its owning App (framework-internal)."""
        self._app_ref = weakref.ref(app)

    @property
    def app(self) -> "App":
        """The owning :class:`~nuiitivet.runtime.app.App`.

        Raises:
            RuntimeError: If the window is not attached to an App (it attaches
                at :meth:`open`, or when passed to the App constructor).
        """
        app = self._app_ref() if self._app_ref is not None else None
        if app is None:
            raise RuntimeError("Window is not attached to an App.")
        return app

    @property
    def parent(self) -> "Window | None":
        """The parent window, or ``None`` for a top-level window."""
        return self._parent

    @property
    def modal(self) -> bool:
        """Whether this window blocks input to its parent chain while open."""
        return self._modal

    @property
    def is_open(self) -> "ObservableBase[bool]":
        """Observable open state: ``True`` between :meth:`open` and :meth:`close`."""
        return self._is_open_obs

    @property
    def is_main(self) -> bool:
        """Whether this is the App's main window."""
        app = self._app_ref() if self._app_ref is not None else None
        return app is not None and app.main_window is self

    @property
    def closed(self) -> Any:
        """An awaitable that resolves once the window has closed."""
        return self._wait_closed()

    async def _wait_closed(self) -> None:
        if self._lifecycle_state == "closed":
            return
        if self._closed_event is None:
            import asyncio

            self._closed_event = asyncio.Event()
        await self._closed_event.wait()

    @property
    def _theme_manager(self) -> "ThemeManager":
        """The App's theme manager (the theme is app-wide)."""
        return self.app._theme_manager

    def open(self) -> "Window":
        """Realize the window: build and mount the tree, register with the App.

        The OS window itself is created by the running backend — immediately
        when the loop is already running, or when ``app.run()`` starts for
        windows opened before it.

        Returns:
            ``self``, for chaining.

        Raises:
            RuntimeError: If the window is already open, is already closed
                (one object is one window lifetime), no App exists yet, or
                the parent window is not open.
        """
        if self._lifecycle_state == "open":
            raise RuntimeError("Window is already open.")
        if self._lifecycle_state == "closed":
            raise RuntimeError(
                "A closed Window is finished; construct a new Window to show its content again."
            )
        app = self._app_ref() if self._app_ref is not None else None
        if app is None:
            from nuiitivet.runtime.app import current_app

            app = current_app()
            if app is None:
                raise RuntimeError("Window.open() requires an App; construct the App first.")
            self._app_ref = weakref.ref(app)
        if self._parent is not None and self._parent._lifecycle_state != "open":
            raise RuntimeError("Window.open(): the parent window is not open.")

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
            overlay_factory=self._overlay_factory,
        )
        # Nothing to unmount on the initial path, so adopt straight away; the
        # reload path defers this to :meth:`_commit_content_root`.
        self._navigator = built.navigator
        self._overlay = built.overlay

        # Apply the chrome decoration and scope wrapping. This must precede the
        # auto-size measurement below: the AppScope installed here is what
        # ``Theme.of`` resolves against, so a tree measured before it exists is
        # measured against the default theme.
        self.root = self._wrap_with_chrome_and_scope(built.widget)

        self._update_background_color()
        self._subscribe_title_updates()

        self._lifecycle_state = "open"
        self._is_open_obs.value = True

        # Mounting comes after every attribute a lifecycle hook might touch is
        # initialized (see ``__init__``): ``mount()`` runs on_mount for the
        # whole tree, and that user code can call straight back into the Window.
        try:
            self.root.mount(self)
        except Exception:
            exception_once(logger, "window_open_root_mount_exc", "root.mount(self) raised during Window.open()")

        width_sizing = parse_window_sizing(self._width_spec)
        height_sizing = parse_window_sizing(self._height_spec)
        if width_sizing.kind == "auto" or height_sizing.kind == "auto":
            self._apply_auto_window_size(
                width=self._width_spec,
                height=self._height_spec,
                target=built.initial_route_widget,
                chrome=self.chrome,
            )

        app._register_window(self)
        self._notify_visibility_changed()
        return self

    def close(self) -> None:
        """Destroy the window: unmount the tree and close the OS window.

        Closing is one-way — the object is finished afterwards. Children close
        first, transitively. Closing a window that is not open is a no-op.
        """
        if self._lifecycle_state != "open":
            return
        app = self._app_ref() if self._app_ref is not None else None

        if app is not None:
            for child in [w for w in app.windows if w.parent is self]:
                try:
                    child.close()
                except Exception:
                    exception_once(logger, "window_close_child_exc", "Closing a child window raised")

        self._lifecycle_state = "closed"
        self._is_open_obs.value = False

        self._unsubscribe_title_updates()

        try:
            root = getattr(self, "root", None)
            if root is not None:
                root.unmount()
        except Exception:
            exception_once(logger, "window_close_root_unmount_exc", "root.unmount raised")

        self._reset_interaction_state()

        os_window = self._window
        self._window = None
        self._event_loop = None
        if os_window is not None:
            try:
                os_window.close()
            except Exception:
                exception_once(logger, "window_close_os_window_exc", "Backend window close raised")

        event = self._closed_event
        if event is not None:
            try:
                event.set()
            except Exception:
                exception_once(logger, "window_closed_event_set_exc", "closed event set raised")

        if app is not None:
            app._unregister_window(self)
        # After unregistration, so the menu bar coordinator re-resolves
        # against the open set without this window.
        self._menubar_controller.window_closed()
        self._notify_visibility_changed()

    # --- Visibility ------------------------------------------------------

    @property
    def is_visible(self) -> "ObservableBase[bool]":
        """Whether the window is visible (or will be, once realized).

        Hidden is not closed: the object, its widget tree, and its geometry
        stay alive, and the window still counts for the App's exit policy.
        On Windows/Linux the taskbar entry follows this by itself.
        """
        return self._visible_obs

    def hide(self) -> None:
        """Hide the window, keeping the object and its widget tree alive.

        The counterpart of :meth:`show` — the pair a tray-resident app parks
        and summons its window with. Before the backend realizes the OS
        window this just records the desired state (so a window can start
        hidden); hiding a window that is not open is a no-op.
        """
        if self._lifecycle_state != "open" or not self._visible_obs.value:
            return
        self._visible_obs.value = False
        window = self._window
        if window is not None:
            try:
                window.set_visible(False)
            except Exception:
                exception_once(logger, "window_hide_exc", "Window.hide failed")
        self._notify_visibility_changed()

    def show(self) -> None:
        """Make the window visible and bring it to the front, focused.

        Also the "summon" action for an already-visible window: it raises
        and refocuses. Showing a window that is not open is a no-op (a
        closed Window is finished — construct a new one).
        """
        if self._lifecycle_state != "open":
            return
        was_hidden = not self._visible_obs.value
        self._visible_obs.value = True
        if was_hidden:
            # Before the OS window reappears, so a dock_visibility="auto"
            # tray restores the regular activation policy first.
            self._notify_visibility_changed()
        window = self._window
        if window is not None:
            try:
                window.set_visible(True)
                window.activate()
            except Exception:
                exception_once(logger, "window_show_exc", "Window.show failed")
            if was_hidden:
                self.invalidate(immediate=True)

    def _notify_visibility_changed(self) -> None:
        app = self._app_ref() if self._app_ref is not None else None
        if app is None:
            return
        try:
            app._window_visibility_changed()
        except Exception:
            exception_once(logger, "window_visibility_notify_exc", "visibility change notify raised")

    def _handle_close_request(self) -> None:
        """Act on the OS close button per ``close_action`` (``"close"`` | ``"hide"``).

        Called by the backend. Hiding the last visible window while no tray
        icon is showing leaves the user no way back to the app; that is
        almost certainly an app bug, so it logs a warning — but behaves as
        written (bind ``close_action`` to ``TrayIcon.installed`` instead).
        """
        action = self._close_action
        if isinstance(action, ObservableBase):
            action = action.value
        if action != "hide":
            self.close()
            return
        app = self._app_ref() if self._app_ref is not None else None
        if app is not None and self._visible_obs.value:
            others_visible = any(
                w is not self and w._lifecycle_state == "open" and w._visible_obs.value
                for w in app.windows
            )
            tray = getattr(app, "tray", None)
            tray_showing = tray is not None and bool(tray.installed.value)
            if not others_visible and not tray_showing:
                warning_once(
                    logger,
                    "window_hide_no_way_back",
                    'close_action="hide" hid the last visible window with no tray icon '
                    "showing; the user may have no way back to the app. Bind "
                    "close_action to TrayIcon.installed so it falls back to closing.",
                )
        self.hide()

    def _modal_blocked(self) -> bool:
        """Whether an open modal child (transitively) blocks this window's input."""
        app = self._app_ref() if self._app_ref is not None else None
        if app is None:
            return False
        for w in app.windows:
            if w is self or not w._modal or w._lifecycle_state != "open":
                continue
            p = w._parent
            while p is not None:
                if p is self:
                    return True
                p = p._parent
        return False

    def _modal_child(self) -> "Window | None":
        """The open modal window blocking this one, if any (topmost found)."""
        app = self._app_ref() if self._app_ref is not None else None
        if app is None:
            return None
        for w in reversed(app.windows):
            if w is self or not w._modal or w._lifecycle_state != "open":
                continue
            p = w._parent
            while p is not None:
                if p is self:
                    return w
                p = p._parent
        return None

    def _debug_record_invalidate(self) -> None:
        if not self._debug_invalidate:
            return

        # Extract a small stack and pick the first meaningful callsite above
        # framework internals. This is intentionally lightweight and best-effort.
        ignore_suffixes = (
            "/nuiitivet/runtime/window.py",
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
        root = getattr(self, "root", None)
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
        if getattr(self, "root", None) is None:
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

    def _render_to_png_bytes(self, clip: Optional[tuple[float, float, float, float]] = None) -> bytes:
        """Render the root widget to PNG bytes (raster surface).

        Uses `self._scale` when available to generate a high-DPI image. ``clip``
        is a logical ``(x, y, w, h)`` rect; only that region is rendered.
        """
        scale = max(1.0, float(getattr(self, "_scale", 1.0)))
        img = self._render_snapshot(scale=scale, settle=True, clip=clip)
        data = img.encodeToData()
        if data is None:
            raise RuntimeError("encodeToData() returned None (failed to encode image)")
        return bytes(data)

    def _render_snapshot(
        self,
        scale: float = 1.0,
        *,
        for_display: bool = False,
        settle: bool = False,
        clip: Optional[tuple[float, float, float, float]] = None,
    ):
        """Create a Skia image snapshot for the current root at given scale.

        Returns an image object. Raises RuntimeError if Skia is missing or
        snapshot/encoding fails.

        Args:
            scale: Device-pixel scale factor for the raster surface.
            clip: A logical ``(x, y, w, h)`` rect to render instead of the whole
                window. Layout is unchanged; the surface is just that region,
                so paint outside it is culled rather than cropped afterwards.
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

        clip_x, clip_y, clip_w, clip_h = clip if clip is not None else (0.0, 0.0, self.width, self.height)
        phys_w = max(1, int(round(clip_w * scale)))
        phys_h = max(1, int(round(clip_h * scale)))

        surface = make_raster_surface(phys_w, phys_h)
        canvas = surface.getCanvas()

        # Map logical coordinates to device pixels
        if scale != 1.0:
            canvas.scale(scale, scale)
        if clip is not None:
            canvas.translate(-clip_x, -clip_y)

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
        if self._modal_blocked():
            return
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
        return occluding if occluding is not None else getattr(self, "root", None)

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
        # Framework modal: key input to a window blocked by an open modal
        # child is consumed (True), never delivered — reporting it unhandled
        # would let the backend's key defaults (pyglet's ESC-closes-window)
        # act on the blocked window.
        if self._modal_blocked():
            return True

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
        is withheld from the bindings outright.
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
            root = getattr(self, "root", None)
            if root is not None:
                walk(root)
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
        if self._modal_blocked():
            return True

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
        if self._modal_blocked():
            return True
        if self._focused_node:
            try:
                if self._focused_node.handle_text_event(text):
                    return True
            except Exception:
                exception_once(logger, "app_focused_node_handle_text_exc", "Focused node handle_text_event raised")
        return False

    def _dispatch_text_motion(self, motion: int, select: bool = False) -> bool:
        """Handle text motion events (arrow keys, home/end, etc)."""
        if self._modal_blocked():
            return True
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
        if self._modal_blocked():
            return True
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
        if self._modal_blocked():
            return
        self._last_input_source = FocusSource.POINTER
        _dispatch_mouse_press_fn(self, x, y, button=button, modifier_keys=modifier_keys)

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Optional[int] = None, modifier_keys: int = 0):
        if self._modal_blocked():
            return
        _dispatch_mouse_release_fn(self, x, y, button=button, modifier_keys=modifier_keys)

    def _dispatch_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> Optional[Widget]:
        """Deliver a wheel event; return the widget that consumed it, if any."""
        if self._modal_blocked():
            return None
        return _dispatch_mouse_scroll_fn(self, x, y, scroll_x, scroll_y)

    def _dispatch_file_drop(self, x: int, y: int, paths: Sequence[str]) -> Optional[Widget]:
        """Deliver an OS file drop; return the widget that consumed it, if any."""
        if self._modal_blocked():
            return None
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
        # A hidden window produces no frames; :meth:`show` invalidates, so the
        # first frame after reappearing repaints everything that changed.
        if not self._visible_obs.value:
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

    # --- Window operations ---------------------------------------------
    # Each is a no-op when the OS window does not exist (not realized yet, or
    # already closed).

    def center(self) -> None:
        """Center the window on its screen."""
        window = self._window
        if window is None:
            return
        try:
            screen = window.screen
            if screen:
                x = (screen.width - window.width) // 2
                y = (screen.height - window.height) // 2
                window.set_location(x, y)
        except Exception:
            exception_once(logger, "window_center_exc", "Window.center failed")

    def maximize(self) -> None:
        """Maximize the window."""
        window = self._window
        if window is None:
            return
        try:
            # Save current window rect before maximizing
            try:
                wx, wy = window.get_location()
                ww, wh = window.width, window.height
                self._saved_window_rect = (wx, wy, ww, wh)
            except Exception:
                self._saved_window_rect = None

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
            exception_once(logger, "window_maximize_exc", "Window.maximize failed")

    def minimize(self) -> None:
        """Minimize the window."""
        window = self._window
        if window is None:
            return
        try:
            window.minimize()
        except Exception:
            exception_once(logger, "window_minimize_exc", "Window.minimize failed")

    def restore(self) -> None:
        """Restore the window from maximized/minimized/full-screen state."""
        window = self._window
        if window is None:
            return
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
                exception_once(logger, "window_restore_win32_exc", "Windows restore fallback failed")

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
                    exception_once(logger, "window_restore_rect_exc", "Failed to restore window rect")

            # Note: Pyglet doesn't have a direct 'unmaximize' or 'restore' from maximize
            # that is consistent across platforms.
        except Exception:
            exception_once(logger, "window_restore_exc", "Window.restore failed")

    def full_screen(self) -> None:
        """Enter full screen mode (no toggle; :meth:`restore` is the way back)."""
        window = self._window
        if window is None:
            return
        try:
            window.set_fullscreen(True)
        except Exception:
            exception_once(logger, "window_full_screen_exc", "Window.full_screen failed")

    def move_to(self, x: int, y: int) -> None:
        """Move the window to a specific screen position."""
        window = self._window
        if window is None:
            return
        try:
            window.set_location(int(x), int(y))
        except Exception:
            exception_once(logger, "window_move_to_exc", "Window.move_to failed")

    def resize(self, width: int, height: int) -> None:
        """Resize the window."""
        window = self._window
        if window is None:
            return
        try:
            window.set_size(int(width), int(height))
        except Exception:
            exception_once(logger, "window_resize_exc", "Window.resize failed")
