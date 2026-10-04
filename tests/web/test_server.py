"""Tests for what ``python -m nuiitivet.web run`` serves."""

import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

import pytest

from nuiitivet.common.target import is_web
from nuiitivet.web.__main__ import main
from nuiitivet.web.server import build_bundle, make_server


@pytest.fixture
def app_path(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text("print('app')\n")
    (tmp_path / "views").mkdir()
    (tmp_path / "views" / "home.py").write_text("")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "app.cpython-311.pyc").write_bytes(b"")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("")
    return tmp_path / "app.py"


@pytest.fixture
def base_url(app_path: Path, tmp_path: Path) -> Iterator[str]:
    font = tmp_path / "font.ttf"
    font.write_bytes(b"font")
    server = make_server(app_path, font, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_bundle_holds_the_app_directory_and_the_framework(app_path: Path) -> None:
    names = set(zipfile.ZipFile(io.BytesIO(build_bundle(app_path))).namelist())

    assert {"app/app.py", "app/views/home.py"} <= names
    assert {"lib/nuiitivet/__init__.py", "lib/nuiitivet/backends/web/skia.py"} <= names
    assert any(name.startswith("lib/materialyoucolor/") for name in names)
    assert not any("__pycache__" in name or ".venv" in name or name.endswith(".ttf") for name in names)


def test_bundle_is_read_again_at_every_request(app_path: Path, base_url: str) -> None:
    (app_path.parent / "added.py").write_text("")
    with urllib.request.urlopen(base_url + "/bundle.zip") as response:
        names = zipfile.ZipFile(io.BytesIO(response.read())).namelist()

    assert "app/added.py" in names


def test_server_serves_the_page_and_names_the_entry(base_url: str) -> None:
    with urllib.request.urlopen(base_url + "/") as response:
        assert b'<canvas id="nuiitivet"' in response.read()
    with urllib.request.urlopen(base_url + "/config.json") as response:
        assert json.load(response) == {"entry": "app.py"}
    with urllib.request.urlopen(base_url + "/font.ttf") as response:
        assert response.read() == b"font"


def test_server_refuses_any_other_path(base_url: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(base_url + "/app.py")
    assert error.value.code == 404


def test_run_reports_a_missing_app(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", str(tmp_path / "missing.py"), "--no-open"]) == 2
    assert "app not found" in capsys.readouterr().err


def test_the_runtime_decides_the_target(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_web()
    monkeypatch.setattr("sys.platform", "emscripten")
    assert is_web()
