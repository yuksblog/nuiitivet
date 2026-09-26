"""Intent-shown dialogs survive a hot reload; widget-shown ones close."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

import pytest

from nuiitivet.dev.overlay_snapshot import restore_overlay, snapshot_overlay
from nuiitivet.layout.container import Container
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.window import MaterialWindow
from nuiitivet.overlay.intent_resolver import MappingIntentResolver
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _Card(Widget):
    def __init__(self, version: int, text: str) -> None:
        super().__init__()
        self.version = version
        self.text = text

    def build(self) -> Widget:
        return self


def _intent_class(name: str) -> type[Any]:
    """A fresh class with a fixed qualified name, as a reload redefines one."""

    @dataclass(frozen=True)
    class _Intent:
        text: str

    _Intent.__qualname__ = name
    _Intent.__name__ = name
    return _Intent


def _overlay_factory(version: int, *intent_types: type[Any]) -> Callable[[], MaterialOverlay]:
    def build() -> MaterialOverlay:
        return MaterialOverlay(intents={tp: (lambda i: _Card(version, i.text)) for tp in intent_types})

    return build


def _window(overlay: Callable[[], MaterialOverlay]) -> Window:
    return App(MaterialWindow(content=Container, overlay=overlay)).main_window


def _reload(window: Window, overlay: Callable[[], MaterialOverlay]) -> int:
    """Replay the controller's order: rebuild, snapshot, commit, restore."""
    window._overlay_factory = overlay
    content = window._rebuild_content_root()
    records = snapshot_overlay(window)
    window._commit_content_root(content)
    return restore_overlay(window, records)


def _cards(window: Window) -> list[tuple[int, str]]:
    return [(e.content.version, e.content.text) for e in window.overlay.open_entries]  # type: ignore[union-attr]


def test_an_intent_dialog_stays_open_with_the_edited_content() -> None:
    ask = _intent_class("Ask")
    window = _window(_overlay_factory(1, ask))
    window.overlay.dialog(ask("hello"))  # type: ignore[attr-defined]

    assert _reload(window, _overlay_factory(2, _intent_class("Ask"))) == 1

    assert _cards(window) == [(2, "hello")]


async def test_an_await_started_before_the_reload_gets_the_value_chosen_after() -> None:
    ask = _intent_class("Ask")
    window = _window(_overlay_factory(1, ask))
    handle = window.overlay.dialog(ask("hello"))  # type: ignore[attr-defined]

    async def wait() -> Any:
        return await handle

    task = asyncio.ensure_future(wait())
    await asyncio.sleep(0)
    _reload(window, _overlay_factory(2, _intent_class("Ask")))
    window.overlay.close("yes")

    result = await task
    assert result.value == "yes"
    assert result.reason is OverlayDismissReason.CLOSED


def test_the_handle_closes_the_re_shown_dialog() -> None:
    ask = _intent_class("Ask")
    window = _window(_overlay_factory(1, ask))
    handle = window.overlay.dialog(ask("hello"))  # type: ignore[attr-defined]
    _reload(window, _overlay_factory(2, _intent_class("Ask")))

    handle.close("done")

    assert window.overlay._top_entry() is None
    assert handle.done()
    result = handle.result()
    assert result is not None and result.value == "done"


def test_a_widget_dialog_closes_on_reload() -> None:
    window = _window(_overlay_factory(1))
    handle = window.overlay.dialog(_Card(1, "widget"))  # type: ignore[attr-defined]

    assert _reload(window, _overlay_factory(2)) == 0

    assert window.overlay.open_entries == ()
    result = handle.result()
    assert result is not None and result.reason is OverlayDismissReason.DISPOSED


def test_an_instance_overlay_closes_widget_dialogs_and_re_shows_intent_ones() -> None:
    ask = _intent_class("Ask")
    overlay = _overlay_factory(1, ask)()
    window = App(MaterialWindow(content=Container, overlay=overlay)).main_window
    shown = overlay.dialog(ask("kept"))
    closed = overlay.dialog(_Card(1, "widget"))

    content = window._rebuild_content_root()
    records = snapshot_overlay(window)
    window._commit_content_root(content)
    assert restore_overlay(window, records) == 1

    assert window.overlay is overlay
    assert _cards(window) == [(1, "kept")]
    assert not shown.done()
    result = closed.result()
    assert result is not None and result.reason is OverlayDismissReason.DISPOSED


def test_unmounting_the_overlay_completes_every_open_handle() -> None:
    window = _window(_overlay_factory(1))
    overlay = window.overlay
    handle = overlay.dialog(_Card(1, "widget"))  # type: ignore[attr-defined]

    overlay.unmount()

    assert overlay.open_entries == ()
    result = handle.result()
    assert result is not None and result.reason is OverlayDismissReason.DISPOSED


def test_stacked_dialogs_restore_in_order_and_an_unresolvable_one_drops_alone() -> None:
    ask, gone, tell = _intent_class("Ask"), _intent_class("Gone"), _intent_class("Tell")
    window = _window(_overlay_factory(1, ask, gone, tell))
    window.overlay.dialog(ask("a"))  # type: ignore[attr-defined]
    dropped = window.overlay.dialog(gone("b"))  # type: ignore[attr-defined]
    window.overlay.dialog(tell("c"))  # type: ignore[attr-defined]

    restored = _reload(window, _overlay_factory(2, _intent_class("Ask"), _intent_class("Tell")))

    assert restored == 2
    assert _cards(window) == [(2, "a"), (2, "c")]
    result = dropped.result()
    assert result is not None and result.reason is OverlayDismissReason.DISPOSED


def test_a_snapshot_without_a_commit_leaves_the_old_dialog_closable() -> None:
    ask = _intent_class("Ask")
    window = _window(_overlay_factory(1, ask))
    handle = window.overlay.dialog(ask("hello"))  # type: ignore[attr-defined]

    snapshot_overlay(window)
    handle.close("kept")

    result = handle.result()
    assert result is not None and result.value == "kept"


def test_the_resolver_matches_a_redefined_intent_by_qualified_name() -> None:
    old, new = _intent_class("Ask"), _intent_class("Ask")
    resolver = MappingIntentResolver({new: lambda i: _Card(2, i.text)})

    card = resolver.resolve(old("hello"))

    assert isinstance(card, _Card) and card.version == 2


def test_the_resolver_still_rejects_an_unknown_intent() -> None:
    resolver = MappingIntentResolver({})

    with pytest.raises(RuntimeError, match="No overlay intent"):
        resolver.resolve(_intent_class("Ask")("hello"))


class _OverlaylessApp:
    _overlay = None


def test_snapshot_and_restore_without_an_overlay_are_no_ops() -> None:
    assert snapshot_overlay(_OverlaylessApp()) == []  # type: ignore[arg-type]
    assert restore_overlay(_OverlaylessApp(), [object()]) == 0  # type: ignore[arg-type, list-item]
