"""Manual IME check: two windows, one text field each (issue #625).

Run from a real terminal (not agent-launched) so the OS input method engages:

    python scripts/debug/ime_two_windows.py

Manual pass, with a Japanese (or other composing) IME active:

1. Start a composition in window A (type, do not confirm), then click
   window B: A's provisional text must be committed (it stays, no underline),
   and typing in B must start a clean composition.
2. With B's field focused, compose in B: the candidate window must appear at
   B's cursor — including right after switching from A, and after moving B.
3. Switch back to A mid-composition-in-B, then to B again, and type: no stale
   or resumed marked text.
"""

from __future__ import annotations

import nuiitivet.material as nv


def _content(title: str) -> nv.Widget:
    return nv.Column(
        children=[
            nv.Text(title, type_scale=nv.TypeScale.TITLE_SMALL),
            nv.TextField(value="", label="Type here"),
        ],
        gap=12,
        padding=24,
    )


def main() -> None:
    app = nv.App(nv.Window(content=lambda: _content("Window A"), title="IME A", width=360, height=160))
    nv.Window(content=lambda: _content("Window B"), title="IME B", width=360, height=160).open()
    app.run()


if __name__ == "__main__":
    main()
