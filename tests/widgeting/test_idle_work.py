from time import perf_counter

import pytest

from nuiitivet.widgeting import idle_work
from nuiitivet.widgeting.idle_work import cancel_idle_work, has_idle_work, request_idle_work, run_idle_work


@pytest.fixture(autouse=True)
def no_leftover_work():
    idle_work._tasks.clear()
    yield
    idle_work._tasks.clear()


def test_a_task_runs_until_it_reports_no_more_work():
    runs = []

    def task(deadline: float) -> bool:
        runs.append(deadline)
        return len(runs) < 3

    request_idle_work(task)
    assert run_idle_work(1.0) is True, "one call, work remains"
    assert run_idle_work(1.0) is True
    assert run_idle_work(1.0) is False, "the third call finished it"
    assert not has_idle_work()
    assert len(runs) == 3


def test_a_task_is_registered_once():
    runs = []

    def task(deadline: float) -> bool:
        runs.append(1)
        return False

    request_idle_work(task)
    request_idle_work(task)
    run_idle_work(1.0)
    assert runs == [1]


def test_the_deadline_is_the_budget_from_now():
    seen = []

    def task(deadline: float) -> bool:
        seen.append(deadline - perf_counter())
        return False

    request_idle_work(task)
    run_idle_work(0.05)
    assert 0.0 < seen[0] <= 0.05


def test_a_spent_budget_leaves_the_next_task_for_later():
    runs = []

    def slow(deadline: float) -> bool:
        while perf_counter() < deadline:
            pass
        runs.append("slow")
        return False

    def later(deadline: float) -> bool:
        runs.append("later")
        return False

    request_idle_work(slow)
    request_idle_work(later)
    assert run_idle_work(0.001) is True, "the second task waits for the next wait"
    assert runs == ["slow"]
    assert run_idle_work(0.001) is False
    assert runs == ["slow", "later"]


def test_a_task_that_raises_is_dropped():
    def broken(deadline: float) -> bool:
        raise RuntimeError("boom")

    request_idle_work(broken)
    assert run_idle_work(1.0) is False
    assert not has_idle_work()


def test_cancel_drops_a_task_and_tolerates_an_unknown_one():
    def task(deadline: float) -> bool:
        return True

    request_idle_work(task)
    cancel_idle_work(task)
    cancel_idle_work(task)
    assert not has_idle_work()
