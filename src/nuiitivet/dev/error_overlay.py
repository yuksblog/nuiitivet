"""Surface reload errors without killing the app (§9.4 of HOT_RELOAD.md).

Editing is a half-broken-code activity: a syntax or build error on save must not
tear down the window or the debug session. When a reload fails the previous tree
is kept alive (the controller never commits the broken one) and the error is
reported two ways:

- always to ``stderr`` (shows up in the VSCode debug console / terminal), and
- best-effort as an on-screen banner over the still-running UI.

The banner is shown through the live overlay and cleared on the next successful
reload. Any failure to render the banner is swallowed — reporting must never
itself break the loop.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)

# The banner shown for a given app, so it can be dismissed later. Keyed by
# id(app); the value is (overlay, banner) so we only close the banner while its
# original overlay is still the live root — a successful reload rebuilds the tree
# (and the overlay), which discards the banner on its own.
_active_banner: dict[int, tuple[Any, Any]] = {}


def _build_banner(message: str) -> Any:
    import nuiitivet.material as nv

    # Keep it short; the full traceback is on stderr.
    lines = message.strip().splitlines()
    headline = lines[-1] if lines else "Reload failed"
    detail = "\n".join(lines[-6:]) if len(lines) > 1 else headline

    return nv.Container(
        width="wt",
        padding=12,
        child=nv.Column(
            gap=4,
            children=[
                nv.Text("⚠ Hot reload failed"),
                nv.Text(headline),
                nv.Text(detail),
            ],
        ),
    ).modifier(nv.background("#B3261E"))


def show_reload_error(app: Any, message: str) -> None:
    """Report a reload error to stderr and (best-effort) as an on-screen banner."""
    print("\n[nuiitivet.dev] hot reload failed — keeping the previous UI:\n", file=sys.stderr)
    print(message, file=sys.stderr, flush=True)

    try:
        overlay = app.overlay
        clear_reload_error(app)
        banner = _build_banner(message)
        overlay.show(banner, passthrough=True)
        _active_banner[id(app)] = (overlay, banner)
    except Exception:
        # A visible banner is a nicety; stderr already carried the report.
        logger.debug("hot reload: failed to show error banner", exc_info=True)


def clear_reload_error(app: Any) -> None:
    """Dismiss the error banner for ``app`` if one is showing.

    Only closes it while the banner's original overlay is still the App's live
    one. A successful reload rebuilds the tree (and overlay), which discards the
    banner already — attempting to close it against the new overlay would be a
    no-op that logs a spurious "no active overlay entry" warning.
    """
    entry: Optional[tuple[Any, Any]] = _active_banner.pop(id(app), None)
    if entry is None:
        return
    overlay, banner = entry
    try:
        if app.overlay is overlay:
            overlay.close(target=banner)
    except Exception:
        logger.debug("hot reload: failed to clear error banner", exc_info=True)
