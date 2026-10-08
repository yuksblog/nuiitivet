"""What the page gets for its ``@worker`` functions: the scripts, and the modules the worker imports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nuiitivet.web import server
from nuiitivet.web.assets import Asset
from nuiitivet.web.server import read, site
from nuiitivet.web.stubs import worker_modules

_JOBS = "import nuiitivet.material as nv\n\n\n@nv.worker\ndef count(limit: int) -> int:\n    return limit\n"
_BACKEND = "import nuiitivet.material as nv\n\nnv.server_only()\n\n\n@nv.worker\ndef wrong() -> None:\n    pass\n"


@pytest.fixture(autouse=True)
def no_downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fetch(asset: Asset) -> Path:
        target = tmp_path / "cache" / asset.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(asset.path)
        return target

    monkeypatch.setattr(server, "fetch", fetch)


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "work").mkdir(parents=True)
    (root / "app.py").write_text("from jobs import count\n")
    (root / "jobs.py").write_text(_JOBS)
    (root / "work" / "__init__.py").write_text("")
    (root / "work" / "more.py").write_text(_JOBS)
    (root / "backend.py").write_text(_BACKEND)
    (root / "views.py").write_text("def worker() -> None:\n    pass\n")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "jobs.py").write_text(_JOBS)
    return root


def test_the_modules_with_a_worker_function_are_listed_dotted(app_dir: Path) -> None:
    assert worker_modules(app_dir) == ["jobs", "work.more"]


def test_a_server_only_module_is_not_a_worker_module(app_dir: Path) -> None:
    assert "backend" not in worker_modules(app_dir)


def test_the_page_names_the_worker_modules_and_carries_the_scripts(app_dir: Path) -> None:
    files = site(app_dir / "app.py", bundle_runtime=False)

    assert json.loads(read(files["config.json"]))["workers"] == ["jobs", "work.more"]
    assert b"loadPyodide" in read(files["worker.mjs"])
    assert b"NV_WORKERS" in read(files["workers.mjs"])


def test_an_app_without_a_worker_function_names_none(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("")

    assert json.loads(read(site(tmp_path / "app.py", bundle_runtime=False)["config.json"]))["workers"] == []
