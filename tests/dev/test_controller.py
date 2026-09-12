"""Tests for the hot-reload controller's journal recording.

The controller's reload sequence touches many collaborators (snapshot, reloader,
app root rebuild/commit, error overlay); these tests patch those out and drive
``_do_reload`` directly to assert that each outcome -- success and both failure
paths -- is recorded into the injected :class:`ReloadJournal`.
"""

from __future__ import annotations

import contextlib
import types
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest import mock

from nuiitivet.dev import controller as controller_mod
from nuiitivet.dev.controller import HotReloadController
from nuiitivet.dev.journal import ReloadJournal
from nuiitivet.dev.reloader import ReloadResult


def _fake_factory() -> Any:
    """A stand-in root factory (typed ``Any`` to satisfy ``RootFactory``)."""
    return object()


class _FakeApp:
    def __init__(self) -> None:
        self.root = object()
        self.invalidated = False
        # The App owns its navigation layers; these tests never build a tree.
        self._navigator = None
        self._overlay = None
        # Stands in for the owning App; tests append fake windows as needed.
        self.app = types.SimpleNamespace(windows=[])

    def _rebuild_content_root(self, factory: Any) -> Any:
        return object()

    def _commit_content_root(self, content: Any) -> None:
        pass

    def invalidate(self) -> None:
        self.invalidated = True


def _make_controller(
    journal: Optional[ReloadJournal], app: Optional[_FakeApp] = None
) -> HotReloadController:
    return HotReloadController(
        app or _FakeApp(),  # type: ignore[arg-type]
        Path("."),
        _fake_factory,
        journal=journal,
    )


@contextlib.contextmanager
def _patched_reload(
    *,
    reload: Any = None,
    reload_side_effect: Any = None,
    restore: Any = 0,
    restore_side_effect: Any = None,
) -> Iterator[None]:
    """Patch the controller's reload collaborators for a single ``_do_reload``.

    ``reload`` / ``reload_side_effect`` control ``reload_user_modules``;
    ``restore`` / ``restore_side_effect`` control ``restore_observables``. The
    error-overlay hooks are stubbed so the tree is never actually touched, and
    the navigation snapshot/restore glue is stubbed so it never reads the
    process-global ``Navigator`` root.
    """
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(controller_mod, "snapshot_observables", return_value={}))
        stack.enter_context(mock.patch.object(controller_mod, "snapshot_navigation", return_value=[]))
        stack.enter_context(mock.patch.object(controller_mod, "restore_navigation", return_value=0))
        stack.enter_context(mock.patch.object(controller_mod, "clear_reload_error"))
        stack.enter_context(mock.patch.object(controller_mod, "show_reload_error"))
        # No real user modules to hash: change detection is exercised separately.
        stack.enter_context(mock.patch.object(controller_mod, "identify_user_modules", return_value={}))
        stack.enter_context(
            mock.patch.object(
                controller_mod,
                "reload_user_modules",
                return_value=reload,
                side_effect=reload_side_effect,
            )
        )
        stack.enter_context(
            mock.patch.object(
                controller_mod,
                "restore_observables",
                return_value=restore,
                side_effect=restore_side_effect,
            )
        )
        yield


def test_successful_reload_records_modules() -> None:
    journal = ReloadJournal()
    controller = _make_controller(journal)
    result = ReloadResult(reloaded=["pkg.a", "pkg.b"], new_factory=_fake_factory)

    with _patched_reload(reload=result):
        controller._do_reload()

    events = journal.recent()
    assert len(events) == 1
    assert events[0].outcome == "success"
    assert events[0].modules == ("pkg.a", "pkg.b")


def _fake_window(win_id: int, *, inert: bool) -> Any:
    """A stand-in secondary window the reload sequence can rebuild."""
    return types.SimpleNamespace(
        id=win_id,
        _hot_reload_inert=inert,
        root=object(),
        _rebuild_content_root=lambda: object(),
        _commit_content_root=lambda content: None,
        invalidate=lambda: None,
    )


def test_successful_reload_records_inert_windows() -> None:
    """Per-window ids, so a mixed factory/instance multi-window app stays legible."""
    journal = ReloadJournal()
    fake_app = _FakeApp()
    fake_app.app.windows = [_fake_window(1, inert=False), _fake_window(2, inert=True)]
    controller = _make_controller(journal, app=fake_app)
    result = ReloadResult(reloaded=["pkg.a"], new_factory=_fake_factory)

    with _patched_reload(reload=result):
        controller._do_reload()

    events = journal.recent()
    assert len(events) == 1
    assert events[0].inert_windows == (2,)


def test_successful_reload_replays_navigation_snapshot() -> None:
    """The nav stack captured before the swap is replayed after the commit."""
    controller = _make_controller(None)
    result = ReloadResult(reloaded=["pkg.a"], new_factory=_fake_factory)
    sentinel = [object(), object()]

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(controller_mod, "snapshot_observables", return_value={}))
        stack.enter_context(mock.patch.object(controller_mod, "clear_reload_error"))
        stack.enter_context(mock.patch.object(controller_mod, "show_reload_error"))
        stack.enter_context(mock.patch.object(controller_mod, "identify_user_modules", return_value={}))
        stack.enter_context(mock.patch.object(controller_mod, "reload_user_modules", return_value=result))
        stack.enter_context(mock.patch.object(controller_mod, "restore_observables", return_value=0))
        stack.enter_context(mock.patch.object(controller_mod, "snapshot_navigation", return_value=sentinel))
        restore = stack.enter_context(mock.patch.object(controller_mod, "restore_navigation", return_value=2))

        controller._do_reload()

    # Replayed against the App, which by then has adopted the new navigator.
    restore.assert_called_once_with(controller._app, sentinel)


def test_failed_reload_records_error_traceback() -> None:
    journal = ReloadJournal()
    controller = _make_controller(journal)

    with _patched_reload(reload_side_effect=ValueError("bad import")):
        controller._do_reload()

    events = journal.recent()
    assert len(events) == 1
    assert events[0].outcome == "error"
    assert events[0].modules == ()
    assert events[0].error is not None
    assert "ValueError: bad import" in events[0].error


def test_failed_commit_records_error() -> None:
    journal = ReloadJournal()
    controller = _make_controller(journal)
    result = ReloadResult(reloaded=["pkg.a"], new_factory=_fake_factory)

    with _patched_reload(reload=result, restore_side_effect=RuntimeError("restore failed")):
        controller._do_reload()

    events = journal.recent()
    assert len(events) == 1
    assert events[0].outcome == "error"
    assert "RuntimeError: restore failed" in (events[0].error or "")


def test_no_journal_is_tolerated() -> None:
    controller = _make_controller(None)
    result = ReloadResult(reloaded=["pkg.a"], new_factory=_fake_factory)

    with _patched_reload(reload=result):
        # Should not raise despite no journal attached.
        controller._do_reload()


def _fake_user_modules(*paths: Path) -> dict[str, Any]:
    """Map ``<stem> -> fake module`` for change-detection tests."""
    return {p.stem: types.SimpleNamespace(__file__=str(p)) for p in paths}


def test_detect_changed_modules_reports_content_changes(tmp_path: Path) -> None:
    file = tmp_path / "widgets.py"
    file.write_text("x = 1\n", encoding="utf-8")
    controller = _make_controller(ReloadJournal())

    with mock.patch.object(
        controller_mod, "identify_user_modules", return_value=_fake_user_modules(file)
    ):
        # First detection seeds the baseline: everything looks new.
        assert controller._detect_changed_modules() == ["widgets"]
        # No content change -> no-op even though we detect again.
        assert controller._detect_changed_modules() == []
        # Real content change -> reported.
        file.write_text("x = 2\n", encoding="utf-8")
        assert controller._detect_changed_modules() == ["widgets"]


def test_detect_changed_modules_ignores_no_op_save(tmp_path: Path) -> None:
    file = tmp_path / "app.py"
    file.write_text("y = 0\n", encoding="utf-8")
    controller = _make_controller(ReloadJournal())

    with mock.patch.object(
        controller_mod, "identify_user_modules", return_value=_fake_user_modules(file)
    ):
        controller._detect_changed_modules()  # seed
        # Rewrite identical bytes (a no-op save bumps mtime but not content).
        file.write_text("y = 0\n", encoding="utf-8")
        assert controller._detect_changed_modules() == []


def test_successful_reload_records_changed_subset(tmp_path: Path) -> None:
    file = tmp_path / "hot.py"
    file.write_text("v = 1\n", encoding="utf-8")
    journal = ReloadJournal()
    controller = _make_controller(journal)
    result = ReloadResult(reloaded=["hot", "helper"], new_factory=_fake_factory)

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(controller_mod, "snapshot_observables", return_value={}))
        stack.enter_context(mock.patch.object(controller_mod, "restore_observables", return_value=0))
        stack.enter_context(mock.patch.object(controller_mod, "clear_reload_error"))
        stack.enter_context(
            mock.patch.object(controller_mod, "reload_user_modules", return_value=result)
        )
        stack.enter_context(
            mock.patch.object(
                controller_mod, "identify_user_modules", return_value=_fake_user_modules(file)
            )
        )
        controller._do_reload()  # first: seeds + reports "hot" changed
        file.write_text("v = 2\n", encoding="utf-8")
        controller._do_reload()  # second: "hot" changed again

    events = journal.recent()
    assert len(events) == 2
    # All modules reloaded, but only the edited file is reported as changed.
    assert events[-1].modules == ("hot", "helper")
    assert events[-1].changed == ("hot",)


# --- layout mode's edits --------------------------------------------------------


class _FakeEdits:
    """Stands in for the edit log: records which outcome the controller reported."""

    def __init__(self) -> None:
        self.landed: list[list[Any]] = []
        self.failed: list[str] = []

    def after_reload(self, roots: Any) -> None:
        self.landed.append(list(roots))

    def reload_failed(self, traceback_text: str) -> None:
        self.failed.append(traceback_text)


def test_a_successful_reload_lets_the_pending_edit_check_every_window() -> None:
    app = _FakeApp()
    second = _fake_window(2, inert=False)
    app.app.windows = [app, second]
    edits = _FakeEdits()
    controller = HotReloadController(app, Path("."), _fake_factory, edits=edits)  # type: ignore[arg-type]

    with _patched_reload(reload=ReloadResult(reloaded=["pkg"], new_factory=_fake_factory)):
        controller._do_reload()

    assert edits.landed == [[app.root, second.root]]
    assert edits.failed == []


def test_a_failed_reload_is_reported_to_the_pending_edit() -> None:
    edits = _FakeEdits()
    controller = HotReloadController(_FakeApp(), Path("."), _fake_factory, edits=edits)  # type: ignore[arg-type]

    with _patched_reload(reload_side_effect=SyntaxError("bad edit")):
        controller._do_reload()

    assert edits.landed == []
    assert len(edits.failed) == 1 and "bad edit" in edits.failed[0]


def test_request_reload_sets_the_flag_and_acknowledges_the_file(tmp_path: Path) -> None:
    """A file the runner wrote itself must not reload twice: once on request,
    once more when the watcher notices the mtime."""
    file = tmp_path / "app.py"
    file.write_text("v = 1\n", encoding="utf-8")
    controller = _make_controller(None)

    controller.request_reload(str(file))

    assert controller._pending.is_set()
    assert controller._watcher._mtimes[file] == file.stat().st_mtime
