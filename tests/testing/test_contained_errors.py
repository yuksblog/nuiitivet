"""A callback that raised and was contained must not read as one that worked.

The framework catches exceptions out of user callbacks and carries on, which is
correct in production and is the failure this package exists to remove in a test.
The async half of that already surfaces (``idle()`` re-raises what the handler
raised); these cover the synchronous half, the seven containment sites it reaches
through, and the guarantee that production behaviour is unchanged.
"""

from __future__ import annotations

import warnings

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
from nuiitivet.testing import AppHarness, ContainedCallbackWarning, mount
from nuiitivet.widgeting import callbacks as _callbacks
from nuiitivet.widgeting.widget import ComposableWidget, Widget


SIZE = (400, 300)


def _text(value: object, key: str) -> Widget:
    return Text(value, key=key)  # type: ignore[arg-type]


class _Screen(ComposableWidget):
    """A screen whose button runs a synchronous handler."""

    def __init__(self, work) -> None:
        super().__init__()
        self.status = Observable("idle")
        self._work = work

    def build(self) -> Widget:
        return Column(
            children=[
                _text(self.status, "status"),
                Button("go", on_click=self._go, key="go"),
            ]
        )

    def _go(self) -> None:
        self.status.value = "working"
        self._work()
        self.status.value = "done"


def _boom() -> None:
    raise ValueError("handler blew up")


# -- the failure this issue exists for -------------------------------------


def test_a_sync_handler_that_raises_fails_at_the_click(nuiitivet_app) -> None:
    """The whole point: the click raises, rather than the assert after it."""
    screen = _Screen(_boom)
    app = nuiitivet_app(screen, size=SIZE)

    with pytest.raises(ValueError, match="handler blew up"):
        app.click(key="go")


def test_without_the_check_the_test_would_have_gone_green(nuiitivet_app) -> None:
    """What ``callback_errors="off"`` restores -- and why it is not the default.

    The handler stops on its first line, ``status`` never reaches ``"done"``,
    and nothing anywhere says so. This is the production behaviour, pinned.
    """
    screen = _Screen(_boom)
    app = nuiitivet_app(screen, size=SIZE, callback_errors="off")

    app.click(key="go")

    assert screen.status.value == "working"  # never reached "done"


def test_the_exception_keeps_its_own_type_and_traceback(nuiitivet_app) -> None:
    """A ``ValueError`` arrives as a ``ValueError``, from the handler's own line."""
    app = nuiitivet_app(_Screen(_boom), size=SIZE)

    with pytest.raises(ValueError) as excinfo:
        app.click(key="go")

    assert excinfo.traceback[-1].name == "_boom"


@pytest.mark.skipif(
    not hasattr(BaseException, "add_note"), reason="notes need Python 3.11"
)
def test_the_owner_and_the_site_ride_along_as_a_note(nuiitivet_app) -> None:
    app = nuiitivet_app(_Screen(_boom), size=SIZE)

    with pytest.raises(ValueError) as excinfo:
        app.click(key="go")

    note = "\n".join(getattr(excinfo.value, "__notes__", []))
    assert "contained by the framework" in note
    assert 'callback_errors="off"' in note


# -- the containment sites -------------------------------------------------


class _RaisingOnMount(Widget):
    def on_mount(self) -> None:
        super().on_mount()
        raise ValueError("on_mount blew up")


def test_a_raising_on_mount_reaches_the_test() -> None:
    """``mount()`` runs it, so the failure surfaces at the first settle."""
    with pytest.raises(ValueError, match="on_mount blew up"):
        with mount(_RaisingOnMount()) as host:
            host.layout(100, 100)


class _RaisingInvalidate(Widget):
    """A widget whose rebuild raises when its binding source changes."""

    def __init__(self, source) -> None:
        super().__init__()
        self._source = source

    def on_mount(self) -> None:
        super().on_mount()
        self.bind_to(self._source, lambda _value: None)

    def invalidate(self, immediate: bool = False) -> None:
        raise ValueError("invalidate blew up")


def test_a_raising_invalidate_during_a_binding_flush_reaches_the_test() -> None:
    source = Observable("a")
    with pytest.raises(ValueError, match="invalidate blew up"):
        with mount(_RaisingInvalidate(source)) as host:
            host.layout(100, 100)
            source.value = "b"
            host.settle()


def test_a_raising_dispose_callback_reaches_the_test() -> None:
    """Contained at unmount, so the only boundary left is the teardown report."""

    class _RaisingDispose(Widget):
        def on_mount(self) -> None:
            super().on_mount()
            self.on_dispose(_boom)

    with pytest.raises(ValueError, match="handler blew up"):
        with mount(_RaisingDispose()) as host:
            host.layout(100, 100)


# -- levels -----------------------------------------------------------------


def test_warn_reports_everything_once_at_teardown(nuiitivet_app) -> None:
    screen = _Screen(_boom)
    app = nuiitivet_app(screen, size=SIZE, callback_errors="warn")

    app.click(key="go")  # does not raise
    app.click(key="go")

    with pytest.warns(ContainedCallbackWarning, match="2 callback error"):
        app.close()


def test_off_installs_no_sink_at_all(nuiitivet_app) -> None:
    """Not merely quiet: the framework must see production's empty set."""
    before = set(_callbacks._error_sinks)
    app = nuiitivet_app(_Screen(_boom), size=SIZE, callback_errors="off")

    assert set(_callbacks._error_sinks) == before

    app.click(key="go")
    app.close()


def test_an_invalid_level_is_refused() -> None:
    with pytest.raises(ValueError, match="invalid callback_errors"):
        AppHarness(_Screen(_boom), size=SIZE, callback_errors="loud")


# -- teardown, and a test that already failed -------------------------------


def test_an_error_after_the_last_action_still_surfaces_at_close() -> None:
    """The last chance to notice: nothing settles after the failure."""
    app = AppHarness(_Screen(_boom), size=SIZE)
    _callbacks.report_contained(ValueError("late failure"), owner="X", site="late")

    with pytest.raises(ValueError, match="late failure"):
        app.close()


def test_a_second_queued_error_is_warned_rather_than_dropped() -> None:
    """Only one exception can be raised; the rest must not vanish."""
    app = AppHarness(_Screen(_boom), size=SIZE)
    _callbacks.report_contained(ValueError("first"), owner="X", site="a")
    _callbacks.report_contained(ValueError("second"), owner="Y", site="b")

    with pytest.warns(ContainedCallbackWarning, match="second"):
        with pytest.raises(ValueError, match="first"):
            app.close()


def test_a_failing_test_gets_a_warning_rather_than_a_second_failure() -> None:
    """Inverse of the leak check: this is usually *why* the test failed.

    Suppressing it hides the answer, and raising it would replace the failure
    the author is already reading. So it is reported, as a warning.
    """
    from nuiitivet.testing import _support

    app = AppHarness(_Screen(_boom), size=SIZE)
    _callbacks.report_contained(ValueError("the cause"), owner="X", site="a")
    _support._set_test_failed(True)
    try:
        with pytest.warns(ContainedCallbackWarning, match="the cause"):
            app.close()
    finally:
        _support._set_test_failed(False)


def test_two_harnesses_do_not_both_claim_one_failure() -> None:
    """One containment, one report, even though both sinks receive it.

    Which of the two claims it is set iteration order and deliberately not
    specified; that exactly one does is the guarantee.
    """
    harnesses = [AppHarness(_Screen(_boom), size=SIZE) for _ in range(2)]
    _callbacks.report_contained(ValueError("once"), owner="X", site="a")

    raised = 0
    with warnings.catch_warnings():
        warnings.simplefilter("error", ContainedCallbackWarning)
        for harness in harnesses:
            try:
                harness.close()
            except ValueError:
                raised += 1

    assert raised == 1


# -- production behaviour is unchanged --------------------------------------


def test_the_framework_still_contains_when_nothing_is_listening() -> None:
    """No harness, no sink: a raising handler must not kill the frame.

    The regression that matters most here. If this ever fails, the containment
    the framework relies on in production has been turned into a crash by a
    test-only feature.
    """
    assert not _callbacks._error_sinks

    calls: list = []
    _callbacks.invoke_event_handler(
        _boom,
        error_key="test_click",
        error_msg="Exception in click handler",
        owner_name="Button",
    )
    calls.append("survived")

    assert calls == ["survived"]


def test_a_sink_that_raises_cannot_break_the_containment() -> None:
    """A sink runs mid-containment; an exception there defeats the whole point."""

    def _bad_sink(_error) -> None:
        raise RuntimeError("sink blew up")

    _callbacks._error_sinks.add(_bad_sink)
    try:
        _callbacks.invoke_event_handler(
            _boom,
            error_key="test_click",
            error_msg="Exception in click handler",
            owner_name="Button",
        )
    finally:
        _callbacks._error_sinks.discard(_bad_sink)
