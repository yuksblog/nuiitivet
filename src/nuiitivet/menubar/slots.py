"""Menu bar rendering slots.

A slot is a widget marking *where* the App-registered menu model renders; the
model itself stays on the App. Two kinds exist:

- :class:`DefaultMenuBarSlot` — inserted by the App below the chrome when a
  menu is registered at construction. The zero-configuration placement.
- :class:`MenuBarArea` — public; placed by the app author (e.g. inside a
  ``CustomChrome`` header row) to take over rendering from the default slot.

Both register with the App's :class:`~nuiitivet.menubar.controller.MenuBarController`
on mount; the controller decides which one is active. An inactive slot (and a
slot with no registered menu) renders nothing and takes no space.
"""

from __future__ import annotations

import logging
from typing import Optional

from nuiitivet.layout.spacer import Spacer
from nuiitivet.widgeting.widget import ComposableWidget, Widget

from .model import MenuBar

logger = logging.getLogger(__name__)


class MenuBarSlotBase(ComposableWidget):
    """Common slot behavior: registry membership and conditional rendering."""

    #: A user-placed area suppresses the App's default slot.
    is_user_area: bool = False

    def __init__(self, *, key: Optional[str] = None) -> None:
        super().__init__(key=key)
        self._active = False
        self._model: Optional[MenuBar] = None
        self._controller = None

    def build(self) -> Widget:
        if self._active and self._model is not None:
            from .bar import MenuBarWidget

            return MenuBarWidget(self._model)
        return Spacer(width=0, height=0)

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.widgeting.context_lookup import find_window

        window = find_window(self)
        controller = getattr(window, "_menubar_controller", None)
        if controller is None:
            logger.warning("MenuBar slot mounted outside a Window; it will render nothing.")
            return
        self._controller = controller
        controller.register_slot(self)

    def on_unmount(self) -> None:
        if self._controller is not None:
            self._controller.unregister_slot(self)
            self._controller = None
        super().on_unmount()

    def menubar_changed(self, *, active: bool, model: Optional[MenuBar]) -> None:
        """Called by the controller when the model or the active slot changed."""
        if active == self._active and model is self._model:
            return
        self._active = active
        self._model = model
        self.rebuild()
        self.invalidate()


class DefaultMenuBarSlot(MenuBarSlotBase):
    """The App-inserted slot at the top of the content area. Internal."""

    is_user_area = False


class MenuBarArea(MenuBarSlotBase):
    """Marks where the registered menu bar renders, instead of the default spot.

    Place it anywhere in the tree — typically inside a ``CustomChrome`` header
    row — and the App-registered menu model renders there; the App's automatic
    insertion below the chrome is suppressed. Menu definitions, callbacks and
    shortcuts are unaffected by placement.

    With no menu registered it renders nothing, so conditional menus are fine.
    If several ``MenuBarArea`` widgets are mounted at once, only the first one
    renders (a warning is logged).

    On macOS the menu goes to the global menu bar (``NSMenu``) and the area
    collapses to zero size — a chrome written around a ``MenuBarArea``
    degrades to a plain title bar with no platform branching.
    """

    is_user_area = True
