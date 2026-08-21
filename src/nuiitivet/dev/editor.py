"""Open an editor at a file and line (#593).

The other half of :mod:`nuiitivet.dev.source`: that module answers *which line
built this widget*, and this one takes the human there.

The whole mechanism is the editor's own CLI, because a Nuiitivet app is a local
process and can simply spawn one. Worth contrasting with the browser-based prior
art -- React's and Vue's devtools route this through a dev-server endpoint
(``__open-in-editor``) purely because a page cannot start a process. That detour
buys nothing here.

An MCP server would be the wrong shape for the same reason: MCP is how a *model*
calls tools, and no model is involved -- inspect mode picks the node, reads its
site, and launches the editor, all in one process.
"""

from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import sys
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

#: Overrides the command, so any editor works: ``"pycharm --line {line} {file}"``.
COMMAND_ENV = "NUIITIVET_DEV_OPEN_COMMAND"

# VS Code, because it is the common case and its CLI takes the whole location as
# one argument. Anything else is one environment variable away.
_DEFAULT_TEMPLATE = "code --goto {file}:{line}"

# Where VS Code keeps its CLI when the ``code`` shim was never put on ``PATH``.
# That shim is an explicit opt-in step on macOS ("Shell Command: Install 'code'
# command in PATH"), so an editor that is plainly installed routinely fails to
# be found -- which the first real use of this feature hit immediately. Falling
# back is only ever done for the *default* command: a template the human
# configured is theirs, and quietly substituting something else for it would be
# worse than saying it is missing.
_FALLBACKS = (
    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
    os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
)


def open_at(path: str, line: int) -> Optional[str]:
    """Open ``path`` at ``line``. Returns ``None`` on success, else why not.

    The caller shows the reason rather than failing silently: a jump that does
    nothing and says nothing is indistinguishable from a broken feature, and the
    likely cause -- an editor CLI that was never installed on ``PATH`` -- is
    something only the human can fix.

    Three routes, in order:

    1. A command the human configured. Theirs, always, unmodified.
    2. The ``vscode://`` URL, wherever the platform has an opener and VS Code is
       installed -- **fourteen times faster**, measured at ~95 ms against
       ~1400 ms for the CLI.
    3. The CLI template.
    """
    configured = os.environ.get(COMMAND_ENV)
    if configured is not None:
        return _run_template(configured, path, line, configured=True)
    if _resolve("code", configured=False) is not None and _url_opener() is not None:
        return _open_url(path, line)
    return _run_template(_DEFAULT_TEMPLATE, path, line, configured=False)


def _url_opener() -> Optional[str]:
    """How this platform hands a URL to its registered application, or ``None``.

    ``"startfile"`` names the Windows API rather than a command, since there is
    no process to spawn there.

    All three routes were confirmed against a real editor -- the caret lands on
    the line, and the jump is fast enough to be the URL rather than the CLI. CI
    cannot check any of this: it is headless, and the question is where the
    cursor ended up. Set ``NUIITIVET_DEV_OPEN_COMMAND`` to fall back to a CLI if
    one of them misbehaves.
    """
    if sys.platform == "darwin":
        return "open"
    if sys.platform == "win32":
        return "startfile"
    # xdg-open is the freedesktop standard, but a minimal desktop may not ship
    # it; without it there is nothing to hand the URL to.
    return "xdg-open" if shutil.which("xdg-open") is not None else None


def _open_url(path: str, line: int) -> Optional[str]:
    """Hand the location to the running editor as a URL, via LaunchServices.

    Why this is worth a second route: the ``code`` CLI is a shell script whose
    last line runs the Electron binary *as Node*, so every jump boots a Node
    runtime purely to send one IPC message -- ~1400 ms. The URL reaches the same
    window in ~95 ms.

    An earlier attempt at the same shortcut, ``open -a ... --args --goto``, was
    rejected because LaunchServices passes ``--args`` only when it actually
    *launches* the application, so an already-running editor received the file
    without the line. Here the line is part of the URL, so there is nothing for
    that rule to drop -- verified by watching the cursor land on it.

    Guarded by VS Code being installed rather than by checking the scheme, since
    checking would mean waiting on ``open`` and paying its ~95 ms on the UI
    thread for a result that is almost always the same.
    """
    url = _file_url(path, line)
    opener = _url_opener()
    try:
        if opener == "startfile":
            # No process to spawn; the shell API raises when nothing is
            # registered, which is the one platform where that is detectable
            # without waiting.
            os.startfile(url)  # type: ignore[attr-defined]  # Windows only
        else:
            subprocess.Popen(
                [str(opener), url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
    except OSError as exc:
        logger.debug("dev: opening the editor URL failed", exc_info=True)
        return f"could not open the editor URL: {exc}"
    return None


def _file_url(path: str, line: int) -> str:
    """``vscode://file/...`` for ``path``, in the form the handler expects.

    The path is absolute and slash-separated with a leading slash, which is what
    turns a Windows ``C:\\dir\\app.py`` into ``/C:/dir/app.py``; POSIX paths
    already have both. Percent-encoding keeps a space from ending the URL early,
    while the separators and the drive-letter colon are left intact.
    """
    absolute = os.path.abspath(path).replace(os.sep, "/")
    if not absolute.startswith("/"):
        absolute = "/" + absolute
    return f"vscode://file{quote(absolute, safe='/:')}:{line}:1"


def _run_template(template: str, path: str, line: int, *, configured: bool) -> Optional[str]:
    """Launch an editor CLI from a command template.

    Never runs through a shell. The template is split into arguments *first* and
    the path substituted into the resulting tokens, so a path containing spaces
    stays one argument and a path containing shell metacharacters stays inert.
    """
    try:
        parts = shlex.split(template)
    except ValueError as exc:
        return f"{COMMAND_ENV} is not a valid command: {exc}"
    if not parts:
        return f"{COMMAND_ENV} is empty"

    try:
        argv = [part.format(file=path, line=line) for part in parts]
    except (KeyError, IndexError) as exc:
        return f"{COMMAND_ENV} has an unknown placeholder: {exc}"

    executable = _resolve(argv[0], configured=configured)
    if executable is None:
        # Short, because this replaces a caption drawn at the widget's own x and
        # has nowhere to wrap. The actionable half goes to the log.
        logger.warning(
            "dev: cannot open an editor -- %r is not on PATH. Install VS Code's "
            "'Shell Command: Install code command in PATH', or set %s "
            '(e.g. "pycharm --line {line} {file}").',
            argv[0],
            COMMAND_ENV,
        )
        return f"{argv[0]} is not on PATH"
    argv[0] = executable

    try:
        subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # Detached from the app's stdin so a terminal editor launched by
            # mistake cannot take over the dev runner's console.
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        logger.debug("dev: launching the editor failed", exc_info=True)
        return f"could not run {argv[0]}: {exc}"
    return None


def _resolve(command: str, *, configured: bool) -> Optional[str]:
    """Return what to actually run for ``command``, or ``None`` if nothing can.

    ``PATH`` first, always -- and unchanged when it hits, so the process list
    reads the way the template does. The well-known install locations are
    consulted only for the default command and only after that fails, so a
    template the human set is never quietly redirected to a different program.
    """
    if shutil.which(command) is not None:
        return command
    if configured:
        return None
    for candidate in _FALLBACKS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None
