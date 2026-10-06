"""Which modules hold server code, as the app declares them."""

from __future__ import annotations

import sys

from nuiitivet.common.target import is_web

_server_only: set[str] = set()


def server_only() -> None:
    """Declare that the calling module never leaves the server.

    Call it at the top of a module. In a package's ``__init__.py`` it covers
    every module and file of the package. The web build leaves what is
    declared out of the page, so database addresses, keys and the code that
    uses them belong here. A ``@server`` function must live in such a module.

    Raises:
        RuntimeError: If the module is loaded in a browser.
    """
    name = sys._getframe(1).f_globals["__name__"]
    if is_web():
        raise RuntimeError(f"{name} is server-only and was loaded in the browser")
    _server_only.add(name)


def is_server_only(module: str) -> bool:
    """Whether *module*, or a package above it, called :func:`server_only`.

    Args:
        module: A dotted module name.
    """
    parts = module.split(".")
    return any(".".join(parts[:end]) in _server_only for end in range(1, len(parts) + 1))


__all__ = ["is_server_only", "server_only"]
