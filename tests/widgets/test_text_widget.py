from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.observable import Observable
from nuiitivet.layout.row import Row


def _make_obs(initial):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_text_auto_bind_and_unbind(nuiitivet_mount):
    s = _make_obs("hello")
    t = Text(s)
    host = nuiitivet_mount(t)
    assert t._label_unsub is not None
    s.value = "world"
    # `> 0`, not `== 1`: coalescing two invalidations into one would break an
    # exact count with no change in behaviour. What matters is that the binding
    # requested a repaint at all, and that unbinding stopped it.
    assert host.invalidate_count > 0
    after_bind = host.invalidate_count

    t.unmount()
    assert t._label_unsub is None
    s.value = "again"
    assert host.invalidate_count == after_bind


def test_text_observable_change_marks_layout_needs_on_parent(nuiitivet_mount) -> None:
    s = _make_obs("hi")
    bound = Text(s)
    root = Row([Text("Last click:"), bound], gap=8)
    nuiitivet_mount(root)

    root.layout(400, 40)
    assert root.needs_layout is False
    assert bound.needs_layout is False

    s.value = "Clicked: " + ("X" * 80)
    assert root.needs_layout is True
