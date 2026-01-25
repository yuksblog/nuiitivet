from nuiitivet.widgeting.widget import Widget


class Dummy(Widget):
    def build(self) -> "Widget":  # pragma: no cover - not used in tests
        return self


def test_add_and_snapshot_and_mount():
    owner = Dummy()
    # owner not mounted yet; adding child should set parent but not mount
    a = Dummy()
    owner.add_child(a)
    assert a._parent is owner
    assert a._app is None
    assert owner.children_snapshot() == [a]

    # mount owner; new children get mounted on add
    owner.mount("app")
    b = Dummy()
    owner.add_child(b)
    assert b._parent is owner
    assert b._app == "app"


def test_eviction_evict_oldest_policy():
    owner = Dummy(max_children=2, overflow_policy="evict_oldest")
    owner.mount("app")
    a = Dummy()
    b = Dummy()
    c = Dummy()
    owner.add_child(a)
    owner.add_child(b)
    # at capacity now
    owner.add_child(c)
    snaps = owner.children_snapshot()
    assert len(snaps) == 2
    # oldest (a) should be evicted
    assert snaps[0] is b and snaps[1] is c
    assert getattr(a, "_parent", None) is None


def test_remove_and_unmount():
    owner = Dummy()
    owner.mount("app")
    a = Dummy()
    owner.add_child(a)
    assert a._app == "app"
    owner.remove_child(a)
    assert a._parent is None
    assert a._app is None
