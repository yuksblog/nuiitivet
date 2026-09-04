"""Tests for the once-per-process log helpers: de-dup, the global toggle, and
the per-exception keying used by the callback boundary."""

from __future__ import annotations

import logging
from typing import Iterator

import pytest

from nuiitivet.common import logging_once
from nuiitivet.common.logging_once import (
    exception_once,
    exception_once_per_exc,
    is_log_once_enabled,
    set_log_once_enabled,
    warning_once,
)


@pytest.fixture(autouse=True)
def _reset_log_once_state() -> Iterator[None]:
    """Keep the process-global de-dup state from leaking between tests."""
    logging_once._clear_log_once_keys_for_tests()
    set_log_once_enabled(True)
    try:
        yield
    finally:
        logging_once._clear_log_once_keys_for_tests()
        set_log_once_enabled(True)


def _logger() -> logging.Logger:
    return logging.getLogger("nuiitivet.tests.logging_once")


def test_warning_once_emits_only_first_for_a_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warning_once(_logger(), "dup-key", "first")
        warning_once(_logger(), "dup-key", "second")
    assert [r.getMessage() for r in caplog.records] == ["first"]


def test_disabling_toggle_emits_every_time(caplog: pytest.LogCaptureFixture) -> None:
    set_log_once_enabled(False)
    assert is_log_once_enabled() is False
    with caplog.at_level(logging.WARNING):
        warning_once(_logger(), "dup-key", "a")
        warning_once(_logger(), "dup-key", "b")
    assert [r.getMessage() for r in caplog.records] == ["a", "b"]


def test_reenabling_starts_fresh(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        set_log_once_enabled(False)
        warning_once(_logger(), "dup-key", "while-off")
        set_log_once_enabled(True)
        caplog.clear()
        # The key was never recorded while disabled, so the first post-enable
        # call still emits (and the second is then suppressed).
        warning_once(_logger(), "dup-key", "first-after")
        warning_once(_logger(), "dup-key", "second-after")
    assert [r.getMessage() for r in caplog.records] == ["first-after"]


def test_exception_once_per_exc_distinguishes_by_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def raise_value() -> None:
        raise ValueError("v")

    def raise_key() -> None:
        raise KeyError("k")

    with caplog.at_level(logging.ERROR):
        for _ in range(2):
            try:
                raise_value()
            except Exception:
                exception_once_per_exc(_logger(), "site", "boom")
        try:
            raise_key()
        except Exception:
            exception_once_per_exc(_logger(), "site", "boom")

    # Same site + same exception collapses to one; a different exception at the
    # same site surfaces as a second record.
    exc_types = [r.exc_info[0] for r in caplog.records if r.exc_info]
    assert exc_types == [ValueError, KeyError]


def test_exception_once_still_collapses_identical_repeats(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        for _ in range(3):
            try:
                raise RuntimeError("same")
            except Exception:
                exception_once(_logger(), "fixed-key", "boom")
    assert len(caplog.records) == 1
