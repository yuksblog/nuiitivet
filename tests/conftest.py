import pathlib
import sys
import warnings

import pyglet
import pytest

# Importing pyglet.window creates a shadow window, which needs a display
# connection and raises NoSuchDisplayException under headless CI. Tests never
# open a real window, so disable it before any test module imports pyglet.window.
pyglet.options["shadow_window"] = False


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_SRC_STR = str(_SRC)
if _SRC_STR not in sys.path:
    sys.path.insert(0, _SRC_STR)


# Silence skia deprecation warnings during tests (font-related deprecations).
# Target DeprecationWarning originating from the `skia` module. This keeps
# the test output clean while still showing other relevant warnings.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"^skia(\.|$)",
)


# Some versions of skia-python may emit warnings coming from extension
# modules where the module name isn't exactly 'skia'. Also ignore Deprecation
# messages that explicitly mention 'skia' in the message as a fallback.
warnings.filterwarnings(
    "ignore",
    message=r".*skia.*is deprecated.*",
    category=DeprecationWarning,
)

# Specific filter: some skia versions emit a DeprecationWarning about the
# "Default typeface" (message originates when calling skia.Typeface()).
# Silence that specific upstream deprecation to keep test output clean.
warnings.filterwarnings(
    "ignore",
    message=r".*Default typeface.*",
    category=DeprecationWarning,
)


@pytest.fixture(autouse=True)
def cancel_pending_clock_callbacks():
    """Leave no scheduled clock callback behind at the end of a test.

    With no backend running, ``runtime.clock`` is the fallback
    ``_ThreadClock``, which fires callbacks on background threads. A widget
    that schedules a delayed callback — an Overlay auto-dismiss timeout, a
    tooltip delay — and is never torn down leaves that timer armed for the
    rest of the session. It then fires in the middle of some *later*,
    unrelated test, mutating process-global widget state and logging an
    ``assert_ui_thread`` failure into that test's ``caplog``. See #468.

    Clocks installed by a test (the ``_FakeClock`` pattern) have no timers to
    cancel and simply do not provide ``cancel_all``.
    """
    from nuiitivet.observable import runtime

    def _cancel() -> None:
        cancel_all = getattr(runtime.clock, "cancel_all", None)
        if cancel_all is not None:
            cancel_all()

    _cancel()
    try:
        yield
    finally:
        _cancel()


# An App's Overlay and Navigator are per-instance, so building an App in a test
# leaks nothing into the next one. The autouse fixture that used to save and
# restore the process-global roots is gone with them (#518).
