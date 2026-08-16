"""Tests for SearchBar, DockedSearchBar and their styles.

The assertions here track the decisions recorded on #573: ``width`` names the
box rather than the bar, the outer margin animates on focus, neither widget
carries an elevation, and the docked container clamps to the MD3 height range.
"""

from __future__ import annotations

import dataclasses

from nuiitivet.material.search import (
    DockedSearchBar,
    SearchBar,
    _DockedContainer,
    _SearchBarCore,
    _SearchPane,
)
from nuiitivet.material.styles.search_bar_style import DockedSearchBarStyle, SearchBarStyle
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeApp:
    def invalidate(self) -> None:
        pass

    def request_focus(self, node, source=None) -> None:
        pass


def _mount(widget):
    widget.mount(_FakeApp())
    return widget


def _pane_of(widget) -> _SearchPane:
    """Return the mounted pane a SearchBar / DockedSearchBar built."""
    built = widget.build()
    _mount(built)
    return built


def _settle(pane: _SearchPane) -> None:
    """Snap the margin animation to its target, without running a clock."""
    pane._margin._value.value = pane._margin.target


# ===========================================================================
# Styles
# ===========================================================================


class TestSearchBarStyle:
    def test_no_elevation_field(self):
        """Elevation belongs to the Divided variant, which is not implemented."""
        names = {f.name for f in dataclasses.fields(SearchBarStyle)}
        assert not [n for n in names if "elevation" in n or "shadow" in n or "tint" in n]

    def test_margin_endpoints_match_md3(self):
        style = SearchBarStyle()
        assert style.margin == 24.0
        assert style.focused_margin == 12.0

    def test_container_geometry(self):
        style = SearchBarStyle()
        assert style.container_height == 56.0
        assert (style.min_width, style.max_width) == (360.0, 720.0)


class TestDockedSearchBarStyle:
    def test_no_elevation_or_divider(self):
        names = {f.name for f in dataclasses.fields(DockedSearchBarStyle)}
        assert not [n for n in names if "elevation" in n or "divider" in n or "tint" in n]

    def test_gap_and_height_range(self):
        style = DockedSearchBarStyle()
        assert style.gap == 2.0
        assert style.min_height == 240.0
        assert style.max_height_ratio == 2.0 / 3.0


# ===========================================================================
# The bar itself
# ===========================================================================


class TestSearchBarCore:
    def test_fully_rounded(self):
        core = _SearchBarCore()
        assert core.corner_radii_pixels(400, 56) == (28.0, 28.0, 28.0, 28.0)

    def test_text_starts_after_the_icon_target(self):
        """4dp outer space + 48dp target + 4dp gap puts the glyph edge at 16dp."""
        core = _SearchBarCore(leading_icon="search")
        left, _ = core._slot_bounds(400)
        assert left == 4.0 + 48.0 + 4.0

    def test_no_actions_uses_the_16dp_space(self):
        core = _SearchBarCore(leading_icon=None, trailing_icon=None)
        left, right = core._slot_bounds(400)
        assert left == 16.0
        assert right == 400 - 16.0

    def test_focus_is_published(self):
        core = _mount(_SearchBarCore())
        assert core.focused.value is False
        core._handle_editable_focus_change(True, None)
        assert core.focused.value is True

    def test_on_tap_without_icon_is_rejected(self):
        try:
            _SearchBarCore(on_tap_trailing_icon=lambda: None)
        except ValueError as exc:
            assert "trailing_icon" in str(exc)
        else:
            raise AssertionError("expected ValueError")


# ===========================================================================
# The pane: width names the box
# ===========================================================================


class TestSearchPane:
    def _pane(self, **style_changes) -> _SearchPane:
        style = SearchBarStyle().copy_with(**style_changes) if style_changes else SearchBarStyle()
        core = _SearchBarCore(style=style)
        return _SearchPane(core, core=core)

    def test_bar_is_the_box_minus_both_margins(self):
        pane = self._pane()
        x, _, w, _ = pane._bar_rect(600, 56)
        assert w == 600 - 2 * 24
        assert x == 24

    def test_bar_is_capped_at_max_width_and_centred(self):
        pane = self._pane()
        x, _, w, _ = pane._bar_rect(1200, 56)
        assert w == 720
        assert x == (1200 - 720) // 2

    def test_narrow_box_wins_over_the_360dp_minimum(self):
        """A sub-spec bar beats overflowing the box a resizable window gave us."""
        pane = self._pane()
        x, _, w, _ = pane._bar_rect(300, 56)
        assert w == 300 - 2 * 24
        assert x + w <= 300

    def test_focus_retargets_the_margin(self):
        pane = self._pane()
        _mount(pane)
        assert pane._margin.target == 24.0

        pane._on_focus_changed(True)
        assert pane._margin.target == 12.0
        _settle(pane)
        _, _, focused_w, _ = pane._bar_rect(600, 56)

        pane._on_focus_changed(False)
        assert pane._margin.target == 24.0
        _settle(pane)
        _, _, blurred_w, _ = pane._bar_rect(600, 56)

        # The bar grows by 12dp on each side while focused; the box does not move.
        assert focused_w - blurred_w == 24

    def test_preferred_size_is_the_box(self):
        pane = self._pane()
        assert pane.preferred_size(800, 600) == (800, 56)


# ===========================================================================
# The docked container
# ===========================================================================


class TestDockedContainer:
    def _container(self, bar_rect, content_height=100, viewport=900) -> _DockedContainer:
        content = Box(width=200, height=content_height)
        return _DockedContainer(
            content,
            style=DockedSearchBarStyle(),
            bar_rect=lambda: bar_rect,
            viewport_height=lambda: viewport,
        )

    def test_width_matches_the_bar(self):
        node = self._container((24, 0, 500, 56))
        w, _ = node.preferred_size()
        assert w == 500

    def test_short_content_is_raised_to_the_240dp_minimum(self):
        node = self._container((24, 0, 500, 56), content_height=50)
        _, h = node.preferred_size()
        assert h == 240

    def test_height_is_capped_at_two_thirds_of_the_window(self):
        node = self._container((24, 0, 500, 56), content_height=5000)
        _, h = node.preferred_size()
        assert h == int(900 * (2.0 / 3.0))

    def test_the_minimum_is_a_floor_that_beats_the_two_thirds_cap(self):
        """In a window short enough for the two to disagree, the floor wins."""
        node = self._container((24, 0, 500, 56), content_height=5000, viewport=300)
        _, h = node.preferred_size()
        assert int(300 * (2.0 / 3.0)) < 240  # the two really do disagree here
        assert h == 240

    def test_the_container_overflows_rather_than_shrinking_below_the_minimum(self):
        """A bar low in a short window: the container runs off the bottom.

        Deliberate. A search bar does not belong where its container cannot
        open, so the minimum is honoured and the overflow is left visible
        rather than shrinking the container into a useless sliver. It stays
        harmless because the panel is never slid upwards — see
        ``TestDockedContainerNeverCoversTheBar``.
        """
        node = self._container((24, 180, 416, 56), content_height=5000, viewport=360)
        _, h = node.preferred_size()  # measured unbounded, exactly as the overlay does
        assert h == 240
        assert 180 + 56 + 2 + h > 360  # runs past the bottom edge, by design

    def test_viewport_falls_back_to_max_height_when_unresolved(self):
        content = Box(width=200, height=5000)
        node = _DockedContainer(
            content,
            style=DockedSearchBarStyle(),
            bar_rect=lambda: None,
            viewport_height=lambda: None,
        )
        _, h = node.preferred_size(1000, 900)
        assert h == int(900 * (2.0 / 3.0))


# ===========================================================================
# Public widgets
# ===========================================================================


class TestSearchBar:
    def test_value_observable_is_written_back(self):
        query: Observable[str] = Observable("")
        bar = SearchBar(query)
        _mount(bar)
        bar._core._editable.value = "kiwi"
        assert query.value == "kiwi"

    def test_observable_value_is_displayed(self):
        query: Observable[str] = Observable("apricot")
        bar = SearchBar(query)
        _mount(bar)
        assert bar.value == "apricot"

    def test_build_returns_a_pane_wrapping_the_same_core(self):
        bar = SearchBar()
        _mount(bar)
        pane = _pane_of(bar)
        assert isinstance(pane, _SearchPane)
        assert pane._core is bar._core

    def test_core_survives_a_rebuild(self):
        """Focus and cursor position depend on the core outliving recomposition."""
        bar = SearchBar()
        _mount(bar)
        assert bar.build()._core is bar.build()._core


class TestDockedSearchBar:
    def _docked(self) -> DockedSearchBar:
        return DockedSearchBar(content=Box(width=200, height=100))

    def test_opens_on_focus_even_with_an_empty_query(self):
        docked = _mount(self._docked())
        try:
            assert docked.is_open.value is False

            docked._core.focused.value = True
            assert docked.is_open.value is True
        finally:
            docked.unmount()

    def test_closes_on_blur(self):
        docked = _mount(self._docked())
        try:
            docked._core.focused.value = True
            docked._core.focused.value = False
            assert docked.is_open.value is False
        finally:
            docked.unmount()

    def test_an_app_supplied_is_open_is_the_one_that_is_driven(self):
        panel: Observable[bool] = Observable(False)
        docked = _mount(DockedSearchBar(content=Box(width=200, height=100), is_open=panel))
        try:
            assert docked.is_open is panel
            docked._core.focused.value = True
            assert panel.value is True
        finally:
            docked.unmount()

    def test_typing_reopens_a_container_the_app_closed(self):
        """The gap that made "Enter closes it, results on the page" unusable.

        Focus never changes across the close, so without a user-edit trigger
        the container could never come back.
        """
        docked = _mount(self._docked())
        try:
            docked._core.focused.value = True
            docked.is_open.value = False  # the app closes it

            docked._core._editable._handle_text("a")
            assert docked.is_open.value is True
        finally:
            docked.unmount()

    def test_a_write_by_the_app_does_not_reopen_it(self):
        """Filling the bar in after a pick must not bring the container back."""
        docked = _mount(self._docked())
        try:
            docked._core.focused.value = True
            docked.is_open.value = False

            docked._core.value = "apricot"
            assert docked.is_open.value is False
            assert docked.value == "apricot"
        finally:
            docked.unmount()

    def test_a_write_through_the_bound_observable_does_not_reopen_it(self):
        query: Observable[str] = Observable("")
        docked = _mount(DockedSearchBar(query, content=Box(width=200, height=100)))
        try:
            docked._core.focused.value = True
            docked.is_open.value = False

            query.value = "apricot"
            assert docked.is_open.value is False
            assert docked.value == "apricot"
        finally:
            docked.unmount()

    def test_enter_closes_the_container_and_still_reports_the_query(self):
        seen: list[str] = []
        docked = _mount(DockedSearchBar(content=Box(width=200, height=100), on_submit=seen.append))
        try:
            docked._core.focused.value = True
            for ch in "kiwi":
                docked._core._editable._handle_text(ch)
            docked._core._editable._handle_key("enter", 0)

            assert seen == ["kiwi"]
            assert docked.is_open.value is False
        finally:
            docked.unmount()

    def test_close_on_enter_false_keeps_the_container_up(self):
        seen: list[str] = []
        docked = _mount(
            DockedSearchBar(
                content=Box(width=200, height=100),
                on_submit=seen.append,
                close_on_enter=False,
            )
        )
        try:
            docked._core.focused.value = True
            docked._core._editable._handle_text("k")
            docked._core._editable._handle_key("enter", 0)

            assert seen == ["k"]
            assert docked.is_open.value is True
        finally:
            docked.unmount()

    def test_enter_closes_the_container_even_without_an_on_submit(self):
        docked = _mount(self._docked())
        try:
            docked._core.focused.value = True
            docked._core._editable._handle_key("enter", 0)
            assert docked.is_open.value is False
        finally:
            docked.unmount()

    def test_a_repeat_enter_on_an_unchanged_query_still_closes_it(self):
        """on_submit is suppressed for an unchanged value; the close is not.

        Searching, reopening the container and pressing Enter again is an
        ordinary thing to do, and the key has to keep working.
        """
        seen: list[str] = []
        docked = _mount(DockedSearchBar(content=Box(width=200, height=100), on_submit=seen.append))
        try:
            docked._core.focused.value = True
            docked._core._editable._handle_text("k")
            docked._core._editable._handle_key("enter", 0)
            assert seen == ["k"]

            docked.is_open.value = True  # the user comes back to the bar
            docked._core._editable._handle_key("enter", 0)

            assert seen == ["k"]  # unchanged query: no second search
            assert docked.is_open.value is False

        finally:
            docked.unmount()

    def test_enter_is_left_alone_when_it_would_do_nothing(self):
        """No submit handler and no close: the key stays free for a shortcut."""
        docked = DockedSearchBar(content=Box(width=200, height=100), close_on_enter=False)
        assert docked._core._editable._on_submit is None
        assert docked._core._editable._on_enter_key is None
        assert docked._core._editable._handle_key("enter", 0) is False

    def test_popup_is_anchored_to_the_bar_not_the_pane(self):
        """The anchor rect is re-resolved per layout, so it tracks the margin."""
        docked = self._docked()
        pane = docked.build()
        # The pane's child is the popup wrapper, and PopupBox is coextensive
        # with the widget it wraps -- the bar, not the pane. That is what makes
        # a constant 2dp offset track the margin animation.
        assert pane._child is not docked._core
        assert pane._child._child is docked._core


class TestDockedContainerNeverCoversTheBar:
    """The bar stays visible; the container yields.

    ``popup`` only ever shifts content along the cross axis, so nothing can
    slide the container up over the bar. ``flip=False`` then keeps it below the
    bar rather than opening upwards, which is the settled behaviour: it
    overflows the window instead.
    """

    def test_the_panel_does_not_flip_above_the_bar(self):
        docked = DockedSearchBar(content=Box(width=200, height=100))
        popup_box = docked.build()._child
        assert popup_box._flip is False
        assert popup_box._shift is True

    def test_overflow_is_safe_because_the_panel_is_never_slid_upwards(self):
        """With no room left, the container keeps its size and overflows."""
        content = Box(width=200, height=5000)
        node = _DockedContainer(
            content,
            style=DockedSearchBarStyle(),
            bar_rect=lambda: (24, 300, 416, 56),
            viewport_height=lambda: 360,  # bar bottom is 356, 4px short of the edge
        )
        _, h = node.preferred_size()
        assert h == 240

        docked = DockedSearchBar(content=Box(width=200, height=100))
        assert docked.build()._child._flip is False


class TestBarRectRounding:
    """Sub-pixel motion must not become a whole-pixel twitch.

    The settling spring overshoots its target by ~5e-6 px. Truncating the
    resulting edge turns that into a 1px jump on exactly one frame, which is
    visible as a flick at the end of the animation. `button_group.py` already
    rounds boundaries rather than sizes for the same reason.
    """

    def _pane(self) -> _SearchPane:
        core = _SearchBarCore()
        return _SearchPane(core, core=core)

    def test_a_hair_of_overshoot_does_not_move_the_bar(self):
        pane = self._pane()
        pane._margin._value.value = 12.0
        settled = pane._bar_rect(440, 56)

        pane._margin._value.value = 11.999995  # the spring's real overshoot
        assert pane._bar_rect(440, 56) == settled

    def test_edges_stay_symmetric_at_fractional_margins(self):
        """Rounding x and w apart lets the two disagree; rounding edges cannot."""
        pane = self._pane()
        for margin in (12.4, 12.5, 12.6, 17.5, 23.5):
            pane._margin._value.value = margin
            x, _, w, _ = pane._bar_rect(440, 56)
            assert x == 440 - (x + w), f"asymmetric at margin={margin}: x={x} w={w}"
