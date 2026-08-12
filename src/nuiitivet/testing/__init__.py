"""Public test support for nuiitivet app authors.

Three levels, one vocabulary:

============  =========================  =============================
Level         Unit of test               Entry point
============  =========================  =============================
Unit          one widget                 :func:`mount`
Integration   a screen: state + tree     :class:`AppHarness`
E2E           the running process        the dev bridge (already shipped)
============  =========================  =============================

Targeting is by ``key`` / ``label`` at every level, and the action verbs are the
dev bridge's one for one, so what an author learns writing E2E carries down
unchanged. Asserting on an ``Observable`` the test already holds, or on a node's
presence, is the front door; geometry is reachable and deliberately not as
convenient.

This package also ships the deterministic test environment -- :class:`HarnessClock`
and a pytest plugin (``nuiitivet.testing.plugin``, registered via the ``pytest11``
entry point) that installs it and resets the framework's process-global state
around every test.

See ``docs/guide/testing/`` for the guide.
"""

from __future__ import annotations

from ._contained import ContainedCallbackWarning
from ._leaks import SubscriptionLeakWarning, track_subscriptions
from .clock import HarnessClock, NuiitivetClockWarning, PendingCallback
from .errors import (
    ActionNotHandledError,
    IdleTimeoutError,
    LayoutNotConvergedError,
    StaleNodeError,
    SubscriptionLeakError,
    TargetNotFoundError,
    TargetNotVisibleError,
    UnschedulableAsyncWork,
    WaitTimeoutError,
)
from .harness import AppHarness
from .mount import Invalidation, WidgetHost, mount
from .node import Node

__all__ = [
    "ActionNotHandledError",
    "AppHarness",
    "ContainedCallbackWarning",
    "HarnessClock",
    "IdleTimeoutError",
    "Invalidation",
    "LayoutNotConvergedError",
    "Node",
    "NuiitivetClockWarning",
    "PendingCallback",
    "StaleNodeError",
    "SubscriptionLeakError",
    "SubscriptionLeakWarning",
    "TargetNotFoundError",
    "TargetNotVisibleError",
    "UnschedulableAsyncWork",
    "WaitTimeoutError",
    "WidgetHost",
    "mount",
    "track_subscriptions",
]
