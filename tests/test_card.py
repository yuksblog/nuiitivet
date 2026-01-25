from nuiitivet.material.card import Card, FilledCard, ElevatedCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.widgeting.widget import Widget
from nuiitivet.rendering.sizing import Sizing


class FixedWidget(Widget):
    def preferred_size(self):
        return (10, 10)

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def test_border_radius_scalar_normalization():
    mc = Card(None, style=CardStyle(border_radius=8.0))
    assert mc.corner_radii == (8.0, 8.0, 8.0, 8.0)
    assert mc.corner_radius == 8.0


def test_border_radius_tuple_normalization():
    mc = Card(None, style=CardStyle(border_radius=(1, 2, 3, 4)))
    assert mc.corner_radii == (1.0, 2.0, 3.0, 4.0)
    # Box stores the raw value
    assert mc.corner_radius == (1, 2, 3, 4)


def test_default_border_radius():
    # FilledCard defaults to 12.0
    mc = FilledCard(None)
    assert mc.corner_radii == (12.0, 12.0, 12.0, 12.0)
    assert mc.corner_radius == 12.0


def test_bad_tuple_results_in_zeroed_radii():
    # If an invalid-length tuple is provided, the constructor falls back to zeros
    # Note: CardStyle doesn't validate tuple length, but Box might handle it or default to 0
    # Box implementation of corner_radius setter handles normalization
    mc = Card(None, style=CardStyle(border_radius=(1, 2)))
    assert mc.corner_radii == (0.0, 0.0, 0.0, 0.0)
    assert mc.corner_radius == (1, 2)


def test_child_stretch_expands_to_container():
    child = FixedWidget(width=Sizing.flex(1), height=Sizing.flex(1))
    container = Card(child, padding=0)

    # Paint container at 100x100
    container.paint(None, 0, 0, 100, 100)

    # Child should be stretched to 100x100, ignoring its preferred size of 10x10
    assert child.last_rect == (0, 0, 100, 100)


def test_child_stretch_respects_padding():
    child = FixedWidget(width=Sizing.flex(1), height=Sizing.flex(1))
    container = Card(child, padding=10)

    # Paint container at 100x100. Padding is 10 all around.
    # Inner size is 100 - 10 - 10 = 80.
    container.paint(None, 0, 0, 100, 100)

    # Child should be at (10, 10) with size 80x80
    assert child.last_rect == (10, 10, 80, 80)


def test_set_child_replaces_scoped_fragment():
    first = FixedWidget(width=Sizing.flex(1), height=Sizing.flex(1))
    second = FixedWidget(width=Sizing.flex(1), height=Sizing.flex(1))

    container = Card(first, padding=0)
    container.evaluate_build()
    container.set_child(second)
    container.evaluate_build()
    assert len(container.children) == 1
    container.paint(None, 0, 0, 50, 50)
    assert second.last_rect == (0, 0, 50, 50)


def test_callable_child_spec_is_evaluated_per_build():
    builds = []

    def builder():
        widget = FixedWidget(width=Sizing.flex(1), height=Sizing.flex(1))
        builds.append(widget)
        return widget

    container = Card(builder, padding=0)
    container.evaluate_build()
    container.evaluate_build()
    assert len(builds) == 2


def test_elevated_card_reports_shadow_outsets():
    container = ElevatedCard(None)
    left, top, right, bottom = container.paint_outsets()
    # Default shadow for ElevatedCard (elevation 1.0) should reserve bounds
    assert left > 0
    assert top > 0
    assert right > 0
    assert bottom > 0


def test_filled_card_no_shadow():
    container = FilledCard(None)
    left, top, right, bottom = container.paint_outsets()
    assert (left, top, right, bottom) == (0, 0, 0, 0)
