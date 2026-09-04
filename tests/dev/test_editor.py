"""Tests for opening an editor at a construction site.

The cases that matter are the ones a human would otherwise experience as "the
feature is broken". Since the route is a URL, most of those are *silent* -- an
opener succeeds whether or not anything is registered for the scheme -- so what
is worth testing hardest is everything that can still be caught: the install
check, the path form, and the template validation that runs at startup.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet.dev import editor


@pytest.fixture(autouse=True)
def _default_route() -> Iterator[None]:
    """Reset the configured template around every test.

    ``--editor`` is process-wide state, set once at startup, so nothing else
    resets it -- and a leak here would be invisible in one test and baffling in
    the next.
    """
    editor.configure(None)
    yield
    editor.configure(None)


@pytest.fixture
def opened(monkeypatch: Any) -> Iterator[list[str]]:
    """Capture the URL handed to the opener, on a platform that has one."""
    calls: list[str] = []

    def fake_popen(argv: list[str], **_kwargs: Any) -> Any:
        calls.append(argv[1])
        return object()

    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(editor.subprocess, "Popen", fake_popen)
    yield calls


# --- the default route ----------------------------------------------------


def test_macos_hands_the_location_to_the_running_editor_as_a_url(
    opened: list[str],
) -> None:
    """Fourteen times faster than the CLI it replaced: ~95 ms against ~1400 ms.

    That CLI is a shell script that runs the Electron binary *as Node*, booting
    a whole runtime to send one IPC message. The URL goes through LaunchServices
    to the window that is already open.
    """
    assert editor.open_at("/tmp/app.py", 171) is None
    assert opened == ["vscode://file/tmp/app.py:171:1"]


def test_the_line_rides_inside_the_url(opened: list[str]) -> None:
    """The whole reason this route works where ``open -a --args`` did not.

    LaunchServices passes ``--args`` only when it actually launches the
    application, so an already-running editor got the file *without* the line --
    fourteen times faster and missing the one thing the feature delivers. A line
    inside the URL has nothing for that rule to drop.
    """
    editor.open_at("/tmp/app.py", 420)

    assert opened[0].endswith(":420:1")


def test_the_url_route_is_skipped_when_vscode_is_not_installed(
    monkeypatch: Any,
) -> None:
    """The scheme is registered by the installation, so absence means silence.

    Guarding on the install rather than on the scheme keeps the check free --
    asking ``open`` would mean waiting out its ~95 ms on the UI thread.
    """
    monkeypatch.setattr(editor.sys, "platform", "darwin")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)
    monkeypatch.setattr(editor, "_VSCODE_INSTALLS", ())

    assert editor.open_at("/tmp/app.py", 42) == "VS Code was not found"


def test_the_default_finds_a_vscode_that_never_installed_the_shim(
    monkeypatch: Any, opened: list[str]
) -> None:
    """Putting ``code`` on ``PATH`` is an opt-in step on macOS.

    An editor that is plainly installed therefore fails to be found by ``PATH``
    alone, which the first real use of this feature hit immediately.
    """
    monkeypatch.setattr(
        editor.shutil, "which", lambda name: None if name == "code" else f"/usr/bin/{name}"
    )
    monkeypatch.setattr(editor.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(editor.os, "access", lambda p, mode: True)

    assert editor.open_at("/tmp/app.py", 42) is None
    assert opened == ["vscode://file/tmp/app.py:42:1"]


# --- the path form --------------------------------------------------------


def test_a_path_with_spaces_is_percent_encoded(opened: list[str]) -> None:
    """A URL is not a filename: the separators must survive and the rest must not."""
    editor.open_at("/tmp/my project/app.py", 7)

    assert opened == ["vscode://file/tmp/my%20project/app.py:7:1"]


def test_a_windows_drive_letter_becomes_part_of_the_url_path(
    monkeypatch: Any,
) -> None:
    """``C:\\dir\\app.py`` has neither a leading slash nor forward separators.

    Both are required by the handler, and the drive-letter colon must survive
    percent-encoding or the path is mangled.
    """
    monkeypatch.setattr(editor.os.path, "abspath", lambda p: "C:\\dir\\app.py")
    monkeypatch.setattr(editor.os, "sep", "\\")

    assert editor._url_path("app.py") == "/C:/dir/app.py"


def test_the_encoded_path_is_safe_in_a_query_as_well_as_a_path() -> None:
    """A template may put the path in either position -- JetBrains uses ``?path=``.

    So the characters that would end a query early, or start another parameter,
    have to go even though they are legal in a URL path.
    """
    encoded = editor._url_path("/tmp/a&b=c#d?e.py")

    assert encoded == "/tmp/a%26b%3Dc%23d%3Fe.py"


# --- the platforms --------------------------------------------------------


def test_linux_hands_the_url_to_xdg_open(monkeypatch: Any) -> None:
    """The freedesktop standard opener."""
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.open_at("/tmp/app.py", 171)

    assert calls == [["xdg-open", "vscode://file/tmp/app.py:171:1"]]


def test_a_desktop_without_xdg_open_is_told_why_nothing_happens(
    monkeypatch: Any,
) -> None:
    """There is no CLI to fall back to any more, so this is the end of the road.

    Accepted deliberately: one mechanism is worth more than rescuing a
    desktop that ships no opener, and ``--editor`` could not help here anyway --
    what is missing is the opener, not the scheme.
    """
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: None)

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "xdg-open" in reason


def test_windows_uses_the_shell_api_rather_than_a_process(monkeypatch: Any) -> None:
    """There is no opener process on Windows."""
    monkeypatch.setattr(editor.sys, "platform", "win32")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"C:/bin/{name}")
    opened: list[str] = []
    monkeypatch.setattr(editor.os, "startfile", opened.append, raising=False)

    assert editor.open_at("/tmp/app.py", 171) is None
    assert opened == ["vscode://file/tmp/app.py:171:1"]


def test_an_unregistered_scheme_is_reported_on_windows(monkeypatch: Any) -> None:
    """The one platform where a missing handler is detectable without waiting."""
    monkeypatch.setattr(editor.sys, "platform", "win32")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"C:/bin/{name}")

    def boom(url: str) -> None:
        raise OSError("no application is associated with vscode")

    monkeypatch.setattr(editor.os, "startfile", boom, raising=False)

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "no application is associated" in reason


def test_a_failure_to_reach_the_opener_is_reported(monkeypatch: Any) -> None:
    """Reported rather than dropped: silence reads as a broken feature."""
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(editor.shutil, "which", lambda name: f"/usr/bin/{name}")

    def boom(argv: list[str], **_kwargs: Any) -> Any:
        raise OSError("no such file")

    monkeypatch.setattr(editor.subprocess, "Popen", boom)

    reason = editor.open_at("/tmp/app.py", 42)

    assert reason is not None
    assert "no such file" in reason


# --- --editor -------------------------------------------------------------


def test_a_configured_template_replaces_the_default(opened: list[str]) -> None:
    """The escape hatch for every editor this does not ship an entry for.

    A VS Code fork is the case that matters: the shape is identical and only the
    scheme differs, so catching up with one is a single line.
    """
    editor.configure("cursor://file{file}:{line}:1")

    assert editor.open_at("/tmp/app.py", 12) is None
    assert opened == ["cursor://file/tmp/app.py:12:1"]


def test_a_configured_template_gets_the_encoded_path(opened: list[str]) -> None:
    """Nobody writing a template should have to know about ``/C:/`` or ``%20``."""
    editor.configure("jetbrains://pycharm/navigate/reference?project=demo&path={file}:{line}")

    editor.open_at("/tmp/my project/app.py", 9)

    assert opened == [
        "jetbrains://pycharm/navigate/reference?project=demo&path=/tmp/my%20project/app.py:9"
    ]


def test_a_known_name_stands_in_for_its_template(opened: list[str]) -> None:
    """``--editor vscode`` is the default route named out loud."""
    editor.configure("vscode")

    editor.open_at("/tmp/app.py", 3)

    assert opened == ["vscode://file/tmp/app.py:3:1"]


def test_naming_an_editor_skips_the_installed_check(monkeypatch: Any) -> None:
    """Naming one is asserting it exists, and the check is only a proxy anyway.

    It looks for the ``code`` shim, which the URL route does not need -- a
    Flatpak or Snap install registers the scheme with nothing on ``PATH``.
    """
    monkeypatch.setattr(editor.sys, "platform", "linux")
    monkeypatch.setattr(
        editor.shutil, "which", lambda name: None if name == "code" else f"/usr/bin/{name}"
    )
    monkeypatch.setattr(editor, "_VSCODE_INSTALLS", ())
    calls: list[list[str]] = []
    monkeypatch.setattr(editor.subprocess, "Popen", lambda argv, **k: calls.append(argv))

    editor.configure("vscode")

    assert editor.open_at("/tmp/app.py", 42) is None
    assert calls == [["xdg-open", "vscode://file/tmp/app.py:42:1"]]


# --- validation, at startup rather than at click time ----------------------


def test_a_known_name_and_a_well_formed_template_both_pass() -> None:
    assert editor.validate("vscode") is None
    assert editor.validate("cursor://file{file}:{line}:1") is None


def test_something_that_is_not_a_url_is_rejected() -> None:
    """A CLI command is the likeliest thing to try, and no longer a route.

    Catching it at startup is what keeps that mistake from arriving as silence
    on the first Ctrl+Click.
    """
    problem = editor.validate("pycharm --line {line} {file}")

    assert problem is not None
    assert "URL template" in problem


def test_a_template_missing_its_placeholders_is_rejected() -> None:
    problem = editor.validate("cursor://file/only/a/line:{line}")

    assert problem is not None
    assert "{file}" in problem


def test_a_template_that_would_read_as_a_flag_is_rejected() -> None:
    """An opener would take it as an option instead of a location."""
    problem = editor.validate("--file{file}:{line}")

    assert problem is not None
    assert "'-'" in problem


def test_a_stray_placeholder_is_rejected_before_it_can_fail_a_click() -> None:
    """``str.format`` raises on an unknown name, and would do it mid-jump."""
    problem = editor.validate("cursor://file{file}:{line}:{column}")

    assert problem is not None
    assert "placeholder" in problem
