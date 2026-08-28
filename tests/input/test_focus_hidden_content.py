"""Content kept mounted while off screen is out of the Tab sequence (issue #491).

Three containers keep content mounted while the user cannot see it: a ``Deck``
holding the pages it is not showing, a ``Navigator`` holding covered routes, and
an overlay holding everything behind a modal. Tab must stop where the eye does,
focus already inside must be released when the content goes off screen, and a
modal must hand focus back when it closes.

The subtree-wide counterpart (``Collapsible``, ``visible()``) lives in
``test_focus_hidden_subtree.py``.
"""

from __future__ import annotations

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.for_each import ForEach
from nuiitivet.navigation import Navigator, Route
from nuiitivet.observable import Observable
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.testing import AppHarness
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode, FocusSource

SHIFT = 1


def _focus_node(widget: Clickable) -> FocusNode:
    node = widget.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    return node


@pytest.fixture
def mounted_app(nuiitivet_app):
    """Mount ``root`` on a harness, so async work can be awaited rather than guessed."""

    def build(root) -> AppHarness:
        return nuiitivet_app(root, size=(800, 600))

    return build


def _owners(app: AppHarness) -> list:
    return [node.owner for node in app.window._collect_focus_nodes()]


# --- Deck -----------------------------------------------------------------------


def test_deck_tab_visits_only_the_selected_page(mounted_app) -> None:
    before, after = Clickable(), Clickable()
    page0, page1a, page1b = Clickable(), Clickable(), Clickable()
    index = _ObservableValue(0)
    root = Column([before, Deck(children=[page0, Column([page1a, page1b])], index=index), after])
    app = mounted_app(root)

    assert _owners(app) == [before, page0, after]

    index.value = 1
    assert _owners(app) == [before, page1a, page1b, after]


def test_deck_shift_tab_walks_back_through_the_selected_page_only(mounted_app) -> None:
    before, after = Clickable(), Clickable()
    page0, page1 = Clickable(), Clickable()
    root = Column([before, Deck(children=[page0, page1], index=1), after])
    app = mounted_app(root)

    app.window.request_focus(_focus_node(after), FocusSource.KEYBOARD)
    app.window._dispatch_key_press("tab", SHIFT)
    assert page1.state.focused

    app.window._dispatch_key_press("tab", SHIFT)
    assert before.state.focused
    assert not page0.state.focused


def test_switching_deck_page_releases_the_focus_it_held(mounted_app) -> None:
    page0, page1 = Clickable(), Clickable()
    index = _ObservableValue(0)
    root = Column([Deck(children=[page0, page1], index=index)])
    app = mounted_app(root)

    app.window.request_focus(_focus_node(page0), FocusSource.KEYBOARD)
    index.value = 1
    app.window._release_focus_if_blocked()

    assert not page0.state.focused
    assert app.window._focused_node is None


def test_deck_over_a_for_each_follows_the_live_expanded_list(mounted_app) -> None:
    # The index addresses the post-expansion list, so traversal has to resolve it
    # on every call rather than caching the children it saw once.
    items = Observable(["a", "b", "c"])
    built: dict[str, Clickable] = {}

    def builder(item: str, _index: int) -> Clickable:
        widget = Clickable()
        built[item] = widget
        return widget

    deck = Deck(children=[ForEach(items, builder)], index=1)
    app = mounted_app(Column([deck]))
    deck.preferred_size()  # force the ForEach to expand

    assert _owners(app) == [built["b"]]

    items.value = ["x", "y", "z", "w"]
    deck.preferred_size()
    assert _owners(app) == [built["y"]]


def test_deck_over_a_for_each_keeps_its_sizing_and_painting(mounted_app) -> None:
    # Regression guard for the rejected fix: wrapping each Deck child would have
    # swallowed the ForEach expansion, leaving the page empty.
    from nuiitivet.rendering.sizing import Sizing
    from nuiitivet.widgets.box import Box

    items = Observable([1, 2, 3])
    deck = Deck(children=[ForEach(items, lambda _i, _n: Box(width=Sizing.fixed(20), height=Sizing.fixed(10)))], index=1)
    mounted_app(Column([deck]))

    assert deck.preferred_size() == (20, 10)
    assert len(deck.focus_traversal_children()) == 1


# --- Navigator ------------------------------------------------------------------


def test_navigator_tab_visits_only_the_top_route(mounted_app) -> None:
    home, pushed = Clickable(), Clickable()
    navigator = Navigator(Route(builder=lambda: Column([home])))
    app = mounted_app(Column([navigator]))
    navigator.rebuild()

    assert _owners(app) == [home]

    navigator.push(Column([pushed]))
    assert _owners(app) == [pushed]


def test_pushing_a_route_releases_the_focus_the_covered_one_held(mounted_app) -> None:
    home, pushed = Clickable(), Clickable()
    navigator = Navigator(Route(builder=lambda: Column([home])))
    app = mounted_app(Column([navigator]))
    navigator.rebuild()

    app.window.request_focus(_focus_node(home), FocusSource.KEYBOARD)
    navigator.push(Column([pushed]))
    app.window._release_focus_if_blocked()

    assert not home.state.focused
    assert app.window._focused_node is None


async def test_popping_a_route_makes_the_uncovered_one_traversable_again(mounted_app) -> None:
    home, pushed = Clickable(), Clickable()
    navigator = Navigator(Route(builder=lambda: Column([home])))
    app = mounted_app(Column([navigator]))
    navigator.rebuild()
    navigator.push(Column([pushed]))
    assert _owners(app) == [pushed]

    navigator.pop()
    await app.idle()

    assert _owners(app) == [home]


# --- Modal overlay --------------------------------------------------------------


async def test_tab_stays_inside_a_blocking_overlay_entry(mounted_app) -> None:
    background, dialog_a, dialog_b = Clickable(), Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)

    app.window.overlay.show(Column([dialog_a, dialog_b]), backdrop=True)
    await app.idle()

    assert _owners(app) == [dialog_a, dialog_b]

    # Tab wraps within the dialog instead of crossing back to the background.
    app.window.request_focus(_focus_node(dialog_b), FocusSource.KEYBOARD)
    app.window._dispatch_key_press("tab")
    assert dialog_a.state.focused
    assert not background.state.focused


async def test_opening_a_modal_moves_focus_into_it(mounted_app) -> None:
    background, dialog = Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)
    app.window.request_focus(_focus_node(background), FocusSource.KEYBOARD)

    app.window.overlay.show(Column([dialog]), backdrop=True)
    await app.idle()
    app.window._release_focus_if_blocked()

    assert not background.state.focused
    assert dialog.state.focused


async def test_closing_a_modal_restores_focus_to_the_invoker(mounted_app) -> None:
    background, dialog = Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)
    app.window.request_focus(_focus_node(background), FocusSource.KEYBOARD)

    handle = app.window.overlay.show(Column([dialog]), backdrop=True)
    await app.idle()
    app.window._release_focus_if_blocked()

    handle.close()
    await app.idle()
    app.window._release_focus_if_blocked()

    assert not dialog._mounted
    assert background.state.focused
    assert app.window._focused_node is _focus_node(background)


async def test_closing_a_modal_clears_focus_when_the_invoker_is_gone(mounted_app) -> None:
    background, dialog = Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)
    app.window.request_focus(_focus_node(background), FocusSource.KEYBOARD)

    handle = app.window.overlay.show(Column([dialog]), backdrop=True)
    await app.idle()
    app.window._release_focus_if_blocked()

    root.remove_child(background)
    handle.close()
    await app.idle()
    app.window._release_focus_if_blocked()

    assert app.window._focused_node is None
    assert not background.state.focused


async def test_a_passthrough_entry_does_not_trap_focus(mounted_app) -> None:
    background, toast = Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)
    app.window.request_focus(_focus_node(background), FocusSource.KEYBOARD)

    app.window.overlay.show(Column([toast]), passthrough=True)
    await app.idle()
    app.window._release_focus_if_blocked()

    assert background.state.focused
    assert _owners(app) == [background, toast]


async def test_nested_modals_hand_focus_back_one_layer_at_a_time(mounted_app) -> None:
    background, outer, inner = Clickable(), Clickable(), Clickable()
    root = Column([background])
    app = mounted_app(root)
    app.window.request_focus(_focus_node(background), FocusSource.KEYBOARD)

    outer_handle = app.window.overlay.show(Column([outer]), backdrop=True)
    await app.idle()
    app.window._release_focus_if_blocked()
    assert outer.state.focused

    inner_handle = app.window.overlay.show(Column([inner]), backdrop=True)
    await app.idle()
    app.window._release_focus_if_blocked()
    assert inner.state.focused
    assert _owners(app) == [inner]

    inner_handle.close()
    await app.idle()
    app.window._release_focus_if_blocked()
    assert outer.state.focused

    outer_handle.close()
    await app.idle()
    app.window._release_focus_if_blocked()
    assert background.state.focused
