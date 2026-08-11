"""Public test support for nuiitivet app authors.

This package ships the deterministic test environment: :class:`HarnessClock`
(scheduled callbacks fire on the thread that pumps, never on a timer thread)
and a pytest plugin (``nuiitivet.testing.plugin``, registered via the
``pytest11`` entry point) that installs it and resets the framework's
process-global state around every test.

See ``docs/guide/testing/index.md`` for the guide.
"""

from __future__ import annotations

from .clock import HarnessClock, NuiitivetClockWarning, PendingCallback

__all__ = [
    "HarnessClock",
    "NuiitivetClockWarning",
    "PendingCallback",
]
