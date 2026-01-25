"""Easing functions."""

from __future__ import annotations

import logging

from nuiitivet.common.logging_once import exception_once


logger = logging.getLogger(__name__)


def ease_cubic_out(t: float) -> float:
    try:
        return 1.0 - (1.0 - t) ** 3
    except Exception:
        exception_once(logger, "easing_cubic_out_exc", "ease_cubic_out failed")
        return t
