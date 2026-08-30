"""Tests for the Geometry widget and its Size value type."""

from nuiitivet.layout.geometry import Geometry
from nuiitivet.rendering.size import Size
from nuiitivet.layout.container import Container
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _Probe(ComposableWidget):
    """A leaf that reads the nearest Geometry so ``of()`` has a context."""

    def build(self) -> Widget:
        return self


def test_size_is_compared_by_value():
    assert Size(10, 20) == Size(10, 20)
    assert Size(10, 20) != Size(10, 21)
    w, h = Size(10, 20)
    assert (w, h) == (10, 20)


def test_layout_publishes_measured_size():
    geom = Geometry(Container())

    geom.layout(300, 200)

    assert geom.size.value == Size(300, 200)


def test_layout_is_transparent_to_child():
    child = Container()
    geom = Geometry(child)

    geom.layout(300, 200)

    # The child is laid out at the wrapper's own size, at the origin.
    assert child.layout_rect == (0, 0, 300, 200)


def test_size_updates_on_relayout():
    geom = Geometry(Container())

    geom.layout(300, 200)
    geom.layout(640, 480)

    assert geom.size.value == Size(640, 480)


def test_equal_size_is_deduped():
    geom = Geometry(Container())
    seen: list[Size] = []
    geom.size.subscribe(seen.append)

    geom.layout(300, 200)
    geom.layout(300, 200)  # identical: must not re-fire
    geom.layout(300, 201)  # changed: fires

    assert seen == [Size(300, 200), Size(300, 201)]


def test_of_returns_nearest_provider():
    probe = _Probe()
    inner = Geometry(probe)
    outer = Geometry(inner)

    assert Geometry.of(probe) is inner
    assert Geometry.of(inner) is outer


def test_of_falls_back_to_outer_provider():
    probe = _Probe()
    outer = Geometry(Container(probe))

    # No nearer Geometry: resolves to the outer provider.
    assert Geometry.of(probe) is outer


def test_of_raises_when_absent():
    probe = _Probe()
    Container(probe)  # a plain ancestor, but no Geometry

    try:
        Geometry.of(probe)
    except RuntimeError as exc:
        assert "Geometry" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected RuntimeError when no Geometry ancestor")


def test_preferred_size_is_transparent_by_default():
    child = Container(width=120, height=80)
    geom = Geometry(child)

    assert geom.preferred_size() == child.preferred_size()


def test_fixed_sizing_overrides_child_in_preferred_size():
    geom = Geometry(Container(width=10, height=10), width=150, height=90)

    assert geom.preferred_size() == (150, 90)


def test_filling_geometry_measures_available_space():
    from nuiitivet.layout.row import Row

    # A filling ("wt") Geometry must measure the space the parent allocates,
    # not its child's intrinsic size: laid out beside a fixed 200px sibling in a
    # 500px row, it fills the remaining 300px and publishes that.
    pane = Geometry(Container(width=10), width="wt")
    row = Row([Container(width=200), pane], gap=0)

    row.layout(500, 100)

    assert pane.size.value.width == 300
