"""Span surgery on the file that built a widget.

Layout mode's edits are written here. Each one is a handful of character
spans replaced in one file -- the value of a ``width=`` keyword, or a keyword
inserted after the last argument -- located by re-parsing the file with
:mod:`ast` and matching the call at the widget's construction site. Nothing
around a span is touched, so the human's formatting survives every edit.

The file is re-read and re-parsed for every edit rather than cached: a hand
edit or an earlier edit of this mode may have shifted every line since the
widget was built, and the site a reload captured is only exact against the file
as it is now.
"""

from __future__ import annotations

import ast
import logging
import os
import pathlib
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Union

from .source import Frame, widgets_built_at

logger = logging.getLogger(__name__)

#: A landing value as it is written: a pixel count, ``"auto"``, or ``"wt"``.
Value = Union[int, str]

#: Logical pixels within which a drag lands on ``auto`` or ``wt`` rather than
#: on the integer under the pointer. Wide enough to hit by hand, narrow enough
#: that the integers it hides are ones nobody wants written.
SNAP_BAND = 6.0


@dataclass(frozen=True)
class SpanEdit:
    """Replace ``[start, end)`` of a file's text -- character offsets -- with ``text``.

    ``replaces`` is the text expected at the span before the edit, which is what
    lets an inverse edit refuse to apply when the file has moved on.
    """

    start: int
    end: int
    text: str
    replaces: str = ""


@dataclass(frozen=True)
class Refusal:
    """Why a drag could not become one deterministic edit."""

    reason: str


@dataclass
class Edit:
    """One edit layout mode wrote, with everything undo and the badge need."""

    kind: str
    file: str
    site: Frame
    parent_layout: str
    #: What layout gave before, in pixels, per axis.
    before: dict[str, int]
    #: The landing value written, per keyword.
    after: dict[str, Value]
    #: What the ghost predicted layout will give, in pixels, per axis.
    expected: dict[str, int]
    #: Widgets built from the site when the edit was made.
    instances: int
    spans: tuple[SpanEdit, ...]
    #: The class name of the widget resized, which tells its instances apart
    #: from the children it builds for itself at the same site.
    widget: str = ""
    inverse: tuple[SpanEdit, ...] = field(default_factory=tuple)


def locate_call(text: str, site: Frame) -> Optional[ast.Call]:
    """The ``Call`` node at ``site`` in ``text``, or ``None``.

    Matched on the full span, not the start alone: ``Text("a").modifier(m)``
    holds two calls starting at one column, and each builds a widget of its own.
    Without a recorded column the line's only call is accepted; two calls on
    the line cannot be told apart, and neither is guessed.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    on_line: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or node.lineno != site.line:
            continue
        if site.column is None:
            on_line.append(node)
        elif (node.col_offset, node.end_lineno, node.end_col_offset) == (
            site.column,
            site.end_line,
            site.end_column,
        ):
            return node
    if site.column is None and len(on_line) == 1:
        return on_line[0]
    return None


def plan_keywords(text: str, site: Frame, changes: Mapping[str, Value]) -> Union[tuple[SpanEdit, ...], Refusal]:
    """The spans that set each keyword in ``changes`` on the call at ``site``.

    A literal value is replaced in place; an absent keyword is inserted after
    the last argument. A value that is not a literal -- a name, an attribute,
    an expression -- is refused, and so is a call that cannot be located.
    """
    call = locate_call(text, site)
    if call is None:
        return Refusal(f"the call at {os.path.basename(site.file)}:{site.line} could not be found")
    offsets = _Offsets(text)
    keywords = {kw.arg: kw for kw in call.keywords if kw.arg is not None}
    splat = next((kw for kw in call.keywords if kw.arg is None), None)
    edits: list[SpanEdit] = []
    for name, value in changes.items():
        keyword = keywords.get(name)
        if keyword is None:
            if splat is not None:
                return Refusal(f"{name} may come through **{_segment(text, splat.value)}")
            at, prefix = _insertion_point(text, call, offsets)
            edits.append(SpanEdit(at, at, f"{prefix}{name}={_spell(value, None)}"))
            continue
        literal = keyword.value
        if not _is_literal(literal):
            return Refusal(f"{name} is bound to {_segment(text, literal)}")
        start = offsets.of(literal.lineno, literal.col_offset)
        end = offsets.of(literal.end_lineno or literal.lineno, literal.end_col_offset or 0)
        old = text[start:end]
        edits.append(SpanEdit(start, end, _spell(value, old), replaces=old))
    return tuple(edits)


def apply_spans(text: str, spans: Iterable[SpanEdit]) -> tuple[str, tuple[SpanEdit, ...]]:
    """Apply ``spans`` to ``text``; return the new text and the edits that undo it.

    Spans are applied front to back with a running shift, so several at one
    offset land in the order given.
    """
    ordered = sorted(enumerate(spans), key=lambda item: (item[1].start, item[0]))
    shift = 0
    out = text
    inverse: list[SpanEdit] = []
    for _index, span in ordered:
        start, end = span.start + shift, span.end + shift
        old = out[start:end]
        out = out[:start] + span.text + out[end:]
        inverse.append(SpanEdit(start, start + len(span.text), old, replaces=span.text))
        shift += len(span.text) - (end - start)
    return out, tuple(inverse)


def still_applies(text: str, spans: Iterable[SpanEdit]) -> bool:
    """Whether every span still finds the text it expects to replace."""
    return all(text[span.start : span.end] == span.replaces for span in spans)


class EditLog:
    """The edits layout mode wrote this process, newest last, and what each did.

    One per dev runner, shared by every window's mode. ``undo`` reverts the
    newest edit only if the text it wrote is still at its spans; ``outcome``
    holds what the reload after an edit reported, for the mode's badge. All
    methods run on the UI thread.
    """

    def __init__(self) -> None:
        self._edits: list[Edit] = []
        # The edit whose reload has not landed yet, and whether it was an undo,
        # so the check after the reload knows which sizes to expect.
        self._pending: Optional[tuple[Edit, bool]] = None
        self.outcome: Optional[str] = None
        # Told after every reload that landed, edit or not: a mode holding
        # widgets of the old tree has to re-resolve them. Weak, so a closed
        # window's mode does not outlive it here.
        self._reloaded: list[weakref.WeakMethod[Callable[[], None]]] = []

    @property
    def pending(self) -> Optional[Edit]:
        """The edit written but not yet reloaded, or ``None``."""
        return self._pending[0] if self._pending is not None else None

    def on_reloaded(self, method: Callable[[], None]) -> None:
        """Call ``method`` -- a bound method -- after each reload lands."""
        self._reloaded.append(weakref.WeakMethod(method))  # type: ignore[arg-type]

    def _notify_reloaded(self) -> None:
        for ref in list(self._reloaded):
            method = ref()
            if method is None:
                self._reloaded.remove(ref)
                continue
            try:
                method()
            except Exception:
                logger.debug("edit log: a reload listener failed", exc_info=True)

    def apply(self, edit: Edit) -> None:
        """Write ``edit`` to its file and remember how to undo it."""
        text = _read(edit.file)
        new_text, inverse = apply_spans(text, edit.spans)
        edit.inverse = inverse
        _write(edit.file, new_text)
        self._edits.append(edit)
        self._pending = (edit, False)
        self.outcome = None

    def undo(self) -> tuple[Optional[Edit], str]:
        """Revert the newest edit. Returns it and a one-line notice.

        Refused, with the edit left on the stack, when the written text is no
        longer at its spans -- a hand edit has moved it, and applying the
        inverse there would corrupt whatever replaced it.
        """
        if not self._edits:
            return (None, "nothing to undo")
        edit = self._edits[-1]
        text = _read(edit.file)
        if not still_applies(text, edit.inverse):
            return (None, f"cannot undo: {os.path.basename(edit.file)} changed under the edit")
        new_text, _forward = apply_spans(text, edit.inverse)
        _write(edit.file, new_text)
        self._edits.pop()
        self._pending = (edit, True)
        self.outcome = None
        return (edit, "undoing " + _summary(edit))

    def after_reload(self, roots: Iterable[Any]) -> Optional[str]:
        """Check the pending edit against the rebuilt trees; return a badge or ``None``.

        Called after every reload that landed, so the listeners hear about
        hand edits too.
        """
        pending, self._pending = self._pending, None
        outcome = self._check(pending, list(roots)) if pending is not None else None
        self.outcome = outcome
        self._notify_reloaded()
        return outcome

    @staticmethod
    def _check(pending: tuple[Edit, bool], roots: list[Any]) -> Optional[str]:
        edit, undone = pending
        expected = edit.before if undone else edit.expected
        instances = [node for root in roots for node in widgets_built_at(root, edit.site, edit.widget or None)]
        if not instances:
            return f"reloaded, but no widget is built at {os.path.basename(edit.file)}:{edit.site.line}"
        rect = getattr(instances[0], "layout_rect", None)
        if rect is None:
            return None
        got = {"width": int(rect[2]), "height": int(rect[3])}
        for axis, want in expected.items():
            if abs(got[axis] - want) > SNAP_BAND:
                return f"{axis} landed at {got[axis]}, expected {want}"
        return None

    def reload_failed(self, traceback_text: str) -> Optional[str]:
        """Blame the pending edit for a failed reload; return the badge or ``None``."""
        pending, self._pending = self._pending, None
        if pending is None:
            return None
        last = traceback_text.strip().splitlines()[-1] if traceback_text.strip() else "unknown error"
        self.outcome = f"reload failed: {last}"
        return self.outcome


def _summary(edit: Edit) -> str:
    return ", ".join(f"{name} → {value}" for name, value in edit.after.items())


def _is_literal(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float, str))
        and not isinstance(node.value, bool)
    )


def _segment(text: str, node: ast.expr) -> str:
    return ast.get_source_segment(text, node) or type(node).__name__


def _spell(value: Value, like: Optional[str]) -> str:
    """``value`` as source: an int bare, a string in the quotes ``like`` used."""
    if isinstance(value, int):
        return str(value)
    quote = like[0] if like and like[0] in "'\"" else '"'
    return f"{quote}{value}{quote}"


def _insertion_point(text: str, call: ast.Call, offsets: "_Offsets") -> tuple[int, str]:
    """Where a new keyword goes, and what precedes it: after the last argument,
    or straight after the opening parenthesis of an empty call."""
    last: Optional[ast.expr] = None
    for arg in (*call.args, *(kw.value for kw in call.keywords)):
        if last is None or (arg.end_lineno or 0, arg.end_col_offset or 0) > (
            last.end_lineno or 0,
            last.end_col_offset or 0,
        ):
            last = arg
    if last is not None:
        return (offsets.of(last.end_lineno or last.lineno, last.end_col_offset or 0), ", ")
    func_end = offsets.of(call.func.end_lineno or call.func.lineno, call.func.end_col_offset or 0)
    return (text.index("(", func_end) + 1, "")


class _Offsets:
    """Turn ``ast``'s line and UTF-8 byte column into a character offset."""

    def __init__(self, text: str) -> None:
        self._text = text
        starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                starts.append(index + 1)
        self._starts = starts

    def of(self, line: int, column: int) -> int:
        start = self._starts[line - 1]
        end = self._starts[line] if line < len(self._starts) else len(self._text)
        head = self._text[start:end].encode("utf-8")[:column]
        return start + len(head.decode("utf-8"))


def is_project_file(path: str) -> bool:
    """Whether ``path`` is the human's to edit: not under an install directory.

    A site can only point at a dependency's file when a widget was built with
    no user frame nearer than the event loop, and a size written there would
    be silent corruption of a package.
    """
    from .reloader import _site_directories

    try:
        resolved = pathlib.Path(path).resolve()
    except OSError:
        return False
    return not any(_under(resolved, site) for site in _site_directories())


def _under(path: "pathlib.Path", directory: "pathlib.Path") -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _read(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


__all__ = [
    "Edit",
    "EditLog",
    "Refusal",
    "SNAP_BAND",
    "SpanEdit",
    "Value",
    "apply_spans",
    "is_project_file",
    "locate_call",
    "plan_keywords",
    "still_applies",
]
