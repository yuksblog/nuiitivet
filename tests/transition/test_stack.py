from __future__ import annotations

from nuiitivet.transition.stack import EntryLifecycle, StackRuntime


class _Element:
    def __init__(self) -> None:
        self.dispose_count = 0

    def dispose(self) -> None:
        self.dispose_count += 1


def test_push_sets_entering_then_active() -> None:
    base = _Element()
    runtime = StackRuntime(initial=[base], pinned=[base])
    element = _Element()

    entry = runtime.push(element)
    assert entry.state is EntryLifecycle.ENTERING

    changed = runtime.mark_active(element)
    assert changed is True
    assert runtime.entries[-1].state is EntryLifecycle.ACTIVE


def test_begin_pop_sets_exiting_and_complete_exit_disposes() -> None:
    base = _Element()
    element = _Element()
    runtime = StackRuntime(initial=[base, element], pinned=[base])

    popped = runtime.begin_pop()
    assert popped is element
    assert runtime.entries[-1].state is EntryLifecycle.EXITING

    completed = runtime.complete_exit(element)
    assert completed is True
    assert element.dispose_count == 1
    assert len(runtime.elements) == 1
    assert runtime.top() is base


def test_pinned_element_cannot_pop() -> None:
    base = _Element()
    runtime = StackRuntime(initial=[base], pinned=[base])

    assert runtime.can_pop(min_elements=1) is False
    assert runtime.begin_pop() is None


def test_remove_marks_exit_and_disposes() -> None:
    base = _Element()
    element = _Element()
    runtime = StackRuntime(initial=[base, element], pinned=[base])

    removed = runtime.remove(element)
    assert removed is True
    assert element.dispose_count == 1
    assert len(runtime.elements) == 1
    assert runtime.top() is base
