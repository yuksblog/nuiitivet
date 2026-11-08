"""Work the frame loop does while it would otherwise wait."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable, List

from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)

# Called with the deadline, a ``perf_counter()`` value; returns ``True`` while
# it has more to do, ``False`` once it is finished.
IdleTask = Callable[[float], bool]

_tasks: List[IdleTask] = []


def request_idle_work(task: IdleTask) -> None:
    """Have the loop call ``task`` before it waits, until the task returns ``False``.

    A task already registered is registered once.

    Args:
        task: Called with the deadline; does a slice of work and returns
            whether more remains.
    """
    if task not in _tasks:
        _tasks.append(task)


def cancel_idle_work(task: IdleTask) -> None:
    """Drop ``task`` from the work the loop does; nothing when it is not registered."""
    try:
        _tasks.remove(task)
    except ValueError:
        pass


def has_idle_work() -> bool:
    """Whether any task is waiting for the loop."""
    return bool(_tasks)


def run_idle_work(budget: float) -> bool:
    """Run the registered tasks until ``budget`` seconds have passed.

    Args:
        budget: Seconds the tasks may use together.

    Returns:
        Whether work remains after the budget.
    """
    deadline = perf_counter() + max(0.0, float(budget))
    for task in list(_tasks):
        if perf_counter() >= deadline:
            break
        try:
            more = task(deadline)
        except Exception:
            exception_once(logger, f"idle_work_task_exc:{task!r}", "Idle work raised; the task is dropped")
            more = False
        if not more:
            cancel_idle_work(task)
    return bool(_tasks)
