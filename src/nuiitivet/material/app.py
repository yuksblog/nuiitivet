"""Material App entry point."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, cast

from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.navigation.route import Route
from nuiitivet.runtime.app import App
from nuiitivet.runtime.title_bar import TitleBar
from nuiitivet.runtime.window import WindowPosition, WindowSizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import Widget


class MaterialApp(App):
    """Material Design application runner.

    This class configures the App with Material Design defaults:
    - Material Theme (light/dark)
    - Material Dialogs (Alert, Loading)
    - Material Background color
    """

    @classmethod
    def navigation(  # type: ignore[override]
        cls,
        routes: Mapping[type[Any], Callable[[Any], Route | Widget]],
        initial_route: Any,
        *,
        overlay_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        background: ColorSpec = ColorRole.SURFACE,
        theme: Optional[Any] = None,
        title_bar: Optional[TitleBar] = None,
        window_position: WindowPosition | None = None,
    ) -> "MaterialApp":
        """Create a MaterialApp with a root Navigator and Overlay.

        Args:
            routes: A mapping of Intent types to route builder functions.
            initial_route: The initial Intent to launch.
            overlay_routes: Optional mapping of Intent types to overlay builder functions.
            width: Window width specification ("auto", fixed integer, etc.).
            height: Window height specification.
            background: Background color of the window. Defaults to Material Surface color.
            theme: The MaterialTheme to use. Defaults to Light theme.
            title_bar: Custom window title bar.
            window_position: Initial window position.

        Returns:
            Configured MaterialApp instance.
        """
        if theme is None:
            theme = MaterialTheme.light("#6750A4")

        def _overlay_factory() -> MaterialOverlay:
            return MaterialOverlay(intents=overlay_routes)

        return cast(
            MaterialApp,
            super().navigation(
                routes=routes,
                initial_route=initial_route,
                overlay_factory=_overlay_factory,
                width=width,
                height=height,
                title_bar=title_bar,
                background=background,
                theme=theme,
                window_position=window_position,
            ),
        )

    def __init__(
        self,
        content: Widget,
        *,
        overlay_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        background: ColorSpec = ColorRole.SURFACE,
        theme: Optional[Any] = None,
        title_bar: Optional[TitleBar] = None,
        window_position: WindowPosition | None = None,
    ) -> None:
        """Initialize a MaterialApp with a single root widget.

        Args:
            content: The root widget of the application.
            overlay_routes: Optional mapping of Intent types to overlay builder functions.
            width: Window width specification ("auto", fixed integer, etc.).
            height: Window height specification.
            background: Background color of the window. Defaults to Material Surface color.
            theme: The MaterialTheme to use. Defaults to Light theme.
            title_bar: Custom window title bar.
            window_position: Initial window position.
        """
        if theme is None:
            theme = MaterialTheme.light("#6750A4")

        def _overlay_factory() -> MaterialOverlay:
            return MaterialOverlay(intents=overlay_routes)

        super().__init__(
            content=content,
            width=width,
            height=height,
            title_bar=title_bar,
            background=background,
            theme=theme,
            overlay_factory=_overlay_factory,
            window_position=window_position,
        )
