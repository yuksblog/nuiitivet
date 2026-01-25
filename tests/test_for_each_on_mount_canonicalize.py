from nuiitivet.observable import Observable, _ObservableValue
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.for_each import ForEach


class DummyWidget(Widget):

    def __init__(self, tag: object):
        super().__init__()
        self.tag = tag

    def preferred_size(self):
        return (10, 10)

    def paint(self, canvas, x, y, w, h):
        self.set_last_rect(x, y, w, h)


def _resolve_payload(widget: Widget) -> Widget:
    current = widget
    while True:
        nxt = getattr(current, "built_child", None)
        if nxt is None:
            break
        current = nxt
    return current


def _child_tags(widget: ForEach):
    tags = []
    for child in widget.provide_layout_children():
        payload = _resolve_payload(child)
        tags.append(getattr(payload, "tag", None))
    return tags


def _make_model():

    class _Model:
        items = Observable([])

    return _Model()


def test_foreach_mount_subscribes_to_canonical_observable():
    model = _make_model()
    model.items.value = ["alpha", "beta"]
    transient = _ObservableValue([], owner=model, name="items")

    def builder(item, idx):
        return DummyWidget(tag=item)

    widget = ForEach(transient, builder)
    widget.on_mount()
    try:
        assert _child_tags(widget) == ["alpha", "beta"]
        model.items.value = ["updated"]
        assert _child_tags(widget) == ["updated"]
    finally:
        widget.on_unmount()
