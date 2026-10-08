"""What the page gets in place of the server-only modules, and which modules the server imports."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from nuiitivet.web.stubs import ServerOnly, server_modules, stub_source
from nuiitivet.web.server import build_bundle

_BACKEND_INIT = "import nuiitivet.material as nv\n\nnv.server_only()\n"
_JOBS = "import nuiitivet.material as nv\n\n\n@nv.server\ndef count(limit: int) -> int:\n    return limit\n"
_ORDERS = '''\
from __future__ import annotations

import os
import nuiitivet.material as nv
from models import Order
from .db import connect

SECRET = os.environ["SECRET"]


@nv.server
def load_orders(
    user_id: int, progress: nv.WriteOnlyObservable[float], cancel: nv.CancelToken = nv.CancelToken()
) -> list[Order]:
    return connect(SECRET).query(user_id)


def helper() -> None:
    pass
'''


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "backend" / "db").mkdir(parents=True)
    (root / "app.py").write_text("import backend.orders\n")
    (root / "models.py").write_text("from dataclasses import dataclass\n\n\n@dataclass\nclass Order:\n    id: int\n")
    (root / "backend" / "__init__.py").write_text(_BACKEND_INIT)
    (root / "backend" / "orders.py").write_text(_ORDERS)
    (root / "backend" / "db" / "__init__.py").write_text("")
    (root / "backend" / "db" / "config.toml").write_text("url = 'postgres://...'\n")
    (root / "keys.py").write_text("from nuiitivet import server_only\n\nserver_only()\n\nKEY = 'x'\n")
    (root / "jobs.py").write_text(_JOBS)
    (root / "views.py").write_text("")
    return root


def test_a_package_with_the_call_in_its_init_is_covered_whole(app_dir: Path) -> None:
    server_only = ServerOnly(app_dir)

    assert server_only.covers(app_dir / "backend" / "__init__.py")
    assert server_only.covers(app_dir / "backend" / "orders.py")
    assert server_only.covers(app_dir / "backend" / "db" / "config.toml")
    assert server_only.covers(app_dir / "keys.py")
    assert not server_only.covers(app_dir / "app.py")
    assert not server_only.covers(app_dir / "models.py")


def test_the_modules_with_a_server_function_are_listed_for_import(app_dir: Path) -> None:
    assert server_modules(app_dir) == ["backend.orders", "jobs"]


def test_a_stub_keeps_the_signature_and_the_imports_it_needs(app_dir: Path) -> None:
    source = stub_source(app_dir / "backend" / "orders.py", "backend.orders")

    assert source == (
        "from __future__ import annotations\n"
        "from nuiitivet.remote.function import stub as _stub\n"
        "import nuiitivet.material as nv\n"
        "from models import Order\n"
        "\n"
        "\n"
        "@_stub\n"
        "def load_orders(user_id: int, progress: nv.WriteOnlyObservable[float], "
        "cancel: nv.CancelToken=nv.CancelToken()) -> list[Order]:\n"
        "    ...\n"
    )


def test_a_module_without_a_server_function_gets_no_stub(app_dir: Path) -> None:
    assert stub_source(app_dir / "keys.py", "keys") is None


def test_the_stubs_cover_each_package_init_and_each_module_with_a_function(app_dir: Path) -> None:
    stubs = dict(ServerOnly(app_dir).stubs())

    assert set(stubs) == {"backend/__init__.py", "backend/orders.py", "backend/db/__init__.py"}
    assert stubs["backend/__init__.py"] == ""


def test_a_type_the_module_defines_itself_is_refused(app_dir: Path) -> None:
    path = app_dir / "backend" / "orders.py"
    path.write_text(
        "import nuiitivet.material as nv\n"
        "class Row: ...\n"
        "@nv.server\n"
        "def rows() -> list[Row]: ...\n"
    )

    with pytest.raises(RuntimeError, match="backend.orders.rows: Row is not imported"):
        stub_source(path, "backend.orders")


def test_the_bundle_carries_the_stubs_and_nothing_server_only(app_dir: Path) -> None:
    archive = zipfile.ZipFile(io.BytesIO(build_bundle(app_dir / "app.py")))
    names = {name for name in archive.namelist() if name.startswith("app/")}

    assert names == {"app/app.py", "app/jobs.py", "app/models.py", "app/views.py", "app/backend/__init__.py",
                     "app/backend/orders.py", "app/backend/db/__init__.py"}
    orders = archive.read("app/backend/orders.py").decode()
    assert "SECRET" not in orders
    assert "connect" not in orders
    assert "@_stub" in orders


def test_a_server_function_in_a_plain_module_ships_as_written(app_dir: Path) -> None:
    archive = zipfile.ZipFile(io.BytesIO(build_bundle(app_dir / "app.py")))

    assert archive.read("app/jobs.py").decode() == _JOBS
