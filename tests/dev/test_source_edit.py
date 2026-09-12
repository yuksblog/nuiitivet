"""Tests for span surgery on a widget's construction site.

What has to hold: the edit lands on exactly the call that built the widget --
even when a line holds several -- replaces or inserts one keyword without
touching anything around it, refuses whatever it cannot write as a literal,
and can be undone only while the text it wrote is still there.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterator

import pytest

from nuiitivet.dev import source
from nuiitivet.dev.source import Frame
from nuiitivet.dev.source_edit import (
    Edit,
    EditLog,
    Refusal,
    SpanEdit,
    apply_spans,
    locate_call,
    plan_keywords,
    plan_move,
    still_applies,
)
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def _site(text: str, snippet: str, *, file: str = "app.py") -> Frame:
    """The frame of the call whose source is exactly ``snippet``."""
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Call) and ast.get_source_segment(text, node) == snippet:
            return Frame(file, node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, "build")
    raise AssertionError(f"no call {snippet!r} in the text")


def _edited(text: str, snippet: str, **changes: Any) -> str:
    planned = plan_keywords(text, _site(text, snippet), changes)
    assert not isinstance(planned, Refusal), planned.reason
    return apply_spans(text, planned)[0]


# --- locating ----------------------------------------------------------------


def test_the_call_is_matched_on_its_full_span() -> None:
    """``Text("a").modifier(m)`` holds two calls starting at one column, each
    building a widget of its own."""
    text = 'x = Text("a", width=1).modifier(m)\n'

    inner = locate_call(text, _site(text, 'Text("a", width=1)'))
    outer = locate_call(text, _site(text, 'Text("a", width=1).modifier(m)'))

    assert inner is not None and outer is not None
    assert ast.get_source_segment(text, inner) == 'Text("a", width=1)'
    assert ast.get_source_segment(text, outer) == 'Text("a", width=1).modifier(m)'


def test_without_a_column_the_lines_only_call_is_accepted() -> None:
    text = 'x = Text("a")\ny = [Text("b"), Text("c")]\n'

    assert locate_call(text, Frame("app.py", 1, None, None, None, "f")) is not None
    assert locate_call(text, Frame("app.py", 2, None, None, None, "f")) is None


def test_a_site_that_matches_nothing_is_refused() -> None:
    text = 'x = Text("a")\n'

    planned = plan_keywords(text, Frame("app.py", 1, 40, 1, 50, "f"), {"width": 1})

    assert isinstance(planned, Refusal)
    assert "app.py:1" in planned.reason


def test_a_file_that_does_not_parse_is_refused() -> None:
    planned = plan_keywords("x = Text(\n", Frame("app.py", 1, 4, 1, 9, "f"), {"width": 1})

    assert isinstance(planned, Refusal)


# --- replacing and inserting -----------------------------------------------


def test_an_int_literal_is_replaced_in_place() -> None:
    assert _edited('Text("a", width=180)\n', 'Text("a", width=180)', width=240) == 'Text("a", width=240)\n'


def test_a_string_literal_keeps_its_quotes() -> None:
    assert _edited("Text('a', width='wt')\n", "Text('a', width='wt')", width="auto") == "Text('a', width='auto')\n"


def test_an_int_becomes_a_double_quoted_string() -> None:
    assert _edited("Text('a', width=180)\n", "Text('a', width=180)", width="wt") == "Text('a', width=\"wt\")\n"


def test_an_absent_keyword_is_inserted_after_the_last_argument() -> None:
    assert _edited('Text("a")\n', 'Text("a")', width=240) == 'Text("a", width=240)\n'


def test_an_absent_keyword_goes_after_an_existing_keyword() -> None:
    assert _edited('Text("a", key="k")\n', 'Text("a", key="k")', height=40) == 'Text("a", key="k", height=40)\n'


def test_an_empty_call_gets_its_first_keyword() -> None:
    assert _edited("Spacer()\n", "Spacer()", width=240) == "Spacer(width=240)\n"


def test_two_absent_keywords_land_in_the_order_given() -> None:
    assert _edited('Text("a")\n', 'Text("a")', width=240, height=40) == 'Text("a", width=240, height=40)\n'


def test_a_replacement_and_an_insertion_combine() -> None:
    assert (
        _edited('Text("a", width=180)\n', 'Text("a", width=180)', width=240, height=40)
        == 'Text("a", width=240, height=40)\n'
    )


def test_a_multi_line_call_is_edited_where_its_last_argument_ends() -> None:
    text = 'Text(\n    "a",\n    key="k",\n)\n'

    assert _edited(text, text.strip(), width=240) == 'Text(\n    "a",\n    key="k", width=240,\n)\n'


def test_non_ascii_text_before_the_keyword_does_not_shift_the_span() -> None:
    """``ast`` columns are UTF-8 bytes; the file is edited in characters."""
    text = 'Text("こんにちは", width=180)\n'

    assert _edited(text, text.strip(), width=240) == 'Text("こんにちは", width=240)\n'


def test_only_the_call_at_the_site_is_edited_when_a_line_holds_two() -> None:
    text = 'Row([Text("a", width=1), Text("b", width=1)])\n'

    assert _edited(text, 'Text("b", width=1)', width=2) == 'Row([Text("a", width=1), Text("b", width=2)])\n'


def test_the_chained_wrapper_is_edited_without_touching_the_inner_call() -> None:
    text = 'Text("a", width=1).modifier(m)\n'

    assert _edited(text, text.strip(), width=2) == 'Text("a", width=1).modifier(m, width=2)\n'


# --- refusals ----------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["self.card_w", "w * 2", "width", "some_call()", "-1", "True", "None"],
)
def test_a_value_that_is_not_a_literal_is_refused_by_name(value: str) -> None:
    text = f'Text("a", width={value})\n'

    planned = plan_keywords(text, _site(text, text.strip()), {"width": 240})

    assert isinstance(planned, Refusal)
    assert value in planned.reason


def test_a_keyword_that_may_come_through_a_splat_is_refused() -> None:
    text = 'Text("a", **opts)\n'

    planned = plan_keywords(text, _site(text, text.strip()), {"width": 240})

    assert isinstance(planned, Refusal)
    assert "**opts" in planned.reason


# --- spans -------------------------------------------------------------------


def test_applying_the_inverse_restores_the_text() -> None:
    text = 'Text("a", width=180)\n'
    spans = plan_keywords(text, _site(text, text.strip()), {"width": 240, "height": 40})
    assert not isinstance(spans, Refusal)

    edited, inverse = apply_spans(text, spans)
    restored, _forward = apply_spans(edited, inverse)

    assert restored == text
    assert still_applies(edited, inverse)


def test_an_inverse_no_longer_applies_once_the_text_moved() -> None:
    text = 'Text("a", width=180)\n'
    spans = plan_keywords(text, _site(text, text.strip()), {"width": 240})
    assert not isinstance(spans, Refusal)
    edited, inverse = apply_spans(text, spans)

    assert not still_applies("# added\n" + edited, inverse)
    assert not still_applies(edited.replace("240", "250"), inverse)


# --- the edit log ------------------------------------------------------------


# --- moving a list element ---------------------------------------------------


def _moved(text: str, snippet: str, index: int, slot: int, count: int = 3) -> str:
    planned = plan_move(text, _site(text, snippet), index, slot, count)
    assert not isinstance(planned, Refusal), planned.reason
    return apply_spans(text, planned)[0]


def _refused(text: str, snippet: str, index: int, slot: int, count: int = 3) -> str:
    planned = plan_move(text, _site(text, snippet), index, slot, count)
    assert isinstance(planned, Refusal)
    return planned.reason


_LIST = "Column(children=[a(), b(), c()])"


def test_a_middle_element_moves_to_the_front() -> None:
    assert _moved(_LIST, _LIST, 1, 0) == "Column(children=[b(), a(), c()])"


def test_the_first_element_moves_to_the_end() -> None:
    assert _moved(_LIST, _LIST, 0, 2) == "Column(children=[b(), c(), a()])"


def test_the_last_element_moves_to_the_front() -> None:
    assert _moved(_LIST, _LIST, 2, 0) == "Column(children=[c(), a(), b()])"


def test_a_positional_children_list_is_edited_too() -> None:
    text = "Row([a(), b()])"
    assert _moved(text, text, 0, 1, count=2) == "Row([b(), a()])"


def test_a_multi_line_list_keeps_its_indentation_and_trailing_comma() -> None:
    text = "Column(\n    children=[\n        a(),\n        b(),\n        c(),\n    ],\n)"

    moved = _moved(text, text, 2, 0)

    assert moved == "Column(\n    children=[\n        c(),\n        a(),\n        b(),\n    ],\n)"


def test_the_inverse_of_a_move_restores_the_text() -> None:
    planned = plan_move(_LIST, _site(_LIST, _LIST), 0, 2, 3)
    assert not isinstance(planned, Refusal)
    moved, inverse = apply_spans(_LIST, planned)

    assert still_applies(moved, inverse)
    assert apply_spans(moved, inverse)[0] == _LIST


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("Column(children=[a() for _ in items])", "items is not bound to a list literal in this file"),
        ("Column(children=items)", "items is not bound to a list literal in this file"),
        ("Column(children=head + tail)", "children are an expression, not one list"),
        ("Column(children=make())", "children are the result of make(...), not one list"),
        ("Column(children=[a(), *rest])", "the list spreads rest"),
        ("Column(gap=0)", "no children are written on this call"),
    ],
)
def test_children_that_are_not_one_list_literal_are_refused(text: str, reason: str) -> None:
    assert _refused(text, text, 0, 1, count=2) == reason


def test_a_list_whose_length_disagrees_with_layout_is_refused() -> None:
    assert _refused(_LIST, _LIST, 0, 1, count=2) == "the list holds 3 elements but layout saw 2 children"


# --- the literal that owns the order ----------------------------------------

_COMP = "Column(children=[Text(t) for t in tags])"
_LOCAL = 'def build():\n    tags = ["a", "b", "c"]\n    return ' + _COMP + "\n"
_BUILDER = "Column.builder(TAGS, make)"
_MODULE = 'TAGS = ["a", "b", "c"]\n\n\ndef build():\n    return ' + _BUILDER + "\n"


def test_a_comprehension_over_a_name_bound_in_the_function_moves_the_element_there() -> None:
    assert _moved(_LOCAL, _COMP, 0, 2) == 'def build():\n    tags = ["b", "c", "a"]\n    return ' + _COMP + "\n"


def test_a_builder_over_a_module_level_literal_moves_the_element_there() -> None:
    assert _moved(_MODULE, _BUILDER, 2, 0).startswith('TAGS = ["c", "a", "b"]\n')


def test_a_comprehension_over_an_inline_list_moves_the_element_in_it() -> None:
    text = 'Column(children=[Text(t) for t in ["a", "b", "c"]])'
    assert _moved(text, text, 1, 0) == 'Column(children=[Text(t) for t in ["b", "a", "c"]])'


def test_a_tuple_literal_owns_an_order_too() -> None:
    text = 'Row(children=[Text(t) for t in ("a", "b", "c")])'
    assert _moved(text, text, 0, 2) == 'Row(children=[Text(t) for t in ("b", "c", "a")])'


def test_builder_items_may_be_a_keyword() -> None:
    call = "Column.builder(items=TAGS, builder=make)"
    text = 'TAGS = ["a", "b", "c"]\n' + call + "\n"
    assert _moved(text, call, 0, 1).startswith('TAGS = ["b", "a", "c"]\n')


def test_an_explicit_for_each_child_is_read_like_a_builder() -> None:
    call = "Column(children=[ForEach(TAGS, make)])"
    text = 'TAGS = ["a", "b", "c"]\n' + call + "\n"
    assert _moved(text, call, 0, 1).startswith('TAGS = ["b", "a", "c"]\n')


_FILTERED = "Column(children=[Text(t) for t in tags if t])"
_NESTED = "Column(children=[Text(t) for row in tags for t in row])"
_CALLED = "Column.builder(load(), make)"


@pytest.mark.parametrize(
    ("text", "call", "reason"),
    [
        ("def build(tags):\n    return " + _COMP + "\n", _COMP, "tags is a parameter of build"),
        (
            'def build():\n    tags = ["a"]\n    tags = ["a", "b", "c"]\n    return ' + _COMP + "\n",
            _COMP,
            "tags is bound more than once",
        ),
        (
            'def build():\n    tags = ["a", "b", "c"]\n    tags.append("d")\n    return ' + _COMP + "\n",
            _COMP,
            "tags is used again after tags = [...]",
        ),
        ("def build():\n    tags = load()\n    return " + _COMP + "\n", _COMP, "tags is bound to load(), not one list"),
        (
            "def build():\n    for tags in rows:\n        pass\n    return " + _COMP + "\n",
            _COMP,
            "tags is bound to rows, not one list",
        ),
        ("def build():\n    return " + _COMP + "\n", _COMP, "tags is not bound to a list literal in this file"),
        (
            'TAGS = ["a", "b", "c"]\n\n\ndef other():\n    return TAGS\n\n\ndef build():\n    return '
            + _BUILDER
            + "\n",
            _BUILDER,
            "TAGS is used again after TAGS = [...]",
        ),
        ('tags = ["a", "b", "c"]\n' + _FILTERED, _FILTERED, "the comprehension filters its items"),
        ('tags = ["a", "b", "c"]\n' + _NESTED, _NESTED, "the comprehension has more than one for"),
        (_CALLED, _CALLED, "items are the result of load(...), not one list"),
    ],
)
def test_an_order_that_is_not_in_one_literal_is_refused_by_name(text: str, call: str, reason: str) -> None:
    assert _refused(text, call, 0, 1) == reason


@pytest.fixture
def app_file(tmp_path: Path) -> Path:
    path = tmp_path / "app.py"
    path.write_text('root = Text("a", width=180)\n', encoding="utf-8")
    return path


def _edit(path: Path, **changes: Any) -> Edit:
    text = path.read_text(encoding="utf-8")
    site = _site(text, 'Text("a", width=180)', file=str(path))
    spans = plan_keywords(text, site, changes)
    assert not isinstance(spans, Refusal)
    return Edit("resize", str(path), site, "Column", {"width": 180}, changes, {"width": 240}, 1, spans)


def test_apply_writes_the_file_and_leaves_the_edit_pending(app_file: Path) -> None:
    log = EditLog()
    edit = _edit(app_file, width=240)

    log.apply(edit)

    assert app_file.read_text(encoding="utf-8") == 'root = Text("a", width=240)\n'
    assert log.pending is edit


def test_undo_restores_the_file(app_file: Path) -> None:
    log = EditLog()
    log.apply(_edit(app_file, width=240))

    undone, notice = log.undo()

    assert undone is not None
    assert "width → 240" in notice
    assert app_file.read_text(encoding="utf-8") == 'root = Text("a", width=180)\n'
    assert log.undo() == (None, "nothing to undo")


def test_undo_is_refused_once_the_written_text_has_moved(app_file: Path) -> None:
    """Applying the inverse to text that moved would corrupt whatever replaced it."""
    log = EditLog()
    log.apply(_edit(app_file, width=240))
    app_file.write_text('# a hand edit\nroot = Text("a", width=240)\n', encoding="utf-8")

    undone, notice = log.undo()

    assert undone is None
    assert "cannot undo" in notice
    assert app_file.read_text(encoding="utf-8").endswith('width=240)\n')


def test_a_failed_reload_is_blamed_on_the_pending_edit(app_file: Path) -> None:
    log = EditLog()
    log.apply(_edit(app_file, width=240))

    outcome = log.reload_failed("Traceback...\nSyntaxError: invalid syntax")

    assert outcome == "reload failed: SyntaxError: invalid syntax"
    assert log.pending is None
    assert log.reload_failed("again") is None, "nothing pending, nothing to blame"


@pytest.fixture
def recording() -> Iterator[None]:
    source.install()
    try:
        yield
    finally:
        source.uninstall()


def test_after_reload_is_quiet_when_the_widget_measures_as_expected(recording: None) -> None:
    leaf = Text("AAA", width=100, height=40)
    site = source.site_of(leaf)[0]
    log = EditLog()
    log._pending = (Edit("resize", site.file, site, "Column", {}, {"width": 100}, {"width": 100}, 1, ()), False)

    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)

        assert log.after_reload([host.root]) is None
    assert log.pending is None


def test_after_reload_reports_a_size_that_missed(recording: None) -> None:
    leaf = Text("AAA", width=100, height=40)
    site = source.site_of(leaf)[0]
    log = EditLog()
    log._pending = (Edit("resize", site.file, site, "Column", {}, {"width": 50}, {"width": 50}, 1, ()), False)

    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)

        assert log.after_reload([host.root]) == "width landed at 100, expected 50"
    assert log.outcome == "width landed at 100, expected 50"


def test_after_reload_reports_a_site_that_built_nothing(recording: None) -> None:
    site = Frame("gone.py", 1, 0, 1, 10, "build")
    log = EditLog()
    log._pending = (Edit("resize", "gone.py", site, "", {}, {"width": 50}, {"width": 50}, 1, ()), False)

    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)

        outcome = log.after_reload([host.root])

    assert outcome is not None and "gone.py:1" in outcome


def test_after_reload_checks_the_class_at_the_slot_of_a_move(recording: None) -> None:
    column = Column(children=[Text("AAA"), Column(children=[])])
    site = source.site_of(column)[0]
    log = EditLog()
    edit = Edit("move", site.file, site, "Column", {"slot": 0}, {"slot": 1}, {"slot": 1}, 1, (), "Column", "Text")
    log._pending = (edit, False)

    with mount(column) as host:
        host.layout(300, 200)

        assert log.after_reload([host.root]) == "position 2 holds Column, expected Text"


def test_only_files_outside_the_install_directories_are_the_humans_to_edit(tmp_path: Path) -> None:
    import pyglet

    from nuiitivet.dev.source_edit import is_project_file

    assert is_project_file(str(tmp_path / "app.py")) is True
    assert is_project_file(str(pyglet.__file__)) is False


def test_span_edit_is_a_value() -> None:
    assert SpanEdit(1, 2, "x") == SpanEdit(1, 2, "x")
