"""A widget-instance root makes hot reload inert; the Window says so.

The wrapping ``lambda: instance`` returns the same object on every rebuild, so
no edit can ever reach that window's tree. The fact is settled in
``Window.__init__`` and surfaced there: a ``_hot_reload_inert`` flag the reload
path reports per window, and one WARNING under the dev runner -- production
constructs silently.
"""

from __future__ import annotations

import logging
from typing import Iterator

import pytest

from nuiitivet.dev.session import DevSession, set_dev_session
from nuiitivet.layout.container import Container
from nuiitivet.runtime.window import Window


@pytest.fixture
def dev_session() -> Iterator[None]:
    set_dev_session(DevSession())
    try:
        yield
    finally:
        set_dev_session(None)


def test_factory_root_is_not_inert() -> None:
    assert Window(content=Container)._hot_reload_inert is False
    assert Window(content=lambda: Container())._hot_reload_inert is False


def test_instance_root_is_inert() -> None:
    assert Window(content=Container())._hot_reload_inert is True


def test_instance_root_warns_under_dev_session(
    dev_session: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="nuiitivet.runtime.window"):
        window = Window(content=Container())

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert f"Window id={window.id}" in warnings[0]
    assert "Container" in warnings[0]
    assert "hot reload" in warnings[0]


def test_instance_root_is_silent_without_dev_session(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="nuiitivet.runtime.window"):
        Window(content=Container())

    assert not caplog.records


def test_factory_root_is_silent_under_dev_session(
    dev_session: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="nuiitivet.runtime.window"):
        Window(content=Container)

    assert not caplog.records
