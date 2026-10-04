"""Form factor: the component sizes a Material theme is built for."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Optional, Union

FormFactorName = Literal["desktop", "mobile"]
"""A built-in form factor, by name."""

# MD3 minimum touch target, in dp.
TOUCH_TARGET = 48

# One density step, in dp.
DENSITY_STEP = 4

_DENSITY_FIELDS = ("text_field", "search_bar", "menu")


def check_density(density: Optional[int], owner: str) -> None:
    """Raise when ``density`` is above 0.

    Args:
        density: The step to check. ``None`` passes.
        owner: The name the error message gives the value.

    Raises:
        ValueError: If ``density`` is positive.
    """
    if density is not None and density > 0:
        raise ValueError(f"{owner} must be 0 or below, got {density}")


def density_shrink(style_density: Optional[int], theme_density: int, floor: int) -> int:
    """Return the dp a component's height loses to density.

    Args:
        style_density: The style's own step. ``None`` follows ``theme_density``.
        theme_density: The form factor's step for the component.
        floor: The lowest step the component supports.

    Returns:
        A non-negative number of dp.
    """
    step = theme_density if style_density is None else style_density
    return -max(step, floor) * DENSITY_STEP


@dataclass(frozen=True)
class FormFactor:
    """The component sizes of one kind of device.

    Colors, shapes, motion and font sizes do not depend on it. A density step
    takes 4dp off a component's height. A step below the component's lowest
    stops there. A style's own ``density`` wins over the step set here.

    Button, IconButton, ToggleButton, ButtonGroup, SplitButton and Fab take
    their height from their size (``"xs"`` to ``"xl"``) only. Dialog, Snackbar,
    the date picker surface, Tooltip, Sheet, NavigationRail and Toolbar do not
    change with the form factor.

    Built-in form factors: :meth:`desktop`, :meth:`mobile`.

    Attributes:
        touch_targets: Whether a control smaller than 48dp reserves a 48dp
            touch target. Applies to Button, IconButton, ToggleButton, Chip,
            Checkbox, RadioButton, Switch and the SearchBar icons.
        text_field: Density step of TextField. The lowest is -5. A filled
            field below 52dp shows its label only while empty.
        search_bar: Density step of SearchBar. The lowest is -4.
        menu: Density step of a menu item. The lowest is -3.
    """

    touch_targets: bool = True
    text_field: int = 0
    search_bar: int = 0
    menu: int = 0

    def __post_init__(self) -> None:
        for name in _DENSITY_FIELDS:
            check_density(getattr(self, name), f"FormFactor.{name}")

    def copy_with(self, **changes: Any) -> "FormFactor":
        """Create a new form factor with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def desktop(cls) -> "FormFactor":
        """Sizes for a pointer: the controls of one row are 40dp tall."""
        return _DESKTOP

    @classmethod
    def mobile(cls) -> "FormFactor":
        """The MD3 baseline sizes, built for touch."""
        return _MOBILE

    @classmethod
    def of(cls, value: "FormFactorLike") -> "FormFactor":
        """Return ``value`` as a :class:`FormFactor`.

        Args:
            value: A form factor or the name of a built-in one.

        Raises:
            ValueError: If ``value`` names no built-in form factor.
        """
        if isinstance(value, FormFactor):
            return value
        if value == "desktop":
            return _DESKTOP
        if value == "mobile":
            return _MOBILE
        raise ValueError(f"Unknown form factor {value!r}; expected 'desktop', 'mobile' or a FormFactor")


FormFactorLike = Union[FormFactor, FormFactorName]
"""A :class:`FormFactor` or the name of a built-in one."""

_DESKTOP = FormFactor(touch_targets=False, text_field=-4, search_bar=-4, menu=-3)
_MOBILE = FormFactor()

DEFAULT_FORM_FACTOR: FormFactorName = "desktop"


def default_form_factor() -> FormFactor:
    """Return the form factor of a theme that names none."""
    return FormFactor.of(DEFAULT_FORM_FACTOR)


def form_factor_of(context: Any) -> FormFactor:
    """Return the form factor of the theme above ``context``.

    Registers a theme dependency, as :meth:`Theme.of` does.

    Args:
        context: A widget in the subtree to search upward from.

    Returns:
        The Material theme's form factor, or the default one when no Material
        theme is reachable.
    """
    from nuiitivet.material.theme.theme_data import MaterialThemeData
    from nuiitivet.theme.theme import Theme

    data = Theme.of(context).extension(MaterialThemeData)
    if data is None:
        return default_form_factor()
    return data.form_factor


def min_extent(explicit: Optional[int], container: float, context: Any) -> int:
    """Return the minimum extent of a control along one axis.

    Args:
        explicit: The style's own minimum. ``None`` follows the form factor.
        container: The control's container extent along the axis.
        context: The widget the minimum is for.

    Returns:
        ``explicit`` when given. Otherwise ``container``, raised to the 48dp
        touch target when the form factor reserves one.
    """
    if explicit is not None:
        return int(explicit)
    if form_factor_of(context).touch_targets:
        return max(int(container), TOUCH_TARGET)
    return int(container)
