"""Regression test: repeated pop during transition should complete.

When ESC/back is requested rapidly, Navigator.pop() can be called multiple times
before the fade transition completes. The desired behavior is to finish the
current transition immediately and apply queued back requests.
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation import Navigator, PageRoute
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def build(self) -> Widget:
        return self


@dataclass(frozen=True, slots=True)
class _Handle:
    cancel_calls: int = 0

    @property
    def is_running(self) -> bool:  # pragma: no cover
        return True

    def pause(self) -> None:  # pragma: no cover
        return

    def resume(self) -> None:  # pragma: no cover
        return

    def cancel(self) -> None:
        object.__setattr__(self, "cancel_calls", self.cancel_calls + 1)


def test_pop_finishes_when_pop_transition_running() -> None:
    nav = Navigator(routes=[PageRoute(builder=_FlagWidget), PageRoute(builder=_FlagWidget)])

    # Simulate an in-flight pop transition without requiring App.animate.
    handle = _Handle()
    nav._transition_handle = handle  # type: ignore[attr-defined]

    class _T:
        kind = "pop"

    nav._transition = _T()  # type: ignore[attr-defined,assignment]

    nav.pop()

    assert handle.cancel_calls == 1
    assert nav.can_pop() is False
