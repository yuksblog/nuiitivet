"""Tests for the interaction journal: ring buffer, event schema, recorder policy."""

from __future__ import annotations

import threading
from typing import Any, Optional

import pytest

from nuiitivet.dev.interaction import (
    DEFAULT_CAPACITY,
    InteractionEvent,
    InteractionJournal,
    InteractionRecorder,
    resolve_target,
    window_identity,
)
from nuiitivet.input.codes import MOD_CTRL, MOD_META, MOD_SHIFT


# --- journal ---------------------------------------------------------------


def test_record_click_captures_target_and_seq() -> None:
    journal = InteractionJournal()
    event = journal.record_click({"type": "Button", "label": "increment"})

    assert event.kind == "click"
    assert event.target == {"type": "Button", "label": "increment"}
    assert event.key is None
    assert event.modifiers == ()
    assert event.seq == 1
    assert event.timestamp > 0


def test_record_key_captures_modifiers() -> None:
    journal = InteractionJournal()
    event = journal.record_key("s", ("ctrl",))
    assert event.kind == "key"
    assert event.key == "s"
    assert event.modifiers == ("ctrl",)


def test_record_text_is_content_free() -> None:
    journal = InteractionJournal()
    event = journal.record_text()
    assert event.kind == "text"
    assert event.target is None and event.key is None and event.modifiers == ()


def test_seq_is_monotonic_across_kinds() -> None:
    journal = InteractionJournal()
    a = journal.record_click({"type": "X"})
    b = journal.record_key("enter")
    c = journal.record_text()
    assert [a.seq, b.seq, c.seq] == [1, 2, 3]


def test_ring_buffer_evicts_oldest() -> None:
    journal = InteractionJournal(capacity=3)
    for _ in range(5):
        journal.record_text()
    events = journal.recent()
    assert [e.seq for e in events] == [3, 4, 5]


def test_recent_limit_returns_newest_tail() -> None:
    journal = InteractionJournal()
    for _ in range(5):
        journal.record_text()
    assert [e.seq for e in journal.recent(limit=2)] == [4, 5]


def test_recent_non_positive_limit_is_empty() -> None:
    journal = InteractionJournal()
    journal.record_text()
    assert journal.recent(limit=0) == []
    assert journal.recent(limit=-1) == []


def test_default_capacity() -> None:
    assert InteractionJournal().capacity == DEFAULT_CAPACITY


def test_non_positive_capacity_rejected() -> None:
    with pytest.raises(ValueError, match="capacity must be positive"):
        InteractionJournal(capacity=0)


def test_to_dict_click_omits_key_and_modifiers() -> None:
    event = InteractionEvent(seq=1, timestamp=1.0, kind="click", target={"type": "Button"})
    assert event.to_dict() == {
        "seq": 1,
        "timestamp": 1.0,
        "kind": "click",
        "target": {"type": "Button"},
    }


def test_to_dict_key_includes_modifiers_only_when_present() -> None:
    bare = InteractionEvent(seq=1, timestamp=1.0, kind="key", key="enter")
    assert bare.to_dict() == {"seq": 1, "timestamp": 1.0, "kind": "key", "key": "enter"}

    chord = InteractionEvent(seq=2, timestamp=1.0, kind="key", key="s", modifiers=("ctrl",))
    assert chord.to_dict()["modifiers"] == ["ctrl"]


def test_to_dict_text_is_bare_marker() -> None:
    event = InteractionEvent(seq=1, timestamp=1.0, kind="text")
    assert event.to_dict() == {"seq": 1, "timestamp": 1.0, "kind": "text"}


def test_record_window_opened_and_closed_interleave_with_inputs() -> None:
    """Lifecycle events share the input events' one seq order (#622)."""
    journal = InteractionJournal()
    opened = journal.record_window_opened({"id": 5, "title": "Palette", "main": False})
    click = journal.record_click({"type": "Button", "label": "close"})
    closed = journal.record_window_closed({"id": 5, "title": "Palette", "main": False})

    assert opened.kind == "window_opened"
    assert closed.kind == "window_closed"
    assert opened.window == {"id": 5, "title": "Palette", "main": False}
    assert [opened.seq, click.seq, closed.seq] == [1, 2, 3]
    assert [e.kind for e in journal.recent()] == ["window_opened", "click", "window_closed"]


def test_to_dict_window_event_carries_window_only() -> None:
    event = InteractionEvent(
        seq=1, timestamp=1.0, kind="window_closed", window={"id": 3, "title": "Settings", "main": False}
    )
    assert event.to_dict() == {
        "seq": 1,
        "timestamp": 1.0,
        "kind": "window_closed",
        "window": {"id": 3, "title": "Settings", "main": False},
    }


def test_to_dict_input_events_omit_window() -> None:
    event = InteractionEvent(seq=1, timestamp=1.0, kind="click", target={"type": "Button"})
    assert "window" not in event.to_dict()


class _WindowStub:
    def __init__(self, id: int, title: Any, is_main: bool) -> None:
        self.id = id
        self.title = title
        self.is_main = is_main


def test_window_identity_reports_id_title_and_main() -> None:
    info = window_identity(_WindowStub(7, "Palette", False))
    assert info == {"id": 7, "title": "Palette", "main": False}


def test_window_identity_omits_unset_title() -> None:
    info = window_identity(_WindowStub(2, None, True))
    assert info == {"id": 2, "main": True}


def test_concurrent_records_keep_unique_seq() -> None:
    journal = InteractionJournal(capacity=1000)
    threads = [
        threading.Thread(target=lambda: [journal.record_text() for _ in range(50)])
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    events = journal.recent()
    assert len(events) == 400
    assert len({e.seq for e in events}) == 400


# --- target resolution -----------------------------------------------------


class _Node:
    """A minimal widget stand-in: an identity, a parent, and a hit target."""

    def __init__(self, parent: Optional["_Node"] = None, **identity: Any) -> None:
        self._parent = parent
        self._hit: Optional[_Node] = None
        for name, value in identity.items():
            setattr(self, name, value)

    def hit_test(self, x: int, y: int) -> Optional["_Node"]:
        return self._hit


def test_resolve_target_prefers_key_and_label() -> None:
    node = _Node(key="submit", label="Save")
    assert resolve_target(node) == {"type": "_Node", "key": "submit", "label": "Save"}


def test_resolve_target_walks_up_to_identifiable_ancestor() -> None:
    button = _Node(key="increment", label="＋")
    inner = _Node(parent=button)  # e.g. an internal gesture layer with no identity
    resolved = resolve_target(inner)
    assert resolved == {"type": "_Node", "key": "increment", "label": "＋"}


def test_resolve_target_prefers_keyed_ancestor_over_inner_label() -> None:
    # A click lands on a Button's inner label Text; the target should resolve to
    # the *keyed Button*, matching describe_tree / action targeting -- not stop at
    # the nearer inner text.
    class Button(_Node):
        pass

    class Text(_Node):
        pass

    button = Button(key="increment-btn", label="increment")
    inner_text = Text(parent=button, text="increment")
    resolved = resolve_target(inner_text)
    assert resolved == {"type": "Button", "key": "increment-btn", "label": "increment"}


def test_resolve_target_keeps_descendant_label_when_keyed_node_has_none() -> None:
    keyed = _Node(key="row-3")  # a keyed container with no visible label
    inner = _Node(parent=keyed, text="Buy milk")
    assert resolve_target(inner) == {"type": "_Node", "key": "row-3", "label": "Buy milk"}


def test_resolve_target_collapses_text_and_title_to_label() -> None:
    node = _Node(text="hello")
    assert resolve_target(node) == {"type": "_Node", "label": "hello"}


def test_resolve_target_falls_back_to_type_when_unidentifiable() -> None:
    anon = _Node(parent=_Node())  # no identity anywhere up the chain
    assert resolve_target(anon) == {"type": "_Node"}


def test_resolve_target_never_includes_coordinates() -> None:
    node = _Node(key="k", label="l")
    resolved = resolve_target(node)
    assert "x" not in resolved and "y" not in resolved and "rect" not in resolved


# --- recorder policy -------------------------------------------------------


class _App:
    def __init__(self, root: Optional[_Node]) -> None:
        self.root = root


def test_recorder_records_click_resolved_to_identity() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    target = _Node(key="submit", label="Save")
    root = _Node()
    root._hit = target
    recorder.on_mouse_press(_App(root), 5, 5)

    events = journal.recent()
    assert len(events) == 1
    assert events[0].kind == "click"
    assert events[0].target == {"type": "_Node", "key": "submit", "label": "Save"}


def test_recorder_ignores_click_on_empty_space() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    root = _Node()  # hit_test returns None
    recorder.on_mouse_press(_App(root), 5, 5)
    assert journal.recent() == []


def test_recorder_records_shortcut_key() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("s", MOD_CTRL)
    events = journal.recent()
    assert len(events) == 1
    assert events[0].key == "s" and events[0].modifiers == ("ctrl",)


def test_recorder_records_semantic_navigation_key() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("enter", 0)
    assert [e.key for e in journal.recent()] == ["enter"]


def test_recorder_drops_bare_character_key_to_protect_content() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("a", 0)
    assert journal.recent() == []


def test_recorder_drops_shift_letter_as_typed_content() -> None:
    # Shift is a typing modifier (capital letter), not a command chord: dropped.
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("a", MOD_SHIFT)
    assert journal.recent() == []


def test_recorder_records_meta_chord() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("c", MOD_META)
    assert [e.key for e in journal.recent()] == ["c"]


def test_recorder_drops_standalone_modifier_keydown() -> None:
    # Pressing Cmd on its own fires a key-down for the modifier key itself, with
    # the meta bit already set. That is noise ahead of the real chord and must be
    # dropped so ``ctrl`` / ``lcommand`` never litter the log.
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_key_press("lcommand", MOD_META)
    recorder.on_key_press("lshift", MOD_SHIFT)
    assert journal.recent() == []


def test_recorder_coalesces_consecutive_text() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    for _ in range(5):  # typing "hello" fires on_text per character
        recorder.on_text()
    assert [e.kind for e in journal.recent()] == ["text"]


def test_recorder_text_marker_resets_after_other_action() -> None:
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_text()
    recorder.on_key_press("enter", 0)
    recorder.on_text()
    assert [e.kind for e in journal.recent()] == ["text", "key", "text"]


def test_recorder_never_receives_or_stores_typed_text() -> None:
    # on_text takes no argument: the recorder has no way to store field content.
    journal = InteractionJournal()
    recorder = InteractionRecorder(journal)
    recorder.on_text()
    event = journal.recent()[0]
    assert event.to_dict() == {"seq": event.seq, "timestamp": event.timestamp, "kind": "text"}


def test_select_marker_is_content_free() -> None:
    """A designation may disclose rects and text -- but not through this journal (#591).

    The marker says only *that* the human designated something; the payload is
    served solely by ``describe_selection``, so the ambient journal never becomes
    a second, unasked-for channel for it.
    """
    journal = InteractionJournal()

    journal.record_select()

    (event,) = journal.recent()
    assert event.to_dict() == {
        "seq": event.seq,
        "timestamp": event.timestamp,
        "kind": "select",
    }


# --- window lifecycle wiring (#622) ----------------------------------------


def test_app_hooks_feed_window_lifecycle_events() -> None:
    """The dev runner's wiring end-to-end: App choke points -> journal.

    Mirrors ``nuiitivet.dev.__main__``: the register hook records opens, the
    unregister hook records closes, and the back-fill loop covers windows opened
    before the hooks existed (the main window, or any opened before ``run()``).
    """
    from nuiitivet.layout.container import Container
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    app = App(Window(content=Container(), title="Main"))
    journal = InteractionJournal()

    def _record_opened(w: Window) -> None:
        journal.record_window_opened(window_identity(w))

    def _record_closed(w: Window) -> None:
        journal.record_window_closed(window_identity(w))

    app._instrument_window_hook = _record_opened
    app._unregister_window_hook = _record_closed
    for win in app.windows:
        journal.record_window_opened(window_identity(win))

    palette = Window(content=Container(), title="Palette").open()
    journal.record_click({"type": "Button", "label": "close palette"})
    palette.close()

    events = [(e.kind, e.window) for e in journal.recent()]
    assert events == [
        ("window_opened", {"id": app.main_window.id, "title": "Main", "main": True}),
        ("window_opened", {"id": palette.id, "title": "Palette", "main": False}),
        ("click", None),
        ("window_closed", {"id": palette.id, "title": "Palette", "main": False}),
    ]
