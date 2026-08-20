"""Tests for launching an editor at a construction site (#593).

The cases that matter are the ones a human would otherwise experience as "the
feature is broken": a command that is not installed, and a path the shell would
have mangled if this went through one.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet.dev import editor


def _installed_but_no_url_opener(name: str) -> Any:
    """Every command resolves except the URL opener, forcing the CLI route.

    Not a contrivance: it is the documented fallback -- a desktop without
    ``xdg-open`` has nothing to hand a URL to.
    """
    return None if name == "xdg-open" else f"/usr/bin/{name}"


@pytest.fixture
def launched(monkeypatch: Any) -> Iterator[list[list[str]]]:
    """Capture argv instead of starting a process, with every command 'installed'.

    Pinned off macOS, because there the default route is the ``vscode://`` URL
    and these cases are about the CLI template.
    """
    calls: list[list[str]] = []

    def fake_popen(argv: list[str], **_kwargs: Any) -> Any:
        calls.append(argv)
        return object()

    monkeypatch.setattr(editor.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(editor.shutil, "which", _installed_but_no_url_opener)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    yield calls


def test_the_default_command_targets_the_file_and_line(
    launched: list[list[str]], monkeypatch: Any
) -> None:
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)

    assert editor.open_at("/tmp/app.py", 42) is None
    assert launched == [["code", "--goto", "/tmp/app.py:42"]]


def test_the_command_is_configurable_for_other_editors(
    launched: list[list[str]], monkeypatch: Any
) -> None:
    """The whole cross-editor story is one environment variable."""
    monkeypatch.setenv(editor.COMMAND_ENV, "pycharm --line {line} {file}")

    editor.open_at("/tmp/app.py", 42)

    assert launched == [["pycharm", "--line", "42", "/tmp/app.py"]]


def test_a_path_with_spaces_stays_one_argument(
    launched: list[list[str]], monkeypatch: Any
) -> None:
    """Substituting *after* the split is what keeps this true."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)

    editor.open_at("/tmp/my project/app.py", 7)

    assert launched == [["code", "--goto", "/tmp/my project/app.py:7"]]


def test_a_path_with_shell_metacharacters_stays_inert(
    launched: list[list[str]], monkeypatch: Any
) -> None:
    """Never runs through a shell, so a crafted path is just a filename.

    Reached with an ordinary repository checkout: a directory named ``$(x)`` or
    containing a semicolon is legal on every platform this runs on.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    nasty = "/tmp/a;rm -rf ~/$(whoami)/app.py"

    editor.open_at(nasty, 1)

    assert launched == [["code", "--goto", f"{nasty}:1"]]


def test_a_missing_editor_is_reported_rather_than_silently_dropped(
    monkeypatch: Any,
) -> None:
    """A jump that does nothing and says nothing looks like a broken feature.

    The likely cause -- the editor's CLI was never put on PATH -- is something
    only the human can fix, so it has to reach them.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)
    monkeypatch.setattr(editor, "_FALLBACKS", ())

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "code" in reason and "PATH" in reason


def test_an_unparsable_command_is_reported(monkeypatch: Any) -> None:
    monkeypatch.setenv(editor.COMMAND_ENV, 'code --goto "unclosed')

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert editor.COMMAND_ENV in reason


def test_an_unknown_placeholder_is_reported(monkeypatch: Any) -> None:
    monkeypatch.setenv(editor.COMMAND_ENV, "code --goto {flie}:{line}")

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert editor.COMMAND_ENV in reason


def test_an_empty_command_is_reported(monkeypatch: Any) -> None:
    monkeypatch.setenv(editor.COMMAND_ENV, "   ")

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None


def test_a_launch_failure_is_reported(monkeypatch: Any) -> None:
    """``which`` finding it is not proof it will start."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")

    def boom(argv: list[str], **_kwargs: Any) -> Any:
        raise OSError("no fork for you")

    monkeypatch.setattr(editor.subprocess, "Popen", boom)

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "no fork for you" in reason


def test_the_editor_never_inherits_the_dev_runners_stdin(
    monkeypatch: Any,
) -> None:
    """A terminal editor launched by mistake must not take over the console."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    seen: dict[str, Any] = {}

    def fake_popen(argv: list[str], **kwargs: Any) -> Any:
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(editor.subprocess, "Popen", fake_popen)

    editor.open_at("/tmp/app.py", 1)

    assert seen["stdin"] == editor.subprocess.DEVNULL


# --- finding an editor that is installed but not on PATH ---------------------


def test_the_default_falls_back_to_a_known_install_location(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """Hit on the very first real use of this feature.

    VS Code's ``code`` shim is an explicit opt-in step on macOS, so an editor
    that is plainly installed is routinely absent from PATH -- and reporting
    that is correct but useless when the binary is sitting in a known place.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)
    installed = tmp_path / "code"
    installed.write_text("#!/bin/sh\n")
    installed.chmod(0o755)
    monkeypatch.setattr(editor, "_FALLBACKS", (str(installed),))
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    assert editor.open_at("/tmp/app.py", 42) is None
    assert calls == [[str(installed), "--goto", "/tmp/app.py:42"]]


def test_a_configured_command_is_never_redirected(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """A template the human set is theirs.

    Quietly running VS Code because *their* editor was missing would be worse
    than saying it is missing -- it opens the wrong program and hides the cause.
    """
    monkeypatch.setenv(editor.COMMAND_ENV, "my-editor {file}:{line}")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)
    installed = tmp_path / "code"
    installed.write_text("#!/bin/sh\n")
    installed.chmod(0o755)
    monkeypatch.setattr(editor, "_FALLBACKS", (str(installed),))

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "my-editor" in reason


def test_path_still_wins_over_the_fallback(monkeypatch: Any) -> None:
    """A deliberately installed shim must not be shadowed by a bundled copy."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(
        editor.shutil, "which", lambda name: None if name == "xdg-open" else "/usr/local/bin/code"
    )
    monkeypatch.setattr(editor, "_FALLBACKS", ("/Applications/never/code",))
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 1)

    assert calls[0][0] == "code", "a shim on PATH must not be shadowed by a bundled copy"


# --- the fast route: the vscode:// URL --------------------------------------


def test_macos_hands_the_location_to_the_running_editor_as_a_url(
    monkeypatch: Any,
) -> None:
    """Fourteen times faster: ~95 ms against ~1400 ms for the CLI.

    The CLI is a shell script that runs the Electron binary *as Node*, booting a
    whole runtime to send one IPC message. The URL goes through LaunchServices
    to the window that is already open.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    assert editor.open_at("/tmp/app.py", 171) is None
    assert calls == [["open", "vscode://file/tmp/app.py:171:1"]]


def test_the_line_rides_inside_the_url(monkeypatch: Any) -> None:
    """The whole reason this route works where ``open -a --args`` did not.

    LaunchServices passes ``--args`` only when it actually launches the
    application, so an already-running editor got the file *without* the line --
    twelve times faster and missing the one thing the feature delivers. A line
    inside the URL has nothing for that rule to drop.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 420)

    assert calls[0][1].endswith(":420:1")


def test_a_path_with_spaces_is_percent_encoded(monkeypatch: Any) -> None:
    """A URL is not a filename; the separators must survive and the rest must not."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/my project/app.py", 7)

    assert calls[0][1] == "vscode://file/tmp/my%20project/app.py:7:1"


def test_the_url_route_is_skipped_when_vscode_is_not_installed(
    monkeypatch: Any,
) -> None:
    """The scheme is registered by the installation, so absence means silence.

    Guarding on the install rather than on the scheme keeps the check free --
    asking ``open`` would mean waiting out its ~95 ms on the UI thread.
    """
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)
    monkeypatch.setattr(editor, "_FALLBACKS", ())

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None


def test_a_configured_command_wins_over_the_url_route(monkeypatch: Any) -> None:
    """Speed does not outrank the human's choice of editor."""
    monkeypatch.setenv(editor.COMMAND_ENV, "pycharm --line {line} {file}")
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 42)

    assert calls == [["pycharm", "--line", "42", "/tmp/app.py"]]


def test_linux_hands_the_url_to_xdg_open(monkeypatch: Any) -> None:
    """The freedesktop standard opener. **Not verified on real hardware** --
    CI is headless and this needs a running editor to observe."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 171)

    assert calls == [["xdg-open", "vscode://file/tmp/app.py:171:1"]]


def test_linux_falls_back_to_the_cli_without_xdg_open(monkeypatch: Any) -> None:
    """A minimal desktop may not ship it, and then there is nothing to hand a
    URL to."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(
        editor.shutil, "which", lambda name: None if name == "xdg-open" else f"/usr/bin/{name}"
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 42)

    assert calls == [["code", "--goto", "/tmp/app.py:42"]]


def test_windows_uses_the_shell_api_rather_than_a_process(monkeypatch: Any) -> None:
    """There is no opener process on Windows. **Not verified on real hardware.**"""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "win32")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"C:/bin/{name}")
    opened: list[str] = []
    monkeypatch.setattr(editor.os, "startfile", opened.append, raising=False)

    assert editor.open_at("/tmp/app.py", 171) is None
    assert opened == ["vscode://file/tmp/app.py:171:1"]


def test_a_windows_drive_letter_becomes_part_of_the_url_path(
    monkeypatch: Any,
) -> None:
    """``C:\\dir\\app.py`` has neither a leading slash nor forward separators.

    Both are required by the handler, and the drive-letter colon must survive
    percent-encoding or the path is mangled.
    """
    monkeypatch.setattr(editor.os.path, "abspath", lambda p: "C:\\dir\\app.py")
    monkeypatch.setattr(editor.os, "sep", "\\")

    assert editor._file_url("app.py", 171) == "vscode://file/C:/dir/app.py:171:1"


def test_an_unregistered_scheme_is_reported_on_windows(monkeypatch: Any) -> None:
    """The one platform where a missing handler is detectable without waiting."""
    monkeypatch.delenv(editor.COMMAND_ENV, raising=False)
    monkeypatch.setattr(editor.sys, "platform", "win32")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"C:/bin/{name}")

    def boom(url: str) -> None:
        raise OSError("no application is associated with vscode")

    monkeypatch.setattr(editor.os, "startfile", boom, raising=False)

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "no application is associated" in reason
