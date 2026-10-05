"""Tests for the files of an app's page: what ``run`` serves and ``build`` writes."""

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
from nuiitivet.web import server
from nuiitivet.web.__main__ import main
from nuiitivet.web.assets import Asset
from nuiitivet.web.server import build_bundle, make_server, site, write_site


@pytest.fixture(autouse=True)
def no_downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Stand in for the download cache: each asset is a file holding its own path."""

    def fetch(asset: Asset) -> Path:
        target = tmp_path / "cache" / asset.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(asset.path)
        return target

    monkeypatch.setattr(server, "fetch", fetch)


@pytest.fixture
def app_path(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "views").mkdir(parents=True)
    (root / "app.py").write_text("print('app')\n")
    (root / "views" / "home.py").write_text("")
    (root / "brand.ttf").write_bytes(b"font")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "app.cpython-311.pyc").write_bytes(b"")
    (root / ".venv").mkdir()
    (root / ".venv" / "pyvenv.cfg").write_text("")
    return root / "app.py"


@pytest.fixture
def base_url(app_path: Path) -> Iterator[str]:
    httpd = make_server(site(app_path, bundle_runtime=False), 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def test_bundle_holds_the_app_directory_and_the_framework(app_path: Path) -> None:
    names = set(zipfile.ZipFile(io.BytesIO(build_bundle(app_path))).namelist())

    assert {"app/app.py", "app/views/home.py"} <= names
    assert {"lib/nuiitivet/__init__.py", "lib/nuiitivet/backends/web/skia.py"} <= names
    assert any(name.startswith("lib/materialyoucolor/") for name in names)
    assert not any("__pycache__" in name or ".venv" in name for name in names)


def test_bundle_keeps_the_fonts_of_the_app_and_drops_the_framework_s(app_path: Path) -> None:
    names = zipfile.ZipFile(io.BytesIO(build_bundle(app_path))).namelist()

    assert "app/brand.ttf" in names
    assert not any(name.startswith("lib/") and name.endswith((".ttf", ".otf")) for name in names)


def test_bundle_is_read_again_at_every_request(app_path: Path, base_url: str) -> None:
    (app_path.parent / "added.py").write_text("")
    with urllib.request.urlopen(base_url + "/bundle.zip") as response:
        names = zipfile.ZipFile(io.BytesIO(response.read())).namelist()

    assert "app/added.py" in names


def test_run_serves_the_page_and_loads_the_runtimes_from_a_cdn(base_url: str) -> None:
    with urllib.request.urlopen(base_url + "/") as response:
        assert b'<canvas id="nuiitivet"' in response.read()
    with urllib.request.urlopen(base_url + "/config.json") as response:
        config = json.load(response)

    assert config["entry"] == "app.py"
    assert config["pyodide"].startswith("https://")
    assert config["canvaskit"].startswith("https://")
    for font in config["fonts"]:
        with urllib.request.urlopen(f"{base_url}/{font['url']}") as response:
            assert response.read().decode() == font["url"]


def test_server_refuses_a_path_outside_the_site(base_url: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(base_url + "/app.py")
    assert error.value.code == 404


def test_build_writes_a_site_that_needs_no_other_server(app_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "dist"

    assert main(["build", str(app_path), "-o", str(out)]) == 0

    config = json.loads((out / "config.json").read_text())
    assert (config["pyodide"], config["canvaskit"]) == ("pyodide/", "canvaskit/")
    for name in ("index.html", "boot.mjs", "host.mjs", "bundle.zip", "pyodide/pyodide.mjs", "canvaskit/canvaskit.wasm"):
        assert (out / name).is_file(), name
    for entry in config["fonts"] + config["files"]:
        assert (out / entry["url"]).is_file(), entry["url"]
    assert "app/app.py" in zipfile.ZipFile(out / "bundle.zip").namelist()
    licenses = {path.name for path in (out / "licenses").iterdir()}
    assert {"pyodide-LICENSE.txt", "canvaskit-LICENSE.txt", "noto-sans-jp-LICENSE.txt"} <= licenses
    assert "material-symbols-LICENSE.txt" in licenses


def test_the_page_refers_to_its_files_by_relative_urls(app_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "dist"
    write_site(site(app_path, bundle_runtime=True), out)

    assert 'src="boot.mjs"' in (out / "index.html").read_text()
    boot = (out / "boot.mjs").read_text()
    assert 'from "./host.mjs"' in boot
    assert 'fetch("config.json")' in boot


def test_a_missing_app_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", str(tmp_path / "missing.py"), "--no-open"]) == 2
    assert "app not found" in capsys.readouterr().err


def test_the_runtime_decides_the_target(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_web()
    monkeypatch.setattr("sys.platform", "emscripten")
    assert is_web()
