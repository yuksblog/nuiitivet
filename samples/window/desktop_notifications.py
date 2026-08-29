"""Desktop notifications: nv.Desktop.notify from a handler and from a worker thread

Demonstrates:
- nv.Desktop.notify(title, body) raising an OS notification immediately
- Notifying from a worker thread when a long job finishes — the case
  notifications exist for: the user has switched to another window
- notify never raises and never blocks; delivery is best-effort
"""

import threading
import time

import nuiitivet.material as nv


class NotificationDemo(nv.ComposableWidget):
    running = nv.Observable(False)
    status = nv.Observable("idle")

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            gap=12,
            children=[
                nv.Text(self.status),
                nv.Button("Notify now", on_click=self._notify_now),
                nv.Button(
                    "Run a 3 s job, notify when done",
                    on_click=self._start_job,
                    disabled=self.running,
                ),
            ],
        )

    def _notify_now(self) -> None:
        nv.Desktop.notify("Hello from nuiitivet", "Raised straight from an event handler")
        self.status.value = "notified"

    def _start_job(self) -> None:
        self.running.value = True
        self.status.value = "working… switch to another window"
        threading.Thread(target=self._job, daemon=True).start()

    def _job(self) -> None:
        time.sleep(3.0)
        # Safe from a worker thread: no marshalling to the UI thread needed.
        nv.Desktop.notify("Job finished", "The 3-second job is done")
        self.running.value = False
        self.status.value = "done — check your notifications"


def main() -> None:
    nv.App(nv.Window(content=NotificationDemo, title="Desktop notifications")).run()


if __name__ == "__main__":
    main()
