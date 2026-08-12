"""Contained callback errors: user code that raised where nobody was looking.

The framework catches exceptions out of user callbacks and carries on. In
production that is correct and must not change -- one broken ``on_click`` must
not kill the frame. In a test it is the failure this package exists to remove:
the handler never ran to completion, the tree never updated, and the assertion
after it reads that absence as success.

**A sink, not a log handler.** The obvious approach is to watch the log records
those containments already emit, and it does not survive contact with the
framework: ``exception_once`` is called from 570 places across 73 modules, the
great majority of them defensive handling of framework internals -- dereferencing
a weakref, resetting an internal deque -- where carrying on is the entire point.
A handler cannot tell those from a user callback, so it would need a permanent
hand-maintained ignore list covering the framework's own error handling. The
containment sites *can* tell, because they know what they were calling. So they
report, through :func:`nuiitivet.widgeting.callbacks.report_contained`, and this
module is what listens.

**The failure keeps its own type.** A contained ``ValueError`` reaches the test
as a ``ValueError``, not wrapped -- the same contract the async half already
ships (``idle()`` re-raises what the handler raised), so ``pytest.raises`` reads
the same for both and the traceback still points at the handler's own line. On
Python 3.11+ the owner and the containment site are attached as a note; below
that the traceback carries the location on its own.
"""

from __future__ import annotations

import warnings
import weakref
from typing import Callable, List, Optional

from nuiitivet.widgeting import callbacks as _callbacks
from nuiitivet.widgeting.callbacks import ContainedError

CALLBACK_ERROR_LEVELS = ("error", "warn", "off")

# How many failures one teardown report lists before truncating.
_MAX_REPORTED_ERRORS = 20

# Failures already handed to a test. One containment produces one record, which
# every open harness's sink receives -- the same deliberate over-sharing the task
# observers do, because the framework knows an owner *name* and not which App
# owns it. Over-waiting on a sibling's task is merely slow; reporting a sibling's
# failure twice would put a duplicate warning under the failure it caused, so the
# first harness to take it claims it.
_claimed: "weakref.WeakSet[ContainedError]" = weakref.WeakSet()


def claim(error: ContainedError) -> bool:
    """Take ownership of a failure. ``False`` if another harness got there first."""
    if error in _claimed:
        return False
    _claimed.add(error)
    return True


class ContainedCallbackWarning(Warning):
    """A callback raised, the framework contained it, and the test carried on.

    Raised as a warning rather than a failure in two cases: under
    ``callback_errors="warn"``, and at the teardown of a test that has already
    failed -- where the contained error is usually *why* it failed, so it must
    be reported, but must not replace the failure the author is reading.
    """


def resolve_level(level: Optional[str], *, source: str) -> str:
    """The level to run at, defaulting to ``"error"``.

    ``"error"`` from the start, with no ``"warn"`` release in front of it. The
    sink is installed by an open harness and removed at its teardown, so a suite
    that never touches ``nuiitivet.testing`` sees nothing -- the same reach
    ``leak_check`` has, and the same reason a warning phase would only be a
    finding nobody reads.
    """
    if level is None:
        return "error"
    if level not in CALLBACK_ERROR_LEVELS:
        raise ValueError(
            f"invalid callback_errors={level!r} in {source}; "
            f"expected one of: {', '.join(CALLBACK_ERROR_LEVELS)}"
        )
    return level


def install_sink(sink: Callable[[ContainedError], None]) -> None:
    """Start listening for contained user-code failures."""
    _callbacks._error_sinks.add(sink)


def remove_sink(sink: Callable[[ContainedError], None]) -> None:
    """Stop listening. Safe to call twice."""
    _callbacks._error_sinks.discard(sink)


def describe(error: ContainedError) -> str:
    """One line naming who raised, where the framework caught it, and what."""
    return (
        f"{type(error.exc).__name__}: {error.exc} "
        f"(owner={error.owner}, contained at {error.site})"
    )


def annotate(error: ContainedError) -> BaseException:
    """Attach the owner and containment site to the exception, and return it.

    The exception is raised *as itself* so that a test reads the same whichever
    half of the framework contained it. That leaves nowhere to put the context
    except a note, which exists from Python 3.11; below that the traceback
    already points at the callback's own line, which is the part that matters.
    """
    add_note = getattr(error.exc, "add_note", None)
    if add_note is not None:
        add_note(
            f"nuiitivet: raised inside a callback owned by {error.owner}, and "
            f"contained by the framework at {error.site}. In production this is "
            "logged and the frame carries on; under a test harness it fails the "
            'test instead. Set callback_errors="off" to opt out.'
        )
    return error.exc


def format_report(errors: List[ContainedError]) -> Optional[str]:
    """The teardown / ``warn``-level message for failures nothing raised on."""
    if not errors:
        return None
    lines = [
        f"{len(errors)} callback error(s) were contained by the framework and "
        "would otherwise have gone unnoticed:",
        "",
    ]
    for error in errors[:_MAX_REPORTED_ERRORS]:
        lines.append(f"  {describe(error)}")
    if len(errors) > _MAX_REPORTED_ERRORS:
        lines.append(f"  (+{len(errors) - _MAX_REPORTED_ERRORS} more)")
    lines.extend(
        [
            "",
            "The framework contains these so one broken callback cannot kill a "
            "frame in production. A test that carries on past one is asserting "
            "on a handler that never finished. Fix the callback, or set "
            'callback_errors="off" for a test that asserts on the containment '
            "itself.",
        ]
    )
    return "\n".join(lines)


def report_at_teardown(errors: List[ContainedError], *, level: str, demote: bool) -> None:
    """Report whatever was still queued when the harness closed.

    ``demote`` warns instead of raising. It is set when the test has already
    failed: unlike a leak report, a contained callback error is usually the
    *cause* of that failure, so suppressing it hides the answer -- but raising
    here would replace the failure the author is already reading with a second
    one.
    """
    if level == "off" or not errors:
        return
    if level == "warn" or demote:
        message = format_report(errors)
        if message is not None:
            warnings.warn(message, ContainedCallbackWarning, stacklevel=2)
        return
    if len(errors) > 1:
        # The extras have nowhere to go: only one exception can be raised, and
        # dropping the rest silently is the behaviour this module exists to stop.
        remainder = format_report(errors[1:])
        if remainder is not None:
            warnings.warn(remainder, ContainedCallbackWarning, stacklevel=2)
    raise annotate(errors[0])


__all__ = [
    "CALLBACK_ERROR_LEVELS",
    "ContainedCallbackWarning",
    "annotate",
    "claim",
    "describe",
    "format_report",
    "install_sink",
    "remove_sink",
    "report_at_teardown",
    "resolve_level",
]
