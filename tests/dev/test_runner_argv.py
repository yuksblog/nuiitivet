"""The dev runner hands the app an argv of its own, not the runner's.

An entry that calls ``argparse.ArgumentParser().parse_args()`` used to die on
the runner's own command line before a window could open.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

import pytest

from nuiitivet.dev import source
from nuiitivet.dev.__main__ import _parse_args, _run
from nuiitivet.dev.session import set_dev_session

# What the generated app writes out: the argv at import time and inside the
# entry. The entry never calls App.run(), so ``_run`` reports a missing hand-off
# and returns 1 without opening a window.
_APP_SOURCE = """
import json
import sys

IMPORT_ARGV = list(sys.argv)


def main():
    from pathlib import Path

    Path(RECORD).write_text(
        json.dumps({"import": IMPORT_ARGV, "entry": list(sys.argv)})
    )
"""


@pytest.fixture
def isolated_runner() -> Iterator[None]:
    """Undo the process-wide state ``_run`` installs."""
    saved_argv = list(sys.argv)
    saved_path = list(sys.path)
    saved_modules = set(sys.modules)
    try:
        yield
    finally:
        set_dev_session(None)
        source.uninstall()
        sys.argv[:] = saved_argv
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_modules:
            del sys.modules[name]


def _write_app(tmp_path: Path, name: str) -> tuple[Path, Path]:
    record = tmp_path / f"{name}.json"
    app = tmp_path / f"{name}.py"
    app.write_text(f"RECORD = {str(record)!r}\n{_APP_SOURCE}")
    return app, record


def _drive(app: Path, *extra: str) -> dict[str, list[str]]:
    """Run ``app`` through the runner and return the argv it observed."""
    args = _parse_args(["run", str(app), *extra])
    assert _run(args) == 1  # the app deliberately never calls App.run()
    record = app.with_suffix(".json")
    return json.loads(record.read_text())


@pytest.mark.usefixtures("isolated_runner")
def test_entry_sees_the_app_path_not_the_runner(tmp_path: Path) -> None:
    app, _ = _write_app(tmp_path, "plain_app")
    sys.argv = ["/somewhere/nuiitivet/dev/__main__.py", "run", str(app)]

    seen = _drive(app)

    assert seen["entry"] == [str(app)]


@pytest.mark.usefixtures("isolated_runner")
def test_import_time_argv_is_already_the_app_s(tmp_path: Path) -> None:
    # A module that parses arguments at import time needs the swap to land
    # before the import, not just before the entry call.
    app, _ = _write_app(tmp_path, "import_time_app")
    sys.argv = ["/somewhere/nuiitivet/dev/__main__.py", "run", str(app)]

    seen = _drive(app)

    assert seen["import"] == [str(app)]


@pytest.mark.usefixtures("isolated_runner")
def test_pass_through_args_reach_the_app(tmp_path: Path) -> None:
    app, _ = _write_app(tmp_path, "args_app")
    args = _parse_args(["run", str(app), "--", "--png", "out.png"])

    assert _run(args) == 1
    seen = json.loads(app.with_suffix(".json").read_text())

    assert seen["entry"] == [str(app), "--png", "out.png"]


@pytest.mark.usefixtures("isolated_runner")
def test_argv_stays_the_app_s_after_the_entry_returns(tmp_path: Path) -> None:
    # Not restored on purpose: hot reload re-imports user modules, so handing
    # the runner's argv back would break a module that parses it at import.
    app, _ = _write_app(tmp_path, "persist_app")
    sys.argv = ["/somewhere/nuiitivet/dev/__main__.py", "run", str(app)]

    _drive(app)

    assert sys.argv == [str(app)]


@pytest.mark.usefixtures("isolated_runner")
def test_relative_target_becomes_an_absolute_path(tmp_path: Path, monkeypatch) -> None:
    app, _ = _write_app(tmp_path, "relative_app")
    monkeypatch.chdir(tmp_path)

    seen = _drive(Path("relative_app.py"))

    assert seen["entry"] == [str(app)]
