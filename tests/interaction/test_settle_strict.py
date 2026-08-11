"""Tests for ``settle(strict=True)`` -- the error policy a test caller needs.

The default settle swallows a failing layout so a long-lived bridge session
survives a bad frame. A test asserting against the tree that layout failed to
produce would pass on a stale one, so the strict path is the same work with
nothing caught, and with the pass loop bounded rather than fixed.
"""

from __future__ import annotations

from typing import Optional

import pytest

from nuiitivet._interaction.action import LayoutNotConvergedError, settle


class _Root:
    def __init__(self, *, layout_error: Optional[Exception] = None) -> None:
        self.layout_error = layout_error
        self.layouts = 0

    def layout(self, width: int, height: int) -> None:
        self.layouts += 1
        if self.layout_error is not None:
            raise self.layout_error

    def clear_needs_layout(self) -> None:
        pass


class _App:
    def __init__(self, root: _Root) -> None:
        self.root = root
        self.width = 360
        self.height = 240
        self.invalidated = 0

    def invalidate(self) -> None:
        self.invalidated += 1


def _flushes(monkeypatch: pytest.MonkeyPatch, *results: bool) -> None:
    """Make ``flush_size_change_callbacks`` report ``results``, then ``False``.

    Patched at its defining module because ``settle`` imports it per call.
    """
    remaining = list(results)
    monkeypatch.setattr(
        "nuiitivet.widgeting.widget_size_change.flush_size_change_callbacks",
        lambda: remaining.pop(0) if remaining else False,
    )


def test_strict_settle_propagates_a_layout_error() -> None:
    app = _App(_Root(layout_error=RuntimeError("bad constraints")))

    with pytest.raises(RuntimeError, match="bad constraints"):
        settle(app, strict=True)


def test_default_settle_swallows_a_layout_error() -> None:
    app = _App(_Root(layout_error=RuntimeError("bad constraints")))

    settle(app)

    assert app.invalidated == 1


def test_strict_settle_leaves_invalidate_uncalled() -> None:
    app = _App(_Root())

    settle(app, strict=True)

    assert app.invalidated == 0
    assert app.root.layouts == 1


def test_strict_settle_relays_out_until_size_callbacks_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _flushes(monkeypatch, True, True)
    app = _App(_Root())

    settle(app, strict=True, max_passes=3)

    # The first pass, plus one for each round of callbacks that fired.
    assert app.root.layouts == 3


def test_strict_settle_raises_when_the_tree_never_converges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _flushes(monkeypatch, True, True, True, True, True)
    app = _App(_Root())

    with pytest.raises(LayoutNotConvergedError, match="after 2 settle passes"):
        settle(app, strict=True, max_passes=2)


def test_strict_settle_without_a_root_is_a_no_op() -> None:
    app = _App(_Root())
    app.root = None  # type: ignore[assignment]

    settle(app, strict=True)
