"""Additional unit tests for FloatingActionButton behavior."""

import pytest

from nuiitivet.material.buttons import FloatingActionButton
from nuiitivet.material.icon import Icon
from nuiitivet.widgets.text import TextBase as Text


def test_fab_preserves_icon_instance():
    """Passing an Icon instance is not supported for Material buttons."""
    icon = Icon("add", size=24)
    with pytest.raises(TypeError):
        FloatingActionButton(icon=icon)


def test_fab_builds_icon_child_from_string():
    fab = FloatingActionButton(icon="add")
    assert len(fab.children) == 1
    assert isinstance(fab.children[0], Icon)


def test_fab_child_override_not_supported():
    with pytest.raises(TypeError):
        FloatingActionButton(icon="add", child=Text("X"))


def test_fab_body_override_not_supported():
    with pytest.raises(TypeError):
        FloatingActionButton(icon="add", body=Text("X"))
