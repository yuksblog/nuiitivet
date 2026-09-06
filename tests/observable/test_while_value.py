import asyncio
import logging
from enum import Enum, auto

import pytest

from nuiitivet.observable import Observable


class Mode(Enum):
    EDIT = auto()
    PREVIEW = auto()


def test_sync_sets_on_entry_and_restores_on_exit():
    busy = Observable(False)

    with busy.while_value(True):
        assert busy.value is True
    assert busy.value is False


def test_async_sets_on_entry_and_restores_on_exit():
    busy = Observable(False)

    async def run() -> None:
        async with busy.while_value(True):
            assert busy.value is True

    asyncio.run(run())
    assert busy.value is False


def test_raising_block_still_restores():
    busy = Observable(False)

    with pytest.raises(RuntimeError):
        with busy.while_value(True):
            raise RuntimeError("boom")
    assert busy.value is False


def test_async_raising_block_still_restores():
    busy = Observable(False)

    async def run() -> None:
        async with busy.while_value(True):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert busy.value is False


def test_non_bool_value_type():
    mode = Observable(Mode.EDIT)

    with mode.while_value(Mode.PREVIEW):
        assert mode.value is Mode.PREVIEW
    assert mode.value is Mode.EDIT


def test_subscribers_notified_once_per_transition():
    mode = Observable(Mode.EDIT)
    events: list[Mode] = []
    mode.subscribe(events.append)

    with mode.while_value(Mode.PREVIEW):
        pass

    assert events == [Mode.PREVIEW, Mode.EDIT]


def test_no_notification_when_value_already_equal():
    busy = Observable(True)
    events: list[bool] = []
    busy.subscribe(events.append)

    with busy.while_value(True):
        pass

    assert events == []
    assert busy.value is True


def test_dedup_uses_custom_compare():
    metric = Observable(0.0, compare=lambda old, new: abs(old - new) < 0.5)
    events: list[float] = []
    metric.subscribe(events.append)

    with metric.while_value(0.1):
        pass

    assert events == []


def test_warns_and_restores_when_written_during_block(caplog):
    count = Observable(0)

    with caplog.at_level(logging.WARNING, logger="nuiitivet.observable.value"):
        with count.while_value(1):
            count.value = 5

    assert count.value == 0
    assert any("while_value" in record.message for record in caplog.records)


def test_no_warning_on_undisturbed_block(caplog):
    count = Observable(0)

    with caplog.at_level(logging.WARNING, logger="nuiitivet.observable.value"):
        with count.while_value(1):
            pass

    assert caplog.records == []


def test_works_through_the_descriptor():
    class ViewModel:
        busy = Observable(False)

    vm = ViewModel()
    with vm.busy.while_value(True):
        assert vm.busy.value is True
    assert vm.busy.value is False
