"""Lazy import helper for the optional skia-python dependency."""

from __future__ import annotations

import logging
import sys
from typing import Any, Literal, Optional, overload

from nuiitivet.common.logging_once import debug_once, exception_once


_logger = logging.getLogger(__name__)

_skia: Any = None
_skia_checked: bool = False


@overload
def get_skia(raise_if_missing: Literal[True]) -> Any: ...


@overload
def get_skia(raise_if_missing: Literal[False] = False) -> Optional[Any]: ...


def get_skia(raise_if_missing: bool = False) -> Optional[Any]:
    """Lazily import and cache the skia module.

    This centralizes the optional dependency import logic for the Skia backend.
    """

    global _skia, _skia_checked

    if _skia_checked:
        try:
            mod = sys.modules.get("skia")
            if mod is not None and mod is not _skia:
                _skia = mod
        except Exception:
            exception_once(
                _logger,
                "skia_module_sys_modules_access_exc",
                "Failed to read sys.modules['skia']",
            )

        if _skia is None and raise_if_missing:
            raise RuntimeError("skia-python is required")

        return _skia

    try:
        import skia as _mod  # type: ignore
    except Exception as e:
        _skia_checked = True
        _skia = None
        debug_once(
            _logger,
            "skia_module_import_exc",
            "Failed to import skia-python (error=%s)",
            e,
        )
        if raise_if_missing:
            raise RuntimeError("skia-python is required") from e
        return None

    _skia = _mod
    _skia_checked = True
    return _skia


def _reset_skia_import_state_for_tests() -> None:
    """Reset cached import state.

    This is intended for unit tests that swap `sys.modules["skia"]`.
    """

    global _skia, _skia_checked
    _skia = None
    _skia_checked = False


__all__ = [
    "get_skia",
]
