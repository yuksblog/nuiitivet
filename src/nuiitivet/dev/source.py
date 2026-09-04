"""Where a widget was constructed.

A designation answers "which widget is this". It stops one step short of
the question that follows it every time: *which line of code built this?* In an
app that passes no ``key=`` -- which is most apps -- the alternative is a chain
of anonymous types twenty levels deep and a grep.

Flutter needs ``--track-widget-creation``, a compile-time transform, because Dart
cannot introspect frames this way at runtime. Python can, and two things here
make it cheap:

* **One chokepoint.** Every widget reaches :meth:`Widget.__init__` -- verified,
  not assumed: of 150 ``Widget`` subclasses, 142 define their own ``__init__``
  and every one of them calls ``super()``.
* **An established idiom.** :func:`nuiitivet.testing._leaks._capture_site`
  already walks raw frames rather than calling ``traceback.extract_stack``, and
  records the reason: ``extract_stack`` builds ``FrameSummary`` objects and reads
  source lines for *every* frame, far too much for a per-construction path.

The wrap is installed by the dev runner and never by the framework itself, so a
production launch pays nothing at all -- not even a flag check on the
construction path. That is the same gating the rest of the bridge uses, and it is
strictly better than needing a special build mode.

**Hot reload composes with this for free.** Sites are captured at construction
and a reload reconstructs the whole tree, so after an edit shifts line numbers
the tree already carries the new ones. There is no invalidation step, and no way
for a site to go stale.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable, Optional, Tuple

import nuiitivet
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)

# Frames climbed before giving up, so a pathological stack cannot turn a
# per-construction path into an unbounded walk.
#
# Not a guess: at 40 this silently lost 9 of 421 nodes in the hero sample, whose
# user frame sat at depth 41-42 -- Material widgets built during layout, several
# composed layers below the ``build()`` that asked for them. The headroom is
# deliberate, and the cost of it is paid only by a widget that has no user frame
# at all, which no real app produces.
_MAX_DEPTH = 150

# User frames kept. Three covered every observed case -- a widget built
# in a helper, called from another helper, called from ``build()`` -- and the
# limit trades payload size against the caller's ability to choose among them.
_MAX_FRAMES = 3

_PACKAGE_ROOT = os.path.dirname(os.path.abspath(nuiitivet.__file__)) + os.sep

#: ``(absolute file, line, function)`` per frame, innermost first.
Frame = Tuple[str, int, str]
Site = Tuple[Frame, ...]

# Sites are shared far more than they are distinct: in the spike, 441 resolved
# widgets held 145 distinct sites, because one helper builds fourteen cards.
# Interning turns a per-widget field into a pointer into a small table.
_interned: dict[Site, Site] = {}

_original: Optional[Callable[..., None]] = None


def _capture() -> Site:
    """Walk out of the framework and keep the first few user frames.

    Frames are collected wherever they occur rather than as one contiguous run:
    a widget built inside a user helper, invoked through a framework callback,
    from another user frame is an ordinary shape (a root factory, a ``ForEach``
    builder), and the far frame is often the more useful of the two.
    """
    try:
        # Skip this function and the __init__ wrapper that called it.
        frame: Any = sys._getframe(2)
    except ValueError:  # pragma: no cover - no caller frame
        return ()
    frames: list[Frame] = []
    for _ in range(_MAX_DEPTH):
        if frame is None:
            break
        filename = frame.f_code.co_filename
        if not filename.startswith(_PACKAGE_ROOT):
            frames.append((filename, frame.f_lineno, frame.f_code.co_name))
            if len(frames) >= _MAX_FRAMES:
                break
        frame = frame.f_back
    site: Site = tuple(frames)
    return _interned.setdefault(site, site)


def site_of(node: Any) -> Site:
    """Return ``node``'s construction site, or ``()`` when it has none.

    Empty for every widget when capture was never installed, and for anything
    built with no user frame within :data:`_MAX_DEPTH` -- which no widget in the
    hero sample now is. Probed by name, like ``visual_offset`` /
    ``is_visually_empty``, so nothing outside dev has to know the attribute
    exists.
    """
    site = getattr(node, "_source_site", None)
    return site if isinstance(site, tuple) else ()


def install() -> None:
    """Start recording construction sites. Idempotent.

    Must run **before the user's entry point builds anything** -- the site is
    only knowable while the constructing frame is still on the stack, so a widget
    built before this lands carries no site and never will.
    """
    global _original
    if _original is not None:
        return
    original = Widget.__init__
    _original = original

    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
        # Recorded before delegating so that a subclass __init__ raising partway
        # through still leaves a site on whatever the debugger is holding.
        self._source_site = _capture()
        original(self, *args, **kwargs)

    Widget.__init__ = __init__  # type: ignore[method-assign]
    logger.debug("dev: widget construction sites are being recorded")


def uninstall() -> None:
    """Stop recording and restore the original ``__init__``. Idempotent."""
    global _original
    if _original is None:
        return
    Widget.__init__ = _original  # type: ignore[method-assign]
    _original = None


def is_installed() -> bool:
    """Whether capture is currently recording."""
    return _original is not None


def payload(node: Any) -> Optional[list[dict[str, Any]]]:
    """``node``'s construction site as JSON, innermost first, or ``None``.

    The innermost frame is flagged ``target``: it is where the widget is
    literally constructed, which is the one place an editor can jump to and the
    same choice Flutter's creation location makes. The rest are kept because a
    rectangle's two readings have an exact analogue here -- "change every tile"
    wants the helper, "change this one" wants the call site, and only the caller
    knows which was meant.

    Paths are relative to the working directory when they sit under it, since
    that is how both the guide and the assistant refer to files.
    """
    site = site_of(node)
    if not site:
        return None
    out: list[dict[str, Any]] = []
    for index, (filename, line, function) in enumerate(site):
        entry: dict[str, Any] = {
            "file": _relative(filename),
            "line": line,
            "function": function,
        }
        if index == 0:
            entry["target"] = True
        out.append(entry)
    return out


def absolute_target(node: Any) -> Optional[tuple[str, int]]:
    """``(absolute path, line)`` an editor should open for ``node``, or ``None``.

    The absolute path, unlike :func:`payload`'s: an editor is launched from the
    dev process and must not depend on where that process was started.
    """
    site = site_of(node)
    if not site:
        return None
    filename, line, _function = site[0]
    return (filename, line)


def _relative(filename: str) -> str:
    try:
        relative = os.path.relpath(filename, os.getcwd())
    except (OSError, ValueError):  # pragma: no cover - different drive on Windows
        return filename
    return filename if relative.startswith(os.pardir) else relative
