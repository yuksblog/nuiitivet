"""``filter``: an observable that updates only on source values passing a test.

``map`` answers "what is ``.value`` right now?" with a pure function of the
source, so it is always defined. ``filter`` cannot: its source may produce
nothing the predicate accepts, ever. That gap is why the operator was originally
rejected (``OBSERVABLE.md`` §3.1), and the seed is what closes it — the caller
states what the UI shows before the first value passes, rather than the framework
inventing a fallback. ``initial`` is therefore keyword-only and **required**.

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
from .wrapper import ShapingObservable, _untracked

T = TypeVar("T")


logger = logging.getLogger(__name__)


class FilteredObservable(ShapingObservable[T]):
    """Observable that emits only the source values satisfying ``pred``.

    ``value`` is the last value that passed, or ``initial`` if none has. At
    construction the source's current value is itself tested, so ``initial``
    means strictly "nothing has passed" rather than "nothing has arrived yet"::

        even = count.filter(lambda n: n % 2 == 0, initial=0)

    Values the predicate rejects change nothing: no emission, and ``value``
    keeps reporting the last one that passed. Lifetime follows the contract in
    :mod:`~nuiitivet.observable.wrapper`: hold this object, or the ``Disposable``
    from :meth:`subscribe`, for as long as the emissions are wanted.

    ``pred`` is a pure function of the value handed to it. It runs with
    dependency tracking suppressed, so reading another observable inside it
    creates no edge and will not re-run the filter — express that dependency
    with ``combine`` instead.

    A ``pred`` that raises is a bug, and is treated as one: logged, and the value
    is taken not to have passed, so nothing is emitted and ``value`` keeps
    reporting the last one that did (``OBSERVABLE.md`` §7). It is guarded here
    rather than by the source's notify loop because this predicate runs on the
    graph's own edge to that source, where an escaping exception would surface on
    whichever thread happened to write it.
    """

    def __init__(
        self,
        source: ReadOnlyObservableProtocol[T],
        pred: Callable[[T], bool],
        *,
        initial: T,
    ):
        self._pred = pred
        super().__init__(source)
        # The base seeded from the source; keep that value only if it passes.
        if not self._passes(self._held_value):
            self._held_value = initial

    def _passes(self, value: T) -> bool:
        try:
            return bool(_untracked(lambda: self._pred(value)))
        except Exception:
            exception_once_per_exc(
                logger,
                "filter_pred_raised",
                "filter predicate raised; the value was treated as not passing",
            )
            return False

    def _on_source_changed(self, value: T) -> None:
        # No equality check of our own: the source already de-dupes before it
        # notifies, and no other wrapper second-guesses that.
        if self._passes(value):
            self._emit_to_subscribers(value)
