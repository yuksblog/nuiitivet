"""What a widget says about itself to assistive technology."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Optional, Sequence, Union, cast

from nuiitivet.observable import ReadOnlyObservableProtocol
from nuiitivet.widgeting.widget import Widget

from .interaction import InteractionHostMixin, InteractionNode


class SemanticsRole(str, Enum):
    """What kind of thing a widget is, as assistive technology announces it."""

    BUTTON = "button"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    RADIO_BUTTON = "radio_button"
    RADIO_GROUP = "radio_group"
    SLIDER = "slider"
    TEXT_FIELD = "text_field"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    TEXT = "text"
    IMAGE = "image"
    GROUP = "group"


class ToggleState(Enum):
    """The state of a widget that is on, off, or neither."""

    OFF = "off"
    ON = "on"
    MIXED = "mixed"


class SemanticsAction(Enum):
    """What assistive technology can ask a widget to do."""

    FOCUS = "focus"
    ACTIVATE = "activate"
    INCREMENT = "increment"
    DECREMENT = "decrement"


# A role outside this set stands for one control: the text beneath it is its
# label, not content of its own.
CONTAINER_ROLES = frozenset({SemanticsRole.GROUP, SemanticsRole.MENU, SemanticsRole.RADIO_GROUP})

#: A label for the widget, or one label per part for a widget that has parts.
SemanticsLabel = Union[str, ReadOnlyObservableProtocol[str], Sequence[str]]


@dataclass(frozen=True, slots=True)
class Semantics:
    """What one entry of the semantics tree says.

    Attributes:
        role: What kind of thing the entry is.
        label: The name read for it. ``None`` leaves a control to take the
            text beneath it.
        value: The text it holds, a text field's content.
        toggled: Whether it is on, off or mixed. ``None`` when it is no toggle.
        selected: Whether it is the chosen one of a set. ``None`` when it
            belongs to no set.
        disabled: Whether it refuses input.
        numeric_value: The number it holds, a slider's position.
        min_value: The lowest ``numeric_value``.
        max_value: The highest ``numeric_value``.
    """

    role: SemanticsRole
    label: Optional[str] = None
    value: Optional[str] = None
    toggled: Optional[ToggleState] = None
    selected: Optional[bool] = None
    disabled: bool = False
    numeric_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


_ids = itertools.count(1)


class SemanticsNode(InteractionNode):
    """Answers the semantics tree for the widget that carries it.

    ``label`` and ``role`` are written by the ``semantics()`` modifier and win
    over what the widget says.
    """

    def __init__(
        self,
        describe: Optional[Callable[[], Optional[Semantics]]] = None,
        *,
        parts: Optional[Callable[[], Sequence[Semantics]]] = None,
        on_activate: Optional[Callable[[], None]] = None,
        on_adjust: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Initialize the node.

        Args:
            describe: Returns what the widget says now, or ``None`` to say
                nothing.
            parts: Returns the parts the widget keeps for itself, in the order
                of its focus scope's stops. Each is an entry beneath the
                widget's own.
            on_activate: Runs when assistive technology presses the widget.
            on_adjust: Runs as ``on_adjust(part, direction)`` when assistive
                technology raises (``+1``) or lowers (``-1``) the widget;
                ``part`` is the index into ``parts``, or ``-1`` for the widget.
        """
        super().__init__()
        self.id = next(_ids)
        self.label: Optional[SemanticsLabel] = None
        self.role: Optional[SemanticsRole] = None
        self._describe = describe
        self._parts = parts
        self._on_activate = on_activate
        self._on_adjust = on_adjust
        self._part_ids: list[int] = []

    def _own_label(self) -> Optional[str]:
        """The label written for the widget itself; ``None`` for none, or for the parts'."""
        label = self.label
        if label is None or isinstance(label, (list, tuple)):
            return None
        if isinstance(label, str):
            return label
        return str(cast(ReadOnlyObservableProtocol[str], label).value)

    def describe(self) -> Optional[Semantics]:
        """Return what the widget says now, or ``None`` when it says nothing."""
        said = self._describe() if self._describe is not None else None
        label = self._own_label()
        if said is None:
            if label is None and self.role is None:
                return None
            said = Semantics(role=SemanticsRole.GROUP)
        if label is not None:
            said = replace(said, label=label)
        if self.role is not None:
            said = replace(said, role=self.role)
        return said

    def parts(self) -> Sequence[Semantics]:
        """Return what each part the widget keeps for itself says now.

        A list written to ``label`` names the parts in order; a part past the
        list's end keeps the widget's name for it.
        """
        if self._parts is None:
            return ()
        parts = list(self._parts() or ())
        labels = self.label if isinstance(self.label, (list, tuple)) else ()
        for index, name in enumerate(labels[: len(parts)]):
            parts[index] = replace(parts[index], label=str(name))
        return parts

    def part_id(self, index: int) -> int:
        """Return the id of the part at ``index``, the same one on every call."""
        while len(self._part_ids) <= index:
            self._part_ids.append(next(_ids))
        return self._part_ids[index]

    @property
    def supports_activate(self) -> bool:
        """Whether a press from assistive technology does anything."""
        return self._on_activate is not None

    @property
    def supports_adjust(self) -> bool:
        """Whether assistive technology can raise and lower the widget."""
        return self._on_adjust is not None

    def activate(self) -> None:
        """Press the widget."""
        if self._on_activate is not None:
            self._on_activate()

    def adjust(self, part: int, direction: int) -> None:
        """Raise or lower the widget, or one of its parts.

        Args:
            part: The index into ``parts``, or ``-1`` for the widget.
            direction: ``+1`` to raise, ``-1`` to lower.
        """
        if self._on_adjust is not None:
            self._on_adjust(part, direction)


def attach_semantics(widget: Widget, node: SemanticsNode) -> None:
    """Make ``node`` the one ``widget`` answers the semantics tree with."""
    if isinstance(widget, InteractionHostMixin):
        widget.add_node(node)
    else:
        node.attach(widget)
    widget._semantics_node = node


__all__ = [
    "CONTAINER_ROLES",
    "Semantics",
    "SemanticsAction",
    "SemanticsLabel",
    "SemanticsNode",
    "SemanticsRole",
    "ToggleState",
    "attach_semantics",
]
