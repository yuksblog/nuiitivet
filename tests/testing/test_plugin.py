"""Plugin behaviour tests, run through pytester sub-sessions.

The plugin is registered by the ``pytest11`` entry point, so every inner
``runpytest_inprocess`` session picks it up the same way a user's suite does.
"""

import threading

import pytest

from nuiitivet.testing.plugin import _refuse_thread_parallel


def test_harness_clock_installed_by_default(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.observable.runtime import get_clock
        from nuiitivet.testing import HarnessClock

        def test_clock():
            assert isinstance(get_clock(), HarnessClock)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1)


def test_mutable_global_leak_is_cleared_between_tests(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.theme import dependency

        def test_leaks():
            dependency._reader_stack.append(object())

        def test_next_starts_clean():
            assert dependency._reader_stack == []
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_armed_timer_is_swept_between_tests(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.observable.runtime import get_clock

        def test_arms_and_forgets():
            get_clock().schedule_once(lambda dt: None, 60.0)

        def test_next_starts_clean(nuiitivet_clock):
            assert nuiitivet_clock.pending() == []
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_harness_clock_fixture_pumps(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.observable.runtime import get_clock

        def test_pump(nuiitivet_clock):
            fired = []
            get_clock().schedule_once(fired.append, 0)
            assert nuiitivet_clock.pump_immediate() == 1
            assert fired == [0.0]
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1)


# These outer tests opt out of the harness clock: the inner session's
# clock="real" keeps whatever is installed when it runs, which would otherwise
# be the *outer* test's HarnessClock.
@pytest.mark.nuiitivet(clock="real")
def test_clock_real_opt_out(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest
        from nuiitivet.observable.runtime import get_clock
        from nuiitivet.testing import HarnessClock

        @pytest.mark.nuiitivet(clock="real")
        def test_real_clock():
            assert not isinstance(get_clock(), HarnessClock)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1)


@pytest.mark.nuiitivet(clock="real")
def test_stacked_markers_merge_kwargs(pytester: pytest.Pytester):
    # Both markers must take effect: clock="real" from one, isolate=False from
    # the other. If isolate=False were dropped, the fixture would restore
    # _LOG_ONCE_ENABLED at teardown and the second test would see True.
    pytester.makepyfile(
        """
        import pytest
        from nuiitivet.common import logging_once
        from nuiitivet.observable.runtime import get_clock
        from nuiitivet.testing import HarnessClock

        @pytest.mark.nuiitivet(isolate=False)
        @pytest.mark.nuiitivet(clock="real")
        def test_fully_opted_out():
            assert not isinstance(get_clock(), HarnessClock)
            logging_once._LOG_ONCE_ENABLED = False

        def test_sees_the_leak():
            assert logging_once._LOG_ONCE_ENABLED is False
            logging_once._LOG_ONCE_ENABLED = True
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_unknown_marker_key_errors(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.nuiitivet(bogus=True)
        def test_x():
            pass
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*unknown nuiitivet testing option*bogus*"])


def test_strict_fails_on_armed_never_fired(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest
        from nuiitivet.observable.runtime import get_clock

        @pytest.mark.nuiitivet(clock="strict")
        def test_arms_and_forgets():
            get_clock().schedule_once(lambda dt: None, 0.3)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(['*clock="strict"*armed and never fired*'])


def test_strict_exempts_explicit_unschedule(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest
        from nuiitivet.observable.runtime import get_clock

        @pytest.mark.nuiitivet(clock="strict")
        def test_debounce_style_rearm():
            def cb(dt):
                pass
            get_clock().schedule_once(cb, 0.3)
            get_clock().unschedule(cb)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1, errors=0)


def test_strict_passes_when_pumped(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import time
        import pytest

        @pytest.mark.nuiitivet(clock="strict")
        def test_fires(nuiitivet_clock):
            fired = []
            nuiitivet_clock.schedule_once(fired.append, 0.01)
            time.sleep(0.02)
            nuiitivet_clock.pump()
            assert fired
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1, errors=0)


def test_teardown_warns_about_due_unpumped_callbacks(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import time
        from nuiitivet.observable.runtime import get_clock

        def test_slow_enough_for_the_delay_to_elapse():
            get_clock().schedule_once(lambda dt: None, 0.01)
            time.sleep(0.02)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(["*NuiitivetClockWarning*"])


def test_harness_clock_fixture_refuses_real_clock(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.nuiitivet(clock="real")
        def test_x(nuiitivet_clock):
            pass
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*nuiitivet_clock requires the harness clock*"])


@pytest.mark.nuiitivet(clock="real")
def test_pyproject_defaults_apply_and_marker_overrides(pytester: pytest.Pytester):
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]

        [tool.nuiitivet.testing]
        clock = "real"
        """
    )
    pytester.makepyfile(
        """
        import pytest
        from nuiitivet.observable.runtime import get_clock
        from nuiitivet.testing import HarnessClock

        def test_suite_default_is_real():
            assert not isinstance(get_clock(), HarnessClock)

        @pytest.mark.nuiitivet(clock="harness")
        def test_marker_overrides_default():
            assert isinstance(get_clock(), HarnessClock)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_pyproject_unknown_key_is_a_usage_error(pytester: pytest.Pytester):
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]

        [tool.nuiitivet.testing]
        bogus = 1
        """
    )
    pytester.makepyfile(
        """
        def test_x():
            pass
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*unknown nuiitivet testing option*bogus*"])


# -- the async test runner -------------------------------------------------
#
# Three configurations matter: pytest-asyncio absent (the runner runs the
# test), strict mode, and auto mode (pytest-asyncio runs it). The absent
# configuration is simulated with ``-p no:asyncio`` / ``-p no:anyio``; the
# installed ones run in a subprocess so the inner pytest-asyncio session
# cannot share state with the outer one.


def test_bare_async_test_runs_without_asyncio_plugins(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import asyncio

        async def test_bare():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-p", "no:anyio")
    result.assert_outcomes(passed=1)


def test_async_failure_is_reported_not_skipped(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        async def test_fails():
            assert False
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-p", "no:anyio")
    result.assert_outcomes(failed=1)


def test_async_test_receives_fixtures(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.testing import HarnessClock

        async def test_with_fixture(nuiitivet_clock):
            assert isinstance(nuiitivet_clock, HarnessClock)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-p", "no:anyio")
    result.assert_outcomes(passed=1)


def test_orphaned_asyncio_marker_still_runs(pytester: pytest.Pytester):
    # --strict-markers also proves the plugin registers the orphaned marker.
    pytester.makepyfile(
        """
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_orphaned():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-p", "no:anyio", "--strict-markers")
    result.assert_outcomes(passed=1)


def test_orphaned_anyio_marker_still_runs(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import asyncio
        import pytest

        @pytest.mark.anyio
        async def test_orphaned():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-p", "no:anyio", "--strict-markers")
    result.assert_outcomes(passed=1)


def test_leftover_tasks_are_cancelled_before_loop_close(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import asyncio

        async def test_leaves_a_task_behind():
            async def linger():
                await asyncio.sleep(60)
            asyncio.get_running_loop().create_task(linger())
        """
    )
    result = pytester.runpytest_subprocess("-p", "no:asyncio", "-p", "no:anyio")
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*Task was destroyed but it is pending*")
    result.stderr.no_fnmatch_line("*Task was destroyed but it is pending*")


def test_defers_to_pytest_asyncio_strict_mode(pytester: pytest.Pytester):
    pytest.importorskip("pytest_asyncio")
    pytester.makepyfile(
        """
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_marked():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_subprocess("-o", "asyncio_mode=strict")
    result.assert_outcomes(passed=1)


def test_defers_to_pytest_asyncio_auto_mode(pytester: pytest.Pytester):
    pytest.importorskip("pytest_asyncio")
    pytester.makepyfile(
        """
        import asyncio

        async def test_unmarked():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_subprocess("-o", "asyncio_mode=auto")
    result.assert_outcomes(passed=1)


def test_runner_takes_unmarked_async_in_strict_mode(pytester: pytest.Pytester):
    # In strict mode pytest-asyncio only runs *marked* tests; before this
    # runner an unmarked async test was collected and silently skipped.
    pytest.importorskip("pytest_asyncio")
    pytester.makepyfile(
        """
        import asyncio

        async def test_unmarked():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_subprocess("-o", "asyncio_mode=strict")
    result.assert_outcomes(passed=1)


def test_defers_to_anyio(pytester: pytest.Pytester):
    pytest.importorskip("anyio")
    pytester.makepyfile(
        """
        import asyncio
        import pytest

        @pytest.mark.anyio
        async def test_marked():
            await asyncio.sleep(0)
        """
    )
    result = pytester.runpytest_subprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=1)


def test_refuses_non_main_thread():
    outcome = {}

    def run():
        try:
            _refuse_thread_parallel()
            outcome["raised"] = False
        except BaseException as exc:  # pytest.fail raises a BaseException subclass
            outcome["raised"] = True
            outcome["message"] = str(exc)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()

    assert outcome["raised"] is True
    assert "thread-parallel" in outcome["message"]


def test_accepts_the_main_thread():
    _refuse_thread_parallel()  # must not raise


# -- the harness fixtures --------------------------------------------------


def test_nuiitivet_app_fixture_closes_what_it_handed_out(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import nuiitivet.material as nv

        held = {}

        def test_builds(nuiitivet_app):
            screen = nv.Text("hello").modifier(nv.keyed("greeting"))
            app = nuiitivet_app(screen, size=(200, 100))
            assert app.get(key="greeting").text == "hello"
            held["screen"] = screen

        def test_the_previous_screen_was_unmounted():
            assert held["screen"]._unmounted is True
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_nuiitivet_mount_fixture_closes_what_it_handed_out(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import nuiitivet.material as nv

        held = {}

        def test_builds(nuiitivet_mount):
            widget = nv.Text("hello").modifier(nv.keyed("greeting"))
            host = nuiitivet_mount(widget)
            host.layout(200, 100)
            assert host.get(key="greeting").text == "hello"
            held["widget"] = widget

        def test_the_previous_widget_was_unmounted():
            assert held["widget"]._unmounted is True
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_a_harness_left_open_is_closed_and_reported(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import nuiitivet.material as nv
        from nuiitivet.testing import AppHarness

        held = {}

        def test_forgets_to_close():
            screen = nv.Text("hello").modifier(nv.keyed("greeting"))
            held["screen"] = screen
            AppHarness(screen, size=(200, 100))   # never closed

        def test_it_was_closed_anyway():
            assert held["screen"]._unmounted is True
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-W", "default")
    result.assert_outcomes(passed=2, warnings=1)
    result.stdout.fnmatch_lines(["*ended with 1 harness(es) still open*"])


def test_a_harness_the_test_closed_itself_is_not_reported(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        import nuiitivet.material as nv
        from nuiitivet.testing import AppHarness

        def test_closes_properly():
            screen = nv.Text("hello").modifier(nv.keyed("greeting"))
            with AppHarness(screen, size=(200, 100)) as app:
                assert app.get(key="greeting").text == "hello"
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio", "-W", "default")
    result.assert_outcomes(passed=1, warnings=0)
