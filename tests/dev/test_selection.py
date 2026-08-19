"""Tests for the inspect-mode designation buffer (#591).

The cases that matter are the two boundaries the module is built around:
designations key off *object identity* (not the resolved identity two anonymous
siblings share), and they survive the hot reload that lands in the middle of
essentially every real use.
"""

from __future__ import annotations

from typing import Any

from nuiitivet.dev.selection import Selection, describe_selection
from nuiitivet.layout.column import Column
from nuiitivet.modifiers.keyed import keyed
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
    selection.leave()
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
    return Text(text).modifier(keyed(key))


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

        payload = describe_selection(selection)

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
    button = Column(children=[inner]).modifier(keyed("increment-btn"))
    with mount(button) as host:
        host.layout(300, 200)
        selection = Selection()
        selection.toggle(inner, root=host.root)

        (node,) = describe_selection(selection)["nodes"]

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

        (node,) = describe_selection(selection)["nodes"]

    assert "target" not in node


def test_describe_selection_without_a_selection_is_an_empty_payload() -> None:
    """The bridge runs without one in tests; that reads as nothing designated."""
    payload = describe_selection(None)

    assert payload == {"seq": 0, "active": False, "nodes": [], "regions": [], "lost": 0}
