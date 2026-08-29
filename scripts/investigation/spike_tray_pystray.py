"""Spike for issue #603: pystray ``run_detached()`` alongside a Nuiitivet app.

Intended for **Windows and Linux** — on macOS use
``spike_tray_nsstatusitem.py`` (the direct cocoapy route; pystray's darwin
backend wants to own ``NSApplication``).

Requires the spike-only dependencies::

    pip install pystray pillow

Run from a real terminal::

    python scripts/investigation/spike_tray_pystray.py

What to verify:

1. A small two-tone square icon appears in the system tray
   (Linux: record the desktop environment — SNI/AppIndicator hosts differ,
   GNOME needs the AppIndicator extension, some Wayland setups show nothing).
2. The window's "uptime" counter ticks once a second throughout.
3. "Ping" in the tray menu prints the delivering thread to the terminal
   (expected: a pystray-owned worker thread, is_ui_thread=False) and bumps the
   ping counter in the window — proving the Observable write path marshals
   tray callbacks onto the UI thread.
4. "Quit spike" exits the app cleanly and removes the tray icon.
"""

from __future__ import annotations

import sys
import threading
import time

import nuiitivet.material as nv


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.uptime = nv.Observable(0)
        self.pings = nv.Observable(0)

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Tray spike, pystray (#603)", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.uptime.map(lambda s: f"uptime: {s}s (must keep ticking)")),
                nv.Text(self.pings.map(lambda n: f"tray pings: {n}")),
                nv.Text("Use the tray icon's menu: Ping, then Quit spike."),
            ],
            gap=12,
            padding=24,
        )


def main() -> None:
    if sys.platform == "darwin":
        print(
            "Note: on macOS the primary route is spike_tray_nsstatusitem.py; "
            "this pystray run is expected to fail or misbehave here."
        )

    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as exc:
        print(f"Missing spike dependency ({exc}); run: pip install pystray pillow")
        return

    screen = Screen()
    app = nv.App(nv.Window(content=screen, title="tray spike (pystray)", width=480, height=240))

    def make_icon_image() -> "Image.Image":
        image = Image.new("RGB", (64, 64), (30, 30, 30))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(0, 200, 120))
        return image

    def ping(icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
        from nuiitivet.runtime.threading import is_ui_thread

        print(
            f"[spike] Ping delivered on thread={threading.current_thread().name!r} "
            f"is_ui_thread={is_ui_thread()}"
        )
        # Worker-thread write; must marshal onto the UI thread and repaint.
        screen.pings.value += 1

    def quit_app(icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
        print("[spike] Quit selected; stopping icon and exiting.")
        icon.stop()
        # We are on pystray's thread; hand the exit to the UI loop.
        import pyglet

        pyglet.clock.schedule_once(lambda dt: app.exit(), 0.0)

    icon = pystray.Icon(
        "nuiitivet-spike",
        make_icon_image(),
        title="nuiitivet tray spike",
        menu=pystray.Menu(
            pystray.MenuItem("Ping", ping),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit spike", quit_app),
        ),
    )

    def tick(stop: threading.Event) -> None:
        while not stop.is_set():
            time.sleep(1.0)
            screen.uptime.value += 1

    stop = threading.Event()
    threading.Thread(target=tick, args=(stop,), name="spike-ticker", daemon=True).start()

    icon.run_detached()
    print("[spike] pystray icon started detached — look for it in the system tray.")

    try:
        app.run()
    finally:
        stop.set()
        icon.stop()
    print("[spike] App exited cleanly.")


if __name__ == "__main__":
    main()
