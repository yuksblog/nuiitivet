"""A lifecycle override that never chains to its base must be reported.

Both losses are silent without the check: ``on_mount`` without ``super()`` never
reaches ``evaluate_build()``, so the composition mounts empty, and ``on_unmount``
without it never reaches ``BindingHostMixin._dispose_bindings``, so subscriptions
accumulate on every re-mount.

The scopes differ: the ``on_mount`` loss belongs to build hosts, the
``on_unmount`` loss to every widget.
"""

from __future__ import annotations

import pytest

from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class _DummyApp:
    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _leaf() -> Box:
    return Box(width=Sizing.fixed(10), height=Sizing.fixed(10))


# --- on_mount: build hosts --------------------------------------------------


def test_on_mount_without_super_is_reported() -> None:
    class _Unchained(ComposableWidget):
        def on_mount(self) -> None:
            pass

        def build(self) -> Widget:
            return _leaf()

    with pytest.raises(RuntimeError, match=r"_Unchained\.on_mount\(\) did not call super\(\)\.on_mount\(\)"):
        _Unchained().mount(_DummyApp())


def test_on_mount_with_super_first_is_accepted() -> None:
    class _SuperFirst(ComposableWidget):
        def on_mount(self) -> None:
            super().on_mount()
            self.marked = True

        def build(self) -> Widget:
            return _leaf()

    widget = _SuperFirst()
    widget.mount(_DummyApp())

    assert widget.marked is True
    assert widget.built_child is not None


def test_on_mount_with_super_last_is_accepted() -> None:
    """Super-last is legitimate: build() may read what the override computes."""

    class _SuperLast(ComposableWidget):
        def on_mount(self) -> None:
            self.label = "computed before build"
            super().on_mount()

        def build(self) -> Widget:
            assert self.label == "computed before build"
            return _leaf()

    widget = _SuperLast()
    widget.mount(_DummyApp())

    assert widget.built_child is not None


def test_plain_widget_on_mount_without_super_is_not_reported() -> None:
    """A widget with no build step loses nothing by skipping a no-op base."""

    class _PlainLeaf(Box):
        def on_mount(self) -> None:
            self.marked = True

    widget = _PlainLeaf()
    widget.mount(_DummyApp())

    assert widget.marked is True


def test_remount_is_checked_again() -> None:
    """The flag is per mount, not per instance."""

    class _ChainsOnce(ComposableWidget):
        def __init__(self) -> None:
            super().__init__()
            self.mounts = 0

        def on_mount(self) -> None:
            self.mounts += 1
            if self.mounts == 1:
                super().on_mount()

        def build(self) -> Widget:
            return _leaf()

    widget = _ChainsOnce()
    app = _DummyApp()
    widget.mount(app)
    widget.unmount()

    with pytest.raises(RuntimeError, match=r"did not call super\(\)\.on_mount\(\)"):
        widget.mount(app)


def test_override_that_raised_before_super_is_not_blamed_on_super() -> None:
    """The real failure is already reported; a second, wrong one would mislead."""

    class _Raises(ComposableWidget):
        def on_mount(self) -> None:
            raise ValueError("boom")

        def build(self) -> Widget:
            return _leaf()

    # Contained by ``_call_contained``, so mount() returns -- and says nothing
    # about super(), which the override never got the chance to call.
    _Raises().mount(_DummyApp())


def test_message_points_at_the_blank_screen() -> None:
    class _Unchained(ComposableWidget):
        def on_mount(self) -> None:
            pass

        def build(self) -> Widget:
            return _leaf()

    with pytest.raises(RuntimeError) as excinfo:
        _Unchained().mount(_DummyApp())

    message = str(excinfo.value)
    assert "build()" in message
    assert "blank screen" in message
    assert "first or last" in message


# --- on_unmount: every widget -----------------------------------------------


def test_on_unmount_without_super_is_reported_on_a_plain_widget() -> None:
    """Binding disposal is universal, so this check is not scoped to hosts."""

    class _Unchained(Box):
        def on_unmount(self) -> None:
            pass

    widget = _Unchained()
    widget.mount(_DummyApp())

    with pytest.raises(RuntimeError, match=r"_Unchained\.on_unmount\(\) did not call super\(\)\.on_unmount\(\)"):
        widget.unmount()


def test_on_unmount_without_super_is_reported_on_a_build_host() -> None:
    class _Unchained(ComposableWidget):
        def on_unmount(self) -> None:
            pass

        def build(self) -> Widget:
            return _leaf()

    widget = _Unchained()
    widget.mount(_DummyApp())

    with pytest.raises(RuntimeError, match=r"did not call super\(\)\.on_unmount\(\)"):
        widget.unmount()


@pytest.mark.parametrize("super_first", [True, False], ids=["super-first", "super-last"])
def test_on_unmount_accepts_super_at_either_end(super_first: bool) -> None:
    calls: list[str] = []

    class _Chained(Box):
        def on_unmount(self) -> None:
            if super_first:
                super().on_unmount()
            calls.append("override")
            if not super_first:
                super().on_unmount()

    widget = _Chained()
    widget.mount(_DummyApp())
    widget.unmount()

    assert calls == ["override"]


def test_unmount_override_that_raised_before_super_is_not_blamed_on_super() -> None:
    class _Raises(Box):
        def on_unmount(self) -> None:
            raise ValueError("boom")

    widget = _Raises()
    widget.mount(_DummyApp())

    widget.unmount()


def test_unmount_completes_before_the_report() -> None:
    """Reported at the end, so the widget is left torn down, not half-unmounted."""

    class _Unchained(Box):
        def on_unmount(self) -> None:
            pass

    widget = _Unchained()
    widget.mount(_DummyApp())

    with pytest.raises(RuntimeError):
        widget.unmount()

    assert widget._app is None
    assert widget._unmounted is True


def test_bindings_registered_in_on_mount_are_disposed_on_unmount() -> None:
    """What the on_unmount check exists to protect: no accumulation on re-mount."""
    source: Observable[int] = Observable(0)
    seen: list[int] = []

    class _Observer(Box):
        def on_mount(self) -> None:
            super().on_mount()
            self.observe(source, seen.append)

    widget = _Observer()
    app = _DummyApp()
    for _ in range(3):
        widget.mount(app)
        widget.unmount()

    seen.clear()
    source.value = 1

    assert seen == []
