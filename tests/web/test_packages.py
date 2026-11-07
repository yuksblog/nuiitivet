"""The page loads the Pyodide packages the app's imports name, and nothing it does not."""

from pathlib import Path
from typing import Any

from nuiitivet.web.packages import imported_names, resolve


def _entry(name: str, *, depends: list[str], imports: list[str]) -> dict[str, Any]:
    return {"name": name, "file_name": f"{name}-wasm32.whl", "sha256": "ab", "depends": depends, "imports": imports}


LOCK: dict[str, Any] = {
    "packages": {
        "matplotlib": _entry("matplotlib", depends=["numpy", "cycler"], imports=["mpl_toolkits", "matplotlib"]),
        "numpy": _entry("numpy", depends=[], imports=["numpy"]),
        "cycler": _entry("cycler", depends=[], imports=["cycler"]),
        "pillow": _entry("pillow", depends=[], imports=["PIL"]),
    }
}


def test_imports_outside_the_standard_library_and_the_app_are_found(tmp_path: Path) -> None:
    (tmp_path / "views").mkdir()
    (tmp_path / "app.py").write_text(
        "import json\nimport numpy as np\nfrom matplotlib.figure import Figure\nimport views.home\nimport helpers\n"
        "def f():\n    from PIL import Image\n"
    )
    (tmp_path / "views" / "home.py").write_text("from . import x\nimport nuiitivet.material as nv\n")
    (tmp_path / "helpers.py").write_text("import js\n")

    assert imported_names(tmp_path) == {"numpy", "matplotlib", "PIL"}


def test_what_a_server_only_module_imports_stays_on_the_server(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("import numpy\n")
    (tmp_path / "db.py").write_text("import nuiitivet.material as nv\nimport psycopg\n\nnv.server_only()\n")

    assert imported_names(tmp_path) == {"numpy"}


def test_a_package_comes_with_what_it_depends_on() -> None:
    names = [entry["name"] for entry in resolve(LOCK, {"matplotlib"})]

    assert names == ["cycler", "matplotlib", "numpy"]


def test_an_import_name_resolves_to_its_package() -> None:
    names = [entry["name"] for entry in resolve(LOCK, {"PIL", "mpl_toolkits"})]

    assert names == ["cycler", "matplotlib", "numpy", "pillow"]


def test_a_name_no_package_provides_is_left_out() -> None:
    assert resolve(LOCK, {"requests"}) == []
