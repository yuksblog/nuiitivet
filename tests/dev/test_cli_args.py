"""Tests for the ``python -m nuiitivet.dev`` subcommand argument parsing."""

from __future__ import annotations

from nuiitivet.dev.__main__ import _parse_args


def test_bare_target_defaults_to_run() -> None:
    args = _parse_args(["app.py"])
    assert args.command == "run"
    assert args.target == "app.py"
    assert args.module is False


def test_explicit_run_subcommand() -> None:
    args = _parse_args(["run", "--module", "pkg.app"])
    assert args.command == "run"
    assert args.target == "pkg.app"
    assert args.module is True


def test_screenshot_subcommand() -> None:
    args = _parse_args(["screenshot", "-o", "out.png"])
    assert args.command == "screenshot"
    assert args.output == "out.png"


def test_screenshot_default_output() -> None:
    args = _parse_args(["screenshot"])
    assert args.command == "screenshot"
    assert args.output == "screenshot.png"


def test_describe_tree_subcommand() -> None:
    args = _parse_args(["describe-tree"])
    assert args.command == "describe-tree"
