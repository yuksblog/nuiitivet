"""Tests for the download cache of the web tools."""

import hashlib
import io
from pathlib import Path
from typing import Any

import pytest

from nuiitivet.web import assets
from nuiitivet.web.assets import Asset, cache_dir, fetch

_BODY = b"font bytes"
_ASSET = Asset("fonts/a.otf", "https://example.invalid/a.otf", hashlib.sha256(_BODY).hexdigest())


@pytest.fixture
def downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setenv("NUIITIVET_CACHE_DIR", str(tmp_path / "cache"))
    urls: list[str] = []

    def urlopen(url: str) -> Any:
        urls.append(url)
        return io.BytesIO(_BODY)

    monkeypatch.setattr(assets.urllib.request, "urlopen", urlopen)
    return urls


def test_cache_dir_follows_the_override(downloads: list[str], tmp_path: Path) -> None:
    assert cache_dir() == tmp_path / "cache"


def test_a_file_is_downloaded_once(downloads: list[str]) -> None:
    first = fetch(_ASSET)
    second = fetch(_ASSET)

    assert first == second
    assert first.read_bytes() == _BODY
    assert downloads == [_ASSET.url]


def test_a_download_with_another_digest_is_refused(downloads: list[str]) -> None:
    wrong = Asset(_ASSET.path, _ASSET.url, "0" * 64)

    with pytest.raises(RuntimeError, match="not the file"):
        fetch(wrong)
    assert not list(cache_dir().rglob("*.otf"))


def test_a_failed_download_is_reported(monkeypatch: pytest.MonkeyPatch, downloads: list[str]) -> None:
    def urlopen(url: str) -> Any:
        raise OSError("offline")

    monkeypatch.setattr(assets.urllib.request, "urlopen", urlopen)

    with pytest.raises(RuntimeError, match="could not download"):
        fetch(_ASSET)
