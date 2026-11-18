"""Give living functions the code of an edited source, and count living instances of classes."""

from __future__ import annotations

import gc
import linecache
import weakref
from contextlib import contextmanager
from types import CodeType, FrameType, FunctionType, ModuleType
from typing import Any, Iterable, Iterator


class Unpatchable(Exception):
    """The edited source cannot replace the code of the living functions."""


def patch_bodies(module: ModuleType, old_source: str, new_source: str) -> int:
    """Give every living function defined in ``module``'s file the code ``new_source`` compiles to.

    A function is matched to its new code by its place in ``old_source``: the
    same name, in the same order, under the same enclosing definitions. Closures
    and lambdas made before the call are functions like any other. A function
    whose definition has no counterpart keeps its code.

    Args:
        module: The module whose file was edited.
        old_source: The source the module last ran with.
        new_source: The edited source. It differs from ``old_source`` only
            inside def bodies.

    Returns:
        The number of function objects that took new code.

    Raises:
        Unpatchable: ``old_source`` is not what the module's functions run, or
            an edited body closes over different variables. Nothing was changed.
    """
    filename = str(module.__file__)
    pairs: dict[CodeType, CodeType] = {}
    # dont_inherit: this module's own __future__ flags would change the compiled code.
    _pair_codes(
        compile(old_source, filename, "exec", dont_inherit=True),
        compile(new_source, filename, "exec", dont_inherit=True),
        pairs,
    )
    for function in _own_functions(module):
        if function.__code__.co_filename == filename and function.__code__ not in pairs:
            raise Unpatchable(f"{function.__qualname__} does not run the source on record")

    targets: list[tuple[FunctionType, CodeType]] = []
    with _thawed():
        objects = gc.get_objects()
    for obj in objects:
        if type(obj) is not FunctionType or obj.__code__.co_filename != filename:
            continue
        code = obj.__code__
        new = pairs.get(code)
        if new is None or new == code:
            continue
        if new.co_freevars != code.co_freevars:
            raise Unpatchable(f"{code.co_qualname} closes over {new.co_freevars}, not {code.co_freevars}")
        targets.append((obj, new))
    for function, new in targets:
        function.__code__ = new
    linecache.checkcache(filename)
    return len(targets)


def runs_source(module: ModuleType, source: str) -> bool:
    """Whether the functions ``module`` binds run the code ``source`` compiles to.

    Args:
        module: A loaded module.
        source: A candidate for the source the module ran with.
    """
    filename = str(module.__file__)
    try:
        codes = _nested_codes(compile(source, filename, "exec", dont_inherit=True))
    except SyntaxError:
        return False
    return all(
        function.__code__ in codes
        for function in _own_functions(module)
        if function.__code__.co_filename == filename
    )


def count_instances(classes: Iterable["weakref.ref[type]"]) -> dict[type, int]:
    """Count the living objects whose type is exactly one of ``classes``.

    Unreachable cycles are collected first, so an object nothing holds is not
    counted, and neither is a class nothing holds. An instance held only by its
    own class, such as an Enum member nobody uses, is not counted either.

    Args:
        classes: References to the classes to look for. A subclass's instances
            are not counted.

    Returns:
        The count per class, for the classes with at least one instance.
    """
    with _thawed():
        gc.collect()
        wanted = {cls for ref in classes if (cls := ref()) is not None}
        if not wanted:
            return {}
        found: dict[type, list[object]] = {}
        for obj in gc.get_objects():
            if type(obj) in wanted:
                found.setdefault(type(obj), []).append(obj)
        counts = {cls: _held_from_outside(cls, instances) for cls, instances in found.items()}
        return {cls: count for cls, count in counts.items() if count}


def _held_from_outside(cls: type, instances: list[object]) -> int:
    """How many of ``instances`` something other than ``cls`` holds.

    When one of the instances the class holds is also held from outside, they all count.
    """
    containers: list[Any] = [referent for referent in gc.get_referents(cls) if isinstance(referent, dict)]
    containers += [
        value for owner in list(containers) for value in owner.values() if isinstance(value, (dict, list, tuple, set))
    ]
    own = [obj for container in containers for obj in gc.get_referents(container) if type(obj) is cls]
    if not own:
        return len(instances)
    ours = {id(container) for container in containers} | {id(instances), id(own)}
    outside = [
        referrer
        for referrer in gc.get_referrers(*own)
        if id(referrer) not in ours and not isinstance(referrer, FrameType)
    ]
    return len(instances) if outside else len(instances) - len({id(obj) for obj in own})


def _pair_codes(old: CodeType, new: CodeType, pairs: dict[CodeType, CodeType]) -> None:
    """Map each code object nested in ``old`` to the one in ``new`` with the same name and order."""
    candidates: dict[str, list[CodeType]] = {}
    for const in new.co_consts:
        if isinstance(const, CodeType):
            candidates.setdefault(const.co_name, []).append(const)
    seen: dict[str, int] = {}
    for const in old.co_consts:
        if not isinstance(const, CodeType):
            continue
        index = seen.get(const.co_name, 0)
        seen[const.co_name] = index + 1
        same_name = candidates.get(const.co_name, [])
        if index < len(same_name):
            pairs[const] = same_name[index]
            _pair_codes(const, same_name[index], pairs)


def _nested_codes(code: CodeType) -> set[CodeType]:
    found: set[CodeType] = set()
    for const in code.co_consts:
        if isinstance(const, CodeType):
            found.add(const)
            found |= _nested_codes(const)
    return found


def _own_functions(module: ModuleType) -> list[FunctionType]:
    """The plain functions the module binds, at its top level and in its classes."""
    found: list[FunctionType] = []
    for value in list(vars(module).values()):
        if isinstance(value, FunctionType) and value.__module__ == module.__name__:
            found.append(value)
        elif isinstance(value, type) and value.__module__ == module.__name__:
            found.extend(member for member in vars(value).values() if isinstance(member, FunctionType))
    return found


@contextmanager
def _thawed() -> Iterator[None]:
    """Run with nothing frozen: a frozen object is neither listed nor collected, and the GC pacer freezes the heap."""
    frozen = gc.get_freeze_count() > 0
    if frozen:
        gc.unfreeze()
    try:
        yield
    finally:
        if frozen:
            gc.freeze()
