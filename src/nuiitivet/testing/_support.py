"""What ``mount()``'s host and ``AppHarness`` share: querying, settling, teardown.

Implemented once, here, because the two objects differ only in what they can
*drive* -- the queries, the settle policy and the teardown discipline are the
same question at both levels, and two copies would drift.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Set

from nuiitivet._interaction.action import LayoutNotConvergedError
from nuiitivet._interaction.action import settle as _core_settle
from nuiitivet._interaction.perception import (
    _coerce_display,
    _iter_tree,
    describe_tree,
    find_targets,
)

from .clock import HarnessClock
from .errors import TargetNotFoundError
from .node import Node, _LastAction


# How many times ``settle()`` may re-run the core settle because the pass it just
# finished armed *new* zero-delay work. The core's own loop converges on layout;
# this one converges on the clock, which is the harness's own concern (see
# :meth:`_HarnessBase.settle`).
_MAX_CLOCK_ROUNDS = 4

# How many identities a failed ``get()`` lists before truncating.
_MAX_REPORTED_IDENTITIES = 30

# Every harness constructed and not yet closed, in construction order. The
# pytest plugin sweeps this at teardown so a harness a test forgot to close
# cannot leak into the next one.
#
# Strong references, deliberately. A weak registry would drop `AppHarness(...)`
# called for its side effect the moment the statement ends, and the sweep would
# find nothing to close -- while the tree stays mounted and subscribed, because
# an observable holds *its* subscribers, not the other way round. The harness is
# meant to live exactly as long as the test, so holding it for that long is the
# correct lifetime rather than a leak of its own.
_open_harnesses: List[Any] = []

# Set by the plugin for a test that opted out of the harness clock. Constructing
# a harness in such a test is a contradiction, and is refused rather than
# silently overriding the choice the test made explicitly.
_clock_opted_out = False


def _set_clock_opted_out(value: bool) -> None:
    """Plugin-only: record whether the current test refused the harness clock."""
    global _clock_opted_out
    _clock_opted_out = value


def open_harnesses() -> List[Any]:
    """Plugin-only: the harnesses still open, in construction order."""
    return list(_open_harnesses)


def forget_open_harnesses() -> None:
    """Plugin-only: drop the registry, after closing whatever was in it."""
    _open_harnesses.clear()


def _resolve_clock() -> tuple[HarnessClock, Optional[Callable[[], None]]]:
    """Return the clock to pump, and how to undo it if we installed one.

    The normal case is that the pytest plugin already installed a
    :class:`~nuiitivet.testing.clock.HarnessClock`, and the harness simply uses
    it. Outside pytest -- a plain ``with AppHarness(...)`` in a script, or a
    suite driven by something else -- nothing has, and the installed clock is
    the fallback ``_ThreadClock``, which fires on timer threads and has no
    ``pump_immediate`` at all. Settling against that would either raise or,
    worse, silently skip the pump and let a ``dispatch_to_ui`` write go
    unobserved. So the harness installs its own and gives the previous one back
    on close.
    """
    from nuiitivet.observable.runtime import get_clock, set_clock

    if _clock_opted_out:
        raise RuntimeError(
            'this test opted out of the harness clock with '
            '@pytest.mark.nuiitivet(clock="real"), but a harness needs to pump '
            "the zero-delay queue to settle -- a dispatch_to_ui write would "
            "never be applied and the test would assert on the stale value. "
            "Drop the marker, or drive the app without a harness."
        )

    current = get_clock()
    if isinstance(current, HarnessClock):
        return current, None

    harness_clock = HarnessClock()
    set_clock(harness_clock)

    def restore() -> None:
        set_clock(current)
        harness_clock.cancel_all()

    return harness_clock, restore


def _has_immediate_work(clock: HarnessClock) -> bool:
    """Whether a zero-delay one-shot is armed and would fire on the next pump."""
    return any(not cb.is_interval and cb.delay == 0.0 for cb in clock.pending())


def _require_one_identifier(key: Optional[str], label: Optional[str]) -> None:
    """Refuse a query that names zero or two identifiers.

    Both is the interesting one. The core matches on *either* -- a target spec
    names one widget two ways -- so ``key=..., label=...`` widens the search
    rather than narrowing it, and an author who wrote it to disambiguate gets
    the opposite of what they meant. An ``assert`` cannot notice that, so it is
    refused here. The core keeps its OR for the dev bridge, whose caller reads
    the result and judges.
    """
    if key is not None and label is not None:
        raise TypeError(
            "pass key= or label=, not both: they are matched as an OR, so naming "
            "both widens the query instead of narrowing it. Use key= alone for "
            "identity, label= alone for presence."
        )
    if key is None and label is None:
        raise TypeError("pass key= or label= to name a target")


def _describe_query(key: Optional[str], label: Optional[str]) -> str:
    return f"key={key!r}" if key is not None else f"label={label!r}"


def _available_identities(root: Any) -> List[str]:
    """Every ``key`` and display identity currently in the tree, for a message."""
    found: List[str] = []
    seen: Set[str] = set()
    for node in _iter_tree(root):
        node_key = _coerce_display(getattr(node, "key", None))
        if node_key is not None and f"key={node_key!r}" not in seen:
            seen.add(f"key={node_key!r}")
            found.append(f"key={node_key!r}")
        for attr in ("label", "text", "title"):
            display = _coerce_display(getattr(node, attr, None))
            if display is not None and f"label={display!r}" not in seen:
                seen.add(f"label={display!r}")
                found.append(f"label={display!r}")
    return found


class _HarnessBase:
    """Queries, settling and teardown, shared by both harness objects."""

    __test__ = False

    def __init__(self) -> None:
        self._clock: Optional[HarnessClock] = None
        self._restore_clock: Optional[Callable[[], None]] = None
        self._last_action = _LastAction()
        self._teardown_hooks: List[Callable[[], None]] = []
        self._closed = False

    def _register(self) -> None:
        """Join the open-harness registry. Called last, by the subclass.

        Last, so a constructor that raises half-way leaves nothing behind: a
        partly-built harness in the registry would be handed to ``close()`` at
        teardown, where it would fail on the attributes it never got -- and be
        reported as a harness the test forgot to close, which it never had.
        """
        _open_harnesses.append(self)

    def _ensure_clock(self) -> HarnessClock:
        """Resolve the clock, at the last moment that is still correct.

        Lazily, because a harness that never settles never needs one -- and an
        animation test that installs its own frame-driving clock and asks only
        for a host to mount against is a real case we would otherwise break by
        taking the clock out from under it.

        :class:`~nuiitivet.testing.AppHarness` is the exception and resolves in
        its constructor: building an ``App`` mounts a whole tree, and mount-time
        ``schedule_once(fn, 0)`` calls have to land somewhere the harness can
        pump rather than on a timer thread.
        """
        if self._clock is None:
            self._clock, self._restore_clock = _resolve_clock()
        return self._clock

    # -- subclass contract -------------------------------------------------

    @property
    def _settle_target(self) -> Any:
        """The object the core settle drives: needs ``root`` / ``width`` / ``height``."""
        raise NotImplementedError

    @property
    def _query_root(self) -> Any:
        """The widget every query walks from."""
        raise NotImplementedError

    # -- settling ----------------------------------------------------------

    @property
    def clock(self) -> HarnessClock:
        """The clock this harness pumps. Sleep past a delay, then ``pump()``."""
        return self._ensure_clock()

    def settle(self) -> None:
        """Flush reactive work and re-lay-out, so an effect becomes observable.

        Strict: a layout that raises reaches the test rather than a debug log,
        and a tree that will not converge raises rather than leaving whichever
        half-laid-out frame the last pass produced.

        Pumps the clock's zero-delay queue at the top of every pass, so a
        ``dispatch_to_ui`` write from a worker thread, a deferred batch flush or
        a ``Computed``'s UI notify is applied and then turned into an updated
        tree by the flush in the same pass. Delayed callbacks and intervals stay
        armed: no time has passed in this call that the test asked for.

        A pass can itself arm new zero-delay work -- a popup re-position retry
        scheduled *from* a layout is the in-tree example -- which the core's
        loop, converging on layout alone, would return without pumping. So this
        re-runs the core settle while such work remains, bounded, and raises if
        it never stops.
        """
        self._require_open()
        clock = self._ensure_clock()
        for _ in range(_MAX_CLOCK_ROUNDS):
            _core_settle(
                self._settle_target,
                strict=True,
                before_pass=clock.pump_immediate,
            )
            if not _has_immediate_work(clock):
                return
        raise LayoutNotConvergedError(
            f"settle did not converge after {_MAX_CLOCK_ROUNDS} rounds: every pass "
            "keeps arming new zero-delay work. Something is rescheduling itself "
            f"through the clock -- still armed: {clock.pending()!r}"
        )

    # -- queries -----------------------------------------------------------

    def get(self, *, key: Optional[str] = None, label: Optional[str] = None) -> Node:
        """The one node matching. Fails on none, and fails on more than one.

        Failing on ambiguity is a deliberate divergence from the dev bridge,
        which takes the first match and says nothing: an assistant can look at
        the screen and try again, an ``assert`` cannot, and a test that silently
        targeted the wrong row of a list is exactly the green-but-meaningless
        result this package exists to prevent.
        """
        self._require_open()
        _require_one_identifier(key, label)
        matches = find_targets(self._query_root, key=key, label=label)
        query = _describe_query(key, label)
        if not matches:
            available = _available_identities(self._query_root)
            listed = ", ".join(available[:_MAX_REPORTED_IDENTITIES]) or "(nothing identifiable)"
            more = (
                f" (+{len(available) - _MAX_REPORTED_IDENTITIES} more)"
                if len(available) > _MAX_REPORTED_IDENTITIES
                else ""
            )
            raise TargetNotFoundError(
                f"no widget matched {query}. Available in the tree: {listed}{more}"
            )
        if len(matches) > 1:
            raise TargetNotFoundError(self._ambiguous_message(query, matches))
        return self._node(matches[0])

    def query(self, *, key: Optional[str] = None, label: Optional[str] = None) -> Optional[Node]:
        """The one node matching, or ``None``. Still fails on more than one.

        Absence is an answer here; ambiguity never is.
        """
        self._require_open()
        _require_one_identifier(key, label)
        matches = find_targets(self._query_root, key=key, label=label)
        if not matches:
            return None
        if len(matches) > 1:
            raise TargetNotFoundError(
                self._ambiguous_message(_describe_query(key, label), matches)
            )
        return self._node(matches[0])

    def get_all(self, *, key: Optional[str] = None, label: Optional[str] = None) -> List[Node]:
        """Every node matching, possibly empty. The verb for "how many"."""
        self._require_open()
        _require_one_identifier(key, label)
        return [self._node(w) for w in find_targets(self._query_root, key=key, label=label)]

    def tree(self) -> dict:
        """The tree as a dict, for ``print(app.tree())`` when a test fails.

        Debug output, not an assertion source: asserting into it by index breaks
        when the tree is restructured without any behaviour changing, which is
        what the three query verbs exist to avoid.
        """
        self._require_open()
        return describe_tree(self._query_root)

    def _ambiguous_message(self, query: str, matches: List[Any]) -> str:
        parts: List[str] = []
        for widget in matches[:_MAX_REPORTED_IDENTITIES]:
            described_one = type(widget).__name__
            widget_key = getattr(widget, "key", None)
            if isinstance(widget_key, str):
                described_one += " key=" + repr(widget_key)
            rect = getattr(widget, "global_layout_rect", None)
            if rect is not None:
                described_one += " at " + str(tuple(round(v) for v in rect))
            parts.append(described_one)
        described = ", ".join(parts)
        return (
            f"{query} matched {len(matches)} widgets, and a test cannot choose "
            f"between them: {described}. Give the one you mean a unique key with "
            "keyed(). (The dev bridge would have taken the first match here; the "
            "harness refuses on purpose.)"
        )

    def _node(self, widget: Any) -> Node:
        key = getattr(widget, "key", None)
        query = f"key={key!r}" if isinstance(key, str) else f"<{type(widget).__name__}>"
        return Node(
            widget,
            root=self._query_root,
            query=query,
            last_action=self._last_action,
        )

    # -- teardown ----------------------------------------------------------

    def add_teardown_hook(self, hook: Callable[[], None]) -> None:
        """Run ``hook`` when this harness closes, on the pass and the fail path.

        The extension point for checks that must run against a torn-down tree --
        subscription-leak detection is the one this was built for. Hooks run in
        registration order, after the tree is unmounted and before the clock is
        restored; a raising hook reaches the test, since a check that fails
        silently is not a check.
        """
        self._teardown_hooks.append(hook)

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                f"{type(self).__name__} is closed: it was torn down by its "
                "fixture or its 'with' block, and the tree it drove is unmounted."
            )

    def close(self) -> None:
        """Unmount, run the teardown hooks, restore the clock. Idempotent."""
        if self._closed:
            return
        self._closed = True
        if self in _open_harnesses:
            _open_harnesses.remove(self)
        try:
            self._teardown()
            for hook in self._teardown_hooks:
                hook()
        finally:
            if self._restore_clock is not None:
                self._restore_clock()

    def _teardown(self) -> None:
        """Subclass hook: unmount whatever this harness mounted."""
        raise NotImplementedError

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
