"""The nuiitivet pytest plugin: per-test isolation and deterministic timers.

Registered via the ``pytest11`` entry point, so it is active on install with
no ``conftest.py`` boilerplate. Around every test it installs a
:class:`~nuiitivet.testing.clock.HarnessClock` and resets the framework's
process-global state, so a test is not affected by — and does not affect —
anything outside itself.

Per-test configuration goes through one marker::

    @pytest.mark.nuiitivet(clock="real")    # keep the real clock
    @pytest.mark.nuiitivet(clock="strict")  # fail on armed-but-never-fired
    @pytest.mark.nuiitivet(isolate=False)   # skip the process-global resets

Stacked ``nuiitivet`` markers merge their keyword arguments, nearest wins per
key. Suite-wide defaults live in ``[tool.nuiitivet.testing]`` in
``pyproject.toml``; the marker overrides them per test.

Bare ``async def`` tests run on an event loop the plugin creates, so neither
``pytest-asyncio`` nor ``anyio`` is required. When one of those plugins is
installed *and* the test carries its marker, the plugin stands aside.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import threading
import warnings
from typing import Any, Coroutine, Dict, Iterator, List, Optional, Tuple

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # ships with pytest on Python 3.10

from nuiitivet.testing import _support
from nuiitivet.testing.clock import HarnessClock, NuiitivetClockWarning, PendingCallback


_CONFIG_KEYS = ("clock", "isolate")
_CLOCK_MODES = ("harness", "strict", "real")
_ASYNC_PLUGINS = ("asyncio", "anyio")
_DEFAULTS_KEY: pytest.StashKey[Dict[str, Any]] = pytest.StashKey()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "nuiitivet(clock=..., isolate=...): configure the nuiitivet test harness. "
        'clock is "harness" (default), "strict" (fail on callbacks armed and '
        'never fired), or "real" (keep the installed clock); isolate=False '
        "skips the process-global resets.",
    )
    config.stash[_DEFAULTS_KEY] = _load_defaults(config)
    # The async runner below executes tests whose asyncio/anyio marker is
    # orphaned (plugin not installed), so it owns those markers too — without
    # this an orphaned marker trips --strict-markers.
    for plugin_name in _ASYNC_PLUGINS:
        if not config.pluginmanager.hasplugin(plugin_name):
            config.addinivalue_line(
                "markers",
                f"{plugin_name}: run by the nuiitivet async runner "
                f"({plugin_name} plugin not installed)",
            )


def _load_defaults(config: pytest.Config) -> Dict[str, Any]:
    """Read ``[tool.nuiitivet.testing]`` from the rootdir's pyproject.toml."""
    path = config.rootpath / "pyproject.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    section = data.get("tool", {}).get("nuiitivet", {}).get("testing", {})
    if not isinstance(section, dict):
        raise pytest.UsageError("[tool.nuiitivet.testing] must be a table")
    _validate_config(section, source=f"[tool.nuiitivet.testing] in {path}")
    return section


def _validate_config(cfg: Dict[str, Any], *, source: str) -> None:
    for key in cfg:
        if key not in _CONFIG_KEYS:
            raise pytest.UsageError(
                f"unknown nuiitivet testing option {key!r} in {source}; "
                f"known options: {', '.join(_CONFIG_KEYS)}"
            )
    clock = cfg.get("clock")
    if clock is not None and clock not in _CLOCK_MODES:
        raise pytest.UsageError(
            f"invalid clock={clock!r} in {source}; "
            f"expected one of: {', '.join(_CLOCK_MODES)}"
        )
    isolate = cfg.get("isolate")
    if isolate is not None and not isinstance(isolate, bool):
        raise pytest.UsageError(f"isolate must be a bool in {source}, got {isolate!r}")


def _item_config(item: pytest.Item) -> Dict[str, Any]:
    """Merge suite defaults and every ``nuiitivet`` marker, nearest wins.

    ``get_closest_marker`` would silently drop all but the nearest of stacked
    markers — an ignored opt-out — so kwargs merge across the whole stack.
    """
    stored = item.config.stash.get(_DEFAULTS_KEY, None)
    cfg: Dict[str, Any] = dict(stored) if stored else {}
    for marker in reversed(list(item.iter_markers("nuiitivet"))):
        if marker.args:
            raise pytest.UsageError(
                f"@pytest.mark.nuiitivet takes keyword arguments only ({item.nodeid})"
            )
        _validate_config(dict(marker.kwargs), source=f"@pytest.mark.nuiitivet on {item.nodeid}")
        cfg.update(marker.kwargs)
    return cfg


def _refuse_thread_parallel() -> None:
    if threading.current_thread() is not threading.main_thread():
        pytest.fail(
            "nuiitivet tests cannot run thread-parallel: the framework keeps "
            "process-global state (runtime.clock, pending invalidations, the "
            "theme reader stack), so concurrent tests in one process would "
            "race and corrupt each other. Use pytest-xdist, which parallelises "
            "across worker processes, instead of a thread-based plugin.",
            pytrace=False,
        )


# -- process-global resets -------------------------------------------------
#
# Most inventory entries are mutable containers a test mutates *in place*, so
# saving and restoring the reference isolates nothing — they are cleared at
# both test boundaries. Only the entries a test *rebinds* are saved/restored.


def _clear_mutable_globals() -> None:
    from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests
    from nuiitivet.observable.contexts import _batch_context
    from nuiitivet.theme import dependency
    from nuiitivet.widgeting import widget_binding, widget_builder, widget_size_change

    widget_binding._pending_invalidation.clear()
    widget_builder._pending_scope_recompositions.clear()
    widget_size_change._pending_size_changes.clear()
    dependency._reader_stack.clear()
    _batch_context.set(None)
    _clear_log_once_keys_for_tests()


def _save_rebindable_globals() -> Tuple[Any, ...]:
    from nuiitivet.common import logging_once
    from nuiitivet.dev import session

    # widgeting/callbacks._task_observer joins this list when the async
    # integration work adds it (#527's successor).
    return (logging_once._LOG_ONCE_ENABLED, session._current_session)


def _restore_rebindable_globals(saved: Tuple[Any, ...]) -> None:
    from nuiitivet.common import logging_once
    from nuiitivet.dev import session

    logging_once._LOG_ONCE_ENABLED = saved[0]
    session._current_session = saved[1]


# -- the per-test fixture --------------------------------------------------


def _cancel_all_on(clock: Any) -> None:
    """Best-effort sweep of a clock we did not install (e.g. _ThreadClock)."""
    cancel_all = getattr(clock, "cancel_all", None)
    if cancel_all is not None:
        cancel_all()


def _format_leftover(leftover: List[PendingCallback]) -> str:
    lines = []
    for cb in leftover:
        kind = "interval" if cb.is_interval else "one-shot"
        state = "due, never fired" if cb.due else "armed, not yet due"
        lines.append(f"  {cb.fn!r} ({kind}, delay={cb.delay}, {state}) scheduled at {cb.site}")
    return "\n".join(lines)


class NuiitivetHarnessWarning(Warning):
    """A test ended with a harness it constructed still open."""


def _close_leaked_harnesses(item: pytest.Item) -> None:
    """Close any harness the test constructed bare and never closed.

    Defensive rather than disciplinary: an unclosed harness leaves its tree
    mounted and subscribed into the next test, and the teardown hooks that later
    checks hang off never run. Closing it silently would hide the omission, so
    it is closed *and* reported -- the same policy an overlay left open gets.
    """
    leaked = _support.open_harnesses()
    if not leaked:
        return
    names = ", ".join(sorted(type(h).__name__ for h in leaked))
    for harness in reversed(leaked):
        try:
            harness.close()
        except Exception:  # pragma: no cover - teardown must not mask the test
            pass
    _support.forget_open_harnesses()
    warnings.warn(
        f"{item.nodeid} ended with {len(leaked)} harness(es) still open ({names}); "
        "closed for you. Use the nuiitivet_app / nuiitivet_mount fixtures, or a "
        "'with' block, so teardown runs even when the test fails.",
        NuiitivetHarnessWarning,
        stacklevel=2,
    )


@pytest.fixture(autouse=True)
def _nuiitivet_test_env(request: pytest.FixtureRequest) -> Iterator[Optional[HarnessClock]]:
    """Install the harness clock and reset process-global state per test."""
    cfg = _item_config(request.node)
    clock_mode = cfg.get("clock", "harness")
    isolate = cfg.get("isolate", True)

    _support._set_clock_opted_out(clock_mode == "real")

    if not isolate and clock_mode == "real":
        try:
            yield None  # fully opted out
        finally:
            _support._set_clock_opted_out(False)
            _support.forget_open_harnesses()
        return

    _refuse_thread_parallel()

    from nuiitivet.observable.runtime import get_clock, set_clock

    previous = get_clock()
    # Timers armed before the test (import time, an earlier opted-out test)
    # must not fire into this one.
    _cancel_all_on(previous)

    harness: Optional[HarnessClock] = None
    if clock_mode != "real":
        harness = HarnessClock()
        set_clock(harness)

    saved = _save_rebindable_globals() if isolate else None
    if isolate:
        _clear_mutable_globals()

    try:
        yield harness
    finally:
        _support._set_clock_opted_out(False)
        _close_leaked_harnesses(request.node)
        if isolate and saved is not None:
            _clear_mutable_globals()
            _restore_rebindable_globals(saved)
        if harness is not None:
            set_clock(previous)
            leftover = harness.cancel_all()
            if clock_mode == "strict" and leftover:
                pytest.fail(
                    "clock=\"strict\": callbacks were armed and never fired "
                    "(explicit unschedule exempts them):\n" + _format_leftover(leftover),
                    pytrace=False,
                )
            else:
                due = [cb for cb in leftover if cb.due]
                if due:
                    warnings.warn(
                        "test ended with clock callbacks due and unpumped — a "
                        "timed effect may have been asserted absent without "
                        "elapsing:\n" + _format_leftover(due),
                        NuiitivetClockWarning,
                        stacklevel=2,
                    )
        else:
            _cancel_all_on(get_clock())


# -- the async test runner -------------------------------------------------
#
# The harness owns the event loop, so pytest-asyncio is not a dependency.
# Deferring must be conditional on the plugin actually being present: standing
# aside for a marker whose plugin is absent defers to nobody, and the test is
# then silently skipped — the failure class this hook exists to remove.


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> Optional[bool]:
    """Run coroutine test functions on a fresh event loop."""
    testfunction = pyfuncitem.obj
    if not inspect.iscoroutinefunction(testfunction):
        return None
    pluginmanager = pyfuncitem.config.pluginmanager
    for plugin_name in _ASYNC_PLUGINS:
        if pyfuncitem.get_closest_marker(plugin_name) and pluginmanager.hasplugin(plugin_name):
            return None  # the marked-for plugin is installed; its test, its loop
    testargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    _run_on_fresh_loop(testfunction(**testargs))
    return True


def _run_on_fresh_loop(coro: Coroutine[Any, Any, object]) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        try:
            loop.run_until_complete(coro)
        finally:
            _cancel_leftover_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def _cancel_leftover_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """A task still pending when the loop closes warns outside any test."""
    leftover = asyncio.all_tasks(loop)
    for task in leftover:
        task.cancel()
    if leftover:
        loop.run_until_complete(asyncio.gather(*leftover, return_exceptions=True))


@pytest.fixture
def nuiitivet_clock(_nuiitivet_test_env: Optional[HarnessClock]) -> HarnessClock:
    """The :class:`HarnessClock` installed for this test, typed — no cast."""
    if _nuiitivet_test_env is None:
        pytest.fail(
            'nuiitivet_clock requires the harness clock, but this test opted '
            'out with @pytest.mark.nuiitivet(clock="real")',
            pytrace=False,
        )
    return _nuiitivet_test_env


# -- the harness fixtures --------------------------------------------------
#
# Factories, not plain fixtures: a harness needs the widget under test, and a
# fixture cannot know it. What they buy over a bare `with` block is that the
# close happens on the failure path too, and at a point the test cannot skip --
# which is what every later check hanging off teardown depends on.


@pytest.fixture
def nuiitivet_app() -> Iterator[Any]:
    """Construct :class:`~nuiitivet.testing.AppHarness` instances for this test.

    ``size`` is required; there is no default::

        def test_counter(nuiitivet_app):
            screen = CounterScreen()
            app = nuiitivet_app(screen, size=(800, 600))
            app.click(key="increment")
            assert screen.count.value == 1
    """
    from nuiitivet.testing.harness import AppHarness

    built: List[Any] = []

    def factory(content: Any, **kwargs: Any) -> Any:
        harness = AppHarness(content, **kwargs)
        built.append(harness)
        return harness

    try:
        yield factory
    finally:
        for harness in reversed(built):
            harness.close()


@pytest.fixture
def nuiitivet_mount() -> Iterator[Any]:
    """Construct :func:`~nuiitivet.testing.mount` hosts for this test.

    The same shape as ``nuiitivet_app``, one level down::

        def test_card(nuiitivet_mount):
            card = Card(title="hello")
            host = nuiitivet_mount(card)
            host.layout(400, 200)
    """
    from nuiitivet.testing.mount import mount as _mount

    built: List[Any] = []

    def factory(widget: Any, **kwargs: Any) -> Any:
        host = _mount(widget, **kwargs)
        built.append(host)
        return host

    try:
        yield factory
    finally:
        for host in reversed(built):
            host.close()
