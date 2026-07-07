"""Renderer selection for the interactive window backend."""

from __future__ import annotations

from typing import Literal, Tuple, cast, get_args

RendererMode = Literal["auto", "gpu", "cpu"]
"""Renderer selection accepted by :meth:`nuiitivet.runtime.app.App.run`.

- ``"auto"``: try the GPU first and silently fall back to software (raster)
  rendering when the GPU backend is unavailable. This is the default.
- ``"gpu"``: require the GPU. Initialization or per-frame GPU failures raise a
  :class:`RuntimeError` instead of degrading, so remote/GPU-less environments
  surface a clear error rather than running unexpectedly slowly.
- ``"cpu"``: always render in software (raster); the GPU is never touched.

Note that ``App.run`` always needs a display/window; truly headless environments
should render offscreen via :meth:`App.render_to_png` instead.
"""

VALID_RENDERER_MODES: Tuple[RendererMode, ...] = get_args(RendererMode)


def parse_renderer_mode(value: RendererMode) -> RendererMode:
    """Validate a renderer selection, raising ``ValueError`` for unknown modes."""

    if value not in VALID_RENDERER_MODES:
        raise ValueError(
            f"renderer must be one of {VALID_RENDERER_MODES!r}, got {value!r}"
        )
    return cast(RendererMode, value)


__all__ = [
    "RendererMode",
    "VALID_RENDERER_MODES",
    "parse_renderer_mode",
]
