"""System clipboard access.

This module is OS-dependent but backend-agnostic.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Callable, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.common.target import is_web


logger = logging.getLogger(__name__)


class Clipboard(ABC):
    @abstractmethod
    def get_text(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_text(self, text: str) -> None:
        raise NotImplementedError


class MacClipboard(Clipboard):
    def get_text(self) -> str:
        try:
            return subprocess.check_output("pbpaste", env={"LANG": "en_US.UTF-8"}).decode("utf-8")
        except Exception:
            exception_once(logger, "clipboard_mac_get_text_exc", "pbpaste failed")
            return ""

    def set_text(self, text: str) -> None:
        try:
            process = subprocess.Popen("pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
        except Exception:
            exception_once(logger, "clipboard_mac_set_text_exc", "pbcopy failed")


class LinuxClipboard(Clipboard):
    def get_text(self) -> str:
        try:
            output = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"],
                stderr=subprocess.DEVNULL,
            )
            return output.decode("utf-8")
        except Exception:
            try:
                output = subprocess.check_output(
                    ["xsel", "--clipboard", "--output"],
                    stderr=subprocess.DEVNULL,
                )
                return output.decode("utf-8")
            except Exception:
                exception_once(logger, "clipboard_linux_get_text_exc", "xclip/xsel clipboard read failed")
                return ""

    def set_text(self, text: str) -> None:
        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-i"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            process.communicate(text.encode("utf-8"))
        except Exception:
            try:
                process = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                process.communicate(text.encode("utf-8"))
            except Exception:
                exception_once(logger, "clipboard_linux_set_text_exc", "xclip/xsel clipboard write failed")


class WindowsClipboard(Clipboard):
    def get_text(self) -> str:
        try:
            return (
                subprocess.check_output(["powershell", "-command", "Get-Clipboard"], stderr=subprocess.DEVNULL)
                .decode("utf-8")
                .rstrip("\r\n")
            )
        except Exception:
            exception_once(logger, "clipboard_windows_get_text_exc", "PowerShell Get-Clipboard failed")
            return ""

    def set_text(self, text: str) -> None:
        try:
            cmd = f'Set-Clipboard -Value "{text}"'
            subprocess.run(["powershell", "-command", cmd], stderr=subprocess.DEVNULL)
        except Exception:
            try:
                process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
                process.communicate(text.encode("utf-8"))
            except Exception:
                exception_once(logger, "clipboard_windows_set_text_exc", "PowerShell Set-Clipboard and clip failed")


class DummyClipboard(Clipboard):
    def __init__(self) -> None:
        self._text = ""

    def get_text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        self._text = text


class BrowserClipboard(Clipboard):
    """The app's side of the browser's clipboard.

    A page may read the browser's clipboard only inside a paste event, so the
    browser backend carries the text across: it calls :meth:`receive` when the
    user pastes, and ``on_copy`` hands it what the app copies.
    """

    def __init__(self) -> None:
        self._text = ""
        self.on_copy: Optional[Callable[[str], None]] = None

    def get_text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        self._text = text
        if self.on_copy is not None:
            self.on_copy(text)

    def receive(self, text: str) -> None:
        """Take the text of a paste event.

        Args:
            text: What the browser's clipboard holds.
        """
        self._text = text


_browser_clipboard = BrowserClipboard()


def get_system_clipboard() -> Clipboard:
    if is_web():
        return _browser_clipboard
    if sys.platform == "darwin":
        return MacClipboard()
    if sys.platform == "linux":
        return LinuxClipboard()
    if sys.platform == "win32":
        return WindowsClipboard()
    return DummyClipboard()
