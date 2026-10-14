"""Tests for the comment-mode mark buffer.

The cases that matter are the two boundaries the module is built around:
marks key off *object identity* (not the resolved identity two anonymous
siblings share), and they survive the hot reload that lands in the middle of
essentially every real use.
"""

from __future__ import annotations

from typing import Any

import pytest

from nuiitivet.dev.comments import Comments, see_comments
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def test_add_marks_a_node_once_and_remove_takes_it_by_number() -> None:
    node = Text("AAA")
    comments = Comments()

    assert comments.add(node) is True
    assert comments.add(node) is False, "already marked"
    assert comments.members() == [node]
    assert comments.index_of(node) == 1

    assert comments.remove(1) is True
    assert comments.members() == []
    assert comments.index_of(node) is None
    assert comments.remove(1) is False


def test_remove_renumbers_the_marks_after_it_and_is_one_undo_step() -> None:
    first, second, third = Text("A"), Text("B"), Text("C")
    comments = Comments()
    comments.add(first)
    comments.add(second)
    comments.add(third)
    comments.write(3, "last")
    comments.enter()

    assert comments.remove(2) is True

    assert comments.members() == [first, third]
    assert comments.editable_line(2) == "last", "the third mark is now the second"
    assert comments.undo() is True
    assert comments.members() == [first, second, third]


def test_two_anonymous_siblings_are_marked_independently() -> None:
    """The object-identity boundary.

    Both resolve to the same ``{"type", "label"}`` dict, so a set keyed on the
    resolved identity would treat marking the second as removing the first.
    """
    first, second = Text("SAME"), Text("SAME")
    comments = Comments()

    comments.add(first)
    comments.add(second)

    assert comments.members() == [first, second]


def test_undo_steps_back_through_the_session_and_redo_forward() -> None:
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.enter()
    comments.add(first)
    comments.add(second)
    comments.write(2, "wider")

    assert comments.undo() is True
    assert comments.editable_line(2) is None, "the text went, the mark stayed"
    assert comments.undo() is True
    assert comments.members() == [first]

    assert comments.redo() is True
    assert comments.redo() is True
    assert comments.members() == [first, second] and comments.editable_line(2) == "wider"
    assert comments.redo() is False


def test_undo_brings_back_a_mark_the_session_removed() -> None:
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.add(first)
    comments.add(second)
    comments.enter()
    comments.remove(1)
    assert comments.members() == [second]

    comments.undo()

    assert comments.members() == [first, second], "back in its place, not appended"


def test_undo_reaches_no_further_than_the_last_send() -> None:
    """What the agent was sent is not the human's to undo."""
    leaf = Text("A")
    comments = Comments()
    comments.enter()
    comments.add(leaf)

    comments.send()

    assert comments.undoable is False
    assert comments.undo() is False
    assert comments.members() == [leaf]


def test_a_new_change_drops_what_could_be_redone() -> None:
    comments = Comments()
    comments.enter()
    comments.add(Text("A"))
    comments.undo()
    assert comments.redoable is True

    comments.add_region((0.0, 0.0, 10.0, 10.0))

    assert comments.redoable is False


def test_undo_outside_a_session_does_nothing() -> None:
    leaf = Text("A")
    comments = Comments()
    comments.add(leaf)

    assert comments.undo() is False
    assert comments.members() == [leaf]


def test_seq_bumps_on_every_change() -> None:
    """What lets an agent notice a mark from the cheap status roll-up."""
    node = Text("A")
    comments = Comments()
    seen = [comments.summary()["seq"]]

    comments.enter()
    seen.append(comments.summary()["seq"])
    comments.add(node)
    seen.append(comments.summary()["seq"])
    comments.leave()
    seen.append(comments.summary()["seq"])

    assert seen == sorted(set(seen)), f"seq must strictly increase, got {seen}"


def test_mode_latches_once() -> None:
    comments = Comments()
    comments.enter()
    after_enter = comments.summary()["seq"]

    comments.enter()

    assert comments.active is True
    assert comments.summary()["seq"] == after_enter


def test_summary_counts_nodes_and_regions_separately() -> None:
    comments = Comments()
    comments.add(Text("A"))

    summary = comments.summary()

    assert summary["nodes"] == 1
    assert summary["regions"] == 0


def test_a_dead_member_disappears_from_the_members_list() -> None:
    """Members are weak, so a mark never keeps a detached subtree alive."""
    comments = Comments()
    node: Any = Text("A")
    comments.add(node)
    del node

    import gc

    gc.collect()

    assert comments.members() == []


# --- hot reload -------------------------------------------------------------


def _keyed(text: str, key: str) -> Any:
    """A ``Text`` carrying a stable key, which is what anchors a path across a reload."""
    return Text(text, key=key)


def _tree(label: str) -> Column:
    return Column(children=[_keyed("HEADER", "header"), _keyed(label, "body")])


def test_restore_re_resolves_members_by_structural_path() -> None:
    """The normal case: the agent's own fix rebuilds the tree mid-mark."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        target = old.children[1]
        comments = Comments()
        comments.add(target, root=host.root)

    new = _tree("AFTER")
    with mount(new) as host:
        host.layout(300, 200)

        assert comments.restore(host.root) == 1
        assert comments.members() == [new.children[1]]
        assert comments.lost == 0


def test_restore_counts_members_it_could_not_find() -> None:
    """A quietly truncated set is the worst outcome, so misses are reported."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(old.children[0], root=host.root)
        comments.add(old.children[1], root=host.root)

    shrunk = Column(children=[_keyed("HEADER", "header")])
    with mount(shrunk) as host:
        host.layout(300, 200)

        assert comments.restore(host.root) == 1
        assert comments.lost == 1


# --- payload ----------------------------------------------------------------


def test_see_comments_reports_identity_rect_path_and_scoped_views() -> None:
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(tree.children[1], root=host.root)

        payload = see_comments(host.root, comments)

    assert payload["regions"] == []
    assert payload["lost_marks"] == 0
    (node,) = payload["nodes"]
    assert node["index"] == 1
    assert node["key"] == "body"
    assert node["path"][-1] == "TextBase"
    assert "rect" in node
    assert node["tree"]["type"] == "TextBase"
    assert "state" in node


def test_a_node_is_described_as_itself_not_as_its_keyed_ancestor() -> None:
    """"What did I point at" and "how do I drive it" are different questions.

    ``resolve_target`` walks up to the keyed ancestor, which is right for an
    action and wrong as the whole answer here: reporting the ancestor's identity
    beside the picked node's rect, path and tree describes neither node.
    """
    inner = Text("increment")
    button = Column(children=[inner], key="increment-btn")
    with mount(button) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(inner, root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert node["type"] == "TextBase"
    assert "key" not in node
    assert node["tree"]["type"] == "TextBase"
    assert node["target"] == {"type": "Column", "key": "increment-btn", "label": "increment"}


def test_target_is_omitted_when_it_would_restate_the_node() -> None:
    """A marked node that carries its own key needs no separate target."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(tree.children[1], root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert "target" not in node


def test_see_comments_without_a_buffer_is_an_empty_payload() -> None:
    """The bridge runs without one in tests; that reads as nothing marked."""
    payload = see_comments(None, None)

    assert payload == {"seq": 0, "sent": 0, "nodes": [], "regions": [], "lost_marks": 0}


# --- regions ---------------------------------------------------------


def test_a_region_is_marked_and_numbered_alongside_nodes() -> None:
    """One ordinal sequence across both, because the human sees one numbering."""
    node = Text("A")
    comments = Comments()

    comments.add(node)
    comments.add_region((10.0, 10.0, 40.0, 20.0))
    comments.add(Text("B"))

    assert [(index, kind) for index, kind, _mark in comments.marks()] == [
        (1, "node"),
        (2, "region"),
        (3, "node"),
    ]


def test_a_zero_area_drag_is_not_a_region() -> None:
    """That is a click the gesture layer failed to classify, not an area."""
    comments = Comments()

    comments.add_region((10.0, 10.0, 0.0, 20.0))

    assert comments.regions() == []


def test_undo_takes_back_whichever_kind_came_last() -> None:
    comments = Comments()
    comments.enter()
    comments.add(Text("A"))
    comments.add_region((0.0, 0.0, 10.0, 10.0))

    comments.undo()

    assert comments.regions() == []
    assert len(comments.members()) == 1


def test_summary_counts_the_two_kinds_apart() -> None:
    comments = Comments()
    comments.add(Text("A"))
    comments.add_region((0.0, 0.0, 10.0, 10.0))

    assert comments.summary()["nodes"] == 1
    assert comments.summary()["regions"] == 1


def test_a_region_survives_a_reload_untouched() -> None:
    """A rect is stable across a rebuild by construction, so there is nothing to
    re-resolve and nothing that can be lost."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add_region((5.0, 5.0, 50.0, 50.0))
        comments.add(old.children[1], root=host.root)

    with mount(_tree("AFTER")) as host:
        host.layout(300, 200)
        comments.restore(host.root)

    assert comments.regions() == [(5.0, 5.0, 50.0, 50.0)]
    assert comments.lost == 0


def test_a_region_payload_is_derived_from_the_tree_as_it_is_now() -> None:
    """Not frozen when it was drawn -- which is what makes it a continuing
    observation point rather than a single-use note."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        host.settle()
        comments = Comments()
        comments.add_region((0.0, 0.0, 300.0, 200.0))

        (region,) = see_comments(host.root, comments)["regions"]

    assert region["index"] == 1
    assert region["rect"] == [0.0, 0.0, 300.0, 200.0]
    assert "children" in region["container"]
    assert "path" in region["container"]
    assert region["contents"]


def test_a_region_over_blank_space_still_names_its_container() -> None:
    """The empty list is the signal, not a failure: the container answers."""
    tree = Column(children=[_keyed("BODY", "body")], padding=40)
    with mount(tree) as host:
        host.layout(300, 200)
        host.settle()
        comments = Comments()
        comments.add_region((2.0, 2.0, 12.0, 12.0))

        (region,) = see_comments(host.root, comments)["regions"]

    assert region["contents"] == []
    assert region["container"]["type"] == "Column"
    assert region["container"]["children"]


def test_a_region_reports_the_structure_it_crosses_without_collapsing_it() -> None:
    """Both readings of a rectangle are served, because geometry cannot choose.

    ``container`` answers "I mean the space between things"; ``contents`` answers
    "I mean these things". A band down a column used to report only the column,
    which is the one thing the human already knew.
    """
    first, second = _keyed("ONE", "one"), _keyed("TWO", "two")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        host.settle()
        comments = Comments()
        comments.add_region((0.0, 0.0, 6.0, 200.0))

        (region,) = see_comments(host.root, comments)["regions"]

    def keys(entries: list[dict[str, Any]]) -> set[str]:
        found: set[str] = set()
        for entry in entries:
            if "key" in entry:
                found.add(entry["key"])
            found |= keys(entry.get("children", []))
        return found

    assert keys(region["contents"]) == {"one", "two"}


def test_a_node_kept_only_for_a_descendant_carries_no_relation() -> None:
    """It is on the path to the answer, not part of it."""
    leaf = _keyed("LEAF", "leaf")
    with mount(Column(children=[Column(children=[leaf], padding=20)])) as host:
        host.layout(300, 200)
        host.settle()
        rect = leaf.global_layout_rect
        assert rect is not None
        comments = Comments()
        # A little wider than the leaf, so the enclosing container is its parent
        # and the leaf itself lands wholly inside the region.
        comments.add_region(
            (float(rect[0]) - 4, float(rect[1]) - 4, float(rect[2]) + 8, float(rect[3]) + 8)
        )

        (region,) = see_comments(host.root, comments)["regions"]

    def find(entries: list[dict[str, Any]], key: str) -> dict[str, Any]:
        for entry in entries:
            if entry.get("key") == key:
                return entry
            hit = find(entry.get("children", []), key)
            if hit:
                return hit
        return {}

    assert find(region["contents"], "leaf")["relation"] == "contained"


# --- construction site -----------------------------------------------


def test_a_marked_node_carries_where_it_was_built() -> None:
    """The step after "which widget is this": which line built it.

    Without it, an app passing no ``key=`` leaves the reader a chain of
    anonymous types and a grep -- which is how this was found.
    """
    from nuiitivet.dev import source

    source.install()
    try:
        tree = _tree("BODY")
        with mount(tree) as host:
            host.layout(300, 200)
            comments = Comments()
            comments.add(tree.children[1], root=host.root)

            (node,) = see_comments(host.root, comments)["nodes"]
    finally:
        source.uninstall()

    assert node["source"][0]["target"] is True
    assert node["source"][0]["file"].endswith("test_comments.py")
    assert node["source"][0]["line"] > 0


def test_the_payload_omits_source_when_nothing_is_recording() -> None:
    """A production-shaped run reports no field at all, rather than nulls."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(tree.children[1], root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert "source" not in node


def test_a_node_payload_names_the_owning_window() -> None:
    """The comments spans windows; each node names its own for ``window=``."""
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    main_content = Container()
    app = App(Window(content=main_content))
    second_content = Container()
    second = Window(content=second_content).open()

    comments = Comments()
    comments.add(main_content, root=app.main_window.root)
    comments.add(second_content, root=second.root)

    nodes = see_comments(app.main_window.root, comments)["nodes"]

    assert [node["window"] for node in nodes] == [app.main_window.id, second.id]


def test_a_bare_tree_payload_carries_no_window() -> None:
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(tree.children[1], root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert "window" not in node


# --- instructions -----------------------------------------------------------


def test_an_instruction_is_written_on_a_mark_by_its_number() -> None:
    first, second = Text("AAA"), Text("BBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(first, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))

        assert comments.write(2, "close this gap") is True
        assert comments.editable_line(1) is None
        assert comments.editable_line(2) == "close this gap"
        assert comments.write(3, "nothing here") is False


def test_a_blank_instruction_clears_the_text() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(leaf, root=host.root)
        comments.write(1, "wider")

        comments.write(1, "   ")

        assert comments.editable_line(1) is None
        assert comments.summary()["instructions"] == 0


def test_the_payload_carries_each_marks_thread_with_who_wrote_every_line() -> None:
    first, second = Text("AAA"), Text("BBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(first, root=host.root)
        comments.add(second, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))
        comments.write(1, "make this wider")
        comments.answer(1, "done", "240 wide now")
        comments.write(1, "a bit more")
        comments.write(3, "close this gap")

        payload = see_comments(host.root, comments)

        one, two = payload["nodes"]
        assert one["thread"] == [
            {"by": "human", "text": "make this wider"},
            {"by": "agent", "outcome": "done", "text": "240 wide now"},
            {"by": "human", "text": "a bit more"},
        ]
        assert list(one)[:3] == ["index", "awaiting", "thread"], "the words come first"
        assert two["thread"] == [], "a bare mark is still a comment"
        (region,) = payload["regions"]
        assert region["thread"] == [{"by": "human", "text": "close this gap"}]


# --- the thread ---------------------------------------------------------------


def _one_mark() -> tuple[Comments, Any]:
    leaf = Text("AAA")
    comments = Comments()
    comments.enter()
    comments.add(leaf)
    return (comments, leaf)


def test_writing_after_an_answer_is_a_new_line_and_blank_text_then_changes_nothing() -> None:
    comments, _leaf = _one_mark()
    comments.write(1, "wider")
    comments.answer(1, "done", "240 wide now")
    assert comments.editable_line(1) is None, "the answered line is not the field's to edit"

    comments.write(1, "   ")
    assert len(comments.thread(1)) == 2

    comments.write(1, "a bit more")
    comments.write(1, "a lot more")

    assert [line.text for line in comments.thread(1)] == ["wider", "240 wide now", "a lot more"]
    assert comments.editable_line(1) == "a lot more"


def test_an_answer_does_not_bump_seq_and_is_refused_for_a_mark_that_is_not_there() -> None:
    comments, _leaf = _one_mark()
    before = comments.summary()["seq"]

    assert comments.answer(1, "refused", "it is bound to a name") is True
    assert comments.answer(2, "done", "") is False

    assert comments.summary()["seq"] == before, "the agent wrote it; nothing new for the agent to read"
    with pytest.raises(ValueError):
        comments.answer(1, "maybe", "")


def test_the_outcome_is_the_answer_that_ends_the_thread() -> None:
    comments, _leaf = _one_mark()
    assert comments.outcome(1) is None
    comments.send()

    comments.answer(1, "question", "which column?")
    assert comments.outcome(1) == "question"

    comments.write(1, "the left one")
    assert comments.outcome(1) is None, "a reply is the human's turn again"
    assert comments.outcome(2) is None


def test_an_answered_mark_stays_until_the_human_removes_it() -> None:
    """Whatever the outcome: the human has Delete, and the agent's done is not a verdict on the mark."""
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.enter()
    comments.add(first)
    comments.add(second)
    comments.send()
    comments.answer(1, "done", "")
    comments.answer(2, "refused", "")

    comments.write(2, "not quite")
    comments.send()
    comments.leave()

    assert comments.members() == [first, second]


def test_an_answer_survives_undo_and_redo() -> None:
    """The answer is not the human's change, so no step of theirs takes it back."""
    comments, _leaf = _one_mark()
    comments.write(1, "wider")
    comments.send()
    comments.add_region((0.0, 0.0, 10.0, 10.0))
    comments.write(2, "this gap")

    comments.answer(1, "done", "240 wide now")
    comments.answer(2, "question", "which gap?")

    comments.undo()
    assert comments.outcome(1) == "done" and comments.outcome(2) == "question"
    comments.redo()
    assert comments.outcome(2) == "question"


def test_a_thread_survives_a_reload_with_its_mark() -> None:
    comments = Comments()
    with mount(_tree("AAA")) as host:
        host.layout(300, 200)
        comments.add(host.root.children[0], root=host.root)
        comments.write(1, "wider")
        comments.answer(1, "done", "240 wide now")
    with mount(_tree("AAA")) as rebuilt:
        rebuilt.layout(300, 200)

        assert comments.restore(rebuilt.root) == 1
        assert [line.by for line in comments.thread(1)] == ["human", "agent"]


def test_the_summary_counts_marks_that_carry_text() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(leaf, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))
        before = comments.summary()["seq"]

        comments.write(2, "close this gap")

        summary = comments.summary()
        assert summary["instructions"] == 1
        assert summary["seq"] > before, "an agent polling status must notice the text"


def test_an_instruction_survives_a_reload_with_its_mark() -> None:
    comments = Comments()
    with mount(_tree("AAA")) as host:
        host.layout(300, 200)
        comments.add(host.root.children[0], root=host.root)
        comments.write(1, "wider")
    with mount(_tree("AAA")) as rebuilt:
        rebuilt.layout(300, 200)

        assert comments.restore(rebuilt.root) == 1
        assert comments.editable_line(1) == "wider"


def test_leaving_keeps_everything_and_the_next_session_goes_on_from_there() -> None:
    """Back from a look at the app, or from layout edit mode, with the undo history intact."""
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.enter()
        comments.add(leaf, root=host.root)
        comments.write(1, "wider")
        comments.leave()
        assert comments.members() == [leaf] and comments.editable_line(1) == "wider"

        comments.enter()
        comments.undo()

        assert comments.members() == [leaf] and comments.editable_line(1) is None

# --- sending -----------------------------------------------------------------


def test_a_send_takes_what_changed_and_nothing_twice() -> None:
    comments, _leaf = _one_mark()
    assert comments.unsent is True

    assert comments.send() is True

    assert comments.unsent is False
    assert comments.summary()["sent"] == comments.summary()["seq"]
    assert comments.send() is False, "nothing new for the agent"
    comments.write(1, "wider")
    assert comments.unsent is True


def test_the_payload_says_which_marks_await_an_answer() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.add(leaf, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))
        comments.send()
        comments.answer(2, "done", "")

        payload = see_comments(host.root, comments)

        assert payload["nodes"][0]["awaiting"] is True
        assert payload["regions"][0]["awaiting"] is False


def test_a_sent_mark_awaits_an_answer_until_one_comes_or_the_human_writes_again() -> None:
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.enter()
    comments.add(first)
    comments.add(second)
    assert not comments.awaiting(1) and not comments.awaiting(2), "not sent yet"

    comments.send()

    assert comments.awaiting(1) and comments.awaiting(2)
    comments.answer(1, "done", "")
    assert not comments.awaiting(1), "answered"
    comments.write(2, "wider")
    assert not comments.awaiting(2), "changed since the send, so not sent yet"
    comments.send()
    assert comments.awaiting(2) and not comments.awaiting(1), "an answered mark is not asked again"
    assert comments.awaiting(3) is False


def test_undoing_a_reply_leaves_the_mark_as_it_was_sent() -> None:
    comments, _leaf = _one_mark()
    comments.send()
    comments.write(1, "a reply")
    assert not comments.awaiting(1)

    comments.undo()

    assert comments.awaiting(1)


def test_wait_returns_on_a_send_and_times_out_otherwise() -> None:
    import threading

    comments, _leaf = _one_mark()
    sent = comments.summary()["sent"]
    assert comments.wait(sent, 0.02) is False

    woke: list[bool] = []
    waiter = threading.Thread(target=lambda: woke.append(comments.wait(sent, 5.0)))
    waiter.start()
    comments.send()
    waiter.join(timeout=5.0)

    assert woke == [True]
    assert comments.wait(sent, 0.0) is True, "a send before the call satisfies it at once"


def test_leaving_does_not_wake_a_wait() -> None:
    """Only a send is the human's hand-over."""
    import threading

    comments, _leaf = _one_mark()
    sent = comments.summary()["sent"]
    woke: list[bool] = []
    waiter = threading.Thread(target=lambda: woke.append(comments.wait(sent, 0.2)))
    waiter.start()
    comments.leave()
    comments.enter()
    waiter.join(timeout=5.0)

    assert woke == [False]


def test_closing_releases_a_wait() -> None:
    import threading

    comments, _leaf = _one_mark()
    woke: list[bool] = []
    waiter = threading.Thread(target=lambda: woke.append(comments.wait(0, 30.0)))
    waiter.start()
    comments.close()
    waiter.join(timeout=5.0)

    assert not waiter.is_alive() and woke == [False]
