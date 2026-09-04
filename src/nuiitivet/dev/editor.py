"""Open an editor at a file and line.

The other half of :mod:`nuiitivet.dev.source`: that module answers *which line
built this widget*, and this one takes the human there.

The mechanism is the editor's **URL scheme**, handed to whatever the platform
has already registered for it. Worth contrasting with the browser-based prior
art -- React's and Vue's devtools route this through a dev-server endpoint
(``__open-in-editor``) purely because a page cannot start a process. A Nuiitivet
app is a local process and has no such constraint, but the CLI it could spawn
turns out to be the *worse* option anyway: see :func:`_open_url`.

An MCP server would be the wrong shape for a different reason: MCP is how a
*model* calls tools, and no model is involved -- inspect mode picks the node,
reads its site, and opens the editor, all in one process.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from typing import Optional
from urllib.parse import quote, urlsplit

logger = logging.getLogger(__name__)

# VS Code, because in 2026 it is effectively the one Python editor worth a
# built-in entry. Anything else is one ``--editor`` away, which is also why this
# stays a single entry rather than a registry: a table of schemes goes stale
# every time another VS Code fork appears, and the template does not.
_VSCODE_TEMPLATE = "vscode://file{file}:{line}:1"

#: Editor names accepted by ``--editor``, mapped to their URL template.
_KNOWN = {"vscode": _VSCODE_TEMPLATE}

# Where to look for VS Code when the ``code`` shim was never put on ``PATH``.
# Nothing is ever *run* from here -- the shim is merely the cheapest proof of an
# installation, and on macOS putting it on ``PATH`` is an explicit opt-in step
# ("Shell Command: Install 'code' command in PATH"), so a plainly-installed
# editor routinely fails to be found by ``PATH`` alone.
_VSCODE_INSTALLS = (
    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
    os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
)

#: The template in force, or ``None`` for the default route. Process-wide,
#: because the dev runner *is* the process: ``--editor`` is read once at startup
#: and cannot change while an app is running.
_template: Optional[str] = None


def configure(spec: Optional[str]) -> None:
    """Point the jump at ``spec`` -- a known editor name, or a URL template.

    Call :func:`validate` first; this assumes the spec is already known good.
    ``None`` restores the default route, which is the one the tests reset to.
    """
    global _template
    _template = None if spec is None else _KNOWN.get(spec, spec)


def validate(spec: str) -> Optional[str]:
    """Say what is wrong with ``spec``, or ``None`` if nothing is.

    Checked at startup rather than at click time, because the failure this
    guards against is a typo in a hand-written template, and a URL is the one
    route that *cannot* report its own failure: ``open`` and ``xdg-open``
    succeed whether or not anything is registered for the scheme. Discovering
    that on the first ``Ctrl+Click``, as silence, would be the worst of both.

    What survives this check is a well-formed URL for a scheme nobody has
    registered. Nothing here can catch that.
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
    """Open ``path`` at ``line``. Returns ``None`` on success, else why not.

    The caller shows the reason rather than failing silently: a jump that does
    nothing and says nothing is indistinguishable from a broken feature, and the
    likely causes -- an editor that was never found, a desktop with no opener --
    are things only the human can fix.

    A template the human passed is used as-is and trusted: naming an editor is
    asserting it exists, so the installed-check that guards the default route
    would only get in the way. That check is a proxy anyway -- it looks for the
    ``code`` shim, which the URL route does not need.
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

    ``"startfile"`` names the Windows API rather than a command, since there is
    no process to spawn there.

    All three were confirmed against a real editor -- the caret lands on
    the line, and the jump is fast enough to be the URL rather than a CLI. CI
    cannot check any of this: it is headless, and the question is where the
    cursor ended up.
    """
    if sys.platform == "darwin":
        return "open"
    if sys.platform == "win32":
        return "startfile"
    # xdg-open is the freedesktop standard, but a minimal desktop may not ship
    # it; without it there is nothing to hand the URL to, and no CLI to fall
    # back to either -- see the module docstring on why there is no second route.
    return "xdg-open" if shutil.which("xdg-open") is not None else None


def _open_url(template: str, path: str, line: int, *, opener: str) -> Optional[str]:
    """Hand the location to the running editor as a URL.

    Why the URL and not the editor's CLI: the ``code`` shim is a shell script
    whose last line runs the Electron binary *as Node*, so every jump boots a
    Node runtime purely to send one IPC message -- ~1400 ms. The URL reaches the
    same window in ~95 ms, measured on macOS. That launcher is shared across
    platforms, which is why no editor gets a CLI route, not even as a fallback:
    it would hand the slow path to exactly the people who had to configure
    something.

    An earlier attempt at the same shortcut on macOS, ``open -a ... --args
    --goto``, was rejected because LaunchServices passes ``--args`` only when it
    actually *launches* the application, so an already-running editor received
    the file without the line. Here the line is part of the URL, so there is
    nothing for that rule to drop.
    """
    url = template.format(file=_url_path(path), line=line)
    try:
        if opener == "startfile":
            # No process to spawn; the shell API raises when nothing is
            # registered, which is the one platform where that is detectable
            # without waiting on an opener.
            os.startfile(url)  # type: ignore[attr-defined]  # Windows only
        else:
            subprocess.Popen(
                [opener, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
    except OSError as exc:
        logger.debug("dev: opening the editor URL failed", exc_info=True)
        return f"could not open the editor URL: {exc}"
    return None


def _url_path(path: str) -> str:
    """``path`` in the form a ``file``-style URL wants, encoding and all.

    Absolute and slash-separated with a leading slash, which is what turns a
    Windows ``C:\\dir\\app.py`` into ``/C:/dir/app.py``; POSIX paths already have
    both. Percent-encoding keeps a space from ending the URL early, while the
    separators and the drive-letter colon are left intact.

    Done here rather than left to whoever writes a template, so nobody has to
    know any of the above. The encoding suits either position a template can put
    it in: ``&``, ``=``, ``#`` and ``?`` are all escaped, so a path is as safe in
    JetBrains' ``?path=`` query as in VS Code's path.
    """
    absolute = os.path.abspath(path).replace(os.sep, "/")
    if not absolute.startswith("/"):
        absolute = "/" + absolute
    return quote(absolute, safe="/:")


def _vscode_installed() -> bool:
    """Whether the default route has an editor to reach.

    Proxy, not proof: it looks for the ``code`` shim and the macOS app bundle,
    while what the URL actually needs is a registered scheme handler. A Flatpak
    or Snap install registers the scheme with no shim on ``PATH`` and so reads
    as missing here -- ``--editor vscode`` says so and skips the check.
    """
    if shutil.which("code") is not None:
        return True
    return any(os.path.isfile(c) and os.access(c, os.X_OK) for c in _VSCODE_INSTALLS)
