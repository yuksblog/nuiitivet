"""Regression tests for Issue #121.

Covers:
- Japanese label / supporting text rendering uses CJK-aware font fallback.
- Click-outside the TextField clears focus state.
- External Observable updates synchronize the floating label state.
- Pointer drag selects a text range.
- Long text is clipped (canvas clip is applied) and the cursor stays in view.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.material.text_fields import TextField
from nuiitivet.observable import Observable
from nuiitivet.runtime.app_events import dispatch_mouse_press
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.widgets.text_editing import TextRange

# ---------------------------------------------------------------------------
# 1. Japanese rendering uses locale-aware font fallback for label/supporting.
# ---------------------------------------------------------------------------


def test_text_field_label_font_uses_locale_fallbacks() -> None:
    tf = TextField(label="入力してください", supporting_text="日本語のテキストフィールドです")

    captured: dict = {}

    def _fake_get_typeface(**kwargs):
        captured["family_candidates"] = kwargs.get("family_candidates")
        return MagicMock()

    with patch("nuiitivet.material.text_fields.get_typeface", side_effect=_fake_get_typeface):
        with patch("nuiitivet.material.text_fields.make_font", return_value=MagicMock()):
            tf._get_font()

    candidates = captured.get("family_candidates")
    assert candidates is not None
    # The fallback chain must include CJK fonts so Japanese glyphs render.
    cjk_markers = ("Hiragino", "Noto Sans CJK", "Noto Sans JP", "Yu Gothic", "Meiryo")
    assert any(any(marker in fam for marker in cjk_markers) for fam in candidates), candidates


# ---------------------------------------------------------------------------
# 2. Click-outside the TextField clears focus.
# ---------------------------------------------------------------------------


class _FakeApp:
    """Minimal app stub for dispatch_mouse_press focus testing."""

    def __init__(self, hit_target):
        self._hit_target = hit_target
        self._focused_node = None
        self._focused_target = None
        self._pressed_target = None
        self._pointer_capture_manager = None
        self._primary_pointer_id = 1
        self.root = MagicMock()
        self.root.hit_test = MagicMock(return_value=hit_target)
        self.invalidate = MagicMock()

    def request_focus(self, node):
        if self._focused_node is node:
            return
        if self._focused_node is not None:
            self._focused_node._set_focused(False)
        self._focused_node = node
        if node is not None:
            node._set_focused(True)


def test_click_outside_text_field_blurs_focus() -> None:
    # Build a focused EditableText and simulate a press elsewhere.
    editable = EditableText(value="hi")
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)

    # Some unrelated widget receives the click.
    other_target = MagicMock()
    other_target._parent = None

    app = _FakeApp(hit_target=other_target)
    app.request_focus(focus_node)
    assert editable.state.focused is True

    dispatch_mouse_press(app, x=999, y=999)

    assert editable.state.focused is False
    assert app._focused_node is None


def test_click_with_no_hit_target_blurs_focus() -> None:
    editable = EditableText(value="hi")
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)

    app = _FakeApp(hit_target=None)
    app.request_focus(focus_node)
    assert editable.state.focused is True

    dispatch_mouse_press(app, x=10, y=10)
    assert editable.state.focused is False


def test_click_inside_focused_widget_keeps_focus() -> None:
    editable = EditableText(value="hi")
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)

    app = _FakeApp(hit_target=editable)
    app.request_focus(focus_node)

    # Avoid triggering the real pointer dispatch chain in this stubbed test;
    # we only care about the focus-blur behavior.
    with patch(
        "nuiitivet.runtime.app_events._deliver_pointer_event",
        return_value=editable,
    ):
        dispatch_mouse_press(app, x=10, y=10)

    # Focus should not be cleared because the press landed on the focused widget.
    assert app._focused_node is focus_node
    assert editable.state.focused is True


def test_click_on_host_keeps_focus_on_inner_focused_descendant() -> None:
    """Edge-clicking a TextField host while its inner EditableText is
    focused must NOT blur the editable. Otherwise focus ping-pongs and the
    pointer-origin flag flips back to keyboard, falsely showing the focus
    ring (and restarting label animation).
    """
    tf = TextField(value="hi")
    editable = tf._editable
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)
    # Wire parent linkage so the press helper can walk up from editable.
    editable._parent = tf

    # The press lands on the host TextField (e.g. the padding area), not on
    # the inner editable. The press handler will internally route focus to
    # the editable, but since editable is already focused that re-request
    # is a no-op — the post-press blur logic must not treat this as
    # "click outside focused".
    app = _FakeApp(hit_target=tf)
    app.request_focus(focus_node)
    assert editable.state.focused is True

    with patch(
        "nuiitivet.runtime.app_events._deliver_pointer_event",
        return_value=tf,
    ):
        dispatch_mouse_press(app, x=5, y=5)

    assert app._focused_node is focus_node
    assert editable.state.focused is True


def test_click_on_sibling_inside_host_keeps_focus_on_focused_descendant() -> None:
    """Clicking a sibling widget (e.g. a leading/trailing icon) inside the
    same TextField host as the focused EditableText must NOT blur focus.

    The deepest hit target (icon) is neither an ancestor nor a descendant
    of the focused editable — they are siblings sharing the TextField as a
    common ancestor. The blur-on-press logic must consult the actual press
    handler (the TextField) so this case is recognised as in-group.
    """
    tf = TextField(value="hi")
    editable = tf._editable
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)
    editable._parent = tf

    # Simulate an icon child that is a sibling of the editable.
    sibling_icon = MagicMock()
    sibling_icon._parent = tf

    app = _FakeApp(hit_target=sibling_icon)
    app.request_focus(focus_node)
    assert editable.state.focused is True

    # The press is delivered to the icon but consumed (handled) by the
    # parent TextField — that is what _pressed_target reflects in real
    # dispatch.
    with patch(
        "nuiitivet.runtime.app_events._deliver_pointer_event",
        return_value=tf,
    ):
        dispatch_mouse_press(app, x=5, y=5)

    assert app._focused_node is focus_node
    assert editable.state.focused is True


def test_click_on_layout_ancestor_blurs_focus() -> None:
    """Clicking on a non-handler layout ancestor of the focused widget
    (e.g. the surrounding Container/Column) MUST blur focus.

    The focused editable's owner has many ancestors going up to the app
    root. Treating any ancestor as "in-group" would make outside-clicks
    fail to blur. Only the actual press handler (Clickable) should keep
    focus, and an unrelated layout container does not consume presses.
    """
    tf = TextField(value="")
    editable = tf._editable
    focus_node = editable.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    focus_node.attach(editable)

    # Layout ancestor (e.g. Column wrapping multiple TextFields).
    layout_ancestor = MagicMock()
    layout_ancestor._parent = None
    tf._parent = layout_ancestor

    app = _FakeApp(hit_target=layout_ancestor)
    app.request_focus(focus_node)
    assert editable.state.focused is True

    # Layout ancestor is not Clickable: no handler consumes the press.
    with patch(
        "nuiitivet.runtime.app_events._deliver_pointer_event",
        return_value=None,
    ):
        dispatch_mouse_press(app, x=10, y=10)

    assert app._focused_node is None
    assert editable.state.focused is False


# ---------------------------------------------------------------------------
# 3. External Observable update synchronizes floating label state.
# ---------------------------------------------------------------------------


def test_external_observable_value_updates_label_state() -> None:
    obs = Observable("")
    tf = TextField(value=obs, label="Name")

    # Mount to wire up the external subscription.
    tf.mount(MagicMock())

    # Initially empty -> label is in rest state.
    assert tf._label_progress.target == 0.0

    obs.value = "Alice"
    assert tf.value == "Alice"
    # Floating label should follow the externally-driven value.
    assert tf._label_progress.target == 1.0

    obs.value = ""
    assert tf._label_progress.target == 0.0

    tf.on_unmount()


# ---------------------------------------------------------------------------
# 4. Pointer drag selects a text range.
# ---------------------------------------------------------------------------


def test_pointer_drag_selects_range() -> None:
    tf = TextField(value="abcdefgh")
    tf.layout(200, 56)
    tf.set_layout_rect(0, 0, 200, 56)
    # Trigger a paint so editable.last_rect / global_layout_rect are populated.
    tf.paint(None, 0, 0, 200, 56)

    editable = tf._editable

    # Stub character measurement so the test does not depend on a real font.
    fake_font = MagicMock()
    fake_font.measureText = MagicMock(side_effect=lambda s: float(len(s) * 10))
    metrics = MagicMock()
    metrics.fAscent = -10
    metrics.fDescent = 3
    fake_font.getMetrics = MagicMock(return_value=metrics)

    with patch.object(EditableText, "_get_font", return_value=fake_font):
        # Place the editable so we can compute local x easily.
        editable.set_last_rect(0, 0, 200, 40)
        editable.set_layout_rect(0, 0, 200, 40)

        # Press at index 1 (x=10).
        editable._handle_press(PointerEvent(id=1, type=PointerEventType.PRESS, x=10, y=10))
        assert editable._drag_anchor == 1
        assert editable._state_internal.value.selection == TextRange(1, 1)

        # Drag to index 5 (x=50).
        editable._handle_drag_update(
            PointerEvent(id=1, type=PointerEventType.MOVE, x=50, y=10),
            dx=40.0,
            dy=0.0,
        )
        sel = editable._state_internal.value.selection
        assert sel == TextRange(1, 5)
        assert sel.is_collapsed is False

        # Release ends the drag.
        editable._handle_drag_end(PointerEvent(id=1, type=PointerEventType.RELEASE, x=50, y=10))
        assert editable._drag_anchor is None


# ---------------------------------------------------------------------------
# 5. Long text overflow handling: clip rect applied + cursor scrolled into view.
# ---------------------------------------------------------------------------


def test_long_text_paint_applies_clip_rect() -> None:
    tf = TextField(value="x" * 200)
    tf.layout(200, 56)

    fake_font = MagicMock()
    fake_font.measureText = MagicMock(side_effect=lambda s: float(len(s) * 10))
    metrics = MagicMock()
    metrics.fAscent = -10
    metrics.fDescent = 3
    fake_font.getMetrics = MagicMock(return_value=metrics)

    canvas = MagicMock()
    canvas.save = MagicMock(return_value=42)

    with patch.object(EditableText, "_get_font", return_value=fake_font):
        with patch("nuiitivet.widgets.editable_text.make_paint", return_value=MagicMock()):
            with patch("nuiitivet.widgets.editable_text.resolve_color_to_rgba", return_value=(0, 0, 0, 255)):
                with patch("nuiitivet.widgets.editable_text.make_text_blob", return_value=MagicMock()):
                    with patch("nuiitivet.widgets.editable_text.make_rect", return_value="<rect>"):
                        tf._editable.paint(canvas, 0, 0, 100, 40)

    # The viewport must be clipped so long text cannot bleed outside the field.
    assert canvas.clipRect.called is True
    assert canvas.save.called is True


def test_long_text_scrolls_cursor_into_view() -> None:
    tf = TextField(value="abcdefghijklmno")
    tf.layout(60, 40)

    fake_font = MagicMock()
    fake_font.measureText = MagicMock(side_effect=lambda s: float(len(s) * 10))
    metrics = MagicMock()
    metrics.fAscent = -10
    metrics.fDescent = 3
    fake_font.getMetrics = MagicMock(return_value=metrics)

    canvas = MagicMock()
    canvas.save = MagicMock(return_value=1)

    editable = tf._editable
    # Cursor at the end so total width (150) > viewport (60).
    editable._state_internal.value = editable._state_internal.value.copy_with(
        selection=TextRange(len("abcdefghijklmno"), len("abcdefghijklmno"))
    )

    with patch.object(EditableText, "_get_font", return_value=fake_font):
        with patch("nuiitivet.widgets.editable_text.make_paint", return_value=MagicMock()):
            with patch("nuiitivet.widgets.editable_text.resolve_color_to_rgba", return_value=(0, 0, 0, 255)):
                with patch("nuiitivet.widgets.editable_text.make_text_blob", return_value=MagicMock()):
                    with patch("nuiitivet.widgets.editable_text.make_rect", return_value="<rect>"):
                        editable.paint(canvas, 0, 0, 60, 40)

    # Scroll offset must be > 0 so that the caret position (150px) is inside
    # the 60px viewport rather than rendered outside.
    assert editable._scroll_x > 0


# ---------------------------------------------------------------------------
# 6. Pointer-driven focus must NOT show the focus ring (MD3 spec).
# ---------------------------------------------------------------------------


def test_pointer_focus_hides_focus_ring() -> None:
    tf = TextField(value="")

    # Pointer-driven focus path: the press handler routes through the
    # editable's pointer-focus entry point, marking it as pointer-origin.
    tf._editable.request_focus_from_pointer()
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True)

    # Even though the editable is focused, the ring must stay hidden
    # because focus originated from a pointer interaction.
    assert tf._editable.is_focus_from_pointer is True
    assert tf.should_show_focus_ring is False


def test_keyboard_focus_shows_focus_ring() -> None:
    tf = TextField(value="")

    # Keyboard navigation focuses the editable directly (Tab traversal
    # collects EditableText's FocusNode since TextField has none).
    tf._editable.focus()
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True)

    assert tf._editable.is_focus_from_pointer is False
    assert tf.should_show_focus_ring is True


def test_blur_resets_pointer_focus_flag() -> None:
    tf = TextField(value="")

    tf._editable.request_focus_from_pointer()
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True)
    assert tf._editable.is_focus_from_pointer is True

    # Releasing focus should clear the pointer-origin flag so that the next
    # keyboard focus correctly shows the ring.
    tf._editable._handle_focus_change(False)
    tf._editable.state.focused = False
    tf._on_editable_focus_change(False)
    assert tf._editable.is_focus_from_pointer is False


def test_pointer_press_on_editable_propagates_to_text_field() -> None:
    """Clicking the center (which hits the inner EditableText directly) must
    still suppress the focus ring on the parent TextField."""
    tf = TextField(value="abc")

    # Simulate the path taken when EditableText handles the press itself.
    tf._editable.request_focus_from_pointer()
    tf._editable.state.focused = True
    tf._on_editable_focus_change(True)

    assert tf._editable.is_focus_from_pointer is True
    assert tf.should_show_focus_ring is False
