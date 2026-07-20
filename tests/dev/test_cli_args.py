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


def test_describe_state_subcommand() -> None:
    args = _parse_args(["describe-state"])
    assert args.command == "describe-state"


def test_reload_log_subcommand_defaults_to_all() -> None:
    args = _parse_args(["reload-log"])
    assert args.command == "reload-log"
    assert args.limit is None


def test_reload_log_subcommand_accepts_limit() -> None:
    args = _parse_args(["reload-log", "--limit", "5"])
    assert args.command == "reload-log"
    assert args.limit == 5


def test_interaction_log_subcommand_defaults_to_all() -> None:
    args = _parse_args(["interaction-log"])
    assert args.command == "interaction-log"
    assert args.limit is None


def test_interaction_log_subcommand_accepts_limit() -> None:
    args = _parse_args(["interaction-log", "--limit", "5"])
    assert args.command == "interaction-log"
    assert args.limit == 5


def test_runtime_log_subcommand_defaults() -> None:
    args = _parse_args(["runtime-log"])
    assert args.command == "runtime-log"
    assert args.limit is None
    assert args.verbose is None


def test_runtime_log_subcommand_accepts_limit() -> None:
    args = _parse_args(["runtime-log", "--limit", "5"])
    assert args.command == "runtime-log"
    assert args.limit == 5


def test_runtime_log_subcommand_accepts_verbose() -> None:
    args = _parse_args(["runtime-log", "--verbose", "on"])
    assert args.command == "runtime-log"
    assert args.verbose == "on"


def test_click_by_label() -> None:
    args = _parse_args(["click", "--label", "increment"])
    assert args.command == "click"
    assert args.label == "increment"
    assert args.key is None
    assert args.xy is None


def test_click_by_key() -> None:
    args = _parse_args(["click", "--key", "submit"])
    assert args.command == "click"
    assert args.key == "submit"


def test_click_by_xy() -> None:
    args = _parse_args(["click", "--xy", "10", "20"])
    assert args.command == "click"
    assert args.xy == [10.0, 20.0]


def test_click_targets_are_mutually_exclusive() -> None:
    import pytest

    with pytest.raises(SystemExit):
        _parse_args(["click", "--key", "a", "--label", "b"])


def test_click_requires_a_target() -> None:
    import pytest

    with pytest.raises(SystemExit):
        _parse_args(["click"])


def test_type_subcommand() -> None:
    args = _parse_args(["type", "hello world"])
    assert args.command == "type"
    assert args.text == "hello world"


def test_key_subcommand_with_modifiers() -> None:
    args = _parse_args(["key", "enter", "--mod", "accel", "--mod", "shift"])
    assert args.command == "key"
    assert args.name == "enter"
    assert args.mod == ["accel", "shift"]


def test_key_subcommand_defaults_no_modifiers() -> None:
    args = _parse_args(["key", "tab"])
    assert args.command == "key"
    assert args.mod == []


def test_wait_for_subcommand_by_label() -> None:
    args = _parse_args(["wait-for", "--label", "Done"])
    assert args.command == "wait-for"
    assert args.label == "Done"
    assert args.key is None
    assert args.text is None
    assert args.absent is False
    assert args.timeout is None


def test_wait_for_subcommand_absent_and_timeout() -> None:
    args = _parse_args(["wait-for", "--key", "spinner", "--absent", "--timeout", "5"])
    assert args.command == "wait-for"
    assert args.key == "spinner"
    assert args.absent is True
    assert args.timeout == 5.0


def test_mcp_subcommand() -> None:
    args = _parse_args(["mcp"])
    assert args.command == "mcp"
