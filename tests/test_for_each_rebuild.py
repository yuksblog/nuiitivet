from nuiitivet.layout.for_each import ForEach
from nuiitivet.widgeting.widget import Widget
from nuiitivet.observable import Observable


def _make_obs(initial):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


class DummyWidget(Widget):

    def __init__(self, pref_w: int, pref_h: int, tag: object = None):
        super().__init__()
        self._pref = (pref_w, pref_h)
        self.tag = tag

    def preferred_size(self):
        return self._pref

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


def _child_tags(fe: ForEach):
    tags = []
    for child in fe.provide_layout_children():
        payload = _resolve_payload(child)
        tags.append(getattr(payload, "tag", None))
    return tags


def test_state_items_trigger_rebuild():
    s = _make_obs([1, 2, 3])

    def builder(item, idx):
        return DummyWidget(10, 5, tag=item)

    fe = ForEach(s, builder)
    fe.on_mount()
    fe.evaluate_build()
    assert _child_tags(fe) == [1, 2, 3]
    s.value = [42]
    fe.evaluate_build()
    assert _child_tags(fe) == [42]


def test_value_change_in_place_invalidates_scope():
    s = _make_obs([1, 2, 3])
    calls = []

    def builder(item, idx):
        calls.append((idx, item))
        return DummyWidget(6, 4, tag=item)

    fe = ForEach(s, builder)
    fe.on_mount()
    fe.evaluate_build()
    calls.clear()
    s.value = [1, 42, 3]
    assert _child_tags(fe) == [1, 42, 3]
    assert calls == [(1, 42)]


def test_builder_invalid_entries_fallback_to_spacer():
    items = [1, 2, 3, 4]

    def builder(item, idx):
        if item == 2:
            return None
        if item == 3:
            raise RuntimeError("boom")
        return DummyWidget(6, 4, tag=item)

    fe = ForEach(items, builder)
    fe.evaluate_build()
    payloads = [_resolve_payload(child) for child in fe.provide_layout_children()]
    assert len(payloads) == 4
    dummy_tags = [p.tag for p in payloads if isinstance(p, DummyWidget)]
    assert dummy_tags == [1, 4]


def test_provide_layout_children_returns_snapshot():
    items = [0, 1]

    def builder(item, idx):
        return DummyWidget(5, 5, tag=item)

    fe = ForEach(items, builder)
    fe.evaluate_build()
    provided = fe.provide_layout_children()
    assert len(provided) == 2
    assert _child_tags(fe)[0] == 0
