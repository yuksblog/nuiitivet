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

        def test_next_starts_clean(harness_clock):
            assert harness_clock.pending() == []
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(passed=2)


def test_harness_clock_fixture_pumps(pytester: pytest.Pytester):
    pytester.makepyfile(
        """
        from nuiitivet.observable.runtime import get_clock

        def test_pump(harness_clock):
            fired = []
            get_clock().schedule_once(fired.append, 0)
            assert harness_clock.pump_immediate() == 1
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
        def test_fires(harness_clock):
            fired = []
            harness_clock.schedule_once(fired.append, 0.01)
            time.sleep(0.02)
            harness_clock.pump()
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
        def test_x(harness_clock):
            pass
        """
    )
    result = pytester.runpytest_inprocess("-p", "no:asyncio")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*harness_clock requires the harness clock*"])


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
