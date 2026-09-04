"""Observable: Thread Safety

Demonstrates:
- Cross-thread writes marshalled onto the UI thread automatically
- Async data loading from a worker thread
- The same work awaited instead: asyncio.to_thread() inside while_loading()
- Loading / error / success state held on the widget itself
"""

import asyncio
import threading
import time

import nuiitivet.material as nv


class ThreadSafetyApp(nv.ComposableWidget):
    """Fetches data on a worker thread; observables are dispatched to the UI thread."""

    data: nv.Observable[str | None] = nv.Observable(None)
    loading: nv.Observable[bool] = nv.Observable(False)
    error: nv.Observable[str | None] = nv.Observable(None)

    def __init__(self) -> None:
        super().__init__()
        # Nothing to enable: a write from the worker below is marshalled onto
        # the UI thread because that is what an Observable does by default.

        # Derived values built on top of dispatched observables
        self.status_text = self.loading.map(lambda loading: "⏳ Loading…" if loading else "")
        self.data_text = self.data.map(lambda d: d if d is not None else "(no data loaded yet)")
        self.error_text = self.error.map(lambda e: f"⚠ {e}" if e else "")

        # Derivations inherit the source's setting, so this marshals too.
        self.data_upper = self.data.map(lambda d: d.upper() if d else "")

    def fetch(self, should_fail: bool = False) -> None:
        """Spawn a worker thread that updates observables safely."""

        def worker() -> None:
            try:
                self.loading.value = True
                self.error.value = None
                self.data.value = None

                time.sleep(1.2)  # Simulate network latency

                if should_fail:
                    raise RuntimeError("Simulated network error")

                self.data.value = f"Result fetched at {time.strftime('%H:%M:%S')}"

            except Exception as exc:
                self.error.value = str(exc)
            finally:
                self.loading.value = False

        threading.Thread(target=worker, daemon=True).start()

    def fetch_blocking(self, should_fail: bool = False) -> str:
        """The same work as a plain blocking call, meant to be awaited."""
        time.sleep(1.2)  # Simulate network latency
        if should_fail:
            raise RuntimeError("Simulated network error")
        return f"Result fetched at {time.strftime('%H:%M:%S')}"

    async def fetch_awaited(self) -> None:
        """Hand the thread to the runtime instead of spawning one.

        `while_loading()` owns the overlay for the duration of the block, and
        the line after the `await` is back on the UI thread — so there is no
        handle to hold and no subscription to dispose.
        """
        self.error.value = None
        self.data.value = None
        try:
            async with nv.Overlay.of(self).while_loading():
                result = await asyncio.to_thread(self.fetch_blocking)
            self.data.value = result
        except Exception as exc:
            self.error.value = str(exc)

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Thread Safety"),
                    nv.Text("Workers update observables from a background thread."),
                    nv.Text("Observable marshals those writes onto the UI thread."),
                    nv.Text(self.status_text),
                    nv.Text(self.data_text),
                    nv.Text(self.data_upper),
                    nv.Text(self.error_text),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Fetch (success)",
                                on_click=lambda: self.fetch(should_fail=False),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Fetch (error)",
                                on_click=lambda: self.fetch(should_fail=True),
                                style=nv.ButtonStyle.outlined(),
                            ),
                            nv.Button(
                                "Fetch (awaited)",
                                on_click=self.fetch_awaited,
                                style=nv.ButtonStyle.tonal(),
                            ),
                        ],
                    ),
                ],
            ),
        )


def main() -> None:
    app = nv.App(nv.Window(content=ThreadSafetyApp()))
    app.run()


if __name__ == "__main__":
    main()
