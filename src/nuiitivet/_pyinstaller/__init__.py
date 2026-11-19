"""PyInstaller support: the hook directory and the module lists the hook passes.

``nuiitivet.material`` and ``nuiitivet.matplotlib`` import their exports in a
module ``__getattr__``. PyInstaller's static analysis does not see those
imports, so the hook lists the modules as hidden imports.
"""

from __future__ import annotations

import importlib.util
import os

EXCLUDED_PACKAGES: tuple[str, ...] = ("nuiitivet.dev", "nuiitivet.testing", "nuiitivet.skills")
"""Packages a frozen app never runs: the hot-reload runner, the test harness and the skill installer."""

MATPLOTLIB_WIDGET_MODULES: tuple[str, ...] = ("nuiitivet.matplotlib.figure", "nuiitivet.matplotlib.controller")
"""Modules that run only with matplotlib installed.

The rest of ``nuiitivet.matplotlib`` holds the figure's theme data, which every theme imports.
"""


def get_hook_dirs() -> list[str]:
    """Return the directory that holds the nuiitivet hook, for the ``pyinstaller40`` entry point."""
    return [os.path.dirname(__file__)]


def matplotlib_installed() -> bool:
    """Return whether matplotlib can be imported in the build environment."""
    return importlib.util.find_spec("matplotlib") is not None


def hidden_imports(*, with_matplotlib: bool) -> list[str]:
    """Return the modules that the lazy exports import, sorted.

    Args:
        with_matplotlib: Whether to include the modules in ``MATPLOTLIB_WIDGET_MODULES``.
    """
    from nuiitivet import material
    from nuiitivet import matplotlib as nv_matplotlib

    modules = {
        importlib.util.resolve_name(module if module.startswith(".") else f".{module}", material.__name__)
        for module, _ in material._EXPORTS.values()
    }
    modules.update(f"{nv_matplotlib.__name__}.{module}" for module in nv_matplotlib._EXPORTS.values())
    if not with_matplotlib:
        modules.difference_update(MATPLOTLIB_WIDGET_MODULES)
    return sorted(modules)


def excluded_imports(*, with_matplotlib: bool) -> list[str]:
    """Return the modules the bundle leaves out, even where nuiitivet imports them.

    Args:
        with_matplotlib: Whether matplotlib is installed; without it the
            modules in ``MATPLOTLIB_WIDGET_MODULES`` are left out too.
    """
    excluded = list(EXCLUDED_PACKAGES)
    if not with_matplotlib:
        excluded.extend(MATPLOTLIB_WIDGET_MODULES)
    return excluded
