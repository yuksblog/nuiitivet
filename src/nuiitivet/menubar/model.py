"""Application menu bar model.

The menu bar is declarative data registered on ``App`` (``App(menu=...)``),
not widgets in the tree: on macOS the global menu bar lives outside the
window, and ``NSMenu`` renders labels, accelerators and check marks — not
widget subtrees. The entries themselves are the surface-neutral
:class:`~nuiitivet.menus.MenuEntry` model. See ``docs/design/MENU_BAR.md``.

Lives in the framework-common ``menubar`` package (not under ``material``):
the menu bar is not a Material Design component, so like the scrollbar it is
a generic widget whose palette arrives through the generic theme seam.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from nuiitivet.menus import MenuEntry

from .style import MenuBarStyle


class MenuBar:
    """The application menu bar model: the root of the declarative menu tree.

    Registered on the App (``App(menu=nv.MenuBar([...]))``) and replaced
    wholesale via ``app.menu = ...``. Structure is not observable — entry
    *properties* (label / enabled / checked) may be Observables, but adding
    or removing entries means assigning a new model.

    Args:
        items: Top-level entries. Bar entries are usually submenus
            (``MenuEntry("File", submenu=[...])``); a plain action entry is
            allowed and activates directly on click.
        style: Optional per-instance style; ``None`` follows the theme.
    """

    def __init__(
        self,
        items: Sequence[MenuEntry],
        *,
        style: Optional[MenuBarStyle] = None,
    ) -> None:
        entries = tuple(items)
        for entry in entries:
            if not isinstance(entry, MenuEntry):
                raise TypeError("MenuBar items must be MenuEntry instances.")
        self.items: Tuple[MenuEntry, ...] = entries
        self.style = style
