"""Material App entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from nuiitivet.material.navigation_visual_state import MaterialNavigationLayerComposer
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.runtime.app import App, RootFactory, _UNSET
from nuiitivet.runtime.window import WindowPosition, WindowSizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import ObservableBase
    from nuiitivet.runtime.chrome import CustomChrome, OSChrome


class MaterialApp(App):
    """Material Design application runner.

    This class configures the App with Material Design defaults:
    - Material Theme (light/dark)
    - Material Overlay (Dialog, Loading)
    - Material Background color
    - Material Navigator (with Material page transitions)

    Pass a ``Widget`` to use it directly as the root screen (with an implicit
    root ``MaterialNavigator``), or pass a ``Navigator`` / ``Navigator.routes(...)``
    / ``Navigator.intents(...)`` to customize the initial navigation stack.
    """

    def _build_default_navigator(self, content: Widget) -> Navigator:
        return MaterialNavigator(
            content,
            layer_composer=MaterialNavigationLayerComposer(),
        )

    def __init__(
        self,
        content: "Widget | RootFactory",
        *,
        overlay_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        background: ColorSpec = ColorRole.SURFACE,
        theme: Optional[Any] = None,
        title: str | None | ObservableBase[str | None] = None,
        chrome: OSChrome | CustomChrome | None = _UNSET,  # type: ignore[assignment]
        window_position: WindowPosition | None = None,
        resizable: bool = True,
    ) -> None:
        """Initialize a MaterialApp.

        Args:
            content: The root content. Accepts a ``Widget`` instance or a **root
                factory** (a zero-argument callable returning the root widget,
                e.g. ``App(content=Home)`` or ``App(content=build_root)``) —
                passing a factory enables hot reload under
                ``python -m nuiitivet.dev``. The resolved root can be a ``Widget``
                (used as the initial screen under an implicit
                ``MaterialNavigator``) or a ``Navigator`` (e.g.
                ``Navigator.routes(...)`` / ``Navigator.intents(...)``) to
                customize the navigation stack.
            overlay_routes: Optional mapping of Intent types to overlay builder functions.
            width: Window width specification ("auto", fixed integer, etc.).
            height: Window height specification.
            background: Background color of the window. Defaults to Material Surface color.
            theme: The MaterialThemeFactory to use. Defaults to Light theme.
            title: OS window title.
            chrome: Window decoration (``OSChrome``, ``CustomChrome``, or
                ``None`` for bare borderless). Omitting defaults to ``OSChrome()``.
            window_position: Initial window position.
            resizable: Whether the window can be resized. Defaults to True.
        """
        if theme is None:
            theme = MaterialThemeFactory.light("#6750A4")

        def _overlay_factory() -> MaterialOverlay:
            return MaterialOverlay(intents=overlay_routes)

        super().__init__(
            content=content,
            width=width,
            height=height,
            title=title,
            chrome=chrome,
            background=background,
            theme=theme,
            overlay_factory=_overlay_factory,
            window_position=window_position,
            resizable=resizable,
        )
