"""Layout metrics helpers (padding, spacing, offsets, space distribution).

This module contains numeric helpers used by layout containers. It replaces
the older `layout/utils.py` module and is intended to clarify the module's
purpose (metrics/measurements rather than a generic "utils").
"""

import logging
from typing import List, Tuple, Union

from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


def normalize_padding(pad: Union[int, Tuple[int, int], Tuple[int, int, int, int]]):
    if isinstance(pad, int):
        return (pad, pad, pad, pad)
    if isinstance(pad, (list, tuple)):
        if len(pad) == 2:
            h, v = pad
            return (h, v, h, v)
        if len(pad) == 4:
            return (pad[0], pad[1], pad[2], pad[3])
    return (0, 0, 0, 0)


def compute_prefix_offsets(sizes: List[int], spacing: int) -> List[int]:
    offsets: List[int] = []
    cur = 0
    for i, s in enumerate(sizes):
        offsets.append(cur)
        cur += max(0, int(s)) + (spacing if i < len(sizes) - 1 else 0)
    return offsets


def distribute_space(prefs: List[int], total: int, spacing: int) -> List[int]:
    n = len(prefs)
    if n == 0:
        return []
    spacing = max(0, int(spacing))
    usable = max(0, total - max(0, n - 1) * spacing)
    prefs_nonneg = [max(0, int(p)) for p in prefs]
    total_pref = sum(prefs_nonneg)

    alloc: List[int] = []
    if total_pref == 0:
        base = usable // n if n > 0 else 0
        alloc = [base] * n
    else:
        for p in prefs_nonneg:
            w = int(p / total_pref * usable) if total_pref > 0 else 0
            alloc.append(max(0, w))

    used = sum(alloc)
    leftover = usable - used
    if leftover > 0 and n > 0:
        for i in range(leftover):
            alloc[i % n] += 1
    return alloc


def align_offset(container: int, child: int, align: str) -> int:
    c = max(0, int(container))
    ch = max(0, int(child))
    if c <= 0:
        return 0
    if align == "start":
        return 0
    if align == "center":
        return max(0, (c - ch) // 2)
    if align == "end":
        return max(0, c - ch)
    else:
        exception_once(logger, "metrics_align_offset_exec", f"Unknown alignment '{align}', defaulting to 'start'")
        return 0


def compute_aligned_offsets(
    sizes: List[int],
    total_space: int,
    gap: int,
    alignment: str,
) -> List[int]:
    """Compute offsets for children based on main-axis alignment."""
    n = len(sizes)
    if n == 0:
        return []

    total_children_size = sum(sizes)
    total_gap = max(0, n - 1) * gap
    content_size = total_children_size + total_gap
    free_space = max(0, total_space - content_size)

    if alignment == "start":
        return compute_prefix_offsets(sizes, gap)

    if alignment == "center":
        start_offset = free_space // 2
        offsets = compute_prefix_offsets(sizes, gap)
        return [o + start_offset for o in offsets]

    if alignment == "end":
        start_offset = free_space
        offsets = compute_prefix_offsets(sizes, gap)
        return [o + start_offset for o in offsets]

    if alignment == "space-between":
        if n == 1:
            return [0]
        step = free_space // (n - 1)
        rem = free_space % (n - 1)
        offsets = []
        cur = 0
        for i in range(n):
            offsets.append(cur)
            if i < n - 1:
                extra = step + (1 if i < rem else 0)
                cur += sizes[i] + gap + extra
        return offsets

    if alignment == "space-around":
        unit = free_space // n
        rem = free_space % n
        offsets = []
        cur = 0
        for i in range(n):
            my_extra = unit + (1 if i < rem else 0)
            before = my_extra // 2
            after = my_extra - before
            cur += before
            offsets.append(cur)
            cur += sizes[i] + gap + after
        return offsets

    if alignment == "space-evenly":
        count = n + 1
        unit = free_space // count
        rem = free_space % count
        offsets = []
        cur = 0
        for i in range(n):
            # Gap i is before item i
            gap_val = unit + (1 if i < rem else 0)
            cur += gap_val
            offsets.append(cur)
            cur += sizes[i] + gap
        return offsets

    # Fallback to start
    return compute_prefix_offsets(sizes, gap)
