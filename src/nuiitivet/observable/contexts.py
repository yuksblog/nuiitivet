from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Optional

_batch_context: ContextVar[Optional[Any]] = ContextVar("batch", default=None)
_tracking_context: ContextVar[Optional[Any]] = ContextVar("tracking", default=None)
