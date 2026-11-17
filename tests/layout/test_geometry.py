"""Tests for the Geometry widget and its Size value type."""

from nuiitivet.layout.geometry import Geometry
from nuiitivet.rendering.size import Size
from nuiitivet.layout.container import Container
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks


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

    # The publish is deferred: layout only queues, the between-frames flush
    # performs the State write.
    assert geom.size.value == Size(0, 0)
    flush_size_change_callbacks()
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
    flush_size_change_callbacks()

    # Two layouts within one frame coalesce into one publish of the final size.
    assert geom.size.value == Size(640, 480)


def test_equal_size_is_deduped():
    geom = Geometry(Container())
    seen: list[Size] = []
    geom.size.subscribe(seen.append)

    geom.layout(300, 200)
    flush_size_change_callbacks()
    geom.layout(300, 200)  # identical: must not re-fire
    flush_size_change_callbacks()
    geom.layout(300, 201)  # changed: fires
    flush_size_change_callbacks()

    assert seen == [Size(300, 200), Size(300, 201)]


class _LazySizeReader(Widget):
    """Reads the source State at measure time, like a bound Text label."""

    def __init__(self, source) -> None:
        super().__init__()
        self._source = source
        self.measured_against: list[Size] = []

    def preferred_size(self, max_width=None, max_height=None):
        size = self._source.value
        self.measured_against.append(size)
        return (max(1, size.width), 16)

    def paint(self, canvas, x, y, width, height) -> None:
        del canvas, x, y, width, height


def test_sibling_measured_before_geometry_is_not_torn():
    from nuiitivet.layout.column import Column

    # A sibling laid out before the Geometry in the same pass must keep seeing
    # the old size for the rest of the frame: measurement and paint then agree,
    # and the new size lands for everyone at the between-frames flush.
    geom = Geometry(Container(height=80), width="wt")
    reader = _LazySizeReader(geom.size)
    root = Column([reader, geom], width=400, height=300)

    root.layout(400, 300)

    assert set(reader.measured_against) == {Size(0, 0)}
    # What a paint-time reader would resolve now is still the measured value.
    assert geom.size.value == Size(0, 0)

    flush_size_change_callbacks()
    assert geom.size.value.width == 400


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
    flush_size_change_callbacks()

    assert pane.size.value.width == 300


# -- Geometry.proxy ---------------------------------------------------------


class _Badge(ComposableWidget):
    """Derives from the proxy's size in ``__init__``, as the guide shows."""

    def __init__(self) -> None:
        super().__init__()
        self.size = Geometry.proxy(self).size
        self.label = self.size.map(lambda s: f"{s.width}px")
        self.built_with: list[Size] = []

    def build(self) -> Widget:
        self.built_with.append(self.size.value)
        return Container()


def _laid_out(geom: Geometry, width: int, height: int) -> Geometry:
    geom.layout(width, height)
    flush_size_change_callbacks()
    return geom


def test_proxy_derivation_is_built_before_mount():
    badge = _Badge()

    assert badge.size.value == Size(0, 0)
    assert badge.label.value == "0px"


def test_proxy_follows_the_provider_after_the_first_layout():
    badge = _Badge()
    geom = Geometry(Container(badge))
    geom.mount(None)

    _laid_out(geom, 300, 200)
    assert badge.label.value == "300px"

    _laid_out(geom, 640, 200)
    assert badge.label.value == "640px"
    geom.unmount()


def test_proxy_nearest_provider_wins():
    badge = _Badge()
    inner = Geometry(badge, width=120)
    outer = Geometry(Container(inner))
    outer.mount(None)

    _laid_out(outer, 500, 300)

    assert inner.size.value.width == 120
    assert badge.size.value == inner.size.value
    outer.unmount()


def test_proxy_size_is_there_for_the_first_build():
    geom = _laid_out(Geometry(Container()), 300, 200)
    badge = _Badge()
    geom.add_child(Container(badge))

    geom.mount(None)

    assert badge.built_with == [Size(300, 200)]
    geom.unmount()


def test_proxy_made_on_a_mounted_widget_follows_at_once():
    probe = Container()
    geom = _laid_out(Geometry(probe), 300, 200)
    geom.mount(None)

    assert Geometry.proxy(probe).size.value == Size(300, 200)
    geom.unmount()


def test_proxy_unmount_releases_the_subscription_and_keeps_the_last_size():
    badge = _Badge()
    geom = Geometry(Container(badge))
    geom.mount(None)
    _laid_out(geom, 300, 200)

    geom.unmount()
    geom.size.value = Size(640, 480)

    assert badge.size.value == Size(300, 200)


def test_proxy_remounted_elsewhere_follows_the_new_provider():
    badge = _Badge()
    first = Geometry(badge)
    first.mount(None)
    _laid_out(first, 300, 200)
    first.unmount()
    first.remove_child(badge)

    second = _laid_out(Geometry(badge), 800, 600)
    second.mount(None)

    assert badge.size.value == Size(800, 600)
    _laid_out(first, 111, 111)
    assert badge.size.value == Size(800, 600)
    second.unmount()


def test_proxy_keeps_the_placeholder_in_a_tree_with_no_provider():
    badge = _Badge()
    root = Container(badge)

    root.mount(None)

    assert badge.size.value == Size(0, 0)
    root.unmount()


def test_proxy_before_super_init_raises():
    import pytest

    class _Early(Widget):
        def __init__(self) -> None:
            Geometry.proxy(self)
            super().__init__()

    with pytest.raises(RuntimeError, match=r"Geometry\.proxy\(\) was called on _Early before super\(\).__init__\(\)"):
        _Early()


def test_proxy_does_not_keep_its_widget_alive():
    import gc
    import weakref

    gc.collect()
    gc.disable()
    try:
        probe = Container()
        proxy = Geometry.proxy(probe)
        ref = weakref.ref(probe)

        del probe
        assert ref() is None
        assert proxy.size.value == Size(0, 0)
    finally:
        gc.enable()
