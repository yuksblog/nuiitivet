from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union, cast

from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionHostMixin, InteractionState, FocusNode
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.observable import ObservableProtocol
from nuiitivet.theme.types import ColorSpec
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import Widget


logger = logging.getLogger(__name__)


class Clickable(InteractionHostMixin, Box):
    """
    A basic interactive widget that handles clicks, hovers, and focus.
    It does not enforce any specific visual style beyond what Box provides.
    """

    def __init__(
        self,
        child: Optional[Widget] = None,
        on_click: Optional[Callable[[], None]] = None,
        on_hover: Optional[Callable[[bool], None]] = None,
        on_press: Optional[Callable[[PointerEvent], None]] = None,
        on_release: Optional[Callable[[PointerEvent], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        focusable: bool = True,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        background_color: ColorSpec = None,
        border_color: ColorSpec = None,
        border_width: float = 0.0,
        corner_radius: Union[float, Tuple[float, float, float, float]] = 0.0,
        **kwargs,
    ):
        self._disabled_external: ObservableProtocol[bool] | None = None
        if hasattr(disabled, "subscribe") and hasattr(disabled, "value"):
            self._disabled_external = cast("ObservableProtocol[bool]", disabled)
            initial_disabled = bool(self._disabled_external.value)
        else:
            initial_disabled = bool(disabled)

        # Used by App focus traversal (see App._collect_focus_nodes).
        self._disabled = bool(initial_disabled)

        self._state = InteractionState(disabled=bool(initial_disabled))
        self._disabled_unsub = None

        super().__init__(
            child=child,
            width=width,
            height=height,
            padding=padding,
            background_color=background_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            **kwargs,
        )

        if on_click or on_press or on_release:
            self.enable_click(on_click=on_click, on_press=on_press, on_release=on_release)

        if on_hover:
            self.enable_hover(on_change=on_hover)
        else:
            self.enable_hover()

        if not initial_disabled and focusable:
            self.add_node(FocusNode())

    def _apply_disabled(self, value: bool) -> None:
        next_disabled = bool(value)

        self._disabled = next_disabled
        self.state.disabled = next_disabled

        if next_disabled:
            # Ensure visual state doesn't get stuck.
            self.state.hovered = False
            self.state.pressed = False
            self.state.pointer_position = None
            self.state.press_position = None

            # Best-effort blur.
            self.state.focused = False
            node = self.get_node(FocusNode)
            if node is not None and isinstance(node, FocusNode):
                try:
                    node._set_focused(False)
                except Exception:
                    # Avoid hard failure on private API mismatch.
                    pass

        else:
            # Lazily add focus support when re-enabled.
            if self.get_node(FocusNode) is None:
                self.add_node(FocusNode())

        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()

        obs = self._disabled_external
        if obs is None:
            return

        subscribe = getattr(obs, "subscribe", None)
        if not callable(subscribe):
            return

        if self._disabled_unsub is not None:
            return

        def _cb(new_value: bool) -> None:
            self._apply_disabled(bool(new_value))

        try:
            unsub = subscribe(_cb)
            if hasattr(unsub, "dispose"):
                self._disabled_unsub = unsub
        except Exception:
            logger.exception("Clickable disabled.subscribe failed")

        # Sync to current value after subscribing.
        try:
            self._apply_disabled(bool(obs.value))
        except Exception:
            logger.exception("Clickable failed to sync disabled value")

    def on_unmount(self) -> None:
        unsub = self._disabled_unsub
        if unsub is not None:
            try:
                unsub.dispose()
            except Exception:
                logger.exception("Clickable disabled unsubscribe dispose failed")
            self._disabled_unsub = None

        super().on_unmount()

    @property
    def disabled(self) -> bool:
        return self.state.disabled

    @disabled.setter
    def disabled(self, value: bool):
        self._apply_disabled(bool(value))
