"""Tests for the comment-mode mark buffer.

The cases that matter are the two boundaries the module is built around:
marks key off *object identity* (not the resolved identity two anonymous
siblings share), and they survive the hot reload that lands in the middle of
essentially every real use.
"""

from __future__ import annotations

from typing import Any

from nuiitivet.dev.comments import Comments, see_comments
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def test_toggle_adds_then_removes() -> None:
    node = Text("AAA")
    comments = Comments()

    assert comments.toggle(node) is True
    assert comments.members() == [node]
    assert comments.toggle(node) is False
    assert comments.members() == []


def test_two_anonymous_siblings_are_marked_independently() -> None:
    """The object-identity boundary.

    Both resolve to the same ``{"type", "label"}`` dict, so a set keyed on the
    resolved identity would treat marking the second as removing the first.
    """
    first, second = Text("SAME"), Text("SAME")
    comments = Comments()

    comments.toggle(first)
    comments.toggle(second)

    assert comments.members() == [first, second]


def test_replace_last_refines_rather_than_appends() -> None:
    """The ancestor walk: one mark being moved, not several being made."""
    first, second, walked = Text("A"), Text("B"), Text("C")
    comments = Comments()
    comments.toggle(first)
    comments.toggle(second)

    comments.replace_last(walked)

    assert comments.members() == [first, walked]


def test_replace_last_on_an_empty_buffer_marks() -> None:
    node = Text("A")
    comments = Comments()

    comments.replace_last(node)

    assert comments.members() == [node]


def test_undo_steps_back_through_the_session_and_redo_forward() -> None:
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.enter()
    comments.toggle(first)
    comments.toggle(second)
    comments.set_instruction(2, "wider")

    assert comments.undo() is True
    assert comments.instruction(2) is None, "the text went, the mark stayed"
    assert comments.undo() is True
    assert comments.members() == [first]

    assert comments.redo() is True
    assert comments.redo() is True
    assert comments.members() == [first, second] and comments.instruction(2) == "wider"
    assert comments.redo() is False


def test_undo_brings_back_a_mark_the_session_removed() -> None:
    first, second = Text("A"), Text("B")
    comments = Comments()
    comments.toggle(first)
    comments.toggle(second)
    comments.enter()
    comments.toggle(first)
    assert comments.members() == [second]

    comments.undo()

    assert comments.members() == [first, second], "back in its place, not appended"


def test_undo_reaches_no_further_than_the_session() -> None:
    """What an earlier session kept is not this one's to undo."""
    leaf = Text("A")
    comments = Comments()
    comments.enter()
    comments.toggle(leaf)
    comments.commit()

    comments.enter()

    assert comments.undoable is False
    assert comments.undo() is False
    assert comments.members() == [leaf]


def test_a_new_change_drops_what_could_be_redone() -> None:
    comments = Comments()
    comments.enter()
    comments.toggle(Text("A"))
    comments.undo()
    assert comments.redoable is True

    comments.add_region((0.0, 0.0, 10.0, 10.0))

    assert comments.redoable is False


def test_undo_outside_a_session_does_nothing() -> None:
    leaf = Text("A")
    comments = Comments()
    comments.toggle(leaf)

    assert comments.undo() is False
    assert comments.members() == [leaf]


def test_seq_bumps_on_every_change() -> None:
    """What lets an agent notice a mark from the cheap status roll-up."""
    node = Text("A")
    comments = Comments()
    seen = [comments.summary()["seq"]]

    comments.enter()
    seen.append(comments.summary()["seq"])
    comments.toggle(node)
    seen.append(comments.summary()["seq"])
    comments.commit()
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
    comments.toggle(Text("A"))

    summary = comments.summary()

    assert summary["nodes"] == 1
    assert summary["regions"] == 0


def test_a_dead_member_disappears_from_the_members_list() -> None:
    """Members are weak, so a mark never keeps a detached subtree alive."""
    comments = Comments()
    node: Any = Text("A")
    comments.toggle(node)
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
        comments.toggle(target, root=host.root)

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
        comments.toggle(old.children[0], root=host.root)
        comments.toggle(old.children[1], root=host.root)

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
        comments.toggle(tree.children[1], root=host.root)

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
        comments.toggle(inner, root=host.root)

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
        comments.toggle(tree.children[1], root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert "target" not in node


def test_see_comments_without_a_buffer_is_an_empty_payload() -> None:
    """The bridge runs without one in tests; that reads as nothing marked."""
    payload = see_comments(None, None)

    assert payload == {"seq": 0, "committed": True, "nodes": [], "regions": [], "lost_marks": 0}


# --- regions ---------------------------------------------------------


def test_a_region_is_marked_and_numbered_alongside_nodes() -> None:
    """One ordinal sequence across both, because the human sees one numbering."""
    node = Text("A")
    comments = Comments()

    comments.toggle(node)
    comments.add_region((10.0, 10.0, 40.0, 20.0))
    comments.toggle(Text("B"))

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


def test_the_ancestor_walk_skips_regions() -> None:
    """A walk has no meaning for an area, so one drawn after a node must not put
    the node out of the walk's reach."""
    first, walked = Text("A"), Text("B")
    comments = Comments()
    comments.toggle(first)
    comments.add_region((0.0, 0.0, 10.0, 10.0))

    comments.replace_last(walked)

    assert comments.members() == [walked]
    assert len(comments.regions()) == 1


def test_undo_takes_back_whichever_kind_came_last() -> None:
    comments = Comments()
    comments.enter()
    comments.toggle(Text("A"))
    comments.add_region((0.0, 0.0, 10.0, 10.0))

    comments.undo()

    assert comments.regions() == []
    assert len(comments.members()) == 1


def test_summary_counts_the_two_kinds_apart() -> None:
    comments = Comments()
    comments.toggle(Text("A"))
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
        comments.toggle(old.children[1], root=host.root)

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
            comments.toggle(tree.children[1], root=host.root)

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
        comments.toggle(tree.children[1], root=host.root)

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
    comments.toggle(main_content, root=app.main_window.root)
    comments.toggle(second_content, root=second.root)

    nodes = see_comments(app.main_window.root, comments)["nodes"]

    assert [node["window"] for node in nodes] == [app.main_window.id, second.id]


def test_a_bare_tree_payload_carries_no_window() -> None:
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(tree.children[1], root=host.root)

        (node,) = see_comments(host.root, comments)["nodes"]

    assert "window" not in node


# --- instructions -----------------------------------------------------------


def test_an_instruction_is_written_on_a_mark_by_its_number() -> None:
    first, second = Text("AAA"), Text("BBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(first, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))

        assert comments.set_instruction(2, "close this gap") is True
        assert comments.instruction(1) is None
        assert comments.instruction(2) == "close this gap"
        assert comments.set_instruction(3, "nothing here") is False


def test_a_blank_instruction_clears_the_text() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(leaf, root=host.root)
        comments.set_instruction(1, "wider")

        comments.set_instruction(1, "   ")

        assert comments.instruction(1) is None
        assert comments.summary()["instructions"] == 0


def test_the_payload_carries_the_instruction_and_omits_it_when_there_is_none() -> None:
    first, second = Text("AAA"), Text("BBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(first, root=host.root)
        comments.toggle(second, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))
        comments.set_instruction(1, "make this wider")
        comments.set_instruction(3, "close this gap")

        payload = see_comments(host.root, comments)

        one, two = payload["nodes"]
        assert one["instruction"] == "make this wider"
        assert list(one)[:2] == ["index", "instruction"], "the human's words come first"
        assert "instruction" not in two
        (region,) = payload["regions"]
        assert region["instruction"] == "close this gap"


def test_the_summary_counts_marks_that_carry_text() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(leaf, root=host.root)
        comments.add_region((100.0, 100.0, 50.0, 40.0))
        before = comments.summary()["seq"]

        comments.set_instruction(2, "close this gap")

        summary = comments.summary()
        assert summary["instructions"] == 1
        assert summary["seq"] > before, "an agent polling status must notice the text"


def test_an_instruction_survives_a_reload_with_its_mark() -> None:
    comments = Comments()
    with mount(_tree("AAA")) as host:
        host.layout(300, 200)
        comments.toggle(host.root.children[0], root=host.root)
        comments.set_instruction(1, "wider")
    with mount(_tree("AAA")) as rebuilt:
        rebuilt.layout(300, 200)

        assert comments.restore(rebuilt.root) == 1
        assert comments.instruction(1) == "wider"


def test_the_walk_keeps_the_text_on_the_refined_mark() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(leaf, root=host.root)
        comments.set_instruction(1, "wider")

        comments.replace_last(host.root, root=host.root)

        assert comments.members() == [host.root]
        assert comments.instruction(1) == "wider"


def test_discarding_a_session_restores_the_text_as_it_was() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.enter()
        comments.toggle(leaf, root=host.root)
        comments.set_instruction(1, "wider")
        comments.commit()

        comments.enter()
        comments.set_instruction(1, "narrower")
        comments.discard()

        assert comments.instruction(1) == "wider"


# --- read receipts ----------------------------------------------------------


def test_committed_marks_are_unread_until_the_payload_is_served() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        assert comments.unread is False

        comments.enter()
        comments.toggle(leaf, root=host.root)
        assert comments.unread is False, "still writing"
        comments.commit()
        assert comments.unread is True

        see_comments(host.root, comments)

        assert comments.unread is False


def test_a_reload_does_not_make_read_marks_unread_again() -> None:
    comments = Comments()
    with mount(_tree("AAA")) as host:
        host.layout(300, 200)
        comments.toggle(host.root.children[0], root=host.root)
        see_comments(host.root, comments)
    with mount(_tree("AAA")) as rebuilt:
        rebuilt.layout(300, 200)
        comments.restore(rebuilt.root)

        assert comments.unread is False


def test_a_session_that_changed_nothing_does_not_prompt_again() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)
        comments = Comments()
        comments.toggle(leaf, root=host.root)
        see_comments(host.root, comments)

        comments.enter()
        comments.discard()
        assert comments.unread is False

        comments.enter()
        comments.set_instruction(1, "wider")
        comments.commit()
        assert comments.unread is True
