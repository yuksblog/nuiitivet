"""Tests for widget construction-site capture.

The boundaries that matter are the ones the feature is built on: capture must be
*off* until the dev runner turns it on (a production launch pays nothing), the
walk must leave the framework rather than stopping at the first frame above
``Widget.__init__``, and a widget with no user frame anywhere must say so instead
of inventing one.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import pytest

from nuiitivet.dev import source
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.background import background
from nuiitivet.widgets.text import TextBase as Text


@pytest.fixture
def recording() -> Iterator[None]:
    """Capture installed for one test, always removed again.

    Leaking the wrap would silently attach sites to every widget built by the
    rest of the suite, so it is torn down even when the test fails.
    """
    source.install()
    try:
        yield
    finally:
        source.uninstall()


def test_nothing_is_recorded_until_the_dev_runner_installs_it() -> None:
    """The production guarantee: not a flag check on the construction path."""
    assert source.is_installed() is False

    node = Text("AAA")

    assert source.site_of(node) == ()
    assert source.payload(node) is None


def test_a_widget_records_the_line_that_built_it(recording: None) -> None:
    node = Text("AAA")
    expected = _line_above()

    (innermost, *_rest) = source.site_of(node)

    assert os.path.abspath(innermost.file) == os.path.abspath(__file__)
    assert innermost.line == expected
    assert innermost.function == "test_a_widget_records_the_line_that_built_it"


def test_a_widget_records_the_span_of_the_call_that_built_it(recording: None) -> None:
    """The column is what turns "this line" into "this call": a line can hold
    several constructions, and an editor of the file needs the one that ran."""
    nodes = [Text("AAA"), Text("BBB")]
    line = _line_above()

    first, second = (source.site_of(node)[0] for node in nodes)

    assert first.line == second.line == line
    assert first.column is not None and second.column is not None
    assert first.column < second.column
    assert first.end_line == line
    assert first.end_column is not None and first.column < first.end_column <= second.column


class _Square(Container):
    def __init__(self, size: int = 24) -> None:
        super().__init__(width=size, height=size)


def test_the_construction_frame_skips_the_widgets_own_init(recording: None) -> None:
    """Inside ``__init__`` the executing call is ``super().__init__``; the call a
    human recognises as building the widget is the one that named its type."""
    node = _Square(size=24)
    line = _line_above()

    frame = source.construction_frame(node)

    assert source.site_of(node)[0].function == "__init__"
    assert frame is not None
    assert frame.line == line
    assert frame.function == "test_the_construction_frame_skips_the_widgets_own_init"


def test_widgets_built_at_gathers_every_instance_of_one_site(recording: None) -> None:
    tiles = [Text(f"Item {index}") for index in range(3)]
    other = Text("other")
    root = Column(children=[*tiles, other])
    frame = source.construction_frame(tiles[0])
    assert frame is not None

    assert source.widgets_built_at(root, frame) == tiles
    # An edit to the call's arguments moves its end; the rebuilt widgets must
    # still be found by the same site.
    assert source.widgets_built_at(root, frame._replace(end_column=999)) == tiles


class _Labeled(Column):
    """Builds its own child, the way a button builds its label."""

    def __init__(self) -> None:
        super().__init__(children=[Text("inner")])


def test_the_children_a_widget_builds_for_itself_have_no_call_of_their_own(recording: None) -> None:
    """The user call built the widget; the child was built by the widget's
    constructor, and its frames say so."""
    labeled = _Labeled()
    child = labeled.children[0]
    frame = source.construction_frame(labeled)
    assert frame is not None

    assert source.site_of(child)[0].function == "__init__"
    assert source.construction_frame(child) is None
    assert source.widgets_built_at(labeled, frame) == [labeled]
    assert source.site_owner(child) is labeled
    assert source.site_owner(labeled) is labeled


def test_a_widget_with_a_call_of_its_own_owns_its_site(recording: None) -> None:
    leaf = Text("AAA")
    Column(children=[leaf])

    assert source.site_owner(leaf) is leaf


def test_without_any_site_a_widget_owns_itself() -> None:
    """Capture off: nothing up the tree has a call, so nothing is adopted."""
    leaf = Text("AAA")
    Column(children=[leaf])

    assert source.site_owner(leaf) is leaf


def test_a_child_built_during_layout_has_no_call_and_belongs_to_its_parent(recording: None) -> None:
    """A group button's label is built when it lays out, against whatever user
    frame triggered the layout. That frame built nothing, and the label is the
    button's to resize."""
    from nuiitivet.material.button_group import GroupButton
    from nuiitivet.testing import mount

    button = GroupButton("Day")
    with mount(Column(children=[button])) as host:
        host.layout(300, 200)
        host.settle()
        [label] = [n for n in _walk(button) if isinstance(n, Text)]

        assert source.site_of(label)[0].direct is False
        assert source.construction_frame(label) is None
        assert source.site_owner(label) is button
        assert source.construction_frame(button) is not None


def test_an_icon_a_rail_item_builds_is_not_its_own_to_resize(recording: None) -> None:
    """The icon is made in the item's constructor and placed in the rail's own
    tree, where the item is not an ancestor. It has no call of its own, so the
    nearest widget with one -- the rail -- is what a pointer on it means, and
    ``size`` is never written into the item's call."""
    from nuiitivet.material.navigation_rail import NavigationRail, RailItem
    from nuiitivet.testing import mount
    from nuiitivet.widgets.icon import IconBase

    rail = NavigationRail(children=[RailItem(icon="home", label="Home")])
    with mount(rail) as host:
        host.layout(300, 400)
        host.settle()
        icons = [n for n in _walk(rail) if isinstance(n, IconBase)]

        assert icons, "the item draws its icon as a widget"
        assert all(source.construction_frame(icon) is None for icon in icons)
        assert all(source.site_owner(icon) is rail for icon in icons)


def _walk(node: Any) -> Any:
    from nuiitivet._interaction.tree import iter_child_widgets

    yield node
    for child in iter_child_widgets(node):
        yield from _walk(child)


def test_a_multi_line_call_records_where_it_starts_and_ends(recording: None) -> None:
    node = Text(
        "AAA",
    )
    end = _line_above()

    frame = source.site_of(node)[0]

    assert frame.line == end - 2
    assert frame.end_line == end


def _line_above() -> int:
    """The line of the caller's previous statement, for asserting on a site."""
    import sys

    frame = sys._getframe(1)
    return frame.f_lineno - 1


def test_the_walk_leaves_the_framework_rather_than_stopping_above_init(
    recording: None,
) -> None:
    """A ``Column`` builds through several framework frames before reaching here.

    Stopping at the first frame above ``Widget.__init__`` would report
    ``layout/column.py``, which tells the reader nothing they can act on.
    """
    column = Column(children=[Text("AAA")])

    (innermost, *_rest) = source.site_of(column)

    assert os.path.abspath(innermost.file) == os.path.abspath(__file__)


def test_a_modifier_wrapper_resolves_to_the_users_modifier_call(
    recording: None,
) -> None:
    """``.modifier()`` builds a ``ModifierBox`` deep inside the framework.

    That wrapper is a real node a human can point at, so it must not report the
    modifier's own implementation file.
    """
    wrapped = Text("AAA").modifier(background("#FF0000"))

    site = source.site_of(wrapped)

    assert site, "the wrapper widget recorded no site at all"
    assert os.path.abspath(site[0].file) == os.path.abspath(__file__)


def test_the_chain_reaches_past_a_helper_to_its_caller(recording: None) -> None:
    """Why a stack and not a location.

    "Change every tile" wants the helper; "change this one" wants the call site.
    Geometry cannot choose, so both are reported and the caller decides.
    """
    node = _build_in_a_helper()

    site = source.site_of(node)

    assert len(site) >= 2
    assert site[0].function == "_build_in_a_helper"
    assert site[1].function == "test_the_chain_reaches_past_a_helper_to_its_caller"


def _build_in_a_helper() -> Any:
    return Text("AAA")


def test_the_chain_is_capped(recording: None) -> None:
    """A per-construction path must not carry an unbounded stack."""

    def one() -> Any:
        return Text("AAA")

    def two() -> Any:
        return one()

    def three() -> Any:
        return two()

    def four() -> Any:
        return three()

    assert len(source.site_of(four())) <= source._MAX_FRAMES


def test_widgets_from_one_line_share_one_interned_site(recording: None) -> None:
    """What keeps this a small table rather than a per-widget field.

    In the spike that shaped this design, 441 resolved widgets held 145
    distinct sites because one helper builds fourteen cards.
    """
    nodes = [Text(f"Item {index}") for index in range(20)]

    sites = {id(source.site_of(node)) for node in nodes}

    assert len(sites) == 1


def test_a_widget_with_no_user_frame_reports_nothing(recording: None) -> None:
    """Honest absence, not a guess.

    Reached when a widget is built with no user frame inside the depth cap. The
    first spike read 9 such nodes as "framework scaffolding"; they were the cap
    cutting the walk two frames short, which is why the cap now carries headroom
    and why this case is expected to be rare rather than routine.
    """
    node = Text("AAA")
    setattr(node, "_source_site", ())

    assert source.site_of(node) == ()
    assert source.payload(node) is None


def test_uninstall_restores_the_original_constructor() -> None:
    """A leaked wrap would attach sites to every widget in the rest of a suite."""
    from nuiitivet.widgeting.widget import Widget

    before = Widget.__init__
    source.install()
    assert Widget.__init__ is not before

    source.uninstall()

    assert Widget.__init__ is before
    assert source.is_installed() is False


def test_install_is_idempotent() -> None:
    """Two installs must not nest, or the walk starts one frame too deep."""
    from nuiitivet.widgeting.widget import Widget

    source.install()
    once = Widget.__init__
    try:
        source.install()

        assert Widget.__init__ is once
    finally:
        source.uninstall()


# --- payload ----------------------------------------------------------------


def test_the_payload_flags_the_innermost_frame_as_the_jump_target(
    recording: None,
) -> None:
    """An editor can open one place; the rest are for a reader who can choose."""
    node = _build_in_a_helper()

    entries = source.payload(node)

    assert entries is not None
    assert entries[0]["target"] is True
    assert all("target" not in entry for entry in entries[1:])
    assert entries[0]["function"] == "_build_in_a_helper"


def test_payload_paths_are_relative_to_the_working_directory(
    recording: None,
) -> None:
    """How the guide and the assistant both refer to files."""
    node = Text("AAA")

    entries = source.payload(node)

    assert entries is not None
    assert not os.path.isabs(entries[0]["file"])


def test_the_editor_target_is_absolute(recording: None) -> None:
    """An editor is launched from the dev process and must not depend on its cwd."""
    node = Text("AAA")

    target = source.absolute_target(node)

    assert target is not None
    path, line = target
    assert os.path.isabs(path)
    assert line > 0


def test_no_editor_target_without_a_site() -> None:
    assert source.absolute_target(Container()) is None
