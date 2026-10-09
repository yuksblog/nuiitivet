"""Tests for the browser file dialog backend, against a fake page host.

The real host is ``NV_HOST`` of the page; the fake answers ``pickFiles`` with
Python objects shaped like the browser's ``File`` and records ``download``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nuiitivet.platform.file_dialog import FileDialogError
from nuiitivet.platform.file_dialog_browser import BrowserFileDialogBackend


class FakeBuffer:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def to_bytes(self) -> bytes:
        return self._data


class FakeFile:
    """What the browser's ``File`` looks like from Python."""

    def __init__(self, name: str, data: bytes, relative_path: str = "") -> None:
        self.name = name
        self.webkitRelativePath = relative_path
        self._data = data

    async def arrayBuffer(self) -> FakeBuffer:
        return FakeBuffer(self._data)


class FakeHost:
    def __init__(self, picked: list[FakeFile], *, in_gesture: bool = True) -> None:
        self.picked = picked
        self.in_gesture = in_gesture
        self.pick_calls: list[tuple[str, bool, bool]] = []
        self.downloads: list[tuple[str, bytes]] = []

    def canShowPicker(self) -> bool:
        return self.in_gesture

    async def pickFiles(self, accept: str, multiple: bool, directory: bool) -> list[FakeFile]:
        self.pick_calls.append((accept, multiple, directory))
        return self.picked

    def download(self, name: str, data: bytes) -> None:
        self.downloads.append((name, bytes(data)))


@pytest.mark.asyncio
async def test_open_file_copies_the_picked_file_under_its_own_name():
    host = FakeHost([FakeFile("pic.png", b"\x89PNG")])
    path = await BrowserFileDialogBackend(host).open_file(file_types=["png", "jpg"])
    assert path is not None
    assert path.name == "pic.png"
    assert path.read_bytes() == b"\x89PNG"
    assert host.pick_calls == [(".png,.jpg", False, False)]


@pytest.mark.asyncio
async def test_open_file_cancel_is_none():
    host = FakeHost([])
    assert await BrowserFileDialogBackend(host).open_file() is None
    assert host.pick_calls == [("", False, False)]


@pytest.mark.asyncio
async def test_open_file_outside_a_user_gesture_raises():
    host = FakeHost([], in_gesture=False)
    with pytest.raises(FileDialogError, match="click"):
        await BrowserFileDialogBackend(host).open_file()
    assert host.pick_calls == []


@pytest.mark.asyncio
async def test_open_files_copies_each_file():
    host = FakeHost([FakeFile("a.txt", b"a"), FakeFile("b.txt", b"b")])
    paths = await BrowserFileDialogBackend(host).open_files()
    assert [p.name for p in paths] == ["a.txt", "b.txt"]
    assert [p.read_bytes() for p in paths] == [b"a", b"b"]
    assert len({p.parent for p in paths}) == 1
    assert host.pick_calls == [("", True, False)]


@pytest.mark.asyncio
async def test_open_files_cancel_is_empty():
    assert await BrowserFileDialogBackend(FakeHost([])).open_files() == []


@pytest.mark.asyncio
async def test_two_picks_land_in_different_directories():
    backend = BrowserFileDialogBackend(FakeHost([FakeFile("same.txt", b"1")]))
    first = await backend.open_file()
    backend._host.picked = [FakeFile("same.txt", b"2")]
    second = await backend.open_file()
    assert first is not None and second is not None
    assert first != second
    assert (first.read_bytes(), second.read_bytes()) == (b"1", b"2")


@pytest.mark.asyncio
async def test_open_directory_keeps_the_layout_and_returns_the_directory():
    host = FakeHost(
        [
            FakeFile("notes.md", b"n", "photos/notes.md"),
            FakeFile("a.png", b"a", "photos/2024/a.png"),
        ]
    )
    path = await BrowserFileDialogBackend(host).open_directory()
    assert path is not None
    assert path.name == "photos"
    assert (path / "notes.md").read_bytes() == b"n"
    assert (path / "2024" / "a.png").read_bytes() == b"a"
    assert host.pick_calls == [("", True, True)]


@pytest.mark.asyncio
async def test_open_directory_with_no_file_is_none():
    assert await BrowserFileDialogBackend(FakeHost([])).open_directory() is None


@pytest.mark.asyncio
async def test_save_file_downloads_the_written_file_when_the_task_ends():
    host = FakeHost([])
    backend = BrowserFileDialogBackend(host)

    async def handler() -> Path:
        path = await backend.save_file(default_name="out.txt")
        assert path is not None
        path.write_text("hello")
        assert host.downloads == []  # not before the handler returns
        return path

    path = await asyncio.create_task(handler())
    await asyncio.sleep(0)  # the done callback runs on the next loop turn
    assert path.name == "out.txt"
    assert host.downloads == [("out.txt", b"hello")]


@pytest.mark.asyncio
async def test_save_file_downloads_nothing_when_nothing_was_written():
    host = FakeHost([])

    async def handler() -> None:
        await BrowserFileDialogBackend(host).save_file()

    await asyncio.create_task(handler())
    await asyncio.sleep(0)
    assert host.downloads == []


@pytest.mark.asyncio
async def test_save_file_names_the_file_from_the_first_type():
    backend = BrowserFileDialogBackend(FakeHost([]))

    async def name(**kwargs: object) -> str:
        path = await backend.save_file(**kwargs)  # type: ignore[arg-type]
        assert path is not None
        return path.name

    assert await name(file_types=["csv"]) == "untitled.csv"
    assert await name(default_name="report", file_types=["csv"]) == "report.csv"
    assert await name(default_name="report.txt", file_types=["csv"]) == "report.txt"
