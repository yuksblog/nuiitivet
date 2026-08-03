"""Tests for the structural tree description (``describe_tree``)."""

from __future__ import annotations

from typing import Any, Optional

import pytest

from nuiitivet.animation.animatable import Animatable
from nuiitivet.dev.perception import (
    describe_state,
    describe_tree,
    find_target,
    match_condition,
)
from nuiitivet.observable.value import Observable


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


# --- match_condition (wait_for predicate) ---------------------------------


def test_match_condition_present_by_key() -> None:
    root = _Node(children=[_Node(key="spinner"), _Node(key="done")])
    assert match_condition(root, key="done") is True
    assert match_condition(root, key="missing") is False


def test_match_condition_present_by_label() -> None:
    root = _Node(children=[_Node(text="Loading…"), _Node(label="Saved")])
    assert match_condition(root, label="Saved") is True
    assert match_condition(root, label="Nope") is False


def test_match_condition_text_is_substring() -> None:
    root = _Node(children=[_Node(text="Loaded 42 rows")])
    assert match_condition(root, text="42 rows") is True
    assert match_condition(root, text="0 rows") is False


def test_match_condition_absent_inverts() -> None:
    root = _Node(children=[_Node(key="spinner")])
    # present=False is satisfied only once the target is gone.
    assert match_condition(root, key="spinner", present=False) is False
    assert match_condition(root, key="gone", present=False) is True


def test_match_condition_combines_fields() -> None:
    # A node must satisfy every supplied field together.
    root = _Node(children=[_Node(key="row", text="Alice"), _Node(key="row", text="Bob")])
    assert match_condition(root, key="row", text="Bob") is True
    assert match_condition(root, key="row", text="Carol") is False


def test_match_condition_unwraps_observable_identity() -> None:
    root = _Node(children=[_Node(label=_Obs("Ready"))])
    assert match_condition(root, label="Ready") is True


def test_match_condition_requires_a_field() -> None:
    with pytest.raises(ValueError, match="needs one of"):
        match_condition(_Node())


# --- describe_state -------------------------------------------------------


def test_describe_state_none_root_is_empty() -> None:
    assert describe_state(None) == {}


def test_describe_state_reports_observable_values() -> None:
    root = _Node()
    # Descriptor storage (``_obs_<name>``) reports under the bare name; a
    # directly-assigned observable drops its leading underscore.
    root._obs_count = Observable(3)  # type: ignore[attr-defined]
    root._enabled = Observable(True)  # type: ignore[attr-defined]

    state = describe_state(root)
    assert state["type"] == "_Node"
    assert state["state"] == {"count": 3, "enabled": True}


def test_describe_state_marks_computed_observables() -> None:
    root = _Node()
    count = Observable(2)
    root._obs_count = count  # type: ignore[attr-defined]
    root._obs_doubled = Observable.compute(lambda: count.value * 2)  # type: ignore[attr-defined]

    state = describe_state(root)
    assert state["state"]["count"] == 2
    assert state["state"]["doubled"] == {"value": 4, "kind": "computed"}


def test_describe_state_prunes_stateless_nodes_but_keeps_ancestors() -> None:
    leaf = _Node(key="deep")
    leaf._obs_value = Observable("x")  # type: ignore[attr-defined]
    middle = _Node(children=[_Node(), leaf])  # a stateless sibling is dropped
    root = _Node(children=[middle])

    state = describe_state(root)
    # The ancestor chain to the stateful leaf is retained...
    assert len(state["children"]) == 1
    middle_out = state["children"][0]
    # ...but the stateless sibling of the leaf is pruned.
    assert len(middle_out["children"]) == 1
    leaf_out = middle_out["children"][0]
    assert leaf_out["key"] == "deep"
    assert leaf_out["state"] == {"value": "x"}


def test_describe_state_empty_when_no_state_anywhere() -> None:
    root = _Node(children=[_Node(), _Node()])
    assert describe_state(root) == {}


def test_describe_state_carries_identity() -> None:
    root = _Node(key="toggle", label="Agree")
    root._obs_checked = Observable(False)  # type: ignore[attr-defined]
    state = describe_state(root)
    assert state["key"] == "toggle"
    assert state["label"] == "Agree"
    assert state["state"] == {"checked": False}


def test_describe_state_truncates_long_string_value() -> None:
    root = _Node()
    root._obs_text = Observable("x" * 500)  # type: ignore[attr-defined]
    value = describe_state(root)["state"]["text"]
    assert len(value) <= 200
    assert value.endswith("…")


def test_describe_state_caps_container_breadth() -> None:
    root = _Node()
    root._obs_items = Observable(list(range(100)))  # type: ignore[attr-defined]
    items = describe_state(root)["state"]["items"]
    assert len(items) == 21  # 20 items + one "… (+80 more)" marker
    assert items[-1] == "… (+80 more)"


def test_describe_state_renders_opaque_value_as_type_repr() -> None:
    class _Opaque:
        def __repr__(self) -> str:
            return "<opaque>"

    root = _Node()
    root._obs_thing = Observable(_Opaque())  # type: ignore[attr-defined]
    value = describe_state(root)["state"]["thing"]
    assert value == "_Opaque: <opaque>"


def test_describe_state_skips_unreadable_observable() -> None:
    from nuiitivet.observable.protocols import ObservableBase

    class _RaisingObs(ObservableBase):  # type: ignore[type-arg]
        @property
        def value(self) -> Any:
            raise RuntimeError("nope")

        def subscribe(self, cb: Any) -> Any:  # pragma: no cover - never called
            return None

        def changes(self) -> Any:  # pragma: no cover - never called
            return self

    root = _Node()
    root._obs_ok = Observable(1)  # type: ignore[attr-defined]
    # A real observable whose getter raises is dropped, not fatal.
    root._obs_boom = _RaisingObs()  # type: ignore[attr-defined]
    state = describe_state(root)
    assert state["state"] == {"ok": 1}


def test_describe_state_ignores_non_observable_duck_type() -> None:
    class _Duck:
        """Has ``.value`` but is not an ``ObservableBase`` -- must be ignored."""

        value = 7

    root = _Node()
    root._duck = _Duck()  # type: ignore[attr-defined]
    root._obs_real = Observable(1)  # type: ignore[attr-defined]
    state = describe_state(root)
    assert state["state"] == {"real": 1}


def test_describe_state_omits_animations_by_default() -> None:
    root = _Node()
    root._obs_checked = Observable(True)  # type: ignore[attr-defined]
    root._state_layer_anim = Animatable(0.25)  # type: ignore[attr-defined]

    state = describe_state(root)
    assert state["state"] == {"checked": True}


def test_describe_state_includes_animations_on_request() -> None:
    root = _Node()
    root._obs_checked = Observable(True)  # type: ignore[attr-defined]
    root._state_layer_anim = Animatable(0.25)  # type: ignore[attr-defined]

    state = describe_state(root, include_animations=True)
    # An ``Animatable`` is not mutable-observable, so it reports as computed.
    assert state["state"] == {
        "checked": True,
        "state_layer_anim": {"value": 0.25, "kind": "computed"},
    }


def test_describe_state_prunes_nodes_left_with_only_animations() -> None:
    # The filter must run *before* pruning: a widget whose only state was
    # animation channels has to prune away like any other stateless node,
    # instead of surviving as a hollow entry plus its ancestor path.
    animated = _Node(key="button")
    animated._bg_color_anim = Animatable(1.0)  # type: ignore[attr-defined]
    root = _Node(children=[_Node(children=[animated])])

    assert describe_state(root) == {}
    # ...and the same tree is reported in full when animations are asked for.
    included = describe_state(root, include_animations=True)
    assert included["children"][0]["children"][0]["key"] == "button"


def test_describe_state_keeps_values_derived_from_animations() -> None:
    # A ``.map()`` over an ``Animatable`` is a plain computed observable and is
    # deliberately still reported -- the filter is on type, not on provenance.
    anim = Animatable(0.0)
    root = _Node()
    root._obs_visible = anim.map(lambda v: v > 0.5)  # type: ignore[attr-defined]

    state = describe_state(root)
    assert state["state"]["visible"] == {"value": False, "kind": "computed"}


def test_describe_state_is_cycle_safe() -> None:
    a = _Node()
    a._obs_v = Observable(1)  # type: ignore[attr-defined]
    b = _Node(children=[a])
    a.children.append(b)  # cycle a -> b -> a
    state = describe_state(a)
    assert state["state"] == {"v": 1}
