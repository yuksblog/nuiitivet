"""Material App entry point."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from nuiitivet.material.navigation_visual_state import MaterialNavigationLayerComposer
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.navigation.navigator import Navigator
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
        content: Widget,
        *,
        overlay_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
        width: WindowSizingLike = "auto",
        height: WindowSizingLike = "auto",
        background: ColorSpec = ColorRole.SURFACE,
        theme: Optional[Any] = None,
        title_bar: Optional[TitleBar] = None,
        window_position: WindowPosition | None = None,
        resizable: bool = True,
    ) -> None:
        """Initialize a MaterialApp.

        Args:
            content: The root content. Can be a ``Widget`` (used as the initial
                screen under an implicit ``MaterialNavigator``) or a
                ``Navigator`` (e.g. ``Navigator.routes(...)`` or
                ``Navigator.intents(...)``) to customize the navigation stack.
            overlay_routes: Optional mapping of Intent types to overlay builder functions.
            width: Window width specification ("auto", fixed integer, etc.).
            height: Window height specification.
            background: Background color of the window. Defaults to Material Surface color.
            theme: The MaterialTheme to use. Defaults to Light theme.
            title_bar: Custom window title bar.
            window_position: Initial window position.
            resizable: Whether the window can be resized. Defaults to True.
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
            resizable=resizable,
        )
