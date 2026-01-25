from nuiitivet.observable import Observable, _ObservableValue
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.scrolling import ScrollDirection
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.scroller import Scroller


class DummyCanvas:

    def save(self):
        return None

    def restore(self):
        return None

    def clipRect(self, *_, **__):
        return None


class DummyCell(Widget):

    def __init__(self, tag: object):
        super().__init__()
        self.tag = tag

    def preferred_size(self):
        return (80, 20)

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


class MockApp:

    def __init__(self):
        self.invalidations = 0
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False):
        self.invalidations += 1


def _make_model(count: int):

    class _Model:
        items: Observable[list[str]] = Observable([])

    model = _Model()
    model.items.value = [f"Item {idx}" for idx in range(count)]
    return model


def test_scroller_reports_extent_with_transient_foreach_items():
    model = _make_model(40)
    transient = _ObservableValue([], owner=model, name="items")

    def builder(item, idx):
        return DummyCell(tag=item)

    column = Column.builder(transient, builder, gap=2, cross_alignment="start")
    scroller = Scroller(column, height=80)
    app = MockApp()
    scroller.mount(app)
    try:
        canvas = DummyCanvas()
        scroller.paint(canvas, 0, 0, 200, 80)
        axis_state = scroller._controller.axis_state(ScrollDirection.VERTICAL)
        assert axis_state.content_size.value > axis_state.viewport_size.value
        assert axis_state.max_extent.value > 0
    finally:
        scroller.unmount()
