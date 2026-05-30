from nuiitivet.observable import Observable


def _make_obs(initial):
    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_subscribe_and_unsubscribe():
    s = _make_obs(0)
    seen = []

    # subscribe returns a Disposable
    disp = s.subscribe(lambda v: seen.append(v))

    s.value = 1
    s.value = 2
    assert seen == [1, 2]

    # disposing the returned Disposable should stop further notifications
    disp.dispose()
    s.value = 3
    assert seen == [1, 2]

    # disposing again should be safe
    disp.dispose()


def test_unsubscribe_by_callback():
    s = _make_obs("x")
    seen = []

    def cb(v):
        seen.append(v)

    disp = s.subscribe(cb)
    s.value = "y"
    assert seen == ["y"]

    # remove by disposing the returned subscription
    disp.dispose()
    s.value = "z"
    assert seen == ["y"]
