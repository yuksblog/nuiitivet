"""Application menu bar: declarative model, styling, and placement.

The menu bar is registered on the App (``App(menu=nv.MenuBar([...]))``) as
plain declarative data, rendered as an in-app bar below the chrome (or at a
user-placed :class:`MenuBarArea`). See ``docs/design/MENU_BAR.md``.
"""

from .model import MenuBar, MenuBarItem, MenuBarRole
from .slots import MenuBarArea
from .style import MenuBarStyle
from .theme_data import MenuBarThemeData

__all__ = [
    "MenuBar",
    "MenuBarArea",
    "MenuBarItem",
    "MenuBarRole",
    "MenuBarStyle",
    "MenuBarThemeData",
]
