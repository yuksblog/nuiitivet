"""``switch_map``: :meth:`map` for a function that takes time to answer.

``map`` declares "the value here is ``fn`` of the source". ``switch_map``
declares the same thing for an ``fn`` that cannot answer immediately, and adds
the one rule that difference forces: if the source changes again before an
answer arrives, that answer is **discarded** rather than raced against the newer
one. Everything the operator can and cannot express follows from being ``map``:

- a run starts only because the source's value changed,
- a run is discarded only because the source's value changed again,
- a run produces exactly one value.

Work that does not fit those three -- started by a button rather than a value,
reporting progress as it goes, stopped by an explicit Cancel -- is not a
mapping, and stays a hand-written worker (see
``samples/state-management/background_work.py``). Note that "how many pieces of
data come back" is not one of the three: a run that answers with items *and* a
total *and* a facet list still answers once, and returns them as one value.

**Failure is a value, not a channel.** ``fn`` runs where no caller is on the
stack, so an exception has nowhere to go. Rather than grow a second read
surface on the returned observable -- which would not survive ``.map()``, and
would need its own supersede and clearing rules -- ``fn`` is expected to catch
what it can handle and *return* it, in whatever type the app already uses for
the result::

    def search(query: str, cancel: CancelToken) -> SearchOutcome:
        try:
            return SearchOutcome(items=search_api(query))
        except RequestError as exc:
            return SearchOutcome(error=str(exc))

An exception that escapes ``fn`` is therefore a bug, and is treated as one:
logged through ``exception_once`` and delivered to nobody, exactly as a raising
``map`` function is.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Sequence, TypeVar

from nuiitivet.common.logging_once import exception_once

from ._sentinel import UNSET, _Unset
from .protocols import ReadOnlyObservableProtocol
from .wrapper import SourceSubscribingObservable
from . import runtime

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


logger = logging.getLogger(__name__)


class CancelToken:
    """Tells a run whether its result is still wanted.

    One token per run, created and set by the operator; the run only reads it.
    That is the whole difference from the hand-rolled ``threading.Event`` this
    replaces: there is no ``clear()`` to misuse and no way to mistake another
    run's flag for your own.

    Checking is **optional and cooperative** -- a superseded run's result is
    discarded whether or not it ever looks. Python cannot interrupt a thread
    from outside, so this only helps work with a seam to check at::

        def load(query: str, cancel: CancelToken) -> list[Row]:
            rows: list[Row] = []
            for page in range(PAGE_COUNT):
                if cancel.superseded:
                    return []          # stop paying for an answer nobody wants
                rows += fetch(query, page)
            return rows

    A single blocking call has no such seam, and gains nothing from the token.
    """

    __slots__ = ("_flag",)

    def __init__(self) -> None:
        # An Event rather than a bool: set on the UI thread, read on the worker.
        self._flag = threading.Event()

    @property
    def superseded(self) -> bool:
        """Whether a newer run has started, making this run's result unwanted."""
        return self._flag.is_set()

    def _supersede(self) -> None:
        self._flag.set()


class SwitchMappedObservable(SourceSubscribingObservable[TIn, TOut]):
    """Observable of the newest run's result, superseding runs still in flight.

    ``value`` is ``initial`` until the first run lands, then the most recent
    landed result::

        results = query.debounce(0.3).switch_map(search, initial=SearchOutcome())

    ``initial`` is required and keyword-only for the same reason as
    ``filter``'s: this observable has no value derivable from its
    source, so the caller states what the UI shows meanwhile. Unlike ``filter``,
    **no run starts at construction** -- building a ViewModel should not fire
    I/O, and the source's construction-time value is usually the empty one -- so
    ``initial`` here means "no run has landed yet".

    ``fn`` never runs on the UI thread. It may read observables, but must not
    touch widgets or anything else the UI thread owns, the same constraint §2
    already places on compute functions. Results are marshalled back before they
    are published, so subscribers and bindings still run on the UI thread.

    Lifetime follows the contract in :mod:`~nuiitivet.observable.wrapper`: hold
    this object, or the ``Disposable`` from :meth:`subscribe`, for as long as the
    results are wanted. :meth:`dispose` supersedes whatever is in flight.
    """

    def __init__(
        self,
        source: ReadOnlyObservableProtocol[TIn],
        fn: Callable[[TIn, CancelToken], TOut],
        *,
        initial: TOut,
    ):
        self._fn = fn
        self._initial = initial
        self._lock = threading.Lock()
        self._current_token: Optional[CancelToken] = None
        self._pending_result: TOut | _Unset = UNSET
        super().__init__(source)

    def _seed(self, source: ReadOnlyObservableProtocol[TIn]) -> TOut:
        # The source is deliberately not read: its value has no bearing on what
        # a run would return, and no run has been started to find out.
        return self._initial

    def _clock_callbacks(self) -> Sequence[Callable[[float], None]]:
        return (self._flush,)

    # -- running -----------------------------------------------------------

    def _on_source_changed(self, value: TIn) -> None:
        token = CancelToken()
        with self._lock:
            if self._disposed:
                return
            if self._current_token is not None:
                self._current_token._supersede()
            self._current_token = token
            # Anything staged by the run just superseded is now unwanted, and
            # dropping it here means a flush already scheduled finds nothing.
            self._pending_result = UNSET

        thread = threading.Thread(
            target=self._run,
            args=(value, token),
            name=f"switch_map:{self._fn_name()}",
            daemon=True,
        )
        thread.start()

    def _fn_name(self) -> str:
        return getattr(self._fn, "__qualname__", None) or type(self._fn).__name__

    def _run(self, value: TIn, token: CancelToken) -> None:
        """The body of one run, on its own thread."""
        try:
            result = self._fn(value, token)
        except Exception:
            # A failure the UI should render is a value ``fn`` returns, so
            # reaching here means ``fn`` itself is broken: a bug to log, not a
            # result to publish. Keyed by the function so two different
            # switch_maps cannot de-duplicate each other's bug into silence.
            exception_once(
                logger,
                f"switch_map_fn_raised:{self._fn_name()}",
                f"switch_map function {self._fn_name()!r} raised; no value was published",
            )
            return
        self._deliver(result, token)

    def _deliver(self, result: TOut, token: CancelToken) -> None:
        """Stage ``result`` for publication, if this run is still the current one.

        The staging is what makes a superseded result unable to land from any
        path -- including ``fn``'s own ``except`` and ``finally`` -- because the
        test is on identity with the live token rather than on a flag the run
        might have read a moment too early.
        """
        with self._lock:
            if self._disposed or token is not self._current_token:
                return
            self._pending_result = result

        # Always through the clock, never straight to subscribers: ``_run`` is
        # on a worker by construction, so this is the same marshalling every
        # other off-thread write goes through (§4.4), and the same one-tick delay.
        runtime.clock.schedule_once(self._flush, 0)

    def _flush(self, dt: float) -> None:
        """Publish the staged result on the UI thread."""
        with self._lock:
            pending = self._pending_result
            if pending is UNSET or self._disposed:
                return
            self._pending_result = UNSET

        # Outside the lock: subscribers run arbitrary app code, and a binding
        # that reads back through this observable would deadlock on a re-entrant
        # acquire.
        self._emit_to_subscribers(pending)

    # -- lifetime ----------------------------------------------------------

    def dispose(self) -> None:
        if self._disposed:
            return
        # Base first: it sets ``_disposed`` and drops the source subscription,
        # so no further run can start while this is finishing.
        super().dispose()
        with self._lock:
            token = self._current_token
            self._current_token = None
            self._pending_result = UNSET
        if token is not None:
            token._supersede()
