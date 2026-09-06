"""Tests for the ``python -m nuiitivet.dev`` subcommand argument parsing."""

from __future__ import annotations

import pytest

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
    assert (args.key, args.label, args.rect, args.padding) == (None, None, None, None)


def test_screenshot_scoped_by_key_with_padding() -> None:
    args = _parse_args(["screenshot", "--key", "save", "--padding", "0"])
    assert args.key == "save"
    assert args.padding == 0.0


def test_screenshot_scoped_by_rect() -> None:
    args = _parse_args(["screenshot", "--rect", "10", "20", "30", "40"])
    assert args.rect == [10.0, 20.0, 30.0, 40.0]


def test_screenshot_scopes_are_exclusive() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["screenshot", "--key", "a", "--label", "b"])


def test_status_subcommand() -> None:
    args = _parse_args(["status"])
    assert args.command == "status"


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


def test_scroll_by_key_with_deltas() -> None:
    args = _parse_args(["scroll", "--key", "feed", "--dy", "5"])
    assert args.command == "scroll"
    assert args.key == "feed"
    assert (args.dx, args.dy) == (0.0, 5.0)


def test_scroll_by_xy() -> None:
    args = _parse_args(["scroll", "--xy", "10", "20", "--dx", "-2"])
    assert args.command == "scroll"
    assert args.xy == [10.0, 20.0]
    assert args.dx == -2.0


def test_scroll_requires_a_target() -> None:
    import pytest

    with pytest.raises(SystemExit):
        _parse_args(["scroll", "--dy", "5"])


def test_scroll_into_view_subcommand() -> None:
    args = _parse_args(["scroll-into-view", "--key", "row-42"])
    assert args.command == "scroll-into-view"
    assert args.key == "row-42"
    assert args.align == "nearest"


def test_scroll_into_view_accepts_an_alignment() -> None:
    args = _parse_args(["scroll-into-view", "--label", "Done", "--align", "center"])
    assert args.align == "center"


def test_scroll_into_view_rejects_an_unknown_alignment() -> None:
    import pytest

    with pytest.raises(SystemExit):
        _parse_args(["scroll-into-view", "--key", "a", "--align", "sideways"])


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


def test_run_without_separator_has_no_app_args() -> None:
    args = _parse_args(["run", "app.py"])
    assert args.app_args == []


def test_run_passes_through_args_after_separator() -> None:
    args = _parse_args(["run", "app.py", "--", "--png", "out.png"])
    assert args.target == "app.py"
    assert args.app_args == ["--png", "out.png"]


def test_bare_target_passes_through_args_after_separator() -> None:
    args = _parse_args(["app.py", "--", "--png", "out.png"])
    assert args.command == "run"
    assert args.target == "app.py"
    assert args.app_args == ["--png", "out.png"]


def test_separator_keeps_runner_flags_out_of_the_runner() -> None:
    # '--entry' after the separator belongs to the app, not to the runner.
    args = _parse_args(["run", "app.py", "--entry", "start", "--", "--entry", "other"])
    assert args.entry == "start"
    assert args.app_args == ["--entry", "other"]


def test_only_the_first_separator_splits() -> None:
    args = _parse_args(["run", "app.py", "--", "--flag", "--", "tail"])
    assert args.app_args == ["--flag", "--", "tail"]


def test_separator_with_no_trailing_args() -> None:
    args = _parse_args(["run", "app.py", "--"])
    assert args.target == "app.py"
    assert args.app_args == []


def test_other_subcommands_leave_the_separator_to_argparse() -> None:
    # Not a 'run', so '--' keeps its plain end-of-options meaning.
    args = _parse_args(["type", "--", "--hello"])
    assert args.command == "type"
    assert args.text == "--hello"


# --- --window -----------------------------------------------------------
#
# Every window-addressed subcommand takes the ids that 'status' lists, so a
# secondary window is reachable from the CLI and not only from MCP.

_WINDOW_SUBCOMMANDS = [
    ["describe-tree"],
    ["describe-state"],
    ["screenshot"],
    ["click", "--key", "a"],
    ["scroll", "--key", "a", "--dy", "1"],
    ["scroll-into-view", "--key", "a"],
    ["type", "hello"],
    ["key", "enter"],
    ["wait-for", "--label", "Done"],
]


def test_window_defaults_to_the_main_window() -> None:
    for argv in _WINDOW_SUBCOMMANDS:
        args = _parse_args(argv)
        assert args.window is None, argv


def test_window_selects_an_open_window_by_id() -> None:
    for argv in _WINDOW_SUBCOMMANDS:
        args = _parse_args([*argv, "--window", "2"])
        assert args.window == 2, argv


def test_window_rejects_a_non_numeric_id() -> None:
    import pytest

    with pytest.raises(SystemExit):
        _parse_args(["describe-tree", "--window", "palette"])
