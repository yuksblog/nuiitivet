"""Tests for the inspect-mode designation buffer.

The cases that matter are the two boundaries the module is built around:
designations key off *object identity* (not the resolved identity two anonymous
siblings share), and they survive the hot reload that lands in the middle of
essentially every real use.
"""

from __future__ import annotations

from typing import Any

from nuiitivet.dev.selection import Selection, describe_selection
from nuiitivet.layout.column import Column
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def test_toggle_adds_then_removes() -> None:
    node = Text("AAA")
    selection = Selection()

    assert selection.toggle(node) is True
    assert selection.members() == [node]
    assert selection.toggle(node) is False
    assert selection.members() == []


def test_two_anonymous_siblings_are_designated_independently() -> None:
    """The object-identity boundary.

    Both resolve to the same ``{"type", "label"}`` dict, so a set keyed on the
    resolved identity would treat designating the second as removing the first.
    """
    first, second = Text("SAME"), Text("SAME")
    selection = Selection()

    selection.toggle(first)
    selection.toggle(second)

    assert selection.members() == [first, second]


def test_replace_last_refines_rather_than_appends() -> None:
    """The ancestor walk: one designation being moved, not several being made."""
    first, second, walked = Text("A"), Text("B"), Text("C")
    selection = Selection()
    selection.toggle(first)
    selection.toggle(second)

    selection.replace_last(walked)

    assert selection.members() == [first, walked]


def test_replace_last_on_an_empty_selection_designates() -> None:
    node = Text("A")
    selection = Selection()

    selection.replace_last(node)

    assert selection.members() == [node]


def test_remove_last_drops_the_newest() -> None:
    first, second = Text("A"), Text("B")
    selection = Selection()
    selection.toggle(first)
    selection.toggle(second)

    selection.remove_last()

    assert selection.members() == [first]


def test_seq_bumps_on_every_change() -> None:
    """What lets an assistant notice a designation from the cheap status roll-up."""
    node = Text("A")
    selection = Selection()
    seen = [selection.summary()["seq"]]

    selection.enter()
    seen.append(selection.summary()["seq"])
    selection.toggle(node)
    seen.append(selection.summary()["seq"])
    selection.commit()
    seen.append(selection.summary()["seq"])

    assert seen == sorted(set(seen)), f"seq must strictly increase, got {seen}"


def test_mode_latches_once() -> None:
    selection = Selection()
    selection.enter()
    after_enter = selection.summary()["seq"]

    selection.enter()

    assert selection.active is True
    assert selection.summary()["seq"] == after_enter


def test_summary_counts_nodes_and_regions_separately() -> None:
    selection = Selection()
    selection.toggle(Text("A"))

    summary = selection.summary()

    assert summary["nodes"] == 1
    assert summary["regions"] == 0


def test_a_dead_member_disappears_from_the_members_list() -> None:
    """Members are weak, so a designation never keeps a detached subtree alive."""
    selection = Selection()
    node: Any = Text("A")
    selection.toggle(node)
    del node

    import gc

    gc.collect()

    assert selection.members() == []


# --- hot reload -------------------------------------------------------------


def _keyed(text: str, key: str) -> Any:
    """A ``Text`` carrying a stable key, which is what anchors a path across a reload."""
    return Text(text, key=key)


def _tree(label: str) -> Column:
    return Column(children=[_keyed("HEADER", "header"), _keyed(label, "body")])


def test_restore_re_resolves_members_by_structural_path() -> None:
    """The normal case: the assistant's own fix rebuilds the tree mid-designation."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        target = old.children[1]
        selection = Selection()
        selection.toggle(target, root=host.root)

    new = _tree("AFTER")
    with mount(new) as host:
        host.layout(300, 200)

        assert selection.restore(host.root) == 1
        assert selection.members() == [new.children[1]]
        assert selection.lost == 0


def test_restore_counts_members_it_could_not_find() -> None:
    """A quietly truncated set is the worst outcome, so misses are reported."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(old.children[0], root=host.root)
        selection.toggle(old.children[1], root=host.root)

    shrunk = Column(children=[_keyed("HEADER", "header")])
    with mount(shrunk) as host:
        host.layout(300, 200)

        assert selection.restore(host.root) == 1
        assert selection.lost == 1


# --- payload ----------------------------------------------------------------


def test_describe_selection_reports_identity_rect_path_and_scoped_views() -> None:
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(tree.children[1], root=host.root)

        payload = describe_selection(host.root, selection)

    assert payload["regions"] == []
    assert payload["lost"] == 0
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
        selection = Selection()
        selection.toggle(inner, root=host.root)

        (node,) = describe_selection(host.root, selection)["nodes"]

    assert node["type"] == "TextBase"
    assert "key" not in node
    assert node["tree"]["type"] == "TextBase"
    assert node["target"] == {"type": "Column", "key": "increment-btn", "label": "increment"}


def test_target_is_omitted_when_it_would_restate_the_node() -> None:
    """A designated node that carries its own key needs no separate target."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(tree.children[1], root=host.root)

        (node,) = describe_selection(host.root, selection)["nodes"]

    assert "target" not in node


def test_describe_selection_without_a_selection_is_an_empty_payload() -> None:
    """The bridge runs without one in tests; that reads as nothing designated."""
    payload = describe_selection(None, None)

    assert payload == {"seq": 0, "active": False, "nodes": [], "regions": [], "lost": 0}


# --- regions ---------------------------------------------------------


def test_a_region_is_designated_and_numbered_alongside_nodes() -> None:
    """One ordinal sequence across both, because the human sees one numbering."""
    node = Text("A")
    selection = Selection()

    selection.toggle(node)
    selection.add_region((10.0, 10.0, 40.0, 20.0))
    selection.toggle(Text("B"))

    assert [(index, kind) for index, kind, _mark in selection.marks()] == [
        (1, "node"),
        (2, "region"),
        (3, "node"),
    ]


def test_a_zero_area_drag_is_not_a_region() -> None:
    """That is a click the gesture layer failed to classify, not an area."""
    selection = Selection()

    selection.add_region((10.0, 10.0, 0.0, 20.0))

    assert selection.regions() == []


def test_the_ancestor_walk_skips_regions() -> None:
    """A walk has no meaning for an area, so one drawn after a node must not put
    the node out of the walk's reach."""
    first, walked = Text("A"), Text("B")
    selection = Selection()
    selection.toggle(first)
    selection.add_region((0.0, 0.0, 10.0, 10.0))

    selection.replace_last(walked)

    assert selection.members() == [walked]
    assert len(selection.regions()) == 1


def test_backspace_removes_whichever_kind_came_last() -> None:
    selection = Selection()
    selection.toggle(Text("A"))
    selection.add_region((0.0, 0.0, 10.0, 10.0))

    selection.remove_last()

    assert selection.regions() == []
    assert len(selection.members()) == 1


def test_summary_counts_the_two_kinds_apart() -> None:
    selection = Selection()
    selection.toggle(Text("A"))
    selection.add_region((0.0, 0.0, 10.0, 10.0))

    assert selection.summary()["nodes"] == 1
    assert selection.summary()["regions"] == 1


def test_a_region_survives_a_reload_untouched() -> None:
    """A rect is stable across a rebuild by construction, so there is nothing to
    re-resolve and nothing that can be lost."""
    old = _tree("BEFORE")
    with mount(old) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.add_region((5.0, 5.0, 50.0, 50.0))
        selection.toggle(old.children[1], root=host.root)

    with mount(_tree("AFTER")) as host:
        host.layout(300, 200)
        selection.restore(host.root)

    assert selection.regions() == [(5.0, 5.0, 50.0, 50.0)]
    assert selection.lost == 0


def test_a_region_payload_is_derived_from_the_tree_as_it_is_now() -> None:
    """Not frozen when it was drawn -- which is what makes it a continuing
    observation point rather than a single-use note."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        host.settle()
        selection = Selection()
        selection.add_region((0.0, 0.0, 300.0, 200.0))

        (region,) = describe_selection(host.root, selection)["regions"]

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
        selection = Selection()
        selection.add_region((2.0, 2.0, 12.0, 12.0))

        (region,) = describe_selection(host.root, selection)["regions"]

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
        selection = Selection()
        selection.add_region((0.0, 0.0, 6.0, 200.0))

        (region,) = describe_selection(host.root, selection)["regions"]

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
        selection = Selection()
        # A little wider than the leaf, so the enclosing container is its parent
        # and the leaf itself lands wholly inside the region.
        selection.add_region(
            (float(rect[0]) - 4, float(rect[1]) - 4, float(rect[2]) + 8, float(rect[3]) + 8)
        )

        (region,) = describe_selection(host.root, selection)["regions"]

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


def test_a_designated_node_carries_where_it_was_built() -> None:
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
            selection = Selection()
            selection.toggle(tree.children[1], root=host.root)

            (node,) = describe_selection(host.root, selection)["nodes"]
    finally:
        source.uninstall()

    assert node["source"][0]["target"] is True
    assert node["source"][0]["file"].endswith("test_selection.py")
    assert node["source"][0]["line"] > 0


def test_the_payload_omits_source_when_nothing_is_recording() -> None:
    """A production-shaped run reports no field at all, rather than nulls."""
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(tree.children[1], root=host.root)

        (node,) = describe_selection(host.root, selection)["nodes"]

    assert "source" not in node


def test_a_node_payload_names_the_owning_window() -> None:
    """The selection spans windows; each node names its own for ``window=``."""
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    main_content = Container()
    app = App(Window(content=main_content))
    second_content = Container()
    second = Window(content=second_content).open()

    selection = Selection()
    selection.toggle(main_content, root=app.main_window.root)
    selection.toggle(second_content, root=second.root)

    nodes = describe_selection(app.main_window.root, selection)["nodes"]

    assert [node["window"] for node in nodes] == [app.main_window.id, second.id]


def test_a_bare_tree_payload_carries_no_window() -> None:
    tree = _tree("BODY")
    with mount(tree) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(tree.children[1], root=host.root)

        (node,) = describe_selection(host.root, selection)["nodes"]

    assert "window" not in node
