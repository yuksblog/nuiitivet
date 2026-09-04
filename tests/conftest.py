import pathlib
import sys
import warnings

import pyglet

# The pytester fixture drives the sub-sessions in tests/testing/test_plugin.py.
pytest_plugins = ["pytester"]

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


# No autouse isolation fixture lives here. The nuiitivet.testing pytest plugin
# (registered via the pytest11 entry point) installs a HarnessClock and resets
# the framework's process-global state around every test — we run on the
# isolation we ship, so a regression there breaks this suite first. The
# fixture that cancelled leaked _ThreadClock timers and the one that
# restored the App roots (since made per-instance) are both superseded.
