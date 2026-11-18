"""Living functions take the code of an edited source, and living instances of a class are counted.

Both walk the collector's heap, which the GC pacer freezes in a running app: a
frozen object is invisible to ``gc.get_objects()``.
"""

from __future__ import annotations

import enum
import gc
import importlib
import sys
import weakref
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator

import pytest

from nuiitivet.dev.patcher import Unpatchable, count_instances, patch_bodies, runs_source

SOURCE = '''\
def top():
    return 1


def below():
    return 1


def make_counter(step):
    def bump(value):
        return value + step

    return bump


def make_factory(name):
    return lambda: "hello " + name


class Thing:
    def size(self):
        return 1

    @property
    def area(self):
        return 1
'''

Loader = Callable[[str], ModuleType]


@pytest.fixture
def load(tmp_path: Path) -> Iterator[Loader]:
    """Write a module's source under ``tmp_path`` and import it."""
    sys.path.insert(0, str(tmp_path))
    loaded: list[str] = []

    def _load(source: str) -> ModuleType:
        name = f"patched_{len(loaded)}"
        (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
        importlib.invalidate_caches()
        loaded.append(name)
        return importlib.import_module(name)

    try:
        yield _load
    finally:
        sys.path.remove(str(tmp_path))
        for name in loaded:
            sys.modules.pop(name, None)


@pytest.fixture
def frozen_heap() -> Iterator[None]:
    """Thaw the heap the test froze, as the GC pacer freezes a running app's."""
    try:
        yield
    finally:
        gc.unfreeze()


def test_every_living_function_takes_the_new_code(load: Loader) -> None:
    module = load(SOURCE)
    thing = module.Thing()
    held = module.top

    edited = SOURCE.replace("def top():\n    return 1", "def top():\n    return 2").replace(
        "def size(self):\n        return 1", "def size(self):\n        return 2"
    ).replace("def area(self):\n        return 1", "def area(self):\n        return 2")
    patched = patch_bodies(module, SOURCE, edited)

    assert patched == 3
    assert (held(), thing.size(), thing.area) == (2, 2, 2)
    assert module.top is held


def test_a_closure_and_a_lambda_made_before_the_edit_take_the_new_code(load: Loader) -> None:
    module = load(SOURCE)
    bump = module.make_counter(2)
    factory = module.make_factory("root")

    edited = SOURCE.replace("return value + step", "return value + step * 10").replace('"hello "', '"HELLO "')
    patch_bodies(module, SOURCE, edited)

    assert bump(1) == 21
    assert factory() == "HELLO root"


def test_a_function_below_shifted_lines_reports_its_new_line(load: Loader) -> None:
    module = load(SOURCE)

    patch_bodies(module, SOURCE, "# one\n# two\n" + SOURCE)

    assert module.top.__code__.co_firstlineno == 3
    assert module.below.__code__.co_firstlineno == 7


def test_a_body_that_closes_over_other_variables_changes_nothing(load: Loader) -> None:
    source = (
        "def outer():\n    kept = 1\n    other = 2\n\n    def inner():\n        return kept\n\n    return inner\n"
        "\n\ndef plain():\n    return 1\n"
    )
    module = load(source)
    inner = module.outer()

    edited = source.replace("        return kept\n", "        return kept + other\n").replace(
        "def plain():\n    return 1", "def plain():\n    return 2"
    )
    with pytest.raises(Unpatchable):
        patch_bodies(module, source, edited)

    assert (inner(), module.plain()) == (1, 1)


def test_a_source_the_module_does_not_run_is_refused(load: Loader) -> None:
    module = load(SOURCE)
    not_what_ran = SOURCE.replace("def top():\n    return 1", "def top():\n    return 5")

    assert runs_source(module, SOURCE)
    assert not runs_source(module, not_what_ran)
    with pytest.raises(Unpatchable):
        patch_bodies(module, not_what_ran, SOURCE)


def test_a_frozen_function_takes_the_new_code(load: Loader, frozen_heap: None) -> None:
    module = load(SOURCE)
    gc.freeze()

    patch_bodies(module, SOURCE, SOURCE.replace("def top():\n    return 1", "def top():\n    return 2"))

    assert module.top() == 2
    assert gc.get_freeze_count() > 0


class _Service:
    pass


class _Node:
    """Holds itself, so only the cycle collector frees it."""

    def __init__(self) -> None:
        self.me = self


def test_living_instances_are_counted_per_class() -> None:
    services = [_Service(), _Service()]

    assert count_instances([weakref.ref(_Service), weakref.ref(_Node)]) == {_Service: 2}
    del services


def test_an_instance_only_a_cycle_holds_is_not_counted() -> None:
    _Node()

    assert count_instances([weakref.ref(_Node)]) == {}


def test_a_frozen_instance_is_counted(frozen_heap: None) -> None:
    service = _Service()
    gc.freeze()

    assert count_instances([weakref.ref(_Service)]) == {_Service: 1}
    del service


def test_an_enum_member_only_its_class_holds_is_not_counted() -> None:
    class Axis(enum.Enum):
        X = "x"
        Y = "y"

    assert count_instances([weakref.ref(Axis)]) == {}


def test_an_enum_member_something_else_holds_counts_the_members() -> None:
    class Axis(enum.Enum):
        X = "x"
        Y = "y"

    positions = {Axis.X: 0}

    assert count_instances([weakref.ref(Axis)]) == {Axis: 2}
    del positions


def test_a_class_nothing_holds_is_not_counted() -> None:
    def make() -> "weakref.ref[type]":
        class Gone(enum.Enum):
            X = "x"

        return weakref.ref(Gone)

    assert count_instances([make()]) == {}
