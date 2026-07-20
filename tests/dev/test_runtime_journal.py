"""Tests for the runtime journal: ring buffer, event schema, capping, threads."""

from __future__ import annotations

import threading

import pytest

from nuiitivet.dev.runtime_journal import (
    DEFAULT_CAPACITY,
    _MESSAGE_CAP,
    _MESSAGE_TRUNCATION_MARKER,
    _TRACEBACK_CAP,
    _TRUNCATION_MARKER,
    RuntimeEvent,
    RuntimeJournal,
)


def test_record_captures_fields_and_seq() -> None:
    journal = RuntimeJournal()
    event = journal.record(
        level="ERROR",
        source="logging",
        thread="MainThread",
        message="boom",
        logger="pkg.mod",
        exc_type="ValueError",
        traceback="Traceback...\nValueError: boom",
    )
    assert event.level == "ERROR"
    assert event.source == "logging"
    assert event.thread == "MainThread"
    assert event.message == "boom"
    assert event.logger == "pkg.mod"
    assert event.exc_type == "ValueError"
    assert event.seq == 1
    assert event.timestamp > 0


def test_seq_is_monotonic_across_records() -> None:
    journal = RuntimeJournal()
    a = journal.record(level="WARNING", source="logging", thread="t", message="a")
    b = journal.record(level="ERROR", source="thread", thread="t", message="b")
    assert [a.seq, b.seq] == [1, 2]


def test_message_is_capped() -> None:
    journal = RuntimeJournal()
    event = journal.record(
        level="WARNING", source="logging", thread="t", message="x" * (_MESSAGE_CAP + 100)
    )
    assert event.message.endswith(_MESSAGE_TRUNCATION_MARKER)
    assert len(event.message) == _MESSAGE_CAP + len(_MESSAGE_TRUNCATION_MARKER)


def test_traceback_is_capped() -> None:
    journal = RuntimeJournal()
    event = journal.record(
        level="ERROR",
        source="excepthook",
        thread="t",
        message="boom",
        traceback="y" * (_TRACEBACK_CAP + 100),
    )
    assert event.traceback is not None
    assert event.traceback.endswith(_TRUNCATION_MARKER)
    assert len(event.traceback) == _TRACEBACK_CAP + len(_TRUNCATION_MARKER)


def test_to_dict_omits_absent_optionals() -> None:
    event = RuntimeEvent(
        seq=1, timestamp=1.0, level="WARNING", source="logging", thread="t", message="hi"
    )
    payload = event.to_dict()
    assert payload == {
        "seq": 1,
        "timestamp": 1.0,
        "level": "WARNING",
        "source": "logging",
        "thread": "t",
        "message": "hi",
    }
    assert "logger" not in payload
    assert "exc_type" not in payload
    assert "traceback" not in payload


def test_to_dict_includes_populated_optionals() -> None:
    event = RuntimeEvent(
        seq=2,
        timestamp=1.0,
        level="ERROR",
        source="thread",
        thread="worker",
        message="boom",
        logger="pkg",
        exc_type="RuntimeError",
        traceback="trace",
    )
    payload = event.to_dict()
    assert payload["logger"] == "pkg"
    assert payload["exc_type"] == "RuntimeError"
    assert payload["traceback"] == "trace"


def test_ring_buffer_evicts_oldest() -> None:
    journal = RuntimeJournal(capacity=3)
    for i in range(5):
        journal.record(level="WARNING", source="logging", thread="t", message=f"m{i}")
    events = journal.recent()
    assert [e.seq for e in events] == [3, 4, 5]


def test_recent_limit_and_bounds() -> None:
    journal = RuntimeJournal()
    for i in range(5):
        journal.record(level="WARNING", source="logging", thread="t", message=f"m{i}")
    assert [e.seq for e in journal.recent(limit=2)] == [4, 5]
    assert journal.recent(limit=0) == []
    assert journal.recent(limit=-1) == []
    assert len(journal.recent(None)) == 5


def test_default_capacity_and_rejects_non_positive() -> None:
    assert RuntimeJournal().capacity == DEFAULT_CAPACITY
    with pytest.raises(ValueError, match="capacity must be positive"):
        RuntimeJournal(capacity=0)


def test_concurrent_records_keep_unique_seqs() -> None:
    journal = RuntimeJournal(capacity=1000)
    threads = [
        threading.Thread(
            target=lambda: [
                journal.record(level="WARNING", source="logging", thread="t", message="x")
                for _ in range(50)
            ]
        )
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    events = journal.recent()
    assert len(events) == 400
    assert len({e.seq for e in events}) == 400
