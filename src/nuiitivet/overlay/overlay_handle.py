"""Awaitable handle for overlay operations."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, Generic, Optional, Protocol, TypeVar

from .result import OverlayResult


T = TypeVar("T")


class _OverlayHandleHost(Protocol):
    def _close_entry(self, entry: Any, value: Any = None) -> None: ...

    def _future_for_entry(self, entry: Any) -> asyncio.Future[OverlayResult[Any]]: ...

    def _get_future_for_entry(self, entry: Any) -> asyncio.Future[OverlayResult[Any]] | None: ...

    def _get_pending_result_for_entry(self, entry: Any) -> OverlayResult[Any] | None: ...

    def _pop_pending_result_for_entry(self, entry: Any) -> OverlayResult[Any] | None: ...


class OverlayHandle(Generic[T]):
    """Handle returned by Overlay APIs.

    This is intentionally lightweight:
    - `close(value)` closes this specific entry.
    - `await handle` waits for an OverlayResult.

    Notes:
        Awaiting requires a running async runtime.
    """

    def __init__(self, *, overlay: _OverlayHandleHost, entry: Any) -> None:
        self._overlay = overlay
        self._entry = entry

    def close(self, value: T | None = None) -> None:
        self._overlay._close_entry(self._entry, value)

    def __await__(self) -> Generator[Any, None, OverlayResult[T]]:
        future: asyncio.Future[OverlayResult[T]] = self._overlay._future_for_entry(self._entry)
        return future.__await__()

    def done(self) -> bool:
        pending = self._overlay._get_pending_result_for_entry(self._entry)
        if pending is not None:
            return True
        future = self._overlay._get_future_for_entry(self._entry)
        return future is not None and future.done()

    def result(self) -> Optional[OverlayResult[T]]:
        pending = self._overlay._pop_pending_result_for_entry(self._entry)
        if pending is not None:
            return pending  # type: ignore[return-value]

        future = self._overlay._get_future_for_entry(self._entry)
        if future is None:
            raise RuntimeError("Result is not available because the handle was never awaited.")
        return future.result()
