"""Tests for geometric picking (``pick_at``) -- the inspect-mode picker (#591).

``pick_at`` is the devtools-picker counterpart to ``hit_test``, and the cases
that matter are the ones where the two must *disagree*: a widget that
participates in no hit testing is pickable, and a widget the eye cannot see is
not -- even when nothing occludes it in the hit-testing sense.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet._interaction.perception import (
    enclosing_container,
    find_obstruction,
    global_visual_rect,
    intersecting_subtree,
    pick_at,
    visible_rect,
)
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.layout.stack import Stack
from nuiitivet.modifiers.clip import clip
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.testing import mount
from nuiitivet.widgets.text import TextBase as Text


def _covers(rect: Optional[tuple[float, float, float, float]], x: float, y: float) -> bool:
    """Whether ``rect`` contains the point, tolerating a node with no rect."""
    if rect is None:
        return False
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def test_picks_a_widget_that_does_not_participate_in_hit_testing() -> None:
    """The whole reason ``hit_test`` cannot be reused.

    A bare ``Text`` catches no pointer input, so ``hit_test`` reports nothing
    there -- but it is very often the exact node a human means to point at.
    """
    first, second = Text("AAA"), Text("BBB")
    with mount(Column(children=[first, second])) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 2, 2) is first


def test_picks_the_deepest_node_not_the_container() -> None:
    leaf = Text("AAA")
    with mount(Column(children=[leaf])) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 2, 2) is leaf


def test_overlapping_siblings_resolve_top_most_first() -> None:
    """Reverse sibling order, matching ``_hit_test_children``'s convention."""
    under, over = Text("UNDER"), Text("OVER")
    with mount(Stack(children=[under, over])) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 2, 2) is over


def test_a_decks_hidden_page_is_never_picked() -> None:
    """The case occlusion filtering alone cannot catch (#591).

    Both pages carry the same rect and neither participates in hit testing, so
    ``hit_test`` at the point returns ``None`` -- which ``find_obstruction``
    deliberately does not treat as an obstruction. Without narrowing the descent
    to ``focus_traversal_children()``, reverse sibling order picks the page that
    is *not* on screen.
    """
    shown, hidden = Text("SHOWN"), Text("HIDDEN")
    with mount(Deck(children=[shown, hidden], index=0)) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 2, 2) is shown


def test_a_deck_follows_its_selected_index() -> None:
    first, second = Text("FIRST"), Text("SECOND")
    with mount(Deck(children=[first, second], index=1)) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 2, 2) is second


def test_a_navigators_covered_route_is_never_picked() -> None:
    """Every route stays mounted; only the top one is on screen."""
    navigator = Navigator(Route(builder=lambda: Text("FIRST")))
    with mount(navigator) as host:
        host.layout(300, 200)
        host.settle()
        navigator.push(Route(builder=lambda: Text("SECOND")))
        host.settle()
        host.layout(300, 200)
        host.settle()

        top = navigator.focus_traversal_children()[0]
        assert pick_at(host.root, 2, 2) is top


def test_a_row_scrolled_out_of_view_is_not_picked() -> None:
    """``global_visual_rect`` applies the scroll offset, so it is not a candidate."""
    rows = [Text(f"Item {index}") for index in range(30)]
    scroller = VerticalScrollable(child=Column(rows))
    with mount(scroller) as host:
        host.layout(200, 100)
        host.settle()
        scroller._controller.scroll_to(150.0)
        host.settle()

        picked = pick_at(host.root, 5, 2)
        assert picked is not rows[0]
        assert picked in rows


def test_a_row_clipped_by_the_viewport_loses_to_what_is_painted_there() -> None:
    """A clipped candidate is rejected, and the pick falls back outwards.

    The row still has a rect at that point -- it is laid out, just painted
    nowhere -- so only ``find_obstruction``'s clip check separates it from the
    widget genuinely drawn there.
    """
    rows = [Text(f"Item {index}") for index in range(30)]
    scroller = VerticalScrollable(child=Column(rows))
    below = Text("BELOW")
    outer = Column([Container(child=scroller, width=200, height=60), below])
    with mount(outer) as host:
        host.layout(200, 300)
        host.settle()

        # Aim at the middle of ``below`` rather than a fixed offset. Text
        # metrics differ per platform, and a hardcoded y that lands just past
        # its bottom edge on one of them makes the pick fall outwards to the
        # enclosing Column -- failing for a reason the test is not about.
        target = global_visual_rect(below)
        assert target is not None and target[2] > 0 and target[3] > 0, (
            f"BELOW must occupy a real rect for there to be a point to aim at, got {target}"
        )
        x, y = target[0] + target[2] / 2, target[1] + target[3] / 2

        # State the premise instead of assuming it: some row must be laid out
        # across that point while painted nowhere near it, or there is nothing
        # for the clip check to reject and the assertion below proves nothing.
        assert any(_covers(global_visual_rect(row), x, y) for row in rows)

        assert pick_at(host.root, x, y) is below


def test_a_point_reaching_nothing_is_none() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)

        assert pick_at(host.root, 9_999, 9_999) is None


def test_no_root_is_none() -> None:
    assert pick_at(None, 1, 1) is None


class _Empty:
    """A container that stays mounted at full size while drawing nothing."""

    def __init__(self, rect: tuple[int, int, int, int], child: object) -> None:
        self.children = [child]
        self.global_layout_rect = rect
        self.parent = None
        child.parent = self  # type: ignore[attr-defined]

    def is_visually_empty(self) -> bool:
        return True


class _Node:
    def __init__(self, rect: tuple[int, int, int, int]) -> None:
        self.children: list[object] = []
        self.global_layout_rect = rect
        self.parent = None


def test_a_visually_empty_container_drops_out_with_its_subtree() -> None:
    """Neither geometry nor occlusion can catch this one.

    Such a container keeps a full-window rect, so it contains every point, and
    ``find_obstruction`` clears it because ``hit_test`` there returns ``None`` --
    which is deliberately not an obstruction, since that rule is what keeps a
    non-interactive target reachable.
    """
    hidden = _Node((0, 0, 100, 100))
    empty = _Empty((0, 0, 100, 100), hidden)

    assert pick_at(empty, 10, 10) is None


def test_an_empty_overlay_does_not_shadow_the_app() -> None:
    """The real shape of the bug: every App puts an Overlay over its content.

    Painted last, its idle scaffolding covers the window, so without the
    visually-empty probe it wins every pick over any widget that does not
    participate in hit testing -- exactly what ``pick_at`` exists to reach.
    """
    from nuiitivet.overlay.overlay import Overlay

    leaf = Text("AAA")
    with mount(Stack(children=[Column(children=[leaf]), Overlay()])) as host:
        host.layout(300, 200)
        host.settle()

        assert pick_at(host.root, 2, 2) is leaf


# --- region geometry (#591) --------------------------------------------------


def test_the_container_of_a_region_over_blank_space_names_what_should_have_painted() -> None:
    """The case node picking cannot express at all.

    A box over an empty band covers no widget, so ``contents`` is empty -- and
    the container is the whole answer: it names the widget that should have put
    something there.
    """
    leaf = Text("AAA")
    column = Column(children=[leaf], padding=40)
    with mount(column) as host:
        host.layout(300, 200)
        host.settle()

        blank = (4.0, 4.0, 20.0, 20.0)
        container = enclosing_container(host.root, blank)

        assert container is column
        assert intersecting_subtree(container, blank) == []


def test_a_rough_box_over_rows_reports_them_by_intersection() -> None:
    """Humans drag rough boxes, so a clipped row still counts -- and says so."""
    rows = [Text(f"Item {index}") for index in range(4)]
    column = Column(children=rows)
    with mount(column) as host:
        host.layout(300, 200)
        host.settle()

        first, second = rows[0].global_layout_rect, rows[1].global_layout_rect
        assert first is not None and second is not None
        # From halfway down the first row to the bottom of the second: the first
        # is clipped by the box, the second wholly inside it.
        rough = (0.0, first[1] + first[3] / 2, 300.0, second[1] + second[3] - first[1])

        found = {node: relation for node, relation, _children in intersecting_subtree(column, rough)}

        assert found.get(rows[0]) == "clipped"
        assert found.get(rows[1]) == "contained"
        assert rows[3] not in found


def test_region_contents_keep_the_structure_instead_of_collapsing_it() -> None:
    """Nothing is dropped for being nested inside another match.

    ``find_targets`` collapses that way because it answers "which widget did you
    name?". A region asks "what is under this box?", and the same rectangle may
    equally mean the gap between things or the things it crosses -- geometry
    cannot tell those apart, so collapsing to one reading would destroy the
    other. The caller, which knows what the human said, decides.
    """
    inner = Text("inner")
    card = Column(children=[inner])
    outer = Column(children=[card])
    with mount(outer) as host:
        host.layout(300, 200)
        host.settle()

        whole = (0.0, 0.0, 300.0, 200.0)
        (top,) = intersecting_subtree(outer, whole)
        node, relation, children = top

        assert node is card
        assert relation == "contained"
        assert [child[0] for child in children] == [inner]


def test_a_band_across_a_column_reports_what_it_actually_crosses() -> None:
    """The case that motivated keeping the structure (#591).

    A narrow band drawn down a column overlaps the column itself, so collapsing
    to the outermost match reported only the column -- telling the human what
    they already knew and hiding every row the band went through.
    """
    first, second = Text("Item one"), Text("Item two")
    column = Column(children=[first, second])
    with mount(column) as host:
        host.layout(300, 200)
        host.settle()

        band = (0.0, 0.0, 8.0, 200.0)
        (top,) = intersecting_subtree(host.root, band)

        def flatten(entry: tuple[Any, Any, list[Any]]) -> list[Any]:
            node, _relation, children = entry
            found: list[Any] = [node]
            for child in children:
                found.extend(flatten(child))
            return found

        crossed = flatten(top)
        assert first in crossed
        assert second in crossed


def test_an_idle_overlay_never_answers_for_a_region() -> None:
    """Same shadowing hazard as picking: the idle layer encloses everything."""
    from nuiitivet.overlay.overlay import Overlay

    content = Column(children=[Text("AAA")])
    with mount(Stack(children=[content, Overlay()])) as host:
        host.layout(300, 200)
        host.settle()

        container = enclosing_container(host.root, (2.0, 2.0, 10.0, 10.0))

        assert container is not None
        assert type(container).__name__ != "Container"


def test_no_enclosing_container_for_a_region_outside_the_tree() -> None:
    with mount(Column(children=[Text("AAA")])) as host:
        host.layout(300, 200)

        assert enclosing_container(host.root, (9_000.0, 9_000.0, 10.0, 10.0)) is None


# --- clipped-away content (#591) ---------------------------------------------


def _clipped_tile() -> tuple[Any, Any, Any]:
    """The gradient idiom: an oversized shape trimmed to a small box.

    ``samples/readme/readme_hero_showcase.py`` fakes a gradient this way -- a
    circle far larger than its parent, anchored to one corner and clipped, so
    only a soft wedge of it shows. The child's *layout* rect therefore extends
    well outside anything painted, and here reaches negative coordinates.
    """
    bubble = Container(width=200, height=200)
    tile = Container(
        child=Stack([bubble], width="wt", height="wt", alignment=("end", "start")),
        width=60,
        height=60,
    ).modifier(clip())
    return bubble, tile, Stack([Text("BACKDROP"), tile])


def test_a_clipped_away_child_is_not_picked_where_it_paints_nothing() -> None:
    """The third instance of one blind spot, found in a real app (#591).

    ``Box.hit_test`` has always honoured ``clip_content``, but the clip was not
    published under ``visual_clip_rect``, so ``find_obstruction`` could not see
    it. The occlusion check cannot cover for that here: the point lands on
    nothing, and a ``None`` hit is deliberately not an obstruction.
    """
    bubble, _tile, root = _clipped_tile()
    with mount(root) as host:
        host.layout(300, 300)
        host.settle()

        rect = global_visual_rect(bubble)
        assert rect is not None
        assert rect[0] < 0, "the bubble must overhang its parent for this to test anything"
        outside = (rect[0] + 10, rect[1] + 150)

        assert root.hit_test(int(outside[0]), int(outside[1])) is None
        assert find_obstruction(root, bubble, *outside) is not None
        assert pick_at(root, *outside) is not bubble


def test_a_clipped_child_is_still_picked_where_it_does_paint() -> None:
    """The trimming must not cost the reachable part."""
    bubble, tile, root = _clipped_tile()
    with mount(root) as host:
        host.layout(300, 300)
        host.settle()

        assert find_obstruction(root, bubble, 50.0, 5.0) is None
        assert pick_at(root, 50.0, 5.0) is bubble
        assert tile is not None


def test_a_clipped_nodes_reported_rect_is_what_survives_the_clip() -> None:
    """What the human sees drawn, and what the payload says, must be one rect.

    Reporting the layout rect drew a bracket across a neighbouring pane and told
    the assistant the designation covered it -- the visible symptom that led
    here.
    """
    bubble, _tile, root = _clipped_tile()
    with mount(root) as host:
        host.layout(300, 300)
        host.settle()

        assert global_visual_rect(bubble) == (-140.0, 0.0, 200.0, 200.0)
        assert visible_rect(bubble) == (0.0, 0.0, 60.0, 60.0)


def test_a_node_clipped_entirely_out_of_sight_has_no_visible_rect() -> None:
    """A collapsed label (a clip of zero height) is painted nowhere at all."""
    hidden = Text("COLLAPSED")
    box = Container(child=hidden, width=96, height=0).modifier(clip())
    with mount(Column(children=[box])) as host:
        host.layout(300, 200)
        host.settle()

        assert visible_rect(hidden) is None


def test_an_unclipped_box_reports_no_clip_at_all() -> None:
    """The common case must stay free: no clip means the rect is untouched."""
    leaf = Text("AAA")
    with mount(Container(child=leaf, width=100, height=40)) as host:
        host.layout(300, 200)
        host.settle()

        assert visible_rect(leaf) == global_visual_rect(leaf)
