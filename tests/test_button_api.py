import pytest
from nuiitivet.material.buttons import Fab, Button
from nuiitivet.material.text import Text
from nuiitivet.material.icon import Icon
from nuiitivet.layout.row import Row
from nuiitivet.material import ButtonStyle


def test_filled_button_label_only():
    btn = Button(label="Save", style=ButtonStyle.filled())
    assert len(btn.children) == 1
    child = btn.children[0]
    assert isinstance(child, Text)
    assert child.label == "Save"


def test_filled_button_icon_only():
    btn = Button(icon="search", style=ButtonStyle.filled())
    assert len(btn.children) == 1
    child = btn.children[0]
    assert isinstance(child, Icon)
    assert child.name == "search"


def test_filled_button_label_and_icon():
    btn = Button(label="Search", icon="search", style=ButtonStyle.filled())
    assert len(btn.children) == 1
    child = btn.children[0]
    assert isinstance(child, Row)
    chs = child.children_snapshot()
    assert isinstance(chs[0], Icon)
    assert isinstance(chs[1], Text)
    assert chs[1].label == "Search"


def test_fab_icon_only():
    fab = Fab(icon="add")
    assert len(fab.children) == 1
    child = fab.children[0]
    assert isinstance(child, Icon)
    assert child.name == "add"


def test_invalid_icon_type_raises():
    with pytest.raises(TypeError):
        Button(icon=123, style=ButtonStyle.filled())


def test_child_override_not_supported():
    with pytest.raises(TypeError):
        Button(child=Row([Icon("search"), Text("X")], gap=6), style=ButtonStyle.filled())


def test_body_override_not_supported():
    with pytest.raises(TypeError):
        Button(body=Row([Icon("search"), Text("X")], gap=6), style=ButtonStyle.filled())
