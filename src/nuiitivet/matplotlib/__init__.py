"""matplotlib in a nuiitivet app: the figure widget, its navigation controller and the figure's palette.

The package needs the extra, ``pip install nuiitivet[matplotlib]``; its names
are imported on first use so that importing the package does not import
matplotlib.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .controller import MatplotlibController
    from .figure import MatplotlibFigure
    from .theme_data import MatplotlibFigureThemeData

__all__ = ["MatplotlibController", "MatplotlibFigure", "MatplotlibFigureThemeData"]

_EXPORTS = {
    "MatplotlibController": "controller",
    "MatplotlibFigure": "figure",
    "MatplotlibFigureThemeData": "theme_data",
}


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
