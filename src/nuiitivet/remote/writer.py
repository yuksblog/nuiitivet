"""The write-only side of an Observable that a server function is handed."""

from __future__ import annotations

import threading
from typing import Any, Protocol, TypeVar

from nuiitivet.observable import runtime
from nuiitivet.observable._sentinel import UNSET, _Unset
from nuiitivet.observable.protocols import MutableObservableBase

from .codec import Codec, Json

T_contra = TypeVar("T_contra", contravariant=True)


class WriteOnlyObservable(Protocol[T_contra]):
    """What a server function receives for an Observable its caller passed.

    Annotate the parameter with it; the caller passes a plain ``Observable``::

        @nv.server
        def import_file(path: str, progress: nv.WriteOnlyObservable[float]) -> int:
            ...
            progress.value = 0.5

    Only assignment works. Reading ``value`` raises, and there is nothing to
    subscribe to: the function runs where the caller's Observable is not.
    The caller's Observable takes the newest value written, on the UI thread;
    values written in between may be skipped. A write after the call has
    ended or was cancelled is dropped.
    """

    @property
    def value(self) -> object: ...

    @value.setter
    def value(self, v: T_contra) -> None: ...


class CallWriter:
    """Carries one call's writes, in their wire form, to the caller's Observable."""

    __slots__ = ("_target", "_codec", "_lock", "_pending", "_scheduled", "_closed")

    def __init__(self, target: MutableObservableBase[Any], codec: Codec) -> None:
        """Initialize CallWriter.

        Args:
            target: The Observable the caller passed.
            codec: The codec of the declared value type.
        """
        self._target = target
        self._codec = codec
        self._lock = threading.Lock()
        self._pending: Any | _Unset = UNSET
        self._scheduled = False
        self._closed = False

    def receive(self, data: Json) -> None:
        """Take one write. Any thread; the Observable is written on the UI thread.

        Args:
            data: The value, encoded.
        """
        value = self._codec.decode(data)
        with self._lock:
            if self._closed:
                return
            self._pending = value
            if self._scheduled:
                return
            self._scheduled = True
        runtime.clock.schedule_once(self._flush, 0)

    def _take(self) -> Any | _Unset:
        with self._lock:
            pending, self._pending = self._pending, UNSET
            self._scheduled = False
            return pending

    def _flush(self, dt: float) -> None:
        pending = self._take()
        if not isinstance(pending, _Unset):
            self._target.value = pending

    def close(self, *, deliver: bool) -> None:
        """End the call's access to the Observable. Runs on the UI thread.

        Args:
            deliver: Whether a value still waiting for the UI thread is
                written first. ``False`` drops it.
        """
        with self._lock:
            self._closed = True
            scheduled = self._scheduled
        if scheduled:
            runtime.clock.unschedule(self._flush)
        pending = self._take()
        if deliver and not isinstance(pending, _Unset):
            self._target.value = pending


__all__ = ["CallWriter", "WriteOnlyObservable"]
