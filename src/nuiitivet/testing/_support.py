"""What ``mount()``'s host and ``AppHarness`` share: querying, settling, teardown.

Implemented once, here, because the two objects differ only in what they can
*drive* -- the queries, the settle policy and the teardown discipline are the
same question at both levels, and two copies would drift.
"""

from __future__ import annotations

import asyncio
import threading
from time import monotonic
from typing import Any, Callable, List, Optional, Set

from nuiitivet._interaction.action import LayoutNotConvergedError
from nuiitivet._interaction.action import settle as _core_settle
from nuiitivet._interaction.perception import (
    _coerce_display,
    _iter_tree,
    describe_tree,
    find_targets,
    match_condition,
)
from nuiitivet.widgeting import callbacks as _callbacks
from nuiitivet.widgeting.callbacks import ContainedError

from ._tasks import TaskRegistry, describe_task, untracked_tasks
from .clock import HarnessClock
from .errors import IdleTimeoutError, TargetNotFoundError, WaitTimeoutError
from .node import Node, _LastAction


# How many times ``settle()`` may re-run the core settle because the pass it just
# finished armed *new* zero-delay work. The core's own loop converges on layout;
# this one converges on the clock, which is the harness's own concern (see
# :meth:`_HarnessBase.settle`).
_MAX_CLOCK_ROUNDS = 4

# How many identities a failed ``get()`` lists before truncating.
_MAX_REPORTED_IDENTITIES = 30

# How much of each queue a timeout diagnostic lists.
_MAX_REPORTED_CALLBACKS = 10
_MAX_REPORTED_TASKS = 10

# How long one round of ``idle()`` waits on its pending tasks. Short, because a
# round that completes nothing must still come back to pump the clock; a task
# that *does* complete wakes the wait immediately.
_IDLE_TURN = 0.001

# Rounds with no task movement before ``idle()`` calls the loop quiescent. More
# than one, because a task can need several turns to make its next observable
# move -- an await chain through an async mock resolves over two or three.
_IDLE_QUIET_ROUNDS = 3

# The sleep in ``idle()``'s no-task branch: enough of a turn for work the
# registry cannot see to reach its next await.
_IDLE_SPIN = 0.001

# Gap between ``wait_for`` polls, when no armed clock callback comes due sooner.
_POLL_INTERVAL = 0.005

# Fallback wait timeout, overridable per suite via ``[tool.nuiitivet.testing]``
# and per call via ``timeout=``.
_DEFAULT_WAIT_TIMEOUT = 1.0

_wait_timeout = _DEFAULT_WAIT_TIMEOUT


def _set_wait_timeout(value: Optional[float]) -> None:
    """Plugin-only: install this test's default ``wait_for`` / ``idle`` timeout."""
    global _wait_timeout
    _wait_timeout = _DEFAULT_WAIT_TIMEOUT if value is None else float(value)


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


# This test's check levels, and whether it has already failed. All three are the
# plugin's to set: the levels come from config the harness cannot read, and the
# outcome is not known until after the test body has run.
_leak_check: Optional[str] = None
_callback_errors: Optional[str] = None
_test_failed = False


def _set_leak_check(level: Optional[str]) -> None:
    """Plugin-only: install this test's default ``leak_check`` level."""
    global _leak_check
    _leak_check = level


def _set_callback_errors(level: Optional[str]) -> None:
    """Plugin-only: install this test's default ``callback_errors`` level."""
    global _callback_errors
    _callback_errors = level


def _set_test_failed(failed: bool) -> None:
    """Plugin-only: record that the current test has already failed."""
    global _test_failed
    _test_failed = failed


def _test_already_failed() -> bool:
    return _test_failed


def open_harnesses() -> List[Any]:
    """Plugin-only: the harnesses still open, in construction order."""
    return list(_open_harnesses)


def forget_open_harnesses() -> None:
    """Plugin-only: drop the registry, after closing whatever was in it."""
    _open_harnesses.clear()


def unobserved_in_flight() -> List[str]:
    """Plugin-only: descriptions of async work the test never waited for.

    Called at the end of the test body, while the loop is still open. Tasks the
    test *watched* park -- a handler blocked on a dialog it then asserted was
    open -- are excluded; what is left was started by an action and never
    awaited, which is the missing ``await app.idle()``.
    """
    described: List[str] = []
    for harness in _open_harnesses:
        registry = getattr(harness, "_tasks", None)
        if registry is None:  # pragma: no cover - half-built harness
            continue
        for task in registry.unobserved_in_flight():
            described.append(describe_task(task))
    return described


def _resolve_clock() -> tuple[HarnessClock, Optional[Callable[[], None]]]:
    """Return the clock to pump, and how to undo it if we installed one.

    The normal case is that the pytest plugin already installed a
    :class:`~nuiitivet.testing.clock.HarnessClock`, and the harness simply uses
    it. Outside pytest -- a plain ``with AppHarness(...)`` in a script, or a
    suite driven by something else -- nothing has, and the installed clock is
    the fallback ``_ThreadClock``, which fires on its own servicing thread and
    has no ``pump_immediate`` at all. Settling against that would either raise
    or, worse, silently skip the pump and let a marshalled write go unobserved.
    So the harness installs its own and gives the previous one back on close.
    """
    from nuiitivet.observable.runtime import get_clock, set_clock

    if _clock_opted_out:
        raise RuntimeError(
            'this test opted out of the harness clock with '
            '@pytest.mark.nuiitivet(clock="real"), but a harness needs to pump '
            "the zero-delay queue to settle -- a cross-thread write would "
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
    """Whether *this thread* armed a zero-delay one-shot that a pump would fire.

    Only work armed by the settling thread counts. The non-convergence this
    guards is the tree rescheduling itself -- a callback that arms another
    callback that arms another -- and that is a UI-thread loop by construction.

    A worker thread arming work is a different thing entirely, and now the
    ordinary thing: every cross-thread ``Observable`` write marshals through a
    zero-delay callback. A worker that keeps writing would keep this true
    forever and turn a live background thread into ``LayoutNotConvergedError``.
    Its writes are still pumped -- ``before_pass`` fires everything due,
    whoever armed it -- they just do not get a vote on whether the tree has
    stopped moving, which is the only question this asks.
    """
    here = threading.get_ident()
    return any(
        not cb.is_interval and cb.delay == 0.0 and cb.armed_by == here for cb in clock.pending()
    )


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

    def __init__(
        self,
        leak_check: Optional[str] = None,
        callback_errors: Optional[str] = None,
    ) -> None:
        self._clock: Optional[HarnessClock] = None
        self._restore_clock: Optional[Callable[[], None]] = None
        self._last_action = _LastAction()
        self._teardown_hooks: List[Callable[[], None]] = []
        self._tasks = TaskRegistry()
        self._closed = False
        self._exception_in_flight = False
        # Set before either installer runs, so a constructor that fails half-way
        # still has something for _stop_observing to find.
        self._error_sink: Optional[Callable[[ContainedError], None]] = None
        self._install_leak_check(leak_check)
        self._install_error_sink(callback_errors)
        # Observing starts here, before the subclass builds anything: mounting a
        # tree runs `on_mount`, which may itself be async, and a task started
        # while the harness was still being constructed is exactly the kind an
        # author would never think to wait for.
        #
        # A set, not a slot: `nuiitivet_app` is a factory, so one test may drive
        # more than one harness, and each keeps its own registry. Both then see
        # every task, since the framework knows an owner *name* and not which
        # App owns it -- so two harnesses in one test wait for each other's
        # work. Over-waiting is slower; under-waiting is flaky.
        _callbacks._task_observers.add(self._tasks.record)

    def _install_leak_check(self, level: Optional[str]) -> None:
        """Register the subscription-leak check for this harness's teardown.

        Registered first, so it runs first: a later hook that raises would
        otherwise skip the check entirely.

        The harness only *reads* the registry. Arming it is the plugin's job,
        around the whole test, because a widget subscribes in its constructor --
        ``Toggleable.__init__`` is the in-tree example -- which has already run by
        the time ``mount(widget)`` sees it. A flag armed here would be armed too
        late for the most common leak site in the framework.
        """
        from ._leaks import make_teardown_check, resolve_level

        resolved = resolve_level(
            level if level is not None else _leak_check,
            source=f"{type(self).__name__}(leak_check=...)",
        )
        self._leak_check_level = resolved
        self.add_teardown_hook(
            make_teardown_check(
                resolved,
                skip=lambda: self._exception_in_flight or _test_already_failed(),
            )
        )

    def _install_error_sink(self, level: Optional[str]) -> None:
        """Listen for exceptions the framework contains on user code's behalf.

        Installed here rather than at the first action, for the same reason the
        task observer is: mounting a tree runs ``on_mount``, and a constructor
        that raised into a containment before the harness was finished building
        is exactly the failure an author would never think to look for.

        ``"off"`` installs nothing at all, so a test that opted out pays no
        branch and the framework's own containment tests see the production
        behaviour they are asserting on.
        """
        from ._contained import install_sink, resolve_level

        resolved = resolve_level(
            level if level is not None else _callback_errors,
            source=f"{type(self).__name__}(callback_errors=...)",
        )
        self._callback_errors_level = resolved
        if resolved == "off":
            self._error_sink = None
            return
        self._error_sink = self._record_contained_error
        install_sink(self._error_sink)

    def _record_contained_error(self, error: ContainedError) -> None:
        """The sink. Queues alongside async handler failures, never raises here.

        Raising from a sink would unwind the very frame the containment exists
        to protect, half-way through a dispatch that has already mutated state.
        So the failure waits for a boundary the test controls -- the end of the
        action verb, an ``idle()``, or teardown.
        """
        from ._contained import claim

        if claim(error):
            self._tasks.record_error(error.exc, owner=error.owner, site=error.site)

    def _stop_observing(self) -> None:
        """Drop the task observer and the error sink. Safe to call twice.

        Both, because this is also the abandon path for a constructor that
        failed: there is no teardown coming to remove them one at a time.
        """
        _callbacks._task_observers.discard(self._tasks.record)
        self._remove_error_sink()

    def _remove_error_sink(self) -> None:
        """Stop listening for contained failures. Safe to call twice.

        Separate from :meth:`_stop_observing` because it happens *later* in a
        normal teardown: unmounting runs ``on_unmount`` and the dispose
        callbacks, both of which are user code behind a containment, so a sink
        dropped before the unmount would miss the last failures the harness is
        responsible for.
        """
        from ._contained import remove_sink

        if self._error_sink is not None:
            remove_sink(self._error_sink)
            self._error_sink = None

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
        pump rather than on the fallback clock's servicing thread.
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
        worker thread's observable write, a deferred batch flush or a
        ``Computed``'s UI notify is applied and then turned into an updated
        tree by the flush in the same pass. Delayed callbacks and intervals stay
        armed: no time has passed in this call that the test asked for.

        A pass can itself arm new zero-delay work -- a popup re-position retry
        scheduled *from* a layout is the in-tree example -- which the core's
        loop, converging on layout alone, would return without pumping. So this
        re-runs the core settle while such work remains, bounded, and raises if
        it never stops. Work armed by *another* thread does not extend the loop;
        see :func:`_has_immediate_work`.
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
                # Every action verb ends here, so this one drain covers click,
                # scroll, type, key and resize. A synchronous callback has
                # finished raising by now -- unlike an async one, which is still
                # a pending task -- so the failure surfaces at the line that
                # caused it rather than three assertions later.
                self._surface_contained_error()
                return
        raise LayoutNotConvergedError(
            f"settle did not converge after {_MAX_CLOCK_ROUNDS} rounds: every pass "
            "keeps arming new zero-delay work. Something is rescheduling itself "
            f"through the clock -- still armed: {clock.pending()!r}"
        )

    # -- awaiting ----------------------------------------------------------

    async def idle(self, timeout: Optional[float] = None) -> None:
        """Drain everything the app can do right now, then return.

        Pumps the clock in full -- not ``settle()``'s zero-delay-only pump,
        because inside an ``await`` the test is deliberately letting time pass,
        so a callback that has come due has come due honestly -- settles, and
        lets pending tasks run, until the loop is **quiescent**.

        Quiescent means no registered task has started or finished for several
        rounds. It deliberately does *not* mean "every task finished": a handler
        parked on ``await overlay.confirm(...)`` is an app at rest waiting for
        input, not work in progress, and waiting for it to complete would hang
        every dialog test. It equally does not mean "the clock is empty": an
        animation ticker fires forever by design, so clock firings are pumped
        and never counted as progress.

        Two things follow, and both are the point:

        - ``idle()`` returns with a dialog open, or with an animation still
          running. Waiting for either to *finish* is waiting for a future event,
          which is :meth:`wait_for`'s job.
        - it does not wait out a timer. A debounce, a tooltip delay or a mocked
          call that sleeps is a future event too.

        Raises:
            IdleTimeoutError: Work never stopped -- a handler spawning a handler,
                round after round.
            Exception: Whatever an async handler raised. The framework contains
                handler errors in production; under a harness that containment
                would let a handler which raised on line one read as one that
                worked, so the exception is re-raised here with its original
                traceback.
        """
        self._require_open()
        clock = self._ensure_clock()
        deadline = monotonic() + self._resolve_timeout(timeout)
        quiet = 0
        while True:
            clock.pump()
            self.settle()
            self._surface_contained_error()

            moved = self._tasks.take_progress()
            pending = self._tasks.in_flight()
            quiet = 0 if moved else quiet + 1

            # One rule, no fast path. An "everything is already done" shortcut
            # would return before the loop had run at all, so work the registry
            # cannot see -- a handler's own `asyncio.create_task`, a coroutine a
            # test drives by hand -- would never get a turn, and the wait would
            # be a no-op exactly where the author most needs one.
            if quiet >= _IDLE_QUIET_ROUNDS:
                self._tasks.mark_observed()
                return
            if monotonic() > deadline:
                raise IdleTimeoutError(
                    "idle() gave up after "
                    f"{self._resolve_timeout(timeout)}s: work is still being "
                    "created faster than it finishes.\n" + self._diagnose()
                )

            if pending:
                # FIRST_COMPLETED, not the default: a completion must be
                # followed by a pump and a settle before the next wait, or a
                # cross-thread marshal waits for a callback only a pump can
                # fire -- a deadlock the harness itself created.
                await asyncio.wait(
                    pending, timeout=_IDLE_TURN, return_when=asyncio.FIRST_COMPLETED
                )
            else:
                await asyncio.sleep(_IDLE_SPIN)

    async def wait_for(
        self,
        condition: Optional[Callable[[], Any]] = None,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        text: Optional[str] = None,
        present: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until something becomes true, or fail saying what did not.

        The verb for anything involving a delay -- a debounce, a transition, a
        mocked call that takes a moment. The delay itself never appears in the
        test, so changing a debounce from 0.3s to 0.5s breaks nothing::

            app.type("hello")
            await app.wait_for(key="results")
            await app.wait_for(key="spinner", present=False)
            await app.wait_for(lambda: vm.saved.value)

        Args:
            condition: A zero-argument callable, truthy when the wait is over.
                The tree vocabulary cannot say "this ``Observable`` changed",
                and the epic sends every state assertion to the ``Observable``
                that drove it, so a predicate is the other half of the surface.
                Mutually exclusive with the identity keywords.
            key: Wait for a node with this ``key``.
            label: Wait for a node with this visible identity.
            text: Wait for a node whose visible identity contains this substring.
            present: ``False`` waits for the match to *disappear* instead.
            timeout: Seconds, defaulting to the suite's ``wait_timeout``.

        Raises:
            WaitTimeoutError: The condition never held.
            TypeError: Neither a predicate nor an identifier, or both.
        """
        self._require_open()
        check = self._condition(condition, key=key, label=label, text=text, present=present)
        clock = self._ensure_clock()
        limit = self._resolve_timeout(timeout)
        deadline = monotonic() + limit
        while True:
            clock.pump()
            self.settle()
            self._surface_contained_error()
            if check():
                self._tasks.mark_observed()
                return
            remaining = deadline - monotonic()
            if remaining <= 0:
                self._tasks.mark_observed()
                raise WaitTimeoutError(
                    f"{self._describe_condition(condition, key, label, text, present)} "
                    f"was not satisfied after {limit}s.\n" + self._diagnose()
                )
            # Sleep to the earlier of the next poll and the next armed callback:
            # unlike the dev bridge, the harness owns the clock and can see what
            # is coming rather than polling blind.
            next_due = clock.next_deadline
            gap = _POLL_INTERVAL if next_due is None else min(_POLL_INTERVAL, next_due)
            await asyncio.sleep(max(_IDLE_SPIN, min(gap, remaining)))

    def _condition(
        self,
        condition: Optional[Callable[[], Any]],
        *,
        key: Optional[str],
        label: Optional[str],
        text: Optional[str],
        present: bool,
    ) -> Callable[[], bool]:
        names = [n for n, v in (("key", key), ("label", label), ("text", text)) if v is not None]
        if condition is not None:
            if names:
                raise TypeError(
                    "pass a predicate or a tree condition, not both: "
                    f"wait_for(<callable>, {names[0]}=...) has two answers to "
                    "'what am I waiting for' and no rule for which wins."
                )
            if not callable(condition):
                raise TypeError(
                    f"wait_for's first argument must be callable, got "
                    f"{type(condition).__name__}. To wait on a tree node, name it: "
                    "wait_for(key=...)."
                )
            return lambda: bool(condition())
        if not names:
            raise TypeError(
                "wait_for needs something to wait for: a predicate "
                "(wait_for(lambda: vm.loaded.value)) or a tree condition "
                "(wait_for(key='results'))."
            )
        # match_condition, not the core's check_condition: that one runs a
        # non-strict settle and never touches the clock, so a debounce armed on
        # the harness clock would never fire and the wait would time out on work
        # it was itself preventing.
        return lambda: match_condition(
            self._query_root, key=key, label=label, text=text, present=present
        )

    def _resolve_timeout(self, timeout: Optional[float]) -> float:
        return _wait_timeout if timeout is None else float(timeout)

    def _surface_contained_error(self) -> None:
        """Hand the test the first failure the framework contained for it.

        The exception is raised **as itself** -- a handler's ``ValueError``
        arrives as a ``ValueError`` -- so that a synchronous callback and an
        async one read identically at the assert, and the traceback still points
        at the line inside the handler. The owner and the containment site ride
        along as a note where the interpreter supports one.

        Below ``"error"`` nothing is taken from the queue, so the failures
        accumulate and are reported together at teardown instead of one at a
        time from wherever the test happened to settle.
        """
        from ._contained import annotate

        if self._callback_errors_level != "error":
            return
        error = self._tasks.take_error()
        if error is not None:
            raise annotate(error)

    def _report_contained_at_teardown(self) -> None:
        """Whatever the test never waited long enough to be handed."""
        from ._contained import report_at_teardown

        report_at_teardown(
            self._tasks.pending_errors(),
            level=self._callback_errors_level,
            demote=self._exception_in_flight or _test_already_failed(),
        )

    @staticmethod
    def _describe_condition(
        condition: Optional[Callable[[], Any]],
        key: Optional[str],
        label: Optional[str],
        text: Optional[str],
        present: bool,
    ) -> str:
        if condition is not None:
            name = getattr(condition, "__qualname__", None) or repr(condition)
            return f"predicate {name}"
        parts = [f"{n}={v!r}" for n, v in (("key", key), ("label", label), ("text", text))
                 if v is not None]
        if not present:
            parts.append("present=False")
        return "condition {" + ", ".join(parts) + "}"

    def _diagnose(self) -> str:
        """What was outstanding, in both queues, when a wait gave up."""
        lines: List[str] = []
        clock = self._clock
        pending_callbacks = clock.pending() if clock is not None else []
        if pending_callbacks:
            lines.append(f"  runtime.clock : {len(pending_callbacks)} pending callback(s)")
            for callback in pending_callbacks[:_MAX_REPORTED_CALLBACKS]:
                state = "due" if callback.due else "armed"
                lines.append(
                    f"                  {callback.fn!r} ({state}, delay={callback.delay}) "
                    f"scheduled at {callback.site}"
                )
        else:
            lines.append("  runtime.clock : nothing armed")

        tracked = self._tasks.in_flight()
        if tracked:
            lines.append(f"  asyncio       : {len(tracked)} task(s) pending")
            for task in list(tracked)[:_MAX_REPORTED_TASKS]:
                lines.append(f"                  {describe_task(task)}")
        else:
            lines.append("  asyncio       : no tracked task pending")

        untracked = untracked_tasks(tracked)
        if untracked:
            lines.append(
                f"  untracked     : {len(untracked)} task(s) not created by the "
                "framework, not waited on"
            )
            for task in untracked[:_MAX_REPORTED_TASKS]:
                lines.append(f"                  {describe_task(task)}")
        return "\n".join(lines)

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
            "key=... in its constructor. (The dev bridge would have taken the "
            "first match here; the harness refuses on purpose.)"
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
        """Unmount, run the teardown hooks, restore the clock. Idempotent.

        Deliberately does **not** cancel in-flight tasks. Under pytest this runs
        in the teardown phase, which is *after* the runner closed the loop the
        tasks live on, so there would be nothing to cancel them on; cancellation
        belongs to the loop's owner and already happens there. What this can
        still do is stop recording.
        """
        if self._closed:
            return
        self._closed = True
        if self in _open_harnesses:
            _open_harnesses.remove(self)
        # The task observer only: the error sink stays until the unmount below
        # has run on_unmount and the dispose callbacks, which are the last user
        # code this harness is answerable for.
        _callbacks._task_observers.discard(self._tasks.record)
        try:
            self._teardown()
            hook_error: Optional[BaseException] = None
            for hook in self._teardown_hooks:
                try:
                    hook()
                except Exception as exc:
                    # Held rather than raised, so one failing hook cannot skip
                    # the rest -- and so a handler that raised still wins the
                    # report below. A subscription leak is a real finding, but an
                    # exception with a traceback into the app's own code is more
                    # likely to be what went wrong first.
                    if hook_error is None:
                        hook_error = exc
            # Before the held hook error: a handler that failed after the test's
            # final wait would otherwise be dropped on the floor, which is the
            # containment this package exists to undo -- just later than usual.
            # All of them, not the first: this is the last chance any of them
            # get, so the rest are warned about rather than discarded.
            self._remove_error_sink()
            self._report_contained_at_teardown()
            if hook_error is not None:
                raise hook_error
        finally:
            self._remove_error_sink()
            if self._restore_clock is not None:
                self._restore_clock()

    def _teardown(self) -> None:
        """Subclass hook: unmount whatever this harness mounted."""
        raise NotImplementedError

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type: Any = None, *rest: Any) -> None:
        # A teardown check must not replace the exception it is unwinding. The
        # plugin does this for a fixture-managed harness by looking at the test's
        # outcome, but a `with` block inside the test body closes *before* there
        # is an outcome to look at -- and raising here would swap the assertion
        # the author is reading for a report about its consequences.
        self._exception_in_flight = exc_type is not None
        self.close()
