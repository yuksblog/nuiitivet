"""Spike for issue #335: AccessKit's macOS adapter on a Nuiitivet window.

macOS only. Hands a three-node accessibility tree (window, button, label) to
``accesskit.macos.SubclassingAdapter`` while a normal Nuiitivet window runs,
then reads the tree back through the content view's ``NSAccessibility``
methods, in this process. No assistive technology is needed for the read-back.

Needs ``pip install accesskit``. Run the automatic checks (exits by itself)::

    python scripts/investigation/spike_accesskit_macos.py

Keep the window open to try VoiceOver (Cmd+F5) from a real terminal::

    python scripts/investigation/spike_accesskit_macos.py --stay

What the automatic run answers:

1. The adapter subclasses pyglet's content view without breaking input.
2. ``accessibilityChildren`` returns the nodes, with role, label and frame.
3. Moving the Nuiitivet focus moves the focused element, from the content
   view, the window and the application alike. A tree update changes a label.
4. An ``accessibilityPerformPress`` on the button reaches the action handler
   on the main thread.

What to verify by hand with ``--stay``:

1. VO+Right from the window reaches "Increment, button" and "count: 0".
2. VO+Space on the button raises the count, and the new count is read.
3. Tab moves the Nuiitivet focus ring and VoiceOver follows it.
4. The VoiceOver cursor rectangle sits on the widget it reads, on a Retina
   display too (the automatic run saw a pixel ratio of 1.0 only).

Findings (accesskit 0.7.0, pyglet 2.1.14, macOS 26.6):

- All four automatic answers are yes, and the four hand checks hold with
  VoiceOver. The content view becomes
  ``AccessKitSubclassOfPygletView``; the ``acceptsFirstMouse:`` and IME
  patches on ``PygletView`` keep working, since the subclass inherits them.
- The tree is built lazily: the activation handler runs on the first query.
- An exception raised inside the activation or the action handler aborts the
  process. So does ``update_if_active`` called from inside the action
  handler. A bridge catches everything in both, and queues an action for the
  next loop turn.
- A button's label arrives as ``accessibilityTitle``, a label node's text as
  ``accessibilityValue``.
- The first responder is ``PygletTextView``, a subview that is not in the
  tree. Left alone, the window answers it as the focused element and
  VoiceOver never reaches a node. ``add_focus_forwarder_to_window_class``
  sends the question to the content view, and the subview is marked as no
  accessibility element.
- A tree whose focus is the root answers no focused element. The window
  stands in.
- A window that has not drawn yet has no layout rects.
- cocoapy's bound methods skip the dynamic subclass, so the read-back goes
  through ``send_message``.
"""

from __future__ import annotations

import sys
import threading
from typing import Any, Optional

import nuiitivet.material as nv
from nuiitivet._interaction.action import settle
from nuiitivet._interaction.perception import find_target
from nuiitivet.widgets.interaction import FocusNode, FocusSource

WINDOW_ID = 1
BUTTON_ID = 2
LABEL_ID = 3
SECOND_BUTTON_ID = 4
_IDS_BY_KEY = {"increment": BUTTON_ID, "reset": SECOND_BUTTON_ID}


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[
                nv.Text("AccessKit spike (#335)", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Button("Increment", on_click=self.increment, key="increment"),
                nv.Text(self.count.map(lambda n: f"count: {n}"), key="count"),
                nv.Button("Reset", on_click=self.reset, key="reset"),
            ],
            gap=12,
            padding=24,
        )

    def increment(self) -> None:
        self.count.value += 1

    def reset(self) -> None:
        self.count.value = 0


class Bridge:
    """The tree this spike hands to AccessKit, built from the live widgets."""

    def __init__(self, screen: Screen, window: Any, pyglet_window: Any) -> None:
        import accesskit

        self._ak = accesskit
        self._screen = screen
        self._window = window
        self._pyglet_window = pyglet_window
        self.activations = 0
        self.actions: list[tuple[str, int, str]] = []
        nswindow = pyglet_window._nswindow
        # The first responder is pyglet's text view, which is not in the tree.
        # Ask the content view, AccessKit's, for the focused element instead.
        accesskit.macos.add_focus_forwarder_to_window_class(_text(_send(nswindow, "className")))
        subviews = nswindow.contentView().subviews()
        for i in range(subviews.count()):
            subviews.objectAtIndex_(i).setAccessibilityElement_(False)
        self.adapter = accesskit.macos.SubclassingAdapter.for_window(
            pyglet_window._nswindow.ptr.value, self._on_activate, self._on_action
        )

    def _bounds(self, key: str) -> Any:
        widget = find_target(self._screen, key=key)
        x, y, w, h = widget.global_layout_rect or (0, 0, 0, 0)
        return self._ak.Rect(float(x), float(y), float(x + w), float(y + h))

    def focus_id(self) -> int:
        """The entry of the widget that holds the Nuiitivet focus."""
        node = self._window._focused_node
        key = getattr(node.owner, "key", None) if node is not None else None
        return _IDS_BY_KEY.get(key, WINDOW_ID)

    def request_focus(self, key: str) -> None:
        widget = find_target(self._screen, key=key)
        node = widget.get_node(FocusNode)
        node.request_focus(FocusSource.KEYBOARD)

    def _button(self, key: str, label: str) -> Any:
        node = self._ak.Node(self._ak.Role.BUTTON)
        node.set_label(label)
        node.set_bounds(self._bounds(key))
        node.add_action(self._ak.Action.FOCUS)
        node.add_action(self._ak.Action.CLICK)
        return node

    def build(self) -> Any:
        ak = self._ak
        # A window that has not drawn yet has no rects; lay it out first.
        settle(self._window)
        root = ak.Node(ak.Role.WINDOW)
        root.set_label("AccessKit spike")
        root.set_children([BUTTON_ID, LABEL_ID, SECOND_BUTTON_ID])
        # Widget rects are logical pixels; AccessKit's are backing pixels.
        scale = float(self._pyglet_window.get_pixel_ratio())
        root.set_transform(ak.Affine([scale, 0.0, 0.0, scale, 0.0, 0.0]))

        label = ak.Node(ak.Role.LABEL)
        label.set_value(f"count: {self._screen.count.value}")
        label.set_bounds(self._bounds("count"))

        update = ak.TreeUpdate(self.focus_id())
        tree = ak.Tree(WINDOW_ID)
        tree.toolkit_name = "nuiitivet"
        update.tree = tree
        update.nodes.append((WINDOW_ID, root))
        update.nodes.append((BUTTON_ID, self._button("increment", "Increment")))
        update.nodes.append((LABEL_ID, label))
        update.nodes.append((SECOND_BUTTON_ID, self._button("reset", "Reset")))
        return update

    def _on_activate(self) -> Any:
        self.activations += 1
        return self.build()

    def _on_action(self, request: Any) -> None:
        # The adapter calls this while it holds its own state: an update, or an
        # exception, from inside here aborts the process. Only queue.
        import pyglet

        self.actions.append((str(request.action), int(request.target), threading.current_thread().name))
        pyglet.clock.schedule_once(lambda dt: self._perform(request), 0)

    def _perform(self, request: Any) -> None:
        if request.action == self._ak.Action.CLICK:
            if request.target == BUTTON_ID:
                self._screen.increment()
            elif request.target == SECOND_BUTTON_ID:
                self._screen.reset()
        elif request.action == self._ak.Action.FOCUS:
            for key, entry in _IDS_BY_KEY.items():
                if entry == request.target:
                    self.request_focus(key)
        self.push()

    def push(self) -> None:
        events = self.adapter.update_if_active(self.build)
        if events is not None:
            events.raise_events()

    def set_view_focused(self, focused: bool) -> None:
        events = self.adapter.update_view_focus_state(focused)
        if events is not None:
            events.raise_events()


def _text(ns_string: Any) -> Optional[str]:
    from pyglet.libs.darwin.cocoapy import cfstring_to_string

    if ns_string is None or not getattr(ns_string, "ptr", ns_string):
        return None
    return cfstring_to_string(ns_string)


def _describe(element: Any) -> dict[str, Any]:
    frame = element.accessibilityFrame()
    return {
        "role": _text(element.accessibilityRole()),
        "title": _text(element.accessibilityTitle()),
        "label": _text(element.accessibilityLabel()),
        "value": _text(element.accessibilityValue()),
        "frame": (
            round(frame.origin.x),
            round(frame.origin.y),
            round(frame.size.width),
            round(frame.size.height),
        ),
    }


def _send(receiver: Any, selector: str) -> Any:
    """Send ``selector`` through ``objc_msgSend`` and wrap the answer.

    cocoapy's bound methods call the IMP of the class the instance was first
    wrapped as, so they miss the overrides of AccessKit's dynamic subclass.
    """
    from ctypes import c_void_p

    from pyglet.libs.darwin.cocoapy import ObjCInstance, send_message

    answer = send_message(receiver, selector, restype=c_void_p, argtypes=[])
    return ObjCInstance(answer) if answer else None


def _children(element: Any) -> list[Any]:
    array = _send(element, "accessibilityChildren")
    if array is None:
        return []
    return [array.objectAtIndex_(i) for i in range(array.count())]


def _role_line(element: Any) -> str:
    from pyglet.libs.darwin.cocoapy import get_selector

    if not element.respondsToSelector_(get_selector("accessibilityRole")):
        return f"(no role) class={_text(_send(element, 'className'))}"
    role = _send(element, "accessibilityRole")
    title = _send(element, "accessibilityTitle")
    cls = _send(element, "className")
    return f"{_text(role)} title={_text(title)!r} class={_text(cls)}"


def _dump(element: Any, depth: int, limit: int) -> None:
    print(f"[spike]   {'  ' * depth}{_role_line(element)}")
    if depth < limit and "(no role)" not in _role_line(element):
        for child in _children(element):
            _dump(child, depth + 1, limit)


def _dump_from_window(nswindow: Any) -> None:
    """Walk down from the NSWindow, the way an assistive technology enters."""
    responder = _send(nswindow, "firstResponder")
    print(f"[spike] first responder: {_text(_send(responder, 'className')) if responder else None}")
    print("[spike] from the window:")
    _dump(nswindow, 0, 3)
    focused = _send(nswindow, "accessibilityFocusedUIElement")
    print(f"[spike] window's focused element: {_role_line(focused) if focused else None}")
    from pyglet.libs.darwin.cocoapy import ObjCClass

    nsapp = ObjCClass("NSApplication").sharedApplication()
    focused = _send(nsapp, "accessibilityFocusedUIElement")
    print(f"[spike] app's focused element: {_role_line(focused) if focused else None}")
    print(f"[spike] key window: {bool(nswindow.isKeyWindow())}, app active: {bool(nsapp.isActive())}")


def _read_back(bridge: Bridge, screen: Screen, app: nv.App, stay: bool) -> None:
    window = bridge._pyglet_window
    view = window._nswindow.contentView()
    print(f"[spike] content view class: {_text(view.className())}")
    print(f"[spike] pixel ratio: {window.get_pixel_ratio()}")

    elements = _children(view)
    print(f"[spike] activations after first query: {bridge.activations}")
    for element in elements:
        print(f"[spike]   child: {_describe(element)}")
        for grandchild in _children(element):
            print(f"[spike]     child: {_describe(grandchild)}")

    _dump_from_window(window._nswindow)

    window_frame = window._nswindow.frame()
    print(
        "[spike] window frame (screen, y up): "
        f"{(round(window_frame.origin.x), round(window_frame.origin.y))} "
        f"{(round(window_frame.size.width), round(window_frame.size.height))}"
    )

    import pyglet

    if stay:
        # Follow the Nuiitivet focus; a real bridge pushes on the change.
        pyglet.clock.schedule_interval(lambda dt: bridge.push(), 0.1)
        print("[spike] staying open: turn VoiceOver on (Cmd+F5) and check by hand.")
        return

    focused = _send(view, "accessibilityFocusedUIElement")
    print(f"[spike] focused before: {_describe(focused) if focused else None}")

    bridge.request_focus("reset")
    screen.increment()
    bridge.push()
    focused = _send(view, "accessibilityFocusedUIElement")
    print(f"[spike] focused after Nuiitivet focus moved: {_describe(focused) if focused else None}")

    root_children = _children(view)
    leaves = _children(root_children[0]) if len(root_children) == 1 else root_children
    for element in leaves:
        if _text(element.accessibilityTitle()) == "Increment":
            pressed = element.accessibilityPerformPress()
            print(f"[spike] accessibilityPerformPress returned {bool(pressed)}")
    print(f"[spike] actions received: {bridge.actions}")

    def finish(dt: float) -> None:
        print(f"[spike] count after press: {screen.count.value}")
        for element in _children(_children(view)[0]):
            print(f"[spike]   child after press: {_describe(element)}")
        app.exit()

    pyglet.clock.schedule_once(finish, 0.3)


def main() -> None:
    if sys.platform != "darwin":
        print("This spike is macOS-only.")
        return
    stay = "--stay" in sys.argv
    # A failure inside an AccessKit callback aborts the process; keep the log.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    screen = Screen()
    app = nv.App(nv.Window(content=screen, title="AccessKit spike", width=420, height=260))

    import pyglet

    def install(dt: float) -> None:
        pyglet_window = next(iter(pyglet.app.windows))
        bridge = Bridge(screen, app.main_window, pyglet_window)
        bridge.set_view_focused(True)
        screen.count.subscribe(lambda _: bridge.push())
        pyglet_window.push_handlers(
            on_activate=lambda: bridge.set_view_focused(True),
            on_deactivate=lambda: bridge.set_view_focused(False),
        )
        print("[spike] adapter installed")
        pyglet.clock.schedule_once(lambda dt: _read_back(bridge, screen, app, stay), 0.5)

    # Defer until the loop is running and the widgets are laid out.
    pyglet.clock.schedule_once(install, 0.5)
    app.run()
    print("[spike] App exited cleanly.")


if __name__ == "__main__":
    main()
