from __future__ import annotations

from typing import Optional, Union, cast

from nuiitivet.widgets.clickable import Clickable
from nuiitivet.observable import Observable, ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.callbacks import invoke_event_handler, OptionalBoolCallback


class Toggleable(Clickable):
    """
    A base class for toggleable widgets (Checkbox, Switch, Radio).
    Handles value state (checked/unchecked/indeterminate) and toggling logic.
    """

    # Internal descriptor-backed observable for simple usage
    _state_internal = Observable(False)

    def __init__(
        self,
        value: Union[bool, None, ObservableProtocol[Optional[bool]]] = False,
        on_change: Optional[OptionalBoolCallback] = None,
        tristate: bool = False,
        disabled: bool | ObservableProtocol[bool] = False,
        # Clickable args
        width: SizingLike = None,
        height: SizingLike = None,
        **kwargs,
    ):
        super().__init__(
            on_click=self._handle_click,
            disabled=disabled,
            width=width,
            height=height,
            **kwargs,
        )

        self.tristate = tristate
        self.on_change = on_change
        self._state_external: ObservableProtocol[Optional[bool]] | None = None

        if hasattr(value, "subscribe") and hasattr(value, "value"):
            self._state_external = cast("ObservableProtocol[Optional[bool]]", value)
        else:
            # Initialize internal observable
            # We allow None (indeterminate) even if tristate is False (e.g. initial state)
            if value is None:
                setattr(self, "_state_internal", None)
            else:
                setattr(self, "_state_internal", bool(value))

        # Initial sync. The subscription that keeps it in sync is taken on mount,
        # not here, but the interaction state has to be right before then: a
        # widget can be measured offscreen without ever being mounted.
        self._on_value_change(self.value)

    def on_mount(self) -> None:
        """Track the value source for as long as this widget is in the tree.

        Bound rather than subscribed bare, and taken here rather than in
        ``__init__``, because the source may be an ``Observable`` the *app* owns
        and outlives this widget by far. A bare ``subscribe`` in the constructor
        left it holding ``self._on_value_change`` forever, so every unmounted
        checkbox stayed alive and kept writing to its interaction state.
        ``bind`` disposes at unmount; taking it on mount is what makes the widget
        work again if it is re-mounted.
        """
        super().on_mount()
        self.bind(self._get_state_obj().subscribe(self._on_value_change))
        # The value may have moved while this widget was out of the tree.
        self._on_value_change(self.value)

    def _get_state_obj(self) -> ObservableProtocol[Optional[bool]]:
        if self._state_external is not None:
            return self._state_external
        return self._state_internal  # type: ignore

    @property
    def value(self) -> Optional[bool]:
        return self._get_state_obj().value

    @value.setter
    def value(self, new_val: Optional[bool]):
        obj = self._get_state_obj()
        if hasattr(obj, "value"):
            setattr(obj, "value", new_val)

    def _handle_click(self):
        if self.disabled:
            return

        current = self.value
        new_val: Optional[bool] = False

        if self.tristate:
            if current is False:
                new_val = True
            elif current is True:
                new_val = None
            else:  # None
                new_val = False
        else:
            new_val = not current

        self.value = new_val

        if self.on_change:
            invoke_event_handler(
                self.on_change,
                new_val,
                error_key="toggleable_on_change",
                error_msg="Toggleable on_change raised",
                owner_name=type(self).__name__,
            )

    def _on_value_change(self, new_val: Optional[bool]):
        # Update InteractionState
        # We map None (indeterminate) to checked=True for visual state usually,
        # but let's just set checked=bool(new_val) for now.
        # The visual representation (indeterminate) should be handled by the widget
        # checking self.value directly if needed, or we add 'indeterminate' to InteractionState?
        # InteractionState has 'checked'.
        # If new_val is None, bool(None) is False.
        # But indeterminate usually shows as a dash (checked-like).
        # Let's leave it as bool(new_val) and let the widget check self.value for indeterminate rendering.
        self.state.checked = bool(new_val)
        self.invalidate()
