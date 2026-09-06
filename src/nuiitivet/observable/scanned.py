"""``scan``: an observable whose value is folded over everything its source emits.

``map`` recomputes from the source's current value, so it cannot express a count,
a total, or anything else that depends on what came before. The imperative
alternative -- ``self.count.value += 1`` -- needs a handler to hold the line, and
an operator's output has none. ``scan`` is that missing place to write it: the
accumulator is this observable's own value.

Everything else follows from the wrapper contract in
:mod:`~nuiitivet.observable.wrapper` rather than being decided again here:
``.value`` is the last value this observable emitted, the source is held weakly,
and ``dispose`` releases it.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from nuiitivet.common.logging_once import exception_once_per_exc

from .protocols import ReadOnlyObservableProtocol
from .wrapper import SourceSubscribingObservable, _untracked

TIn = TypeVar("TIn")
TAcc = TypeVar("TAcc")


logger = logging.getLogger(__name__)


class ScannedObservable(SourceSubscribingObservable[TIn, TAcc]):
    """Observable of ``fn(accumulator, value)`` folded over the source's emissions.

    ``value`` is ``initial`` until the source emits, and the accumulator from
    then on::

        executed = clicks.debounce(0.5).scan(lambda n, _: n + 1, initial=0)

    ``initial`` is required and keyword-only. The value standing at construction
    is not folded in -- what is accumulated is emissions, and that one has not
    been emitted -- so ``initial`` means strictly "the source has emitted
    nothing". Nor does the accumulator ever re-seed: a rebuilt chain is a new
    observable, which starts from ``initial`` again.

    Lifetime follows the contract in
    :mod:`~nuiitivet.observable.wrapper`: hold this object, or the ``Disposable``
    from :meth:`subscribe`, for as long as the emissions are wanted.

    ``fn`` is a pure function of the two values handed to it. It runs with
    dependency tracking suppressed, so reading another observable inside it
    creates no edge and will not re-run the fold -- express that dependency with
    ``combine`` instead.

    An ``fn`` that raises is a bug, and is treated as one: logged, and the
    accumulator is left as it was, so nothing is emitted. It is guarded here
    rather than by the source's notify loop because this function runs on the
    graph's own edge to that source, where an escaping exception would surface on
    whichever thread happened to write it.
    """

    def __init__(
        self,
        source: ReadOnlyObservableProtocol[TIn],
        fn: Callable[[TAcc, TIn], TAcc],
        *,
        initial: TAcc,
    ):
        self._fn = fn
        self._initial = initial
        super().__init__(source)

    def _seed(self, source: ReadOnlyObservableProtocol[TIn]) -> TAcc:
        # The source is deliberately not read: folding the value it happens to
        # hold at construction would count an emission that never happened.
        return self._initial

    def _on_source_changed(self, value: TIn) -> None:
        try:
            accumulated = _untracked(lambda: self._fn(self._held_value, value))
        except Exception:
            exception_once_per_exc(
                logger,
                "scan_fn_raised",
                "scan function raised; the accumulator was left unchanged",
            )
            return
        # No equality check of our own: the source already de-dupes before it
        # notifies, and an accumulator that folds to the same value twice is a
        # legitimate emission -- the fold ran.
        self._emit_to_subscribers(accumulated)
