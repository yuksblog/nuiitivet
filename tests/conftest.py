import pathlib
import sys
import warnings


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
