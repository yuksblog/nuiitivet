"""Material App entry point."""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.runtime.app import App, ExitPolicy
from nuiitivet.runtime.window import Window


class MaterialApp(App):
    """Material Design application runner.

    Takes its main window as the first argument and supplies the Material
    default theme. Through the public surface the window is a
    :class:`~nuiitivet.material.window.MaterialWindow`:
    ``nv.App(nv.Window(content=...))``. Secondary windows are constructed
    with ``nv.Window(...)`` and shown with ``window.open()``.
    """

    def __init__(
        self,
        window: Window,
        *,
        theme: Optional[Any] = None,
        exit_policy: ExitPolicy = ExitPolicy.LAST_WINDOW_CLOSED,
    ) -> None:
        """Initialize a MaterialApp.

        Args:
            window: The main window, typically a
                :class:`~nuiitivet.material.window.MaterialWindow`.
            theme: The MaterialThemeFactory to use. Defaults to Light theme.
            exit_policy: When :meth:`run` returns; see
                :class:`~nuiitivet.runtime.app.ExitPolicy`.
        """
        if theme is None:
            theme = MaterialThemeFactory.light("#6750A4")

        super().__init__(window, theme=theme, exit_policy=exit_policy)
