"""Interactive demo for issue #365 — ForEach lifecycle churn.

Every ForEach item registers ``on_mount`` / ``on_unmount`` modifiers that append
to a shared log. Watching that log while you add / insert / remove / shuffle the
list makes the fix observable:

* the initial render fires each item's ``on_mount`` exactly once,
* appending, inserting or removing one item leaves every surviving item mounted
  (no ``mount`` / ``unmount`` churn), thanks to a stable ``key``,
* removing an item fires exactly one ``unmount``.

Before the fix each item mounted twice on first render, and any append/insert
tore down and re-mounted every surviving item.

Run interactively (needs pyglet/skia):

    python scripts/debug/for_each_lifecycle_demo.py

Run the headless self-check (no GUI deps, prints the log deltas):

    python scripts/debug/for_each_lifecycle_demo.py --headless
"""

from __future__ import annotations

import logging
import sys
from typing import List, Tuple

import nuiitivet.material as nv

_logger = logging.getLogger(__name__)

# An item is (stable_id, label). The stable id is what we key on, so reordering
# or inserting never changes an existing item's identity.
Item = Tuple[int, str]


class LifecycleDemoModel:
    """Holds the item list plus a running lifecycle log."""

    items: nv.Observable[List[Item]] = nv.Observable([])
    log: nv.Observable[str] = nv.Observable("")

    def __init__(self) -> None:
        self._next_id = 0
        self._lines: List[str] = []
        self.items.value = [self._new_item(), self._new_item()]

    def _new_item(self) -> Item:
        self._next_id += 1
        return (self._next_id, f"Item {self._next_id}")

    def record(self, message: str) -> None:
        """Append a lifecycle event to the visible log (and stdout)."""
        print(f"[lifecycle] {message}")
        self._lines.append(message)
        del self._lines[:-18]  # keep only the most recent lines on screen
        self.log.value = "\n".join(self._lines)

    # --- mutations ----------------------------------------------------------
    def append_item(self) -> None:
        self.items.value = [*self.items.value, self._new_item()]

    def insert_head(self) -> None:
        self.items.value = [self._new_item(), *self.items.value]

    def remove_last(self) -> None:
        current = list(self.items.value)
        if current:
            current.pop()
            self.items.value = current

    def shuffle(self) -> None:
        # A deterministic rotation is enough to prove reordering causes no churn.
        current = list(self.items.value)
        if len(current) > 1:
            self.items.value = current[1:] + current[:1]

    def clear_log(self) -> None:
        self._lines.clear()
        self.log.value = ""


def _build_item(model: LifecycleDemoModel, item: Item, index: int) -> nv.Widget:
    del index
    _id, label = item
    return nv.Card(
        nv.Text(label),
        padding=6,
        style=nv.CardStyle.filled().copy_with(border_radius=6),
        alignment="center",
    ).modifier(
        nv.on_mount(lambda: model.record(f"mount   {label}")) | nv.on_unmount(lambda: model.record(f"unmount {label}"))
    )


class LifecycleDemo(nv.ComposableWidget):
    def __init__(self, model: LifecycleDemoModel) -> None:
        super().__init__()
        self.model = model

    def build(self) -> nv.Widget:
        controls = nv.Row(
            [
                nv.Button("Append", on_click=self.model.append_item, style=nv.ButtonStyle.filled()),
                nv.Button("Insert head", on_click=self.model.insert_head, style=nv.ButtonStyle.tonal()),
                nv.Button("Remove last", on_click=self.model.remove_last, style=nv.ButtonStyle.outlined()),
                nv.Button("Shuffle", on_click=self.model.shuffle, style=nv.ButtonStyle.elevated()),
                nv.Button("Clear log", on_click=self.model.clear_log, style=nv.ButtonStyle.text()),
            ],
            gap=8,
            cross_alignment="center",
        )

        item_list = nv.Card(
            nv.Column(
                children=[
                    nv.ForEach(
                        self.model.items,
                        lambda item, idx: _build_item(self.model, item, idx),
                        key=lambda it, i: it[0],
                    )
                ],
                gap=8,
                cross_alignment="start",
            ),
            padding=8,
            style=nv.CardStyle.outlined().copy_with(border_radius=6),
            alignment="start",
        )

        log_view = nv.Card(
            nv.Column(
                [
                    nv.Text("Lifecycle log (newest at bottom):"),
                    nv.VerticalScrollable(
                        nv.Text(self.model.log),
                        width=nv.Sizing.flex(),
                    ),
                ],
                gap=6,
                cross_alignment="start",
                height=220,
            ),
            padding=8,
            style=nv.CardStyle.filled().copy_with(border_radius=6),
            alignment="start",
        )

        return nv.Column(
            [
                nv.Text("ForEach lifecycle demo (#365)"),
                controls,
                nv.Row(
                    [
                        item_list,
                        log_view,
                    ],
                    padding=12,
                    gap=12,
                    cross_alignment="start",
                ),
            ],
        )


class _DummyApp:
    """Minimal host so the headless path can mount widgets without a backend."""

    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _run_headless() -> None:
    """Drive the model through a scripted scenario and print each log delta."""
    model = LifecycleDemoModel()
    root = nv.Column(
        children=[
            nv.ForEach(
                model.items,
                lambda item, idx: _build_item(model, item, idx),
                key=lambda it, i: it[0],
            )
        ]
    )

    print("== initial mount (expect: mount Item 1, mount Item 2) ==")
    root.mount(_DummyApp())

    scenario = [
        ("append (expect: mount of the new item only)", model.append_item),
        ("insert head (expect: mount of the new item only)", model.insert_head),
        ("remove last (expect: unmount of the removed item only)", model.remove_last),
        ("shuffle (expect: no mount/unmount at all)", model.shuffle),
    ]
    for description, action in scenario:
        model.clear_log()
        print(f"\n== {description} ==")
        action()
        if not model.log.value:
            print("[lifecycle] (no lifecycle events)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if "--headless" in sys.argv[1:]:
        _run_headless()
        raise SystemExit(0)

    model = LifecycleDemoModel()
    app = nv.App(content=LifecycleDemo(model), title="ForEach Lifecycle Demo (#365)")
    try:
        app.run()
    except Exception:
        _logger.exception("Interactive run failed; falling back to headless self-check")
        print("Could not start the interactive app; running headless self-check instead.\n")
        _run_headless()
