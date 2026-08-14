import pytest


@pytest.fixture
def collectable():
    """Disarm the leak tracker so a test can observe garbage collection.

    The pytest plugin arms ``track_subscriptions`` around every test and holds
    each ``Disposable`` **strongly**, deliberately — under a weak reference the
    leak it exists to catch would be collected before it could be reported. That
    is exactly the reference a collection test must not have, so these tests run
    outside it. Nothing they subscribe is leak-checked, which is fine: they
    assert on the same lifetime by hand.
    """
    from nuiitivet.observable.protocols import _set_subscription_tracker
    from nuiitivet.testing import _leaks

    registry = _leaks.active_registry()
    _set_subscription_tracker(None)
    try:
        yield
    finally:
        if registry is not None:
            _set_subscription_tracker(registry.record)
