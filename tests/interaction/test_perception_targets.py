"""Tests for target resolution (``find_targets`` / ``find_target``)."""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet._interaction.perception import find_target, find_targets


class _Node:
    """Fake widget with the parent links the outermost-wins rule walks."""

    def __init__(self, **identity: Any) -> None:
        self.children: list[_Node] = []
        self.built_child: Optional[_Node] = None
        self.parent: Optional[_Node] = None
        for name, value in identity.items():
            setattr(self, name, value)

    def add(self, *children: "_Node") -> "_Node":
        for child in children:
            child.parent = self
            self.children.append(child)
        return self


def test_find_targets_reports_every_distinct_match() -> None:
    first, second = _Node(label="Done"), _Node(label="Done")
    root = _Node().add(first, _Node(label="Cancel"), second)

    assert find_targets(root, label="Done") == [first, second]


def test_find_targets_collapses_a_match_inside_a_match() -> None:
    """A composite that surfaces the identity it composes into a child.

    No widget does this today -- a Material button holds no ``label`` of its own
    -- but the day one does, both it and its inner ``Text`` would answer to the
    same ``label=``, and a caller means the button.
    """
    inner = _Node(text="Save")
    button = _Node(label="Save").add(inner)
    root = _Node().add(button)

    assert find_targets(root, label="Save") == [button]


def test_find_targets_matches_key_or_label_independently() -> None:
    by_key = _Node(key="submit")
    by_label = _Node(label="Submit")
    root = _Node().add(by_key, by_label)

    assert find_targets(root, key="submit", label="Submit") == [by_key, by_label]


def test_find_targets_without_an_identifier_is_empty() -> None:
    assert find_targets(_Node(key="submit")) == []
    assert find_targets(None, key="submit") == []


def test_find_target_returns_the_outermost_first_match() -> None:
    inner = _Node(text="Save")
    button = _Node(label="Save").add(inner)
    root = _Node().add(_Node(label="Cancel"), button, _Node(label="Save"))

    assert find_target(root, label="Save") is button
    assert find_target(root, label="Nothing") is None
