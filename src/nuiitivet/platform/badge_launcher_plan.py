"""The D-Bus-free half of the Linux badge backend.

Which app the launcher entry names and what it carries, computed without a
bus, so it runs and is tested on every platform. ``badge_launcher`` puts the
result on the wire. A variant is written as a ``(signature, value)`` pair.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

Variant = Tuple[str, Any]


def desktop_entry_uri(environ: Mapping[str, str], pid: int, parent_pid: int, program: str) -> str:
    """Return the ``application://`` URI a launcher knows this app by.

    Args:
        environ: The process environment.
        pid: This process's id.
        parent_pid: The id of the process that started this one.
        program: The path the app was started as (``sys.argv[0]``).

    Returns:
        The desktop entry the launcher started this process or its parent
        from, or else the entry named after ``program``: ``app.py`` gives
        ``app.desktop``.
    """
    launched = environ.get("GIO_LAUNCHED_DESKTOP_FILE", "")
    # Every descendant inherits the variable: an app started from a terminal would otherwise badge the terminal.
    # The parent counts as this app: a one-file bundle and a wrapper script run the app as their child.
    if launched and environ.get("GIO_LAUNCHED_DESKTOP_FILE_PID") in (str(pid), str(parent_pid)):
        return f"application://{Path(launched).name}"
    return f"application://{Path(program).stem}.desktop"


def launcher_properties(label: str) -> Optional[Dict[str, Variant]]:
    """Return the LauncherEntry properties that show ``label``.

    Args:
        label: The badge text; empty for no badge.

    Returns:
        The count and its visibility, or ``None`` for a text that is not a
        count: a launcher entry carries a number only.
    """
    if not label:
        return {"count": ("x", 0), "count-visible": ("b", False)}
    if not (label.isascii() and label.isdigit()):
        return None
    return {"count": ("x", int(label)), "count-visible": ("b", True)}
