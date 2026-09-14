"""What the dev overlays' captions are made of, shared by the modes composing them and the painters drawing them."""

from __future__ import annotations

#: Between the parts of a caption or a hint line. ASCII on purpose: the
#: overlay draws with the platform's UI font, and a middle dot is missing from
#: macOS's, which paints it as a box.
SEPARATOR = "  |  "

__all__ = ["SEPARATOR"]
