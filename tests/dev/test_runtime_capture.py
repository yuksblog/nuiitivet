"""Tests for the runtime-log capture taps: logging handler, excepthooks, verbose."""

from __future__ import annotations

import logging
import sys
import threading
from typing import Iterator

import pytest

from nuiitivet.common import logging_once
from nuiitivet.common.logging_once import is_log_once_enabled, set_log_once_enabled
from nuiitivet.dev.runtime_capture import RuntimeLogCapture
from nuiitivet.dev.runtime_journal import RuntimeJournal


@pytest.fixture
def capture() -> Iterator[tuple[RuntimeJournal, RuntimeLogCapture]]:
    """Install a capture over a fresh journal, guaranteed to uninstall + reset."""
    logging_once._clear_log_once_keys_for_tests()
    set_log_once_enabled(True)
    journal = RuntimeJournal()
    cap = RuntimeLogCapture(journal)
    sys_hook_before = sys.excepthook
    thread_hook_before = threading.excepthook
    cap.install()
    try:
        yield journal, cap
    finally:
        cap.shutdown()
        # Hooks are restored and de-dup is left enabled.
        assert sys.excepthook is sys_hook_before
        assert threading.excepthook is thread_hook_before
        assert is_log_once_enabled() is True
        logging_once._clear_log_once_keys_for_tests()


def test_captures_warning_records(capture: tuple[RuntimeJournal, RuntimeLogCapture]) -> None:
    journal, _ = capture
    logging.getLogger("demo").warning("watch out %s", "now")
    events = journal.recent()
    assert len(events) == 1
    assert events[0].source == "logging"
    assert events[0].level == "WARNING"
    assert events[0].message == "watch out now"
    assert events[0].logger == "demo"


def test_ignores_info_below_threshold(
    capture: tuple[RuntimeJournal, RuntimeLogCapture],
) -> None:
    journal, _ = capture
    logging.getLogger("demo").info("just fyi")
    assert journal.recent() == []


def test_captures_exception_with_traceback(
    capture: tuple[RuntimeJournal, RuntimeLogCapture],
) -> None:
    journal, _ = capture
    try:
        raise ValueError("kaboom")
    except Exception:
        logging.getLogger("demo").exception("failed")
    event = journal.recent()[-1]
    assert event.exc_type == "ValueError"
    assert event.traceback is not None
    assert "ValueError: kaboom" in event.traceback


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_captures_background_thread_uncaught(
    capture: tuple[RuntimeJournal, RuntimeLogCapture],
) -> None:
    journal, _ = capture

    def boom() -> None:
        raise RuntimeError("thread down")

    t = threading.Thread(target=boom, name="worker-x")
    t.start()
    t.join()

    event = next(e for e in journal.recent() if e.source == "thread")
    assert event.thread == "worker-x"
    assert event.exc_type == "RuntimeError"
    assert "thread down" in event.message


def test_main_thread_excepthook_records_and_chains() -> None:
    # Standalone (no fixture): install over a spy so we can prove the capture
    # records *and* chains to the hook that was live when it installed.
    chained: list[str] = []
    prev = sys.excepthook

    def spy(exc_type, exc_value, tb):  # type: ignore[no-untyped-def]
        chained.append(exc_type.__name__)

    sys.excepthook = spy
    journal = RuntimeJournal()
    cap = RuntimeLogCapture(journal)
    cap.install()
    try:
        try:
            raise IndexError("main uncaught")
        except Exception:
            sys.excepthook(*sys.exc_info())
    finally:
        cap.shutdown()
        sys.excepthook = prev

    assert chained == ["IndexError"]  # chained to the previous hook
    event = journal.recent()[-1]
    assert event.source == "excepthook"
    assert event.exc_type == "IndexError"


def test_excepthook_skips_keyboard_interrupt(
    capture: tuple[RuntimeJournal, RuntimeLogCapture],
) -> None:
    journal, _ = capture
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        sys.excepthook(*sys.exc_info())
    assert all(e.exc_type != "KeyboardInterrupt" for e in journal.recent())


def test_verbose_toggle_controls_dedup(
    capture: tuple[RuntimeJournal, RuntimeLogCapture],
) -> None:
    journal, cap = capture
    assert cap.is_verbose() is False

    # With de-dup on, a repeated once-keyed emission collapses to one record.
    for _ in range(3):
        logging_once.warning_once(logging.getLogger("demo"), "k", "same")
    assert len([e for e in journal.recent() if e.message == "same"]) == 1

    assert cap.set_verbose(True) is True
    assert cap.is_verbose() is True
    for _ in range(3):
        logging_once.warning_once(logging.getLogger("demo"), "k2", "again")
    assert len([e for e in journal.recent() if e.message == "again"]) == 3

    assert cap.set_verbose(False) is False
