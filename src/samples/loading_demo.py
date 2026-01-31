"""MaterialOverlay.loading() demo.

Shows how to display a centered loading indicator overlay.
"""

from __future__ import annotations

import logging
from typing import Any

import nuiitivet as nv
import nuiitivet.material as md

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import runtime
from nuiitivet.overlay import OverlayHandle


_logger = logging.getLogger(__name__)


class LoadingDemo(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self._active_handle: OverlayHandle[Any] | None = None
        self._active_ctx: md.MaterialOverlay._LoadingContext | None = None

    def show_manual_overlay_loading(self) -> None:
        overlay = md.MaterialOverlay.root()
        handle = overlay.show(
            md.LoadingIndicator(size=48),
            passthrough=False,
            dismiss_on_outside_tap=False,
        )
        self._active_handle = handle

        def _close(_dt: float) -> None:
            try:
                handle.close(None)
            except Exception:
                exception_once(_logger, "loading_dialog_demo_close_exc", "Overlay handle.close raised")

        runtime.clock.schedule_once(_close, 2.0)

    def show_loading_context_non_blocking(self) -> None:
        """Show MaterialOverlay.loading() without blocking the UI thread."""
        overlay = md.MaterialOverlay.root()
        ctx = overlay.loading()
        ctx.__enter__()
        self._active_ctx = ctx

        def _close(_dt: float) -> None:
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                exception_once(_logger, "loading_dialog_demo_ctx_exit_exc", "Overlay loading context __exit__ raised")

        runtime.clock.schedule_once(_close, 2.0)

    def build(self) -> nv.Widget:
        return nv.Container(
            padding=32,
            child=nv.Column(
                children=[
                    md.Text("Overlay.loading() Demo"),
                    md.FilledButton("Show Overlay (manual, 2s)", on_click=self.show_manual_overlay_loading),
                    md.FilledButton(
                        "Show Overlay.loading() (context, 2s)",
                        on_click=self.show_loading_context_non_blocking,
                    ),
                    md.Text("Tip: Press Esc to close overlays."),
                ],
                gap=16,
                cross_alignment="start",
            ),
        )


def main() -> None:
    md.MaterialApp(content=LoadingDemo()).run()


if __name__ == "__main__":
    main()
