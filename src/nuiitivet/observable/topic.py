from __future__ import annotations

import logging
import threading
import weakref
from collections import deque
from types import MethodType
from typing import Callable, Deque, Generic, List, Optional, TypeVar

from nuiitivet.runtime.threading import is_ui_thread

from ._notify import notify_all
from .protocols import Disposable
from . import runtime

T = TypeVar("T")

_Resolver = Callable[[], Optional[Callable[[T], None]]]


logger = logging.getLogger(__name__)


def _weak(cb: Callable[[T], None]) -> _Resolver[T]:
    """Return a callable that yields ``cb`` while it lives, ``None`` after."""
    try:
        if isinstance(cb, MethodType):
            return weakref.WeakMethod(cb)
        return weakref.ref(cb)
    except TypeError:
        # A built-in method or a slotted object takes no weak reference.
        return lambda: cb


class _Subscriber(Generic[T]):
    __slots__ = ("ref", "dispatch")

    def __init__(self, ref: _Resolver[T], dispatch: bool) -> None:
        self.ref = ref
        self.dispatch = dispatch


class Topic(Generic[T]):
    """An event source: ``publish(value)`` hands the value to every subscriber.

    A Topic holds no value. It delivers every publish: an equal value is
    delivered again, and so is each of several published from a worker thread
    before the UI thread runs. It keeps no subscriber alive.

    As a class attribute, a Topic is per instance.
    """

    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._lock = threading.Lock()
        self._subscribers: List[_Subscriber[T]] = []
        self._queue: Deque[T] = deque()
        self._is_scheduled = False
        self._is_draining = False

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: object, owner: Optional[type] = None) -> "Topic[T]":
        if instance is None or self._name is None:
            return self
        # Stored under the attribute's own name: the instance dict then
        # shadows this descriptor, so later reads never come back here.
        topic: Topic[T] = instance.__dict__.setdefault(self._name, Topic())
        return topic

    def publish(self, value: T) -> None:
        """Deliver ``value`` to every subscriber.

        On the UI thread the subscribers have run when this returns. From
        another thread the value is queued and they run on the UI thread.
        Subscribers receive values in the order ``publish`` accepted them.

        A publish made by a subscriber of this Topic is delivered after the
        value in hand has reached every subscriber on the UI thread.

        A subscriber that passed ``dispatch=False`` runs on the calling
        thread, before this returns, whatever is still queued.

        A subscriber that raises is logged, and the others still run.

        Args:
            value: The event.
        """
        on_ui_thread = is_ui_thread()
        with self._lock:
            inline = self._live(dispatch=False)
            # Nothing is queued for nobody: a Topic only a worker listens to
            # must not grow a queue the UI thread drains for no one.
            queued = any(s.dispatch for s in self._subscribers)
            if queued:
                self._queue.append(value)
                if not on_ui_thread and not self._is_scheduled:
                    self._is_scheduled = True
                    runtime.clock.schedule_once(self._drain_on_tick, 0)
        if inline:
            notify_all(inline, lambda: value, logger=logger, key="topic")
        if queued and on_ui_thread:
            self._drain()

    def subscribe(self, cb: Callable[[T], None], *, dispatch: bool = True) -> Disposable:
        """Call ``cb`` with every value delivered from now on.

        The Topic does not keep ``cb`` alive. A bound method is called while
        its object lives. Any other callable is called while something
        references it, and the returned ``Disposable`` does. A callable that
        takes no weak reference, such as a built-in method, is held until
        disposed.

        Args:
            cb: Receives each published value.
            dispatch: Whether ``cb`` runs on the UI thread. ``False`` runs it
                on the publishing thread; such a ``cb`` must touch no widget.

        Returns:
            A ``Disposable`` that ends the subscription.
        """
        ref = _weak(cb)
        # What the Disposable holds: a bound method's weak reference, so that
        # holding the Disposable never pins the object, or the callable itself.
        callback: object = ref if isinstance(ref, weakref.WeakMethod) else cb
        with self._lock:
            self._subscribers.append(_Subscriber(ref, dispatch))

        def _dispose() -> None:
            self._unsubscribe(callback)

        return Disposable(_dispose)

    def _unsubscribe(self, callback: object) -> None:
        with self._lock:
            for subscriber in self._subscribers:
                if subscriber.ref is callback or subscriber.ref() is callback:
                    self._subscribers.remove(subscriber)
                    return

    def _live(self, *, dispatch: bool) -> List[Callable[[T], None]]:
        """The living subscribers of one kind. Caller holds the lock."""
        live: List[Callable[[T], None]] = []
        collected = False
        for subscriber in self._subscribers:
            cb = subscriber.ref()
            if cb is None:
                collected = True
            elif subscriber.dispatch is dispatch:
                live.append(cb)
        if collected:
            self._subscribers = [s for s in self._subscribers if s.ref() is not None]
        return live

    def _drain_on_tick(self, dt: float) -> None:
        with self._lock:
            self._is_scheduled = False
        self._drain()

    def _drain(self) -> None:
        """Deliver the queue in order, including what subscribers publish meanwhile."""
        with self._lock:
            if self._is_draining:
                return
            self._is_draining = True
        try:
            while True:
                with self._lock:
                    if not self._queue:
                        # Cleared with the queue seen empty, under one lock: a
                        # publish after this starts its own drain.
                        self._is_draining = False
                        return
                    value = self._queue.popleft()
                    live = self._live(dispatch=True)
                notify_all(live, lambda: value, logger=logger, key="topic")
        except BaseException:
            with self._lock:
                self._is_draining = False
            raise
