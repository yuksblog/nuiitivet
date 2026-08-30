"""Spike for issue #603: NSStatusItem coexistence with the pumped pyglet loop.

macOS only. Creates a native ``NSStatusItem`` (menu-bar extra) through pyglet's
bundled cocoapy — the same ctypes bridge ``nuiitivet.menus.nsmenu`` already
uses for the global menu bar — while a normal Nuiitivet window runs and
repaints. No pystray, no second thread, no loop handover.

Run it from a real terminal (GUI elements may not appear from agent-launched
processes)::

    python scripts/investigation/spike_tray_nsstatusitem.py

What to verify:

1. An "NV" item appears at the right side of the macOS menu bar.
2. The window's "uptime" counter ticks once a second (a worker thread writes
   an Observable; the write path marshals onto the UI thread).
3. Clicking the "NV" item opens its menu; "Ping" prints the delivering thread
   to the terminal (expected: MainThread, is_ui_thread=True) and bumps the
   ping counter shown in the window.
4. While the tray menu is held open, note whether the uptime counter keeps
   painting or pauses (menu tracking runs a Cocoa modal loop; a pause matches
   how the global menu bar already behaves and is acceptable — record it).
5. "Quit" exits the app cleanly and the "NV" item disappears from the menu bar.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import Any, Callable, List

import nuiitivet.material as nv

#: Callables dispatched by NSMenuItem tag, and Python-side references to every
#: ObjC object created, so nothing is collected while AppKit still points at it.
_ACTIONS: List[Callable[[], None]] = []
_RETAINED: List[Any] = []

# The implementation class must stay referenced for the lifetime of the
# process (see nuiitivet.menus.nsmenu: collecting it frees the ctypes
# trampolines behind the registered IMPs — a segfault on the first click).
_TARGET_IMPLEMENTATION: Any = None
_TARGET_CLASS: Any = None


def _target_class() -> Any:
    global _TARGET_IMPLEMENTATION, _TARGET_CLASS
    if _TARGET_CLASS is not None:
        return _TARGET_CLASS

    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCSubclass

    class _Implementation:
        SpikeTrayTarget = ObjCSubclass("NSObject", "SpikeTrayTarget")

        @SpikeTrayTarget.method("v@")
        def spikeMenuAction_(self, sender: Any) -> None:
            tag = int(sender.tag())
            if 0 <= tag < len(_ACTIONS):
                _ACTIONS[tag]()

    _TARGET_IMPLEMENTATION = _Implementation
    _TARGET_CLASS = ObjCClass("SpikeTrayTarget")
    return _TARGET_CLASS


def _install_status_item(pings: Any, app: nv.App) -> None:
    """Create the NSStatusItem with a two-entry menu. Runs on the UI thread."""
    from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString, get_selector

    NSStatusBar = ObjCClass("NSStatusBar")
    NSMenu = ObjCClass("NSMenu")
    NSMenuItem = ObjCClass("NSMenuItem")

    # NSVariableStatusItemLength == -1.0. The bar does not retain for us
    # through cocoapy, so retain explicitly or the item vanishes.
    item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)
    item.retain()
    item.button().setTitle_(get_NSString("NV"))

    menu = NSMenu.alloc().initWithTitle_(get_NSString("SpikeTray"))
    menu.setAutoenablesItems_(False)

    target = _target_class().alloc().init()

    def add_item(title: str, action: Callable[[], None]) -> Any:
        ns_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_NSString(title), get_selector("spikeMenuAction:"), get_NSString("")
        )
        ns_item.setTarget_(target)
        ns_item.setTag_(len(_ACTIONS))
        _ACTIONS.append(action)
        menu.addItem_(ns_item)
        return ns_item

    def ping() -> None:
        from nuiitivet.runtime.threading import is_ui_thread

        print(
            f"[spike] Ping delivered on thread={threading.current_thread().name!r} "
            f"is_ui_thread={is_ui_thread()}"
        )
        pings.value += 1

    def quit_app() -> None:
        print("[spike] Quit selected; removing status item and exiting.")
        NSStatusBar.systemStatusBar().removeStatusItem_(item)
        app.exit()

    ping_item = add_item("Ping", ping)
    menu.addItem_(NSMenuItem.separatorItem())
    quit_item = add_item("Quit spike", quit_app)

    item.setMenu_(menu)
    _RETAINED.extend((item, menu, target, ping_item, quit_item))
    print("[spike] NSStatusItem installed — look for 'NV' in the menu bar.")


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.uptime = nv.Observable(0)
        self.pings = nv.Observable(0)

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Tray spike (#603)", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.uptime.map(lambda s: f"uptime: {s}s (must keep ticking)")),
                nv.Text(self.pings.map(lambda n: f"tray pings: {n}")),
                nv.Text("Use the 'NV' menu-bar item: Ping, then Quit spike."),
            ],
            gap=12,
            padding=24,
        )


def main() -> None:
    if sys.platform != "darwin":
        print("This spike is macOS-only; use spike_tray_pystray.py elsewhere.")
        return

    screen = Screen()
    app = nv.App(nv.Window(content=screen, title="tray spike", width=480, height=240))

    def tick(stop: threading.Event) -> None:
        # Worker-thread writes: the Observable write path marshals to the UI
        # thread — the same path tray callbacks would rely on under pystray.
        while not stop.is_set():
            time.sleep(1.0)
            screen.uptime.value += 1

    stop = threading.Event()
    threading.Thread(target=tick, args=(stop,), name="spike-ticker", daemon=True).start()

    # Defer installation until the loop is running and NSApplication is up.
    import pyglet

    pyglet.clock.schedule_once(lambda dt: _install_status_item(screen.pings, app), 0.5)

    try:
        app.run()
    finally:
        stop.set()
    print("[spike] App exited cleanly.")


if __name__ == "__main__":
    main()
