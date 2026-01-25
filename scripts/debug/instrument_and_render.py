"""Instrument widget paint/preferred_size calls and run the sample.

This script monkey-patches common widget classes to log CALL/RETURN for
`paint` and `preferred_size` (and ForEach._rebuild), then executes the
sample at `src/samples/my_widget.py` as `__main__` to capture runtime
behavior and produce a headless PNG.
"""

from __future__ import annotations

import functools
import importlib
import runpy
from typing import Iterable, Tuple


def safe_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception as e:
        print(f"WARN: could not import {module_name}: {e}", flush=True)
        return None


def wrap_method(cls, name: str) -> bool:
    orig = getattr(cls, name, None)
    if not callable(orig):
        return False

    @functools.wraps(orig)
    def wrapper(self, *args, **kwargs):
        clsname = getattr(self.__class__, "__name__", str(type(self)))
        print(f"CALL {clsname}.{name} id={id(self)} args={args} kwargs={kwargs}", flush=True)
        try:
            result = orig(self, *args, **kwargs)
            print(f"RETURN {clsname}.{name} id={id(self)} -> {result!r}", flush=True)
            return result
        except Exception as exc:  # pragma: no cover - debugging helper
            print(f"EXC {clsname}.{name} id={id(self)} -> {exc}", flush=True)
            raise

    setattr(cls, name, wrapper)
    print(f"Wrapped {cls.__module__}.{cls.__name__}.{name}", flush=True)
    return True


def apply_wraps(targets: Iterable[Tuple[str, str, Iterable[str]]]) -> None:
    for module_name, cls_name, methods in targets:
        mod = safe_import(module_name)
        if mod is None:
            continue
        cls = getattr(mod, cls_name, None)
        if cls is None:
            print(f"WARN: {module_name} has no attribute {cls_name}", flush=True)
            continue
        for m in methods:
            ok = wrap_method(cls, m)
            if not ok:
                print(f"WARN: could not wrap {cls_name}.{m}", flush=True)


def wrap_evaluate_build() -> None:
    mod = safe_import("nuiitivet.widgeting.widget")
    if mod is None:
        return
    cls = getattr(mod, "Widget", None)
    if cls is None:
        return
    orig = getattr(cls, "evaluate_build", None)
    if not callable(orig):
        return

    def wrapper(self, *args, **kwargs):
        print(
            f"CALL evaluate_build on {self.__class__.__name__} id={id(self)}",
            flush=True,
        )
        res = orig(self, *args, **kwargs)
        rn = res.__class__.__name__ if res is not None else None
        print(f"RETURN evaluate_build on {self.__class__.__name__} -> {rn}", flush=True)
        # If a Widget subtree was returned, attempt a shallow dump
        try:
            if res is not None and hasattr(res, "children"):
                print(f"[DUMP] evaluate_build result children for {res.__class__.__name__}", flush=True)
                try:
                    for c in getattr(res, "children"):
                        print(f"  - {c.__class__.__name__} id={id(c)}", flush=True)
                except Exception:
                    print("  - <could not iterate children>", flush=True)
        except Exception:
            pass
        return res

    setattr(cls, "evaluate_build", wrapper)
    print("Wrapped Widget.evaluate_build", flush=True)


TARGETS = [
    ("nuiitivet.widgeting.widget", "Widget", ("paint", "preferred_size")),
    ("nuiitivet.layout", "Column", ("preferred_size", "paint")),
    ("nuiitivet.layout", "Row", ("preferred_size", "paint")),
    ("nuiitivet.layout", "Container", ("preferred_size", "paint")),
    ("nuiitivet.layout.for_each", "ForEach", ("_rebuild", "preferred_size", "paint")),
    ("nuiitivet.layout.scroller", "Scroller", ("preferred_size", "paint")),
    ("nuiitivet.widgets.text", "Text", ("preferred_size", "paint")),
    ("nuiitivet.widgets.icon", "Icon", ("preferred_size", "paint")),
    ("nuiitivet.material.selection_controls", "Checkbox", ("preferred_size", "paint")),
    ("nuiitivet.material.buttons", "FilledButton", ("preferred_size", "paint")),
    ("nuiitivet.material.buttons", "ElevatedButton", ("preferred_size", "paint")),
    ("nuiitivet.material.buttons", "TextButton", ("preferred_size", "paint")),
    ("nuiitivet.material.buttons", "OutlinedButton", ("preferred_size", "paint")),
    ("nuiitivet.material.buttons", "FloatingActionButton", ("preferred_size", "paint")),
]


def main() -> int:
    print("Instrument script started", flush=True)
    apply_wraps(TARGETS)

    # Execute the sample as __main__ so its top-level behavior runs here.
    sample_path = "src/samples/my_widget.py"
    print(f"Running sample: {sample_path}", flush=True)
    try:
        ns = runpy.run_path(sample_path, run_name="__main__")
        # If the sample module created an `app` variable, force a headless
        # render to ensure evaluate_build() runs and the built tree is
        # materialized for inspection.
        app_obj = ns.get("app")
        if app_obj is not None and hasattr(app_obj, "render_to_png"):
            try:
                print("Invoking app.render_to_png('out_widget_restored.png')", flush=True)
                app_obj.render_to_png("out_widget_restored.png")
                print("WROTE out_widget_restored.png", flush=True)
            except Exception as e:
                print(f"render_to_png failed: {e}", flush=True)
    except SystemExit as se:
        # sample may call SystemExit after writing PNG
        print(f"Sample exited: {se}", flush=True)
    except Exception as exc:  # pragma: no cover - this is diagnostic
        print(f"Sample raised: {exc}", flush=True)
        raise
    print("Instrument script finished", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
