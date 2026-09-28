"""Open an editor at a file and line, through the editor's URL scheme."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from typing import Optional
from urllib.parse import quote, urlsplit

logger = logging.getLogger(__name__)

_VSCODE_TEMPLATE = "vscode://file{file}:{line}:1"

_KNOWN = {"vscode": _VSCODE_TEMPLATE}

# macOS puts ``code`` on ``PATH`` only when the user opts in.
_VSCODE_INSTALLS = (
    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
    os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
)

_HOSTILE_TO_EDITORS = ("ELECTRON_RUN_AS_NODE", "NODE_OPTIONS", "SSLKEYLOGFILE")

_template: Optional[str] = None


def configure(spec: Optional[str]) -> None:
    """Point the jump at ``spec``.

    Args:
        spec: A known editor name, a URL template, or ``None`` for the default
            route. It must already pass :func:`validate`.
    """
    global _template
    _template = None if spec is None else _KNOWN.get(spec, spec)


def validate(spec: str) -> Optional[str]:
    """Say what is wrong with ``spec``, or ``None`` if nothing is.

    A well-formed template for an unregistered scheme passes.

    Args:
        spec: A known editor name, or a URL template with ``{file}`` and
            ``{line}``.
    """
    if spec in _KNOWN:
        return None
    if spec.startswith("-"):
        # An opener would read it as a flag rather than a location.
        return "an editor template cannot start with '-'"
    scheme = urlsplit(spec).scheme
    if not scheme or "://" not in spec:
        return (
            f"{spec!r} is neither a known editor ({', '.join(sorted(_KNOWN))}) "
            "nor a URL template like 'cursor://file{file}:{line}:1'"
        )
    missing = [name for name in ("{file}", "{line}") if name not in spec]
    if missing:
        return f"an editor template needs {' and '.join(missing)}"
    try:
        spec.format(file="/x", line=1)
    except (KeyError, IndexError, ValueError) as exc:
        return f"an editor template has an unusable placeholder: {exc}"
    return None


def open_at(path: str, line: int) -> Optional[str]:
    """Open ``path`` at ``line`` in the editor.

    Returns ``None`` once the URL is handed over, which does not prove the
    editor moved. Otherwise returns the reason to show the human.

    Args:
        path: The file to open.
        line: The 1-based line to put the caret on.
    """
    opener = _url_opener()
    if opener is None:
        return "no xdg-open on this desktop, so nothing can open the editor URL"
    if _template is None and not _vscode_installed():
        logger.warning(
            "dev: cannot open an editor -- VS Code was not found. Install its "
            "'Shell Command: Install code command in PATH', or pass "
            "--editor (e.g. --editor \"cursor://file{file}:{line}:1\").",
        )
        return "VS Code was not found"
    return _open_url(_template or _VSCODE_TEMPLATE, path, line, opener=opener)


def _url_opener() -> Optional[str]:
    """How this platform hands a URL to its registered application, or ``None``.

    ``"startfile"`` stands for the Windows shell API, not a command.
    """
    if sys.platform == "darwin":
        return "open"
    if sys.platform == "win32":
        return "startfile"
    return "xdg-open" if shutil.which("xdg-open") is not None else None


def _open_url(template: str, path: str, line: int, *, opener: str) -> Optional[str]:
    """Hand the location to the running editor as a URL."""
    url = template.format(file=_url_path(path), line=line)
    try:
        if opener == "startfile":
            _startfile_without_hostile_env(url)
        else:
            subprocess.Popen(
                [opener, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                env={k: v for k, v in os.environ.items() if k not in _HOSTILE_TO_EDITORS},
            )
    except OSError as exc:
        logger.debug("dev: opening the editor URL failed", exc_info=True)
        return f"could not open the editor URL: {exc}"
    return None


def _startfile_without_hostile_env(url: str) -> None:
    """``os.startfile(url)`` with :data:`_HOSTILE_TO_EDITORS` unset for the call.

    The change is process-wide. It is safe only while nothing else spawns a
    child during the call.
    """
    saved = {name: os.environ.pop(name) for name in _HOSTILE_TO_EDITORS if name in os.environ}
    try:
        os.startfile(url)  # type: ignore[attr-defined]  # Windows only
    finally:
        os.environ.update(saved)


def _url_path(path: str) -> str:
    """``path`` as it goes into an editor URL: ``C:\\dir\\a b.py`` -> ``/C:/dir/a%20b.py``."""
    absolute = os.path.abspath(path).replace(os.sep, "/")
    if not absolute.startswith("/"):
        absolute = "/" + absolute
    return quote(absolute, safe="/:")


def _vscode_installed() -> bool:
    """Whether the ``code`` shim or the macOS app bundle exists."""
    if shutil.which("code") is not None:
        return True
    return any(os.path.isfile(c) and os.access(c, os.X_OK) for c in _VSCODE_INSTALLS)
