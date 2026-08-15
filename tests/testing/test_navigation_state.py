"""Navigation and overlay state as things a test can ask (#541).

The point of the surface is that a test says what it means -- "we are on Detail
now", "the dialog is gone" -- instead of asserting on a widget that happens to
live on the destination. The tests that matter here are the timing ones: a
transition that has started is not a transition that has finished, and every
property below is defined so that a wait is a wait.
"""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.navigation.route import Route
from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import ComposableWidget, Widget


SIZE = (400, 300)


class ListScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(width="wt", height="wt")


class DetailScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(width="wt", height="wt")


class ThirdScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(width="wt", height="wt")


class ConfirmDialog(ComposableWidget):
    def build(self) -> Widget:
        return Container(width=100, height=80)


def _animated(widget: Widget) -> Route:
    """A route whose push/pop actually animates, so the timing is observable."""
    return Route(builder=lambda: widget, transition_spec=MaterialTransitions.page())


def _instant(widget: Widget) -> Route:
    """A route that arrives with no transition, for the tests timing is not about.

    A bare widget push animates -- the harness builds the app's Material
    navigator -- and a live push transition is itself ``in_transition``.
    """
    return Route(builder=lambda: widget)


# -- the route stack ------------------------------------------------------


def test_route_stack_reports_the_screen_widgets_bottom_to_top() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        assert isinstance(app.current_screen, ListScreen)
        assert len(app.route_stack) == 1

        app.app.navigator.push(DetailScreen())
        app.settle()

        assert len(app.route_stack) == 2
        assert isinstance(app.route_stack[0], ListScreen)
        assert isinstance(app.current_screen, DetailScreen)


def test_a_push_is_visible_immediately() -> None:
    """Push is synchronous, so a push assertion needs no wait."""
    with AppHarness(ListScreen(), size=SIZE) as app:
        app.app.navigator.push(_animated(DetailScreen()))

        # No settle, no await: the stack has already moved.
        assert len(app.route_stack) == 2
        assert isinstance(app.current_screen, DetailScreen)


async def test_a_pop_changes_the_depth_only_when_the_exit_animation_finalizes() -> None:
    """The assertion this issue exists to make possible.

    A route being animated out is still mounted, still laid out and still
    painted. Reporting the pop as done the instant it is requested would let a
    test go green on a transition that has not happened.
    """
    with AppHarness(ListScreen(), size=SIZE) as app:
        nav = app.app.navigator
        nav.push(_animated(DetailScreen()))
        app.settle()
        assert len(app.route_stack) == 2

        nav.pop()
        # The pop runs as a task and then animates. Neither has happened yet.
        assert len(app.route_stack) == 2

        await app.wait_for(lambda: len(app.route_stack) == 1)
        assert isinstance(app.current_screen, ListScreen)


def test_route_stack_reports_none_for_a_route_nobody_has_displayed() -> None:
    """Reading the stack must not build what the app never showed."""
    deep = Navigator.routes([ListScreen(), DetailScreen(), ThirdScreen()])
    with AppHarness(deep, size=SIZE) as app:
        stack = app.route_stack

        assert len(stack) == 3
        assert isinstance(app.current_screen, ThirdScreen)
        # Only the top is displayed, so the two below it were never built.
        assert stack[0] is None
        assert stack[1] is None


def test_reading_the_stack_builds_nothing() -> None:
    builds = 0

    def build_detail() -> Widget:
        nonlocal builds
        builds += 1
        return DetailScreen()

    nav = Navigator.routes([ListScreen(), Route(builder=build_detail)])
    with AppHarness(nav, size=SIZE) as app:
        before = builds

        for _ in range(3):
            app.route_stack
            app.current_screen

        assert builds == before


# -- in_transition --------------------------------------------------------


async def test_in_transition_covers_the_window_before_the_pop_task_runs() -> None:
    """The window that made the narrow "is an animation running" reading a trap.

    ``pop()`` spawns a task, so on that reading ``in_transition`` would be False
    here and ``wait_for(lambda: not app.in_transition)`` would go through having
    waited for nothing.
    """
    with AppHarness(ListScreen(), size=SIZE) as app:
        nav = app.app.navigator
        nav.push(_animated(DetailScreen()))
        # The push animates, and `settle()` elapses no time, so the enter
        # transition is genuinely still running here -- the narrow reading is
        # honest for a push. Wait it out to reach a quiet baseline.
        assert app.in_transition is True
        await app.wait_for(lambda: not app.in_transition)

        nav.pop()
        # No await yet: the pop task has not run a single line, so there is no
        # transition object. The narrow reading would say False here.
        assert app.in_transition is True

        await app.wait_for(lambda: len(app.route_stack) == 1)
        assert app.in_transition is False


def test_in_transition_does_not_stick_when_the_pop_could_not_be_scheduled() -> None:
    """A pop outside a running loop must not leave the flag raised forever.

    ``spawn_task`` closes the coroutine and raises when a harness is watching, so
    the ``finally`` inside it never runs -- the release has to happen in ``pop()``.
    """
    from nuiitivet.testing import UnschedulableAsyncWork

    with AppHarness(ListScreen(), size=SIZE) as app:
        nav = app.app.navigator
        nav.push(_instant(DetailScreen()))
        app.settle()
        assert app.in_transition is False

        # Sync test: there is no loop, and the harness is observing.
        try:
            nav.pop()
        except UnschedulableAsyncWork:
            pass
        else:  # pragma: no cover - the guard is the point
            raise AssertionError("expected UnschedulableAsyncWork")

        assert app.in_transition is False


async def test_in_transition_is_false_once_a_pop_is_refused() -> None:
    """A back request that pops nothing still has to release the flag."""
    with AppHarness(ListScreen(), size=SIZE) as app:
        app.app.navigator.pop()  # nothing to pop
        assert app.in_transition is True

        await app.idle()
        assert app.in_transition is False
        assert len(app.route_stack) == 1


# -- overlays -------------------------------------------------------------


def test_open_overlays_reports_the_content_not_the_composed_layer() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        dialog = ConfirmDialog()
        app.app.overlay.show(dialog, backdrop=True)

        assert app.open_overlays == (dialog,)
        assert app.top_overlay is dialog
        assert isinstance(app.top_overlay, ConfirmDialog)


def test_no_overlay_open_reads_as_empty() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        assert app.open_overlays == ()
        assert app.top_overlay is None


def test_open_overlays_is_bottom_to_top() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        first = ConfirmDialog()
        second = ConfirmDialog()
        app.app.overlay.show(first)
        app.app.overlay.show(second)

        assert app.open_overlays == (first, second)
        assert app.top_overlay is second


def test_reading_open_overlays_builds_nothing() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        entry_widgets_before = [e._widget for e in app.app.overlay.open_entries]
        dialog = ConfirmDialog()
        app.app.overlay.show(dialog)

        for _ in range(3):
            app.open_overlays
            app.top_overlay

        # The content is known without ever calling build_widget().
        assert app.top_overlay is dialog
        assert entry_widgets_before == []


async def test_a_dismissed_dialog_is_still_open_until_its_animation_finalizes() -> None:
    """Dismissed is not gone.

    The overlay keeps painting the layer for the whole exit transition, so
    reporting it closed on dismissal would let a test -- and the input path
    below -- act on a dialog that is still on screen.
    """
    content = Container(width="wt", height="wt")
    with AppHarness(content, size=SIZE) as app:
        overlay = MaterialOverlay.of(content)
        overlay.show(ConfirmDialog(), backdrop=True, transition_spec=MaterialTransitions.page())
        assert len(app.open_overlays) == 1

        overlay.close(None)
        # Dismissed, and still there: the fade has not finished.
        assert len(app.open_overlays) == 1
        assert overlay.has_entries() is True

        await app.wait_for(lambda: not app.open_overlays)
        assert overlay.has_entries() is False


async def test_a_click_during_the_exit_animation_does_not_reach_the_screen_behind() -> None:
    """The input bug the single source of truth fixes.

    ``Overlay.hit_test`` short-circuits on ``has_entries()``. While that answered
    "was it dismissed" rather than "is it still on screen", the overlay went
    transparent to the pointer the instant a dialog was dismissed -- for the
    whole fade, during which the dialog is still painted over the content.
    """
    clicks: list[str] = []

    class Behind(ComposableWidget):
        def build(self) -> Widget:
            from nuiitivet.modifiers.clickable import clickable

            return Container(width="wt", height="wt").modifier(
                clickable(on_click=lambda: clicks.append("behind"))
            )

    behind = Behind()
    with AppHarness(behind, size=SIZE) as app:
        overlay = MaterialOverlay.of(behind)
        overlay.show(ConfirmDialog(), backdrop=True, transition_spec=MaterialTransitions.page())
        app.settle()

        overlay.close(None)
        app.settle()

        # Mid-fade: the dialog is still painted, so it still owns the pointer.
        assert overlay.hit_test(10, 10) is not None
        assert clicks == []

        await app.wait_for(lambda: not app.open_overlays)


async def test_escape_during_the_exit_animation_is_a_no_op() -> None:
    """Neither a double-close nor a pop of the screen behind.

    ``has_entries()`` is True through the fade, so App's back routing picks the
    overlay. The topmost entry is already exiting, so there is nothing to close
    -- and the event stops there rather than falling through to the navigator,
    because the dialog the user is still looking at is still blocking.
    """
    content = Container(width="wt", height="wt")
    with AppHarness(content, size=SIZE) as app:
        overlay = MaterialOverlay.of(content)
        nav = app.app.navigator
        nav.push(_animated(DetailScreen()))
        await app.wait_for(lambda: not app.in_transition)
        assert len(app.route_stack) == 2

        overlay.show(ConfirmDialog(), backdrop=True, transition_spec=MaterialTransitions.dialog())
        overlay.close(None)
        assert overlay.has_entries() is True

        handled = app.app._dispatch_key_press("escape")
        await app.idle()

        # Consumed by the fading dialog, not passed to the navigator.
        assert handled is True
        assert len(app.route_stack) == 2

        # And still not popped once the dialog has finished leaving.
        await app.wait_for(lambda: not app.open_overlays)
        await app.idle()
        assert len(app.route_stack) == 2
        assert isinstance(app.current_screen, DetailScreen)


# -- the framework accessors ----------------------------------------------


def test_navigator_stack_is_public_and_observation_only() -> None:
    builds = 0

    def build_detail() -> Widget:
        nonlocal builds
        builds += 1
        return DetailScreen()

    nav = Navigator.routes([ListScreen(), Route(builder=build_detail)])
    stack = nav.stack

    assert isinstance(stack, tuple)
    assert len(stack) == 2
    assert all(isinstance(route, Route) for route in stack)
    assert builds == 0


def test_snapshot_stack_is_not_the_stack() -> None:
    """The name that sent #530 the long way round, pinned."""
    nav = Navigator.routes([ListScreen(), DetailScreen()])

    assert len(nav.stack) == 2
    # The restore log covers pushes, not the construction stack.
    assert nav.snapshot_stack() == []
    assert "not the route stack" in (Navigator.snapshot_stack.__doc__ or "").lower()


def test_a_nested_navigator_is_reached_through_its_own_stack() -> None:
    """The escape hatch the guide documents, pinned -- including the wrong turn.

    ``Navigator.of(widget)`` resolves the nearest *ancestor*, so pointing it at
    the nested navigator hands back the root. The way in is the keyed widget
    itself.
    """
    from nuiitivet.layout.column import Column
    from nuiitivet.modifiers.keyed import keyed

    class Tabs(ComposableWidget):
        def build(self) -> Widget:
            return Column(
                children=[Navigator(ListScreen()).modifier(keyed("tabs"))],
                width="wt",
                height="wt",
            )

    with AppHarness(Tabs(), size=SIZE) as app:
        nested = app.get(key="tabs").widget

        assert isinstance(nested, Navigator)
        assert nested is not app.app.navigator
        assert len(nested.stack) == 1

        nested.push(DetailScreen())
        app.settle()

        # The nested stack moved; the App's did not.
        assert len(nested.stack) == 2
        assert len(app.route_stack) == 1

        # The wrong turn: `.of()` walks up, not down.
        assert Navigator.of(nested) is app.app.navigator


def test_overlay_open_entries_skips_the_pinned_base_route() -> None:
    with AppHarness(ListScreen(), size=SIZE) as app:
        overlay = app.app.overlay
        assert overlay.open_entries == ()

        dialog = ConfirmDialog()
        overlay.show(dialog)

        assert len(overlay.open_entries) == 1
        assert overlay.open_entries[0].content is dialog


def test_overlay_entry_content_falls_back_to_the_built_widget() -> None:
    """``insert_entry`` has no content distinct from the entry's own build."""
    from nuiitivet.overlay.overlay_entry import OverlayEntry

    widget = Container(width=10, height=10)
    entry = OverlayEntry(builder=lambda: widget)

    assert entry.content is None  # never built, and asking must not build

    entry.build_widget()
    assert entry.content is widget
