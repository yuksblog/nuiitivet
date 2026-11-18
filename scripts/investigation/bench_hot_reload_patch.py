"""Benchmark what one save costs the hot-reload engine on a large module and a large heap.

Both in-place patching and the count of old instances walk the collector's
whole heap, so their cost follows the heap, not the edit. The scene is a module
of 40 classes with 10 methods each, the whole Material surface imported, and
enough ballast to bring the heap to about a million tracked objects. The heap is
frozen, as the GC pacer leaves a running app's.

Three saves are timed, each through ``Reloader.reload()``:

* ``one body``:       one method body changes. Patched in place.
* ``lines shifted``:  a comment is added at the top, so every def below moves by
                      one line. Patched in place; every function takes new code.
* ``outside a body``: a module constant changes. The module is re-executed, and
                      the instances of its old classes are counted.

Run:  python scripts/investigation/bench_hot_reload_patch.py [--ballast N] [--rounds N]
"""

from __future__ import annotations

import argparse
import gc
import importlib
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import nuiitivet.material as nv  # noqa: E402
from nuiitivet.dev.patcher import count_instances  # noqa: E402
from nuiitivet.dev.reloader import Reloader  # noqa: E402

CLASSES = 40
METHODS = 10


def _module_source(scale: int) -> str:
    lines = [f"SCALE = {scale}\n"]
    for c in range(CLASSES):
        lines.append(f"\n\nclass Widget{c}:\n")
        for m in range(METHODS):
            lines.append(
                f"    def method{m}(self, value: int) -> int:\n"
                f"        total = value\n"
                f"        for i in range({m}):\n"
                f"            total += i * {c}\n"
                f"        return total\n\n"
            )
    return "".join(lines)


def _timed(action: Callable[[], object]) -> float:
    started = time.perf_counter()
    action()
    return (time.perf_counter() - started) * 1000.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ballast", type=int, default=400_000, help="dicts kept alive, each holding a list")
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args()

    for name in dir(nv):  # import every lazy module: the heap of a real app
        getattr(nv, name)
    ballast = [{"index": i, "items": [i]} for i in range(args.ballast)]

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        path = root / "bench_big.py"
        source = _module_source(1)
        path.write_text(source, encoding="utf-8")
        sys.path.insert(0, str(root))
        module = importlib.import_module("bench_big")
        living = [getattr(module, f"Widget{c}")() for c in range(CLASSES)]
        reloader = Reloader(root)
        reloader.track()
        gc.freeze()

        print(f"defs: {CLASSES * METHODS}, lines: {source.count(chr(10))}, tracked objects: {len(gc.get_objects())}")
        print(f"frozen objects: {gc.get_freeze_count()}, ballast: {len(ballast)}")

        times: dict[str, list[float]] = {"one body": [], "lines shifted": [], "outside a body": []}
        for round_index in range(args.rounds):
            source = source.replace("total += i * 7\n", f"total += i * 7 + {round_index + 1}\n", 1)
            path.write_text(source, encoding="utf-8")
            times["one body"].append(_timed(reloader.reload))
            assert reloader.last.patched == ["bench_big"], reloader.last
            source = source.replace(f"total += i * 7 + {round_index + 1}\n", "total += i * 7\n", 1)

            source = "# shifted\n" + source
            path.write_text(source, encoding="utf-8")
            times["lines shifted"].append(_timed(reloader.reload))
            assert reloader.last.patched == ["bench_big"], reloader.last

            source = source.replace(f"SCALE = {round_index + 1}\n", f"SCALE = {round_index + 2}\n", 1)
            path.write_text(source, encoding="utf-8")

            def reexecute_and_count() -> None:
                result = reloader.reload()
                assert result.reloaded == ["bench_big"], result
                count_instances(result.replaced["bench_big"])

            times["outside a body"].append(_timed(reexecute_and_count))

        gc.unfreeze()
        sys.path.remove(str(root))
        del living

    print(f"\n{'save':<16}{'min ms':>10}{'median ms':>12}")
    for label, samples in times.items():
        ordered = sorted(samples)
        print(f"{label:<16}{ordered[0]:>10.1f}{ordered[len(ordered) // 2]:>12.1f}")


if __name__ == "__main__":
    main()
