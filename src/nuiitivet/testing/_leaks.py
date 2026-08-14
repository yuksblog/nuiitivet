"""Subscription-leak detection: what was subscribed and never disposed.

The framework's central bug class is a subscription that outlives its widget. A
widget subscribes to an ``Observable``; if unmount does not dispose it, the
observable keeps a reference to a dead widget's callback, and firing it later
mutates an unmounted tree -- off the UI thread if the source was a background
one. The failure is silent where it is introduced and loud somewhere unrelated
later, so the harness asserts it automatically and an author gets the check
without knowing it exists.

**Where the hook is, and why there.** Every ``subscribe`` implementation in the
package returns a ``Disposable`` constructed in one of four places -- all of them
``subscribe`` returns -- and ``Animatable.subscribe`` delegates to the first of
them. So ``Disposable.__init__`` is the single point every subscription passes
through, and watching it covers ``debounce``, ``throttle``, ``Computed`` and
``Animatable`` together. The alternative -- scanning a widget for ``Disposable``s
it holds -- cannot see the dominant leak shape, which is
``obs.subscribe(lambda: self.invalidate())`` with the return value dropped on the
floor: there is nothing on the widget to find.

**Attribution happens here, not at subscribe time.** There is no ambient "current
widget" when ``subscribe`` runs, and inventing one would be the whole
implementation. But the owner is recoverable afterwards, from the callback the
subscription holds: ``__self__`` for a bound method, and for a lambda the widget
in its closure -- these lambdas exist to call ``self.invalidate()``.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from nuiitivet.observable.protocols import (
    Disposable,
    ObservableBase,
    _set_subscription_tracker,
    is_internal_subscription,
)

from .errors import SubscriptionLeakError

# Frames that are subscribe plumbing rather than a call site. Without this the
# four Animatable subscriptions in a TextField all report as animatable.py:150,
# which names the delegation and not the bug.
_PLUMBING = (
    os.path.join("nuiitivet", "observable") + os.sep,
    os.path.join("nuiitivet", "animation", "animatable.py"),
    os.path.join("nuiitivet", "widgeting", "widget_binding.py"),
    os.path.join("nuiitivet", "testing", "_leaks.py"),
)

# How far up to look for a call site before giving up. Deep enough for the
# longest in-tree chain (widget -> bind_to -> Animatable.subscribe ->
# _ObservableValue.subscribe -> Disposable), with room to spare.
_MAX_SITE_DEPTH = 16

# How many leaks one message lists before truncating.
_MAX_REPORTED_LEAKS = 20

LEAK_CHECK_LEVELS = ("error", "warn", "off")

_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SubscriptionLeakWarning(Warning):
    """The ``leak_check="warn"`` form of :class:`SubscriptionLeakError`."""


class _Record:
    """One subscription, and where it was made."""

    __slots__ = ("disposable", "site", "claimed")

    def __init__(self, disposable: Disposable, site: str) -> None:
        # A strong reference, deliberately. Under a weak one the leak that
        # matters most -- ``obs.subscribe(...)`` with the return value
        # discarded -- is collected the instant it is created, and the check
        # would report a clean bill of health on exactly the shape it exists to
        # find. The cost is that a widget stays alive until the registry is
        # cleared, which is the end of the test.
        self.disposable = disposable
        self.site = site
        self.claimed = False


class _Registry:
    """Every subscription created while tracking, in creation order."""

    def __init__(self) -> None:
        self.records: List[_Record] = []

    def record(self, disposable: Disposable) -> None:
        self.records.append(_Record(disposable, _capture_site()))

    def unclaimed_undisposed(self) -> List[_Record]:
        """Subscriptions still open and not yet reported by an earlier teardown.

        Claim-once, because the registry is per *test* while the check runs per
        *harness*: a test driving two harnesses would otherwise report the
        first's findings again at the second's teardown. With one harness -- the
        overwhelming case -- the first pass takes everything.
        """
        return [r for r in self.records if not r.claimed and not r.disposable.is_disposed]

    @staticmethod
    def claim(records: List[_Record]) -> None:
        """Mark records as reported, so a later teardown does not repeat them.

        Only what was judged; a subscription belonging to a widget that is still
        mounted stays unclaimed, so the harness that eventually unmounts it can
        still find it. Claiming everything in sight would let a second harness
        silence the first's leaks on the way past.
        """
        for record in records:
            record.claimed = True


_registry: Optional[_Registry] = None
_depth = 0


@contextmanager
def track_subscriptions() -> Iterator[_Registry]:
    """Record every subscription created inside the block.

    Nesting is a no-op: the inner block yields the same registry and does not
    clear it on the way out, so the pytest plugin arming this around a whole test
    and a ``with mount(...)`` inside that test do not fight over ownership.
    """
    global _registry, _depth
    if _registry is None:
        _registry = _Registry()
        _set_subscription_tracker(_registry.record)
    _depth += 1
    registry = _registry
    try:
        yield registry
    finally:
        _depth -= 1
        if _depth == 0:
            _set_subscription_tracker(None)
            _registry = None


def active_registry() -> Optional[_Registry]:
    """The registry currently recording, if anything is."""
    return _registry


# -- call sites -------------------------------------------------------------


def _short_path(filename: str) -> str:
    """``nuiitivet/widgets/text.py`` for our own code; app paths untouched."""
    if filename.startswith(_PACKAGE_ROOT + os.sep):
        return os.path.join("nuiitivet", os.path.relpath(filename, _PACKAGE_ROOT))
    return filename


def _capture_site() -> str:
    """The innermost frame that is not subscribe plumbing.

    Walks raw frames rather than calling ``traceback.extract_stack``, which
    builds ``FrameSummary`` objects and reads source lines for every frame -- too
    much to pay on a path that runs once per subscription in a whole suite.
    """
    try:
        frame: Any = sys._getframe(1)
    except ValueError:  # pragma: no cover - no caller frame
        return "<unknown>"
    for _ in range(_MAX_SITE_DEPTH):
        if frame is None:
            break
        filename = frame.f_code.co_filename
        if not any(part in filename for part in _PLUMBING):
            return f"{_short_path(filename)}:{frame.f_lineno}"
        frame = frame.f_back
    return "<subscribe plumbing only>"


# -- attribution ------------------------------------------------------------


def _closure_of(fn: Any) -> Dict[str, Any]:
    """A closure's free variables by name, or ``{}`` for a plain function."""
    code = getattr(fn, "__code__", None)
    closure = getattr(fn, "__closure__", None)
    if code is None or not closure:
        return {}
    values: Dict[str, Any] = {}
    for name, cell in zip(code.co_freevars, closure):
        try:
            values[name] = cell.cell_contents
        except ValueError:  # pragma: no cover - cell not yet filled
            continue
    return values


def _is_widget(value: Any) -> bool:
    """Whether ``value`` is something the ``bind()`` contract applies to.

    ``BindingHostMixin`` rather than ``Widget`` or a duck-typed probe, because it
    is exactly the contract being enforced: it is what provides ``bind()`` and
    what disposes at unmount, so anything that has it is something a leaked
    subscription can be held against.
    """
    from nuiitivet.widgeting.widget_binding import BindingHostMixin

    return isinstance(value, BindingHostMixin)


def attribute(disposable: Disposable) -> Tuple[Any, Any, Any]:
    """``(observable, callback, owner)`` recovered from the dispose closure.

    Every ``_dispose`` closes over the observable as ``self`` and the subscriber
    as ``cb`` or ``callback``; the owner is then the callback's bound instance,
    or the widget captured by the lambda.
    """
    env = _closure_of(disposable._dispose_fn)
    observable = env.get("self")
    callback = env.get("cb", env.get("callback"))
    owner = getattr(callback, "__self__", None)
    if owner is None and callback is not None:
        for value in _closure_of(callback).values():
            if _is_widget(value):
                owner = value
                break
    return observable, callback, owner


def _classify(record: _Record) -> Tuple[str, Optional[Any]]:
    """``("widget" | "live" | "internal" | "unattributed", owner)``.

    ``internal`` is an edge of the observable graph itself -- ``Computed``'s
    subscription to its dependencies, ``Debounced``'s to its source. Those are
    disposed with the observable that owns them and have nothing to do with a
    widget's lifetime, so reporting them would be the check crying wolf on the
    framework's own wiring. They are recognised by an explicit mark
    (:func:`~nuiitivet.observable.protocols.mark_internal_subscription`) rather
    than by inferring an owner from the callback: both kinds now subscribe
    through a ``weakref`` so their source cannot keep them alive, which leaves
    no owner to infer. Inference previously caught ``Debounced`` -- which held a
    bound method, the very thing that leaked -- and missed ``Computed``
    entirely, so the sentence above described neither.

    ``live`` is a widget that has not been unmounted, and the distinction is
    load-bearing rather than pedantic. A leak is *the widget is gone and the
    subscription remains*, so both other states are outside it: a widget still
    mounted in a second harness the test has not closed yet is working exactly as
    intended, and one constructed but never mounted never entered a tree for a
    subscription to outlive. Reporting either would fail tests that are correct.
    """
    _observable, callback, owner = attribute(record.disposable)
    if is_internal_subscription(callback):
        return "internal", owner
    if owner is None:
        return "unattributed", None
    if isinstance(owner, ObservableBase):
        return "internal", owner
    if _is_widget(owner):
        # The lifecycle flag rather than a public accessor: there is none, and
        # inventing one would be a framework change for a test-only reader.
        return ("widget" if getattr(owner, "_unmounted", False) else "live"), owner
    return "unattributed", owner


# -- reporting --------------------------------------------------------------


def judge(records: List[_Record]) -> Tuple[List[_Record], List[Tuple[str, str]], int]:
    """Split records into ``(judged, widget_leaks, unattributed_count)``.

    ``judged`` is everything this teardown is entitled to claim -- which excludes
    subscriptions belonging to a widget that is still mounted, since the harness
    that eventually unmounts it is the one that can tell whether it leaked.
    """
    judged: List[_Record] = []
    widget_leaks: List[Tuple[str, str]] = []
    unattributed = 0
    for record in records:
        kind, owner = _classify(record)
        if kind == "live":
            continue
        judged.append(record)
        if kind == "widget":
            widget_leaks.append((type(owner).__name__, record.site))
        elif kind == "unattributed":
            unattributed += 1
    return judged, widget_leaks, unattributed


def format_leak_report(widget_leaks: List[Tuple[str, str]], other: int = 0) -> Optional[str]:
    """The message for a set of leaked subscriptions, or ``None`` if none count.

    Only widget-owned subscriptions count. A subscription with no widget behind
    it belongs to app code with a lifetime the harness knows nothing about, so it
    is listed as a tail on a report that already has a reason to exist and never
    causes one on its own.
    """
    if not widget_leaks:
        return None

    lines = [
        f"{len(widget_leaks)} subscription(s) were created during this test and "
        "never disposed. The observable still holds a callback into a widget that "
        "has been unmounted, so firing it now mutates a dead tree:",
        "",
    ]
    width = max(len(name) for name, _ in widget_leaks[:_MAX_REPORTED_LEAKS])
    for name, site in widget_leaks[:_MAX_REPORTED_LEAKS]:
        lines.append(f"  {name:<{width}}  subscribed at {site}")
    if len(widget_leaks) > _MAX_REPORTED_LEAKS:
        lines.append(f"  (+{len(widget_leaks) - _MAX_REPORTED_LEAKS} more)")
    if other:
        lines.append("")
        lines.append(
            f"  ({other} further undisposed subscription(s) belong to no widget, "
            "so their lifetime is not the harness's to judge; not counted above.)"
        )
    lines.extend(
        [
            "",
            "Wrap the call in self.bind(...), which disposes it on unmount, or use "
            "self.observe(obs, cb) / self.bind_to(obs, setter) which do it for you. "
            'If the subscription genuinely outlives the widget, set '
            'leak_check="off" for this test.',
        ]
    )
    return "\n".join(lines)


def resolve_level(level: Optional[str], *, source: str) -> str:
    """The level to run at, defaulting to ``"error"``.

    ``"error"`` rather than ``"warn"`` because a warning in a suite that already
    prints warnings is a finding nobody reads, and the whole point is that a
    green test is trustworthy. The default was only affordable once the in-tree
    audit came back clean -- three widgets' worth of real leaks had to be fixed
    first, which is the work this check was built to do.
    """
    if level is None:
        return "error"
    if level not in LEAK_CHECK_LEVELS:
        raise ValueError(
            f"invalid leak_check={level!r} in {source}; "
            f"expected one of: {', '.join(LEAK_CHECK_LEVELS)}"
        )
    return level


def make_teardown_check(level: str, *, skip: Callable[[], bool]) -> Callable[[], None]:
    """The hook a harness runs after unmounting, at ``level``.

    ``skip`` is consulted at teardown rather than now: whether the test has
    already failed is not known when the harness is built, and a leak report
    appended to a first failure that probably caused it is noise on top of the
    thing worth reading.
    """

    def check() -> None:
        registry = active_registry()
        if registry is None or level == "off":
            return
        judged, widget_leaks, unattributed = judge(registry.unclaimed_undisposed())
        # Claimed even when the report is suppressed below: whatever this
        # teardown looked at has been looked at, and a second harness repeating
        # it would say the same thing twice.
        registry.claim(judged)
        if skip():
            return
        message = format_leak_report(widget_leaks, unattributed)
        if message is None:
            return
        if level == "warn":
            import warnings

            warnings.warn(message, SubscriptionLeakWarning, stacklevel=2)
        else:
            raise SubscriptionLeakError(message)

    return check


__all__ = [
    "LEAK_CHECK_LEVELS",
    "SubscriptionLeakWarning",
    "attribute",
    "format_leak_report",
    "judge",
    "make_teardown_check",
    "resolve_level",
    "track_subscriptions",
]
