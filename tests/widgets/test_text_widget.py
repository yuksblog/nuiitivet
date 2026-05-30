from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.observable import Observable
from nuiitivet.layout.row import Row


def _make_obs(initial):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


class DummyApp:

    def __init__(self):
        self.invalidated = 0

    def invalidate(self):
        self.invalidated += 1


def test_text_auto_bind_and_unbind():
    s = _make_obs("hello")
    t = Text(s)
    app = DummyApp()
    t.mount(app)
    assert t._label_unsub is not None
    s.value = "world"
    assert app.invalidated == 1
    t.unmount()
    assert t._label_unsub is None
    s.value = "again"
    assert app.invalidated == 1


def test_text_observable_change_marks_layout_needs_on_parent() -> None:
    s = _make_obs("hi")
    bound = Text(s)
    root = Row([Text("Last click:"), bound], gap=8)
    app = DummyApp()
    root.mount(app)

    root.layout(400, 40)
    assert root.needs_layout is False
    assert bound.needs_layout is False

    s.value = "Clicked: " + ("X" * 80)
    assert root.needs_layout is True
