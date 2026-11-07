"""The garbage collector's place in the frame loop."""

from __future__ import annotations

import gc
from typing import Optional, Tuple

# A frame that builds a screenful of rich rows allocates about 6,000 tracked
# objects. The backstop sits above a few of those, so an ordinary frame never
# pays the collection the pacer exists to keep out of it, and a loop that
# never waits still frees its young garbage within a bounded cost.
YOUNG_BACKSTOP = 20_000
# Survivors of the young generation wait in the middle one for a collection
# whose cost grows with the objects it holds, so the budget is in objects,
# not in collections as CPython's own threshold is.
MIDDLE_BUDGET = 10_000
# Objects promoted to the old generation since the last full collection above
# which a full collection no longer waits for a quiet moment.
OLD_BUDGET = 300_000
QUIET_SECONDS = 1.0


class GcPacer:
    """Keeps the garbage collector out of the frame.

    While installed, the collector never runs on its own. The loop collects
    the young and middle generations when it is about to wait, and the whole
    heap when it has drawn nothing for a while.
    """

    def __init__(
        self,
        *,
        young_backstop: int = YOUNG_BACKSTOP,
        middle_budget: int = MIDDLE_BUDGET,
        old_budget: int = OLD_BUDGET,
        quiet_seconds: float = QUIET_SECONDS,
        freeze: bool = True,
    ) -> None:
        """
        Args:
            young_backstop: Allocations since the last collection above which
                a frame collects what is due before it starts.
            middle_budget: Objects promoted out of the young generation since
                the middle one was last collected, above which the middle
                generation is collected too.
            old_budget: Objects promoted to the old generation since the last
                full collection, above which a due full collection runs
                without waiting for a quiet moment.
            quiet_seconds: Seconds without a frame after which a due full
                collection runs.
            freeze: At the first wait after the first frame, move everything
                alive out of the collector's reach. A full collection forced
                by ``old_budget`` then skips those objects; a quiet one takes
                them back in, collects the whole heap and freezes what
                survived.
        """
        self._young_backstop = int(young_backstop)
        self._middle_budget = int(middle_budget)
        self._old_budget = int(old_budget)
        self._quiet_seconds = float(quiet_seconds)
        self._freeze = bool(freeze)
        self._installed = False
        self._was_enabled = True
        self._thresholds: Tuple[int, int, int] = gc.get_threshold()
        self._frozen = False
        self._last_frame: Optional[float] = None
        self._promoted = 0
        self._old_promoted = 0

    @property
    def installed(self) -> bool:
        """Whether the pacer currently owns the collector."""
        return self._installed

    def install(self) -> None:
        """Take the collector over: nothing collects until the pacer says so."""
        if self._installed:
            return
        self._was_enabled = gc.isenabled()
        self._thresholds = gc.get_threshold()
        gc.disable()
        self._installed = True

    def uninstall(self) -> None:
        """Hand the collector back in the state :meth:`install` found it."""
        if not self._installed:
            return
        if self._frozen:
            gc.unfreeze()
            self._frozen = False
        if self._was_enabled:
            gc.enable()
        self._installed = False

    def before_frame(self) -> None:
        """Collect what is due before the frame when the backstop is passed."""
        if not self._installed:
            return
        if gc.get_count()[0] > self._young_backstop:
            self._collect_due(quiet=False)

    def after_frame(self, now: float) -> None:
        """Record the frame's end.

        Args:
            now: ``time.perf_counter()`` when the frame ended.
        """
        self._last_frame = now

    def idle(self, now: float) -> Optional[float]:
        """Collect what is due, the loop being about to wait.

        The young generation is collected when it holds more than its
        threshold, the middle one when its budget is spent. A full collection
        that is due runs over the whole heap when the last frame ended
        ``quiet_seconds`` or more ago, and over the unfrozen heap at once when
        the old generation grew past its budget.

        Args:
            now: ``time.perf_counter()`` at the call.

        Returns:
            Seconds until a full collection that is due may run, or ``None``
            when none is waiting.
        """
        if not self._installed:
            return None
        quiet_for = self._quiet_seconds if self._last_frame is None else now - self._last_frame
        self._collect_due(quiet=quiet_for >= self._quiet_seconds)
        if self._freeze and not self._frozen and self._last_frame is not None:
            # The first frame's garbage was just collected; what is left is the startup tree.
            gc.freeze()
            self._frozen = True
        if gc.get_count()[2] <= self._thresholds[2]:
            return None
        return self._quiet_seconds - quiet_for

    def _collect_due(self, *, quiet: bool) -> None:
        threshold0, _, threshold2 = self._thresholds
        young = gc.get_count()[0]
        if young > threshold0:
            # Everything the young generation holds is counted as promoted;
            # what the collection frees instead only makes the budget cautious.
            self._promoted += young
            gc.collect(0)
        if self._promoted > self._middle_budget:
            freed = gc.collect(1)
            self._old_promoted += max(0, self._promoted - freed)
            self._promoted = 0
        if gc.get_count()[2] <= threshold2:
            return
        if quiet:
            self._collect_everything()
        elif self._old_promoted > self._old_budget:
            gc.collect()
            self._old_promoted = 0

    def _collect_everything(self) -> None:
        if self._frozen:
            gc.unfreeze()
        gc.collect()
        if self._frozen:
            gc.freeze()
        self._old_promoted = 0
