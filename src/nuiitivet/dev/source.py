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
import weakref
from typing import Any, Callable, NamedTuple, Optional, Tuple

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


class Frame(NamedTuple):
    """One user frame of a construction site.

    ``column`` through ``end_column`` are the span of the call expression that
    was executing -- the ``Call`` node an editor of the file would find -- as
    ``ast`` reports them: 1-based lines, 0-based UTF-8 byte columns. They are
    ``None`` when the interpreter carries no position table (``-X
    no_debug_ranges``), in which case only the line is known.

    ``direct`` is whether that call constructed the widget itself: nothing but
    the widget's own constructors ran between it and ``Widget.__init__``. A
    label a button builds for itself -- in its constructor, or later during
    layout -- has no user call of its own, and no frame of its site is
    ``direct``.
    """

    file: str
    line: int
    column: Optional[int]
    end_line: Optional[int]
    end_column: Optional[int]
    function: str
    direct: bool = True


#: A widget's construction site: user frames, innermost first.
Site = Tuple[Frame, ...]

# Position tables, one per code object, so a construction pays for decoding
# the table once per function rather than once per widget. Weak: a hot reload
# replaces every user code object, and the old ones must not be kept alive.
_positions: "weakref.WeakKeyDictionary[Any, tuple[tuple[Any, ...], ...]]" = weakref.WeakKeyDictionary()


def _span(frame: Any) -> tuple[int, Optional[int], Optional[int], Optional[int]]:
    """The ``(line, column, end_line, end_column)`` of ``frame``'s current call."""
    code = frame.f_code
    table = _positions.get(code)
    if table is None:
        table = tuple(code.co_positions())
        _positions[code] = table
    index = frame.f_lasti // 2
    if 0 <= index < len(table):
        line, end_line, column, end_column = table[index]
        if line is not None:
            return (int(line), column, end_line, end_column)
    return (int(frame.f_lineno), None, None, None)


# Sites are shared far more than they are distinct: in the spike, 441 resolved
# widgets held 145 distinct sites, because one helper builds fourteen cards.
# Interning turns a per-widget field into a pointer into a small table.
_interned: dict[Site, Site] = {}

_original: Optional[Callable[..., None]] = None


def _capture(widget: Any) -> Site:
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
    # Still inside the widget's own constructor chain, so the next user frame
    # is the call that built it. Another widget's ``__init__`` on the way out
    # -- a button building its label -- ends that: the user call built the
    # button, not the label. A classmethod of the widget's own class
    # (``Column.builder(...)``) is part of the chain: the call naming the
    # factory is the one that built it.
    constructing = True
    for _ in range(_MAX_DEPTH):
        if frame is None:
            break
        code = frame.f_code
        if not code.co_filename.startswith(_PACKAGE_ROOT):
            line, column, end_line, end_column = _span(frame)
            frames.append(Frame(code.co_filename, line, column, end_line, end_column, code.co_name, constructing))
            if len(frames) >= _MAX_FRAMES:
                break
        own = (code.co_name == "__init__" and frame.f_locals.get("self") is widget) or _own_classmethod(frame, widget)
        constructing = constructing and own
        frame = frame.f_back
    site: Site = tuple(frames)
    return _interned.setdefault(site, site)


def _own_classmethod(frame: Any, widget: Any) -> bool:
    """Whether ``frame`` runs a classmethod of ``widget``'s own class, such as ``Column.builder``."""
    code = frame.f_code
    if not code.co_varnames or code.co_varnames[0] != "cls" or frame.f_locals.get("cls") is not type(widget):
        return False
    method = getattr(type(widget), code.co_name, None)
    return getattr(method, "__code__", None) is code


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
        self._source_site = _capture(self)
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
    for index, frame in enumerate(site):
        entry: dict[str, Any] = {
            "file": _relative(frame.file),
            "line": frame.line,
            "function": frame.function,
        }
        if index == 0:
            entry["target"] = True
        out.append(entry)
    return out


def construction_frame(node: Any) -> Optional[Frame]:
    """The call an edit of ``node``'s arguments targets, or ``None``.

    The innermost user frame that constructed the widget directly, outside any
    ``__init__``: inside a constructor the executing call is a
    ``super().__init__(...)``, and the call that names the widget's type -- the
    one a human recognises as building it -- is the frame that called it.
    ``None`` for a widget no user call built -- one its parent made for itself.
    """
    for frame in site_of(node):
        if not frame.direct:
            return None
        if frame.function != "__init__":
            return frame
    return None


def site_owner(node: Any) -> Any:
    """The widget an edit reaches when the pointer is on ``node``.

    ``node`` itself when a user call built it. Otherwise -- a label or icon a
    widget builds for itself, a container a ``build()`` made -- the nearest
    ancestor a user call did build, since an edit to that call is the only
    edit that can reach the pointed-at widget. ``node`` when nothing above it
    has a call either.
    """
    from nuiitivet._interaction.perception import ancestors

    if construction_frame(node) is not None:
        return node
    for ancestor in ancestors(node):
        if construction_frame(ancestor) is not None:
            return ancestor
    return node


def same_call(a: Frame, b: Frame) -> bool:
    """Whether two frames name the same call: same file, line and start column.

    The end is left out on purpose: an edit to the call's own arguments moves
    its end, and the widgets rebuilt from it afterwards must still match.
    """
    return (a.file, a.line, a.column) == (b.file, b.line, b.column)


def widgets_built_at(root: Any, frame: Frame, type_name: Optional[str] = None) -> list[Any]:
    """Every widget in ``root``'s tree whose :func:`construction_frame` is ``frame``.

    One helper builds many widgets, and an edit to its source changes them all;
    this is how an edit finds everything it is about to change. ``type_name``
    narrows the match to widgets of that class, since two chained calls share
    a start. By name, since a reload replaces every class object.
    """
    from nuiitivet._interaction.tree import iter_child_widgets

    found: list[Any] = []
    seen: set[int] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        own = construction_frame(node)
        if own is not None and same_call(own, frame) and (type_name is None or type(node).__name__ == type_name):
            found.append(node)
        stack.extend(reversed(list(iter_child_widgets(node))))
    return found


def absolute_target(node: Any) -> Optional[tuple[str, int]]:
    """``(absolute path, line)`` an editor should open for ``node``, or ``None``.

    The absolute path, unlike :func:`payload`'s: an editor is launched from the
    dev process and must not depend on where that process was started.
    """
    site = site_of(node)
    if not site:
        return None
    return (site[0].file, site[0].line)


def _relative(filename: str) -> str:
    try:
        relative = os.path.relpath(filename, os.getcwd())
    except (OSError, ValueError):  # pragma: no cover - different drive on Windows
        return filename
    return filename if relative.startswith(os.pardir) else relative
