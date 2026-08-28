"""Material Window: a :class:`~nuiitivet.runtime.window.Window` with Material defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

from nuiitivet.material.navigation_visual_state import MaterialNavigationLayerComposer
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.runtime.window import RootFactory, Window, _UNSET
from nuiitivet.runtime.window_sizing import WindowPosition, WindowSizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.menubar.model import MenuBar
    from nuiitivet.observable.protocols import ObservableBase
    from nuiitivet.overlay.overlay import Overlay
    from nuiitivet.runtime.chrome import CustomChrome, OSChrome


class MaterialWindow(Window):
    """A window configured with Material Design defaults.

    Used by :class:`~nuiitivet.material.app.MaterialApp` for the main window,
    and directly (``nv.Window``) for secondary windows:

    - Material Overlay (Dialog, Loading)
    - Material Surface background color
    - Material Navigator (with Material page transitions)
    """

    def _build_default_navigator(self, content: Widget) -> Navigator:
        return MaterialNavigator(
            content,
            layer_composer=MaterialNavigationLayerComposer(),
        )

    def __init__(
        self,
        content: "Widget | RootFactory",
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        *,
        overlay_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
        background: ColorSpec = ColorRole.SURFACE,
        title: "str | None | ObservableBase[str | None]" = None,
        chrome: "OSChrome | CustomChrome | None" = _UNSET,  # type: ignore[assignment]
        overlay_factory: Callable[[], "Overlay"] | None = None,
        window_position: WindowPosition | None = None,
        resizable: bool = True,
        menu: "MenuBar | None" = None,
        parent: "Window | None" = None,
        modal: bool = False,
    ) -> None:
        """Initialize a MaterialWindow.

        Args:
            content: The root content — a ``Widget`` instance or a root
                factory; see :class:`~nuiitivet.runtime.window.Window`.
            width: Window width specification.
            height: Window height specification.
            overlay_routes: Optional mapping of Intent types to overlay
                builder functions (mutually exclusive with
                ``overlay_factory``).
            background: Window background color. Defaults to Material Surface.
            title: OS window title.
            chrome: Window decoration; omitting defaults to ``OSChrome()``.
            overlay_factory: Optional overlay factory overriding the Material
                default.
            window_position: Initial window position.
            resizable: Whether the window can be resized.
            menu: The window's menu bar model, or ``None``.
            parent: The parent window, or ``None`` for a top-level window.
            modal: Whether this window blocks input to its parent chain while
                open (framework modal). Requires ``parent``.
        """
        if overlay_factory is None:

            def overlay_factory() -> MaterialOverlay:
                return MaterialOverlay(intents=overlay_routes)

        elif overlay_routes is not None:
            raise ValueError("Specify only one of overlay_routes or overlay_factory")

        super().__init__(
            content=content,
            width=width,
            height=height,
            title=title,
            chrome=chrome,
            background=background,
            overlay_factory=overlay_factory,
            window_position=window_position,
            resizable=resizable,
            menu=menu,
            parent=parent,
            modal=modal,
        )
