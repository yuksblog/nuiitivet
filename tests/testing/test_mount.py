"""``mount()`` and its host: the contract a single-widget test runs against."""

from __future__ import annotations

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.material.text import Text
from nuiitivet.widgeting.widget import Widget
from nuiitivet.observable import Observable
from nuiitivet.testing import StaleNodeError, TargetNotFoundError, mount
from nuiitivet.theme.plain_theme import PlainTheme
from nuiitivet.theme.theme import Theme


def _text(value: object, key: str) -> Widget:
    """A keyed Text."""
    return Text(value, key=key)  # type: ignore[arg-type]


def test_layout_then_query() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        assert host.get(key="greeting").text == "hello"


def test_settle_before_layout_names_layout() -> None:
    with mount(_text("hello", "greeting")) as host:
        with pytest.raises(RuntimeError, match=r"host\.layout\(width, height\)"):
            host.settle()


def test_state_change_becomes_observable_after_settle() -> None:
    label = Observable("before")
    with mount(_text(label, "greeting")) as host:
        host.layout(200, 50)
        label.value = "after"
        host.settle()
        assert host.get(key="greeting").text == "after"


def test_unmounts_on_exit() -> None:
    widget = _text("hello", "greeting")
    with mount(widget) as host:
        host.layout(200, 50)
    assert widget._unmounted is True


def test_closed_host_refuses_queries() -> None:
    host = mount(_text("hello", "greeting"))
    host.layout(200, 50)
    host.close()
    with pytest.raises(RuntimeError, match="is closed"):
        host.settle()


def test_close_is_idempotent() -> None:
    host = mount(_text("hello", "greeting"))
    host.layout(200, 50)
    host.close()
    host.close()


# -- the theme half --------------------------------------------------------


class _ThemeProbe(Text):
    """Reports the theme it resolved, which is what the scope has to serve."""

    def __init__(self) -> None:
        super().__init__("probe")
        self.seen_modes: list[str] = []

    def on_mount(self) -> None:  # type: ignore[override]
        super().on_mount()
        self.seen_modes.append(Theme.of(self).mode)


def test_default_mount_serves_a_theme() -> None:
    probe = _ThemeProbe()
    with mount(probe) as host:
        host.layout(200, 50)
        assert probe.seen_modes == ["light"]
        assert host.theme_manager.current.mode == "light"


def test_explicit_theme_is_the_one_resolved() -> None:
    probe = _ThemeProbe()
    with mount(probe, theme=PlainTheme.dark()) as host:
        host.layout(200, 50)
        assert probe.seen_modes == ["dark"]


def test_push_theme_is_followed_after_mount() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        assert host.theme_manager.current.mode == "light"
        host.push_theme(PlainTheme.dark())
        assert host.theme_manager.current.mode == "dark"


def test_scope_false_mounts_bare() -> None:
    probe = _ThemeProbe()
    with mount(probe, scope=False) as host:
        host.layout(200, 50)
        # No AppScope: Theme.of falls back, deliberately, and this is the only
        # way a test asks for that rather than getting it by accident.
        assert host.root is probe


def test_theme_with_scope_false_is_a_contradiction() -> None:
    with pytest.raises(ValueError, match="contradict"):
        mount(_text("x", "x"), theme=PlainTheme.dark(), scope=False)


# -- the host contract -----------------------------------------------------


def test_invalidate_takes_the_full_signature() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        before = host.invalidate_count
        host.invalidate()
        host.invalidate(immediate=True)
        host.invalidate(immediate=False, content=False)
        assert host.invalidate_count == before + 3
        assert host.invalidations[-1].content is False
        assert host.invalidations[-2].immediate is True


def test_settle_does_not_request_a_repaint() -> None:
    """A caller counting repaints must not be counting settle's own."""
    label = Observable("before")
    with mount(_text(label, "greeting")) as host:
        host.layout(200, 50)
        before = host.invalidate_count
        host.settle()
        assert host.invalidate_count == before


# -- queries ---------------------------------------------------------------


def test_get_reports_what_was_available() -> None:
    with mount(Column(children=[_text("hello", "greeting")])) as host:
        host.layout(200, 50)
        with pytest.raises(TargetNotFoundError) as excinfo:
            host.get(key="nope")
        message = str(excinfo.value)
        assert "key='greeting'" in message
        assert "label='hello'" in message


def test_get_refuses_more_than_one() -> None:
    with mount(Column(children=[_text("dup", "a"), _text("dup", "b")])) as host:
        host.layout(200, 100)
        with pytest.raises(TargetNotFoundError, match="matched 2 widgets"):
            host.get(label="dup")


def test_query_returns_none_but_still_refuses_ambiguity() -> None:
    with mount(Column(children=[_text("dup", "a"), _text("dup", "b")])) as host:
        host.layout(200, 100)
        assert host.query(key="absent") is None
        with pytest.raises(TargetNotFoundError):
            host.query(label="dup")


def test_get_all_counts() -> None:
    with mount(Column(children=[_text("dup", "a"), _text("dup", "b")])) as host:
        host.layout(200, 100)
        assert len(host.get_all(label="dup")) == 2
        assert host.get_all(key="absent") == []


def test_key_and_label_together_is_refused() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        with pytest.raises(TypeError, match="not both"):
            host.get(key="greeting", label="hello")


def test_no_identifier_is_refused() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        with pytest.raises(TypeError, match="key= or label="):
            host.get()


def test_tree_is_a_dict_dump() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        dump = host.tree()
        assert isinstance(dump, dict)
        assert "type" in dump


# -- Node ------------------------------------------------------------------


def test_node_is_a_snapshot_and_goes_stale() -> None:
    widget = _text("hello", "greeting")
    with mount(widget) as host:
        host.layout(200, 50)
        node = host.get(key="greeting")
        assert node.key == "greeting"
        widget.unmount()
        with pytest.raises(StaleNodeError, match="re-query"):
            _ = node.text


def test_node_rect_is_captured_at_query_time() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        node = host.get(key="greeting")
        rect = node.rect
        host.layout(400, 100)
        assert node.rect == rect


def test_node_repr_is_readable() -> None:
    with mount(_text("hello", "greeting")) as host:
        host.layout(200, 50)
        assert "key='greeting'" in repr(host.get(key="greeting"))
