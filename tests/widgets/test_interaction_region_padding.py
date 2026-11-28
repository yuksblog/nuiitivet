"""An interaction region and the padding of the widget it wraps.

A modifier's wrapper takes no padding of its own, so a padded widget is inset
once, measures and hits as it does bare, and is painted where it is laid out.
A region built with its own padding lays its child out at the inset it paints.
"""

from __future__ import annotations

from typing import Optional

import pytest

from nuiitivet.layout.row import Row
from nuiitivet.material.text import Text
from nuiitivet.modifiers.key_shortcut import key_shortcut
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionRegion


def _shortcut(widget: Widget) -> Widget:
    wrapped = widget.modifier(key_shortcut("A", on_trigger=lambda: None))
    assert isinstance(wrapped, InteractionRegion)
    return wrapped


def _padded_row(text: Text) -> Row:
    return Row([text], padding=(12, 0, 12, 12), width="wt", height="wt")


def test_padded_widget_under_a_modifier_is_inset_once_and_painted_where_laid_out() -> None:
    text = Text("hello")

    with AppHarness(lambda: _shortcut(_padded_row(text)), size=(400, 300)) as app:
        app.settle()
        app.window._render_snapshot()

        assert text.last_rect is not None
        assert text.global_visual_rect is not None
        assert text.last_rect[:2] == (12, 0)
        assert text.global_visual_rect[:2] == (12.0, 0.0)


def test_region_with_its_own_padding_lays_the_child_out_where_it_paints() -> None:
    child = Box(width=Sizing.fixed(40), height=Sizing.fixed(20))
    region = InteractionRegion(child, padding=(5, 7, 3, 2))

    with AppHarness(lambda: region, size=(200, 100)) as app:
        app.settle()
        app.window._render_snapshot()

        painted = child.last_rect
        laid_out = child.global_visual_rect
        assert painted is not None
        assert laid_out is not None
        assert tuple(float(v) for v in painted) == laid_out
        assert laid_out[:2] == (5.0, 7.0)


@pytest.mark.parametrize("max_width", [None, 300])
def test_padded_widget_under_a_modifier_measures_as_it_does_bare(max_width: Optional[int]) -> None:
    bare = _padded_row(Text("hello"))
    wrapped = _shortcut(_padded_row(Text("hello")))

    assert wrapped.preferred_size(max_width=max_width) == bare.preferred_size(max_width=max_width)


def _padded_surface() -> Box:
    return Box(
        Box(width=Sizing.fixed(10), height=Sizing.fixed(10)),
        width=Sizing.fixed(100),
        height=Sizing.fixed(50),
        padding=12,
        background_color="#ff0000",
    )


def _hit_at(root: Widget, x: int, y: int) -> Optional[Widget]:
    root.layout(100, 50)
    return root.hit_test(x, y)


@pytest.mark.parametrize("point", [(1, 1), (98, 48), (98, 1), (1, 48)])
def test_click_on_padding_band_reaches_the_same_target_under_a_modifier(point: tuple[int, int]) -> None:
    bare = _padded_surface()
    inner = _padded_surface()
    wrapped = _shortcut(inner)

    assert _hit_at(bare, *point) is bare
    assert _hit_at(wrapped, *point) is inner
