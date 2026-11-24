"""A widget painted with no layout rect is reported, with the parent that never laid it out."""

from __future__ import annotations

import logging
from typing import Callable, List

import pytest

from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.unlaid_child import warn_child_without_rect
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box

LOGGER = "nuiitivet.widgeting.unlaid_child"


class _Frame(Widget):
    """A widget that keeps the default layout, which lays no child out, and the default paint, which paints them."""

    def __init__(self, child: Widget) -> None:
        super().__init__()
        self.add_child(child)


def _leaf() -> Box:
    return Box(width=Sizing.fixed(50), height=Sizing.fixed(20))


@pytest.fixture(autouse=True)
def every_warning_is_new():
    _clear_log_once_keys_for_tests()
    yield
    _clear_log_once_keys_for_tests()


def _warnings(caplog: pytest.LogCaptureFixture) -> List[str]:
    return [record.getMessage() for record in caplog.records if record.name == LOGGER]


@pytest.mark.parametrize(
    ("make", "name"),
    [
        (lambda leaf: Column([leaf]), "Column"),
        (lambda leaf: Container(leaf), "Container"),
        (lambda leaf: Box(leaf), "Box"),
    ],
    ids=["column", "container", "box"],
)
def test_a_parent_that_never_laid_its_child_out_is_named(
    make: Callable[[Widget], Widget], name: str, caplog: pytest.LogCaptureFixture
) -> None:
    frame = _Frame(make(_leaf()))
    frame.layout(200, 100)

    with caplog.at_level(logging.WARNING):
        frame.paint(None, 0, 0, 200, 100)

    (message,) = _warnings(caplog)
    assert message.startswith(f"{name} has no layout rect when it is painted: its parent _Frame never laid it out.")
    assert "_Frame.layout() must call super().layout(width, height) and lay out each child" in message


def test_a_pair_of_classes_is_named_once(caplog: pytest.LogCaptureFixture) -> None:
    frame = _Frame(Column([_leaf()]))
    frame.layout(200, 100)

    with caplog.at_level(logging.WARNING):
        frame.paint(None, 0, 0, 200, 100)
        frame.paint(None, 0, 0, 200, 100)

    assert len(_warnings(caplog)) == 1


def test_a_parent_that_still_needs_a_layout_is_not_named(caplog: pytest.LogCaptureFixture) -> None:
    column = Column([_leaf()])
    column.layout(200, 100)
    column.add_child(_leaf())
    assert column.needs_layout

    with caplog.at_level(logging.WARNING):
        column.paint(None, 0, 0, 200, 100)

    assert _warnings(caplog) == []


def test_a_parent_whose_layout_never_reaches_the_kernel_is_named(caplog: pytest.LogCaptureFixture) -> None:
    class Forgetful(_Frame):
        """Its mark is never cleared: no layout is coming, whatever the mark says."""

        def layout(self, width: int, height: int) -> None:
            pass

    frame = Forgetful(Column([_leaf()]))
    column = Column([frame])
    column.layout(200, 100)
    assert frame.needs_layout and not column.needs_layout

    with caplog.at_level(logging.WARNING):
        column.paint(None, 0, 0, 200, 100)

    (message,) = _warnings(caplog)
    assert message.startswith("Column has no layout rect when it is painted: its parent Forgetful never laid it out.")


def test_a_child_that_is_no_widget_does_not_break_the_paint(caplog: pytest.LogCaptureFixture) -> None:
    class Stray:
        layout_rect = None

    with caplog.at_level(logging.WARNING):
        warn_child_without_rect(Stray())  # type: ignore[arg-type]

    assert _warnings(caplog) == ["The warning for a child without a rect failed"], "logged, not raised"


def test_a_tree_painted_with_no_layout_at_all_is_told_to_lay_out_first(caplog: pytest.LogCaptureFixture) -> None:
    column = Column([_leaf()])

    with caplog.at_level(logging.WARNING):
        column.paint(None, 0, 0, 200, 100)

    (message,) = _warnings(caplog)
    assert message.startswith("Column has no layout rect when it is painted")
    assert "Call layout(width, height) before paint()" in message


def test_a_tree_laid_out_before_its_paint_is_silent(caplog: pytest.LogCaptureFixture) -> None:
    column = Column([Container(_leaf()), Box(_leaf())])
    column.layout(200, 100)

    with caplog.at_level(logging.WARNING):
        column.paint(None, 0, 0, 200, 100)

    assert _warnings(caplog) == []
