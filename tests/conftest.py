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
def reset_app_roots():
    """Restore the process-global root Overlay/Navigator around every test.

    ``App`` publishes its Overlay and Navigator as class variables, so a test
    that builds a real ``App`` would otherwise leave them set for every later
    test — making tests that assert "no overlay in the tree" pass or fail
    depending on collection order.
    """
    from nuiitivet.navigation import Navigator
    from nuiitivet.overlay import Overlay

    overlay_root = Overlay._root_overlay
    navigator_root = Navigator._root
    try:
        yield
    finally:
        Overlay._root_overlay = overlay_root
        Navigator._root = navigator_root
