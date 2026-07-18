"""Tests for the structural tree description (``describe_tree``)."""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.dev.perception import describe_tree, find_target


class _Obs:
    """Minimal observable-like value (has ``.value``)."""

    def __init__(self, value: Any) -> None:
        self.value = value


class _Node:
    """A fake widget exposing the attributes ``describe_tree`` reads."""

    def __init__(
        self,
        *,
        children: Optional[list["_Node"]] = None,
        built_child: Optional["_Node"] = None,
        rect: Optional[tuple[int, int, int, int]] = None,
        **identity: Any,
    ) -> None:
        self.children = children or []
        self.built_child = built_child
        self.global_layout_rect = rect
        for name, value in identity.items():
            setattr(self, name, value)


def test_describe_tree_reports_type_and_rect() -> None:
    root = _Node(rect=(1, 2, 30, 40))
    tree = describe_tree(root)
    assert tree["type"] == "_Node"
    assert tree["rect"] == [1, 2, 30, 40]


def test_describe_tree_none_root_is_empty() -> None:
    assert describe_tree(None) == {}


def test_describe_tree_unwraps_observable_label() -> None:
    root = _Node(label=_Obs("increment"))
    tree = describe_tree(root)
    assert tree["label"] == "increment"


def test_describe_tree_ignores_non_scalar_identity() -> None:
    # A button's ``label`` may be a child widget, not text — it must be skipped.
    child_widget = _Node()
    root = _Node(label=child_widget)
    tree = describe_tree(root)
    assert "label" not in tree


def test_describe_tree_descends_children_and_built_child() -> None:
    leaf = _Node(text="hello", rect=(0, 0, 5, 5))
    composed = _Node(built_child=_Node(text="built"))
    root = _Node(children=[leaf, composed])

    tree = describe_tree(root)
    children = tree["children"]
    assert children[0]["text"] == "hello"
    # The composed node surfaces its built subtree as a child.
    assert children[1]["children"][0]["text"] == "built"


def test_describe_tree_is_cycle_safe() -> None:
    a = _Node()
    b = _Node(children=[a])
    a.children.append(b)  # cycle a -> b -> a
    # Should terminate rather than recurse forever.
    tree = describe_tree(a)
    assert tree["type"] == "_Node"


def test_describe_tree_truncates_long_identity() -> None:
    root = _Node(text="x" * 500)
    tree = describe_tree(root)
    assert len(tree["text"]) <= 120
    assert tree["text"].endswith("…")


def test_find_target_by_key() -> None:
    target = _Node(key="submit")
    root = _Node(children=[_Node(key="cancel"), target])
    assert find_target(root, key="submit") is target


def test_find_target_by_label_matches_text_and_title() -> None:
    by_text = _Node(text="increment")
    by_title = _Node(title="Settings")
    root = _Node(children=[by_text, by_title])
    assert find_target(root, label="increment") is by_text
    assert find_target(root, label="Settings") is by_title


def test_find_target_unwraps_observable_identity() -> None:
    target = _Node(label=_Obs("increment"))
    root = _Node(children=[target])
    assert find_target(root, label="increment") is target


def test_find_target_descends_built_child() -> None:
    target = _Node(key="deep")
    root = _Node(built_child=_Node(children=[target]))
    assert find_target(root, key="deep") is target


def test_find_target_returns_first_match_depth_first() -> None:
    first = _Node(label="dup")
    second = _Node(label="dup")
    root = _Node(children=[first, second])
    assert find_target(root, label="dup") is first


def test_find_target_no_match_or_no_query() -> None:
    root = _Node(children=[_Node(key="a")])
    assert find_target(root, key="missing") is None
    assert find_target(root) is None
    assert find_target(None, key="a") is None
