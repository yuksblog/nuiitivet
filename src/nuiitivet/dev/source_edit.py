"""Span surgery on the file that built a widget.

Layout mode's edits are written here. Each one is a handful of character
spans replaced in one file -- the value of a ``width=`` keyword, a keyword
inserted after the last argument, an element moved within a ``children`` list
-- located by re-parsing the file with :mod:`ast` and matching the call at the
widget's construction site. Nothing around a span is touched, so the human's
formatting survives every edit.

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
    #: The class name of the widget the site builds -- the one resized, or the
    #: container reordered -- which tells its instances apart from the children
    #: it builds for itself at the same site.
    widget: str = ""
    #: For a move: the class name of the child moved, checked at its slot after
    #: the reload.
    child: str = ""
    inverse: tuple[SpanEdit, ...] = field(default_factory=tuple)
    #: For a move into another container: its site and class name, and -- when
    #: it lives in another file -- that file and the spans written there.
    destination: Optional[Frame] = None
    dest_widget: str = ""
    other_file: str = ""
    other_spans: tuple[SpanEdit, ...] = field(default_factory=tuple)
    other_inverse: tuple[SpanEdit, ...] = field(default_factory=tuple)

    @property
    def files(self) -> tuple[str, ...]:
        """The files this edit writes, the site's first."""
        return (self.file, self.other_file) if self.other_file else (self.file,)


def locate_call(text: str, site: Frame) -> Optional[ast.Call]:
    """The ``Call`` node at ``site`` in ``text``, or ``None``.

    Matched on the full span, not the start alone: ``Text("a").modifier(m)``
    holds two calls starting at one column, and each builds a widget of its own.
    Without a recorded column the line's only call is accepted; two calls on
    the line cannot be told apart, and neither is guessed.
    """
    located = _locate(text, site)
    return located[1] if located is not None else None


def _locate(text: str, site: Frame) -> Optional[tuple[ast.Module, ast.Call]]:
    """The parsed module and the call at ``site`` in it, or ``None``."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    call = _call_at(tree, site)
    return (tree, call) if call is not None else None


def _call_at(tree: ast.Module, site: Frame) -> Optional[ast.Call]:
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


def plan_move(text: str, site: Frame, index: int, slot: int, count: int) -> Union[tuple[SpanEdit, ...], Refusal]:
    """The spans that move the child at ``index`` of the container at ``site`` to ``slot``.

    The edit lands in the list literal that owns the children's order: the
    ``children`` list itself, or the list a comprehension or a ``ForEach``
    iterates -- inline, or bound once to a name in the enclosing function or
    module and never mentioned again. ``slot`` is the element's position in
    the list without it, and ``count`` is how many children layout saw: only
    when that literal has exactly ``count`` elements does a layout index name
    a source span, so anything else is refused. The element travels with one
    of its separators, so the list's formatting comes along.
    """
    located = _locate(text, site)
    if located is None:
        return Refusal(f"the call at {os.path.basename(site.file)}:{site.line} could not be found")
    tree, call = located
    owner = _order_owner(text, tree, call)
    if isinstance(owner, Refusal):
        return owner
    spread = next((elt for elt in owner.elts if isinstance(elt, ast.Starred)), None)
    if spread is not None:
        return Refusal(f"the list spreads {_segment(text, spread.value)}")
    elts = owner.elts
    if len(elts) != count:
        return Refusal(f"the list holds {len(elts)} elements but layout saw {count} children")
    if not 0 <= index < len(elts) or not 0 <= slot < len(elts):
        return Refusal("the slot is outside the list")
    offsets = _Offsets(text)
    starts = [offsets.of(elt.lineno, elt.col_offset) for elt in elts]
    ends = [offsets.of(elt.end_lineno or elt.lineno, elt.end_col_offset or 0) for elt in elts]
    element = text[starts[index] : ends[index]]
    last = len(elts) - 1
    # The element leaves with the separator after it; the last element, which
    # has none, takes the one before it so a trailing comma stays where it is.
    if index < last:
        cut = (starts[index], starts[index + 1])
        separator = text[ends[index] : starts[index + 1]]
    else:
        cut = (ends[index - 1], ends[index])
        separator = text[ends[index - 1] : starts[index]]
    before = slot if slot < index else slot + 1
    if before < len(elts):
        insertion = SpanEdit(starts[before], starts[before], element + separator)
    else:
        insertion = SpanEdit(ends[last], ends[last], separator + element)
    removal = SpanEdit(cut[0], cut[1], "", replaces=text[cut[0] : cut[1]])
    return (removal, insertion)


def plan_move_across(
    text: str,
    site: Frame,
    index: int,
    count: int,
    dest_text: str,
    dest_site: Frame,
    slot: int,
    dest_count: int,
) -> Union[tuple[tuple[SpanEdit, ...], tuple[SpanEdit, ...]], Refusal]:
    """The spans that move child ``index`` of the container at ``site`` into the one at ``dest_site``.

    Returned as two span sets, one per text; when both containers live in one
    file the caller applies both to it. Both ``children`` must be list
    literals written in place: a child built from data has no expression of
    its own to move, and a data-driven list has nowhere to receive one. The
    element leaves with one of its separators, enters with one of the
    destination's, and its continuation lines take the destination's
    indentation.
    """
    source = children_list(text, site, "source")
    if isinstance(source, Refusal):
        return source
    target = children_list(dest_text, dest_site, "destination")
    if isinstance(target, Refusal):
        return target
    if len(source.elts) != count:
        return Refusal(f"the list holds {len(source.elts)} elements but layout saw {count} children")
    if len(target.elts) != dest_count:
        return Refusal(f"the destination holds {len(target.elts)} elements but layout saw {dest_count} children")
    if not 0 <= index < count or not 0 <= slot <= dest_count:
        return Refusal("the slot is outside the list")
    offsets = _Offsets(text)
    starts = [offsets.of(elt.lineno, elt.col_offset) for elt in source.elts]
    ends = [offsets.of(elt.end_lineno or elt.lineno, elt.end_col_offset or 0) for elt in source.elts]
    element = text[starts[index] : ends[index]]
    if count == 1:
        # The only element leaves with everything inside the brackets, a
        # trailing comma included, so ``[]`` is what remains.
        open_at = offsets.of(source.lineno, source.col_offset) + 1
        cut = (open_at, offsets.of(source.end_lineno or source.lineno, source.end_col_offset or 0) - 1)
    elif index < count - 1:
        cut = (starts[index], starts[index + 1])
    else:
        cut = (ends[index - 1], ends[index])
    removal = SpanEdit(cut[0], cut[1], "", replaces=text[cut[0] : cut[1]])
    moved = _reindent(element, _indent_at(text, starts[index]), _dest_indent(dest_text, target, slot))
    return ((removal,), (_insert_element(dest_text, target, slot, moved),))


def children_list(text: str, site: Frame, role: str) -> Union[ast.List, Refusal]:
    """The ``children`` list literal written on the call at ``site``, or why there is none.

    The gate a move across containers passes on each side, ``role`` being
    ``"source"`` or ``"destination"``: a list built by ``builder()``, a
    ``ForEach``, a comprehension or any other expression is refused with
    the reason that side has.
    """
    located = _locate(text, site)
    if located is None:
        return Refusal(f"the call at {os.path.basename(site.file)}:{site.line} could not be found")
    _tree, call = located
    name = _segment(text, call.func)
    if isinstance(call.func, ast.Attribute) and call.func.attr == "builder":
        return _data_refusal(f"{name}()", role)
    children = _argument(call, "children")
    if children is None:
        return Refusal(f"no children are written on {name}")
    if isinstance(children, ast.List) and not any(isinstance(elt, ast.Starred) for elt in children.elts):
        if not (len(children.elts) == 1 and isinstance(children.elts[0], ast.Call) and _is_for_each(children.elts[0])):
            return children
        return _data_refusal("a ForEach", role)
    return _data_refusal(_describe_children(text, children), role)


def _data_refusal(what: str, role: str) -> Refusal:
    if role == "source":
        return Refusal(f"the children come from {what}; the child has no expression of its own to move")
    return Refusal(f"the destination's children come from {what}; it cannot take a widget")


def _insert_element(text: str, target: ast.List, slot: int, element: str) -> SpanEdit:
    """Insert ``element`` at ``slot`` of ``target``, with a separator like its neighbours'."""
    offsets = _Offsets(text)
    open_at = offsets.of(target.lineno, target.col_offset) + 1
    elts = target.elts
    if not elts:
        return SpanEdit(open_at, open_at, element)
    starts = [offsets.of(elt.lineno, elt.col_offset) for elt in elts]
    ends = [offsets.of(elt.end_lineno or elt.lineno, elt.end_col_offset or 0) for elt in elts]
    if slot < len(elts):
        gap = text[(ends[slot - 1] if slot > 0 else open_at) : starts[slot]]
        return SpanEdit(starts[slot], starts[slot], element + _separator(gap))
    gap = text[(ends[-2] if len(elts) > 1 else open_at) : starts[-1]]
    return SpanEdit(ends[-1], ends[-1], _separator(gap) + element)


def _separator(gap: str) -> str:
    """A separator like the one in ``gap``: the gap itself when it holds a comma,
    a comma before it when it is a line break, ``", "`` otherwise."""
    if "," in gap:
        return gap
    return "," + gap if "\n" in gap else ", "


def _indent_at(text: str, offset: int) -> str:
    """The leading whitespace of the line holding ``offset``."""
    start = text.rfind("\n", 0, offset) + 1
    line = text[start : text.find("\n", start) if "\n" in text[start:] else len(text)]
    return line[: len(line) - len(line.lstrip())]


def _dest_indent(text: str, target: ast.List, slot: int) -> str:
    offsets = _Offsets(text)
    if target.elts:
        anchor = target.elts[slot] if slot < len(target.elts) else target.elts[-1]
        return _indent_at(text, offsets.of(anchor.lineno, anchor.col_offset))
    return _indent_at(text, offsets.of(target.lineno, target.col_offset))


def _reindent(element: str, source: str, dest: str) -> str:
    """Shift the continuation lines of ``element`` from ``source`` indentation to ``dest``."""
    if source == dest:
        return element
    lines = element.split("\n")
    for i in range(1, len(lines)):
        if lines[i].startswith(source):
            lines[i] = dest + lines[i][len(source) :]
    return "\n".join(lines)


Literal = Union[ast.List, ast.Tuple]


def _order_owner(text: str, tree: ast.Module, call: ast.Call) -> Union[Literal, Refusal]:
    """The list literal whose element order is the order of ``call``'s children."""
    if isinstance(call.func, ast.Attribute) and call.func.attr == "builder":
        items = _argument(call, "items")
        if items is None:
            return Refusal("no items are written on this call")
        return _literal_behind(text, tree, call, items, "items")
    children = _argument(call, "children")
    if children is None:
        return Refusal("no children are written on this call")
    if isinstance(children, ast.List) and len(children.elts) == 1 and isinstance(children.elts[0], ast.Call):
        provider = children.elts[0]
        if _is_for_each(provider):
            items = _argument(provider, "items")
            if items is None:
                return Refusal("no items are written on the ForEach")
            return _literal_behind(text, tree, call, items, "items")
    return _literal_behind(text, tree, call, children, "children")


def _literal_behind(text: str, tree: ast.Module, call: ast.Call, expr: ast.expr, what: str) -> Union[Literal, Refusal]:
    """``expr`` as the list literal it iterates in order, or why it has none."""
    if isinstance(expr, (ast.List, ast.Tuple)):
        return expr
    if isinstance(expr, ast.ListComp):
        if len(expr.generators) != 1:
            return Refusal("the comprehension has more than one for")
        generator = expr.generators[0]
        if generator.ifs:
            return Refusal("the comprehension filters its items")
        return _literal_behind(text, tree, call, generator.iter, what)
    if isinstance(expr, ast.Name):
        return _binding_of(text, tree, call, expr)
    return Refusal(f"{what} are {_describe_children(text, expr)}, not one list")


def _binding_of(text: str, tree: ast.Module, call: ast.Call, use: ast.Name) -> Union[Literal, Refusal]:
    """The list literal ``use`` names, or why the name's order cannot be trusted.

    The name must be bound exactly once in the innermost scope that binds it
    -- the function holding the call, else the module -- by a plain assignment
    of a literal, and mentioned nowhere else in that scope: a second binding,
    an ``append``, a parameter, or a read from another function could each put
    the order somewhere other than the literal.
    """
    name = use.id
    scope: ast.AST = tree
    function = _enclosing_function(tree, call)
    if function is not None:
        if any(arg.arg == name for arg in function.args.args + function.args.kwonlyargs):
            return Refusal(f"{name} is a parameter of {function.name}")
        if _bindings(function, name):
            scope = function
    bindings = _bindings(scope, name)
    if not bindings:
        return Refusal(f"{name} is not bound to a list literal in this file")
    if len(bindings) > 1:
        return Refusal(f"{name} is bound more than once")
    target, value = bindings[0]
    if not isinstance(value, (ast.List, ast.Tuple)):
        return Refusal(f"{name} is bound to {_segment(text, value)}, not one list")
    mentions = [node for node in ast.walk(scope) if isinstance(node, ast.Name) and node.id == name]
    if any(node is not target and node is not use for node in mentions):
        return Refusal(f"{name} is used again after {name} = [...]")
    return value


def _enclosing_function(tree: ast.Module, call: ast.Call) -> Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]]:
    """The innermost function whose body holds ``call``, or ``None`` at module level."""
    start, end = (call.lineno, call.col_offset), (call.end_lineno or call.lineno, call.end_col_offset or 0)
    innermost: Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (node.lineno, node.col_offset) <= start and end <= (node.end_lineno or 0, node.end_col_offset or 0):
            if innermost is None or node.lineno >= innermost.lineno:
                innermost = node
    return innermost


def _bindings(scope: ast.AST, name: str) -> list[tuple[ast.Name, ast.expr]]:
    """Every statement in ``scope``'s own body that binds ``name``, as ``(target, value)``.

    Nested functions, classes and lambdas are scopes of their own and are not
    entered. A loop target or an augmented assignment counts as a binding too,
    with the expression it draws from as its value.
    """
    found: list[tuple[ast.Name, ast.expr]] = []
    stack: list[ast.AST] = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    found.append((target, node.value))
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found.append((node.target, node.value or node.target))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found.append((node.target, node.iter))
        stack.extend(ast.iter_child_nodes(node))
    return found


def _argument(call: ast.Call, keyword: str) -> Optional[ast.expr]:
    """The value of ``keyword`` on ``call``, else its first positional argument."""
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return call.args[0] if call.args else None


def _is_for_each(node: ast.Call) -> bool:
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "ForEach") or (
        isinstance(func, ast.Attribute) and func.attr == "ForEach"
    )


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
        """Write ``edit`` to its file -- or its two files -- and remember how to undo it.

        A second file that cannot be written leaves the first as it was.
        """
        text = _read(edit.file)
        new_text, edit.inverse = apply_spans(text, edit.spans)
        if edit.other_file:
            other_text = _read(edit.other_file)
            new_other, edit.other_inverse = apply_spans(other_text, edit.other_spans)
            _write(edit.file, new_text)
            try:
                _write(edit.other_file, new_other)
            except OSError:
                _write(edit.file, text)
                raise
        else:
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
        texts = [_read(path) for path in edit.files]
        inverses = (edit.inverse, edit.other_inverse)
        for path, text, inverse in zip(edit.files, texts, inverses):
            if not still_applies(text, inverse):
                return (None, f"cannot undo: {os.path.basename(path)} changed under the edit")
        for path, text, inverse in zip(edit.files, texts, inverses):
            _write(path, apply_spans(text, inverse)[0])
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
        if edit.kind == "move" and edit.destination is not None:
            return _check_move_across(roots, edit, undone, instances[0])
        if edit.kind == "move":
            return _check_slot(instances[0], int(expected["slot"]), edit.child)
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


def _check_slot(container: Any, slot: int, child: str) -> Optional[str]:
    """Whether ``container``'s child at ``slot`` is of the class the move put there.

    A class name is all the rebuilt child shares with the one that was
    dragged, so this catches a move that landed nowhere or on the wrong
    list, not one that swapped two children of a kind.
    """
    from nuiitivet.layout.layout_utils import expand_layout_children

    from .reorder import visible

    children = expand_layout_children(container.children_snapshot())
    if slot >= len(children):
        return f"reloaded, but {type(container).__name__} has {len(children)} children, expected {slot + 1} or more"
    got = type(visible(children[slot])).__name__
    if child and got != child:
        return f"position {slot + 1} holds {got}, expected {child}"
    return None


def _check_move_across(roots: list[Any], edit: Edit, undone: bool, source: Any) -> Optional[str]:
    """Whether the child left its source and sits at its slot in the destination, or the reverse."""
    from nuiitivet.layout.layout_utils import expand_layout_children

    if undone:
        return _check_slot(source, int(edit.before["slot"]), edit.child)
    assert edit.destination is not None
    targets = [node for root in roots for node in widgets_built_at(root, edit.destination, edit.dest_widget or None)]
    if not targets:
        return f"reloaded, but no widget is built at {os.path.basename(edit.destination.file)}:{edit.destination.line}"
    remaining = len(expand_layout_children(source.children_snapshot()))
    if remaining != int(edit.before["count"]) - 1:
        return f"{edit.parent_layout} still has {remaining} children, expected {int(edit.before['count']) - 1}"
    return _check_slot(targets[0], int(edit.expected["slot"]), edit.child)


def _summary(edit: Edit) -> str:
    if edit.kind == "move" and edit.destination is not None:
        return f"{edit.child} → {edit.dest_widget}"
    if edit.kind == "move":
        return f"{edit.child} → position {int(edit.after['slot']) + 1}"
    return ", ".join(f"{name} → {value}" for name, value in edit.after.items())


def _describe_children(text: str, node: ast.expr) -> str:
    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        return "a comprehension"
    if isinstance(node, ast.Starred):
        return "a spread"
    if isinstance(node, (ast.Name, ast.Attribute)):
        return f"bound to {_segment(text, node)}"
    if isinstance(node, ast.Call):
        return f"the result of {_segment(text, node.func)}(...)"
    return "an expression"


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
    "children_list",
    "is_project_file",
    "locate_call",
    "plan_keywords",
    "plan_move",
    "plan_move_across",
    "still_applies",
]
