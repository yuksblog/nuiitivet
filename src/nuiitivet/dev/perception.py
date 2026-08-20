"""The bridge's view of perception: :mod:`nuiitivet._interaction.perception`, unchanged.

Perception is driver-agnostic -- it reads a mounted tree and nothing else -- so it
lives in the shared core, outside this dev-session-gated package. This module is
the bridge's view of it: the names the bridge and its tests reach for, and no
more. Anything else the core offers is imported from the core.
"""

from __future__ import annotations

from nuiitivet._interaction.perception import (
    describe_state,
    describe_tree,
    find_target,
    global_visual_rect,
    match_condition,
    pick_at,
)

__all__ = [
    "describe_state",
    "describe_tree",
    "find_target",
    "global_visual_rect",
    "match_condition",
    "pick_at",
]
