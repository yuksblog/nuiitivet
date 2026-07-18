"""Tests for the reload journal: ring buffer, event schema, thread safety."""

from __future__ import annotations

import threading

import pytest

from nuiitivet.dev.journal import (
    DEFAULT_CAPACITY,
    _TRACEBACK_CAP,
    _TRUNCATION_MARKER,
    ReloadEvent,
    ReloadJournal,
)


def test_record_success_captures_modules_and_seq() -> None:
    journal = ReloadJournal()
    event = journal.record_success(["pkg.a", "pkg.b"], changed=["pkg.a"])

    assert event.outcome == "success"
    assert event.modules == ("pkg.a", "pkg.b")
    assert event.changed == ("pkg.a",)
    assert event.error is None
    assert event.seq == 1
    assert event.timestamp > 0


def test_record_success_defaults_changed_to_empty() -> None:
    journal = ReloadJournal()
    event = journal.record_success(["pkg.a"])
    assert event.changed == ()


def test_seq_is_monotonic_across_records() -> None:
    journal = ReloadJournal()
    first = journal.record_success([])
    second = journal.record_error("boom")
    third = journal.record_success(["m"])

    assert [first.seq, second.seq, third.seq] == [1, 2, 3]


def test_record_error_captures_traceback_and_no_modules() -> None:
    journal = ReloadJournal()
    event = journal.record_error("Traceback...\nValueError: nope")

    assert event.outcome == "error"
    assert event.modules == ()
    assert event.error is not None
    assert "ValueError: nope" in event.error


def test_error_traceback_is_capped() -> None:
    journal = ReloadJournal()
    long_tb = "x" * (_TRACEBACK_CAP + 500)
    event = journal.record_error(long_tb)

    assert event.error is not None
    assert event.error.endswith(_TRUNCATION_MARKER)
    assert len(event.error) == _TRACEBACK_CAP + len(_TRUNCATION_MARKER)


def test_ring_buffer_evicts_oldest() -> None:
    journal = ReloadJournal(capacity=3)
    for i in range(5):
        journal.record_success([f"m{i}"])

    events = journal.recent()
    assert len(events) == 3
    # Oldest two (seq 1, 2) evicted; oldest-first ordering retained.
    assert [e.seq for e in events] == [3, 4, 5]


def test_recent_limit_returns_newest_tail() -> None:
    journal = ReloadJournal()
    for i in range(5):
        journal.record_success([f"m{i}"])

    tail = journal.recent(limit=2)
    assert [e.seq for e in tail] == [4, 5]


def test_recent_non_positive_limit_is_empty() -> None:
    journal = ReloadJournal()
    journal.record_success([])
    assert journal.recent(limit=0) == []
    assert journal.recent(limit=-1) == []


def test_recent_none_limit_returns_all() -> None:
    journal = ReloadJournal()
    journal.record_success([])
    journal.record_success([])
    assert len(journal.recent(None)) == 2


def test_default_capacity() -> None:
    assert ReloadJournal().capacity == DEFAULT_CAPACITY


def test_non_positive_capacity_rejected() -> None:
    with pytest.raises(ValueError, match="capacity must be positive"):
        ReloadJournal(capacity=0)


def test_to_dict_omits_empty_optionals_but_always_emits_changed() -> None:
    success = ReloadEvent(
        seq=1, timestamp=1.0, outcome="success", modules=(), changed=(), error=None
    )
    payload = success.to_dict()
    # ``changed`` is always present (empty == no-op signal); modules/error are not.
    assert payload == {"seq": 1, "timestamp": 1.0, "outcome": "success", "changed": []}
    assert "modules" not in payload and "error" not in payload


def test_to_dict_includes_populated_fields() -> None:
    event = ReloadEvent(
        seq=2, timestamp=1.0, outcome="error", modules=("a",), changed=("a",), error="trace"
    )
    payload = event.to_dict()
    assert payload["modules"] == ["a"]
    assert payload["changed"] == ["a"]
    assert payload["error"] == "trace"


def test_record_error_accepts_changed() -> None:
    journal = ReloadJournal()
    event = journal.record_error("boom", changed=["pkg.a"])
    assert event.changed == ("pkg.a",)


def test_concurrent_records_do_not_lose_events() -> None:
    journal = ReloadJournal(capacity=1000)
    threads = [
        threading.Thread(target=lambda: [journal.record_success([]) for _ in range(50)])
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    events = journal.recent()
    assert len(events) == 400
    # Every seq is unique despite concurrent appends.
    assert len({e.seq for e in events}) == 400
