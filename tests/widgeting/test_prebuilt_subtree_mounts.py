"""A subtree built before its host mounts is the subtree that mounts.

``rebuild()`` on an unmounted host stores the build result, and a scoped
fragment is built the moment its scope is rendered, before the fragment is
placed in the tree. The mount used to run ``build()`` again regardless and
discard that first subtree unseen: every item of a ``ForEach`` list, and every
``render_scope`` child, cost two builds and one wasted widget subtree.
"""

from __future__ import annotations

from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _Leaf(Widget):
    def build(self) -> Widget:  # pragma: no cover - never composed
        return self


class _Counting(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.builds = 0

    def build(self) -> Widget:
        self.builds += 1
        return _Leaf()


class _ScopeHost(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.factory_calls = 0

    def build(self) -> Widget:
        return self.render_scope("body", self._make_body)

    def _make_body(self) -> Widget:
        self.factory_calls += 1
        return _Leaf()


def test_a_host_rebuilt_before_mount_keeps_its_subtree_through_the_mount() -> None:
    host = _Counting()
    host.rebuild()
    prebuilt = host.built_child

    host.mount(None)

    assert host.builds == 1
    assert host.built_child is prebuilt
    assert prebuilt is not None and prebuilt._mounted


def test_a_host_never_built_builds_once_at_mount() -> None:
    host = _Counting()

    host.mount(None)

    assert host.builds == 1
    assert host.built_child is not None and host.built_child._mounted


def test_a_remount_builds_afresh() -> None:
    host = _Counting()
    host.mount(None)
    host.unmount()

    host.mount(None)

    assert host.builds == 2


def test_a_scoped_fragment_runs_its_factory_once_per_mount() -> None:
    host = _ScopeHost()

    host.mount(None)

    assert host.factory_calls == 1
    fragment = host.built_child
    assert isinstance(fragment, ComposableWidget) and fragment._mounted
    assert fragment.built_child is not None and fragment.built_child._mounted
