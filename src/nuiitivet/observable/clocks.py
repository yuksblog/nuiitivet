"""Clock installation, exposed as the ``Clocks`` namespace.

The ``Clocks`` class is a namespace, not something to instantiate — the same
convention as :class:`~nuiitivet.platform.desktop.Desktop`. It scopes the
runtime's clock indirection point: everything nuiitivet schedules (animations,
debounced observables, cross-thread notification delivery) goes through the
installed :class:`~nuiitivet.observable.runtime.Clock`, and swapping it is how
a test takes control of time.
"""

from __future__ import annotations

from .runtime import Clock, get_clock, set_clock


class Clocks:
    """The runtime's installed clock (read and replace)."""

    @staticmethod
    def get() -> Clock:
        """Return the clock currently installed.

        Read the clock through this call every time instead of keeping a
        reference: the backend installs its own clock during ``App.run()``,
        so a saved reference goes stale. Save and restore around a test with
        this.
        """
        return get_clock()

    @staticmethod
    def set(new_clock: Clock) -> None:
        """Install ``new_clock`` as the clock every scheduled callback runs on."""
        set_clock(new_clock)
