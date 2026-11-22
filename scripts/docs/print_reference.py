"""Print the reference of public symbols: what the API pages show, as text.

For a class: its signature, its docstring, and the signature and docstring of
each public member the class itself defines. For a function: its signature and
docstring. Inherited members are left out.

A name is looked up on ``nuiitivet.material``, the root an app imports, and may
go one level down: ``RasterSurface``, ``RasterSurface.draw``, ``worker``.

Run:  python scripts/docs/print_reference.py NAME...
"""

from __future__ import annotations

import inspect
import sys
from typing import Any

import nuiitivet.material as nv


def _signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return ""


def _unwrap(member: Any) -> Any:
    if isinstance(member, (classmethod, staticmethod)):
        return member.__func__
    if isinstance(member, property):
        return member.fget
    return member


def _entry(title: str, obj: Any) -> str:
    doc = inspect.getdoc(obj) or "(no docstring)"
    return f"{title}{_signature(obj)}\n\n{doc}\n"


def reference(name: str) -> str:
    """The reference text of ``name``."""
    obj: Any = nv
    for part in name.split("."):
        obj = getattr(obj, part)
    if not inspect.isclass(obj):
        return _entry(name, _unwrap(obj))
    parts = [_entry(f"class {name}", obj)]
    for member_name, member in vars(obj).items():
        target = _unwrap(member)
        if member_name.startswith("_") or not callable(target) or not inspect.getdoc(target):
            continue
        kind = "property " if isinstance(member, property) else ""
        parts.append(_entry(f"{kind}{name}.{member_name}", target))
    return "\n".join(parts)


def main() -> int:
    if len(sys.argv) < 2:
        print((__doc__ or "").strip())
        return 2
    print(("\n" + "=" * 76 + "\n\n").join(reference(name) for name in sys.argv[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
