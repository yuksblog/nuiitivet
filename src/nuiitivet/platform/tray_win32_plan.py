"""The platform-free half of the Windows tray backend.

What the popup menu and the icon bitmap will be, computed without a Win32
call, so it runs and is tested on every platform. ``tray_win32`` turns the
results into an ``HMENU`` and an ``HICON``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from nuiitivet.menus import MenuEntry

MF_STRING = 0x0000
MF_GRAYED = 0x0001
MF_CHECKED = 0x0008
MF_POPUP = 0x0010
MF_SEPARATOR = 0x0800

# TrackPopupMenu returns 0 for a dismissed menu, so command ids start above it.
_FIRST_COMMAND_ID = 1


@dataclass(frozen=True)
class MenuItemPlan:
    """One ``AppendMenuW`` call.

    Attributes:
        label: Item text with ``&`` escaped; empty for a separator.
        flags: The ``MF_*`` flags.
        command_id: Id ``TrackPopupMenu`` returns for the item; ``0`` for a
            separator or a submenu.
        children: The submenu's items; empty unless ``flags`` has ``MF_POPUP``.
    """

    label: str
    flags: int
    command_id: int = 0
    children: Tuple["MenuItemPlan", ...] = ()


def plan_menu(
    entries: Sequence[MenuEntry],
) -> Tuple[Tuple[MenuItemPlan, ...], Dict[int, MenuEntry]]:
    """Plan the popup menu for ``entries`` as they are now.

    Args:
        entries: The tray menu's top-level entries.

    Returns:
        The items in display order, and the entry each command id activates.
    """
    commands: Dict[int, MenuEntry] = {}
    return _plan_level(entries, commands), commands


def _plan_level(entries: Sequence[MenuEntry], commands: Dict[int, MenuEntry]) -> Tuple[MenuItemPlan, ...]:
    items = []
    for entry in entries:
        if entry.is_separator:
            items.append(MenuItemPlan("", MF_SEPARATOR))
            continue
        # A lone "&" would underline the next character as a mnemonic.
        label = entry.resolved_label().replace("&", "&&")
        flags = MF_STRING if entry.resolved_enabled() else MF_STRING | MF_GRAYED
        if entry.submenu is not None:
            children = _plan_level(entry.submenu, commands)
            items.append(MenuItemPlan(label, flags | MF_POPUP, children=children))
            continue
        if entry.checked is not None and entry.checked.value:
            flags |= MF_CHECKED
        command_id = _FIRST_COMMAND_ID + len(commands)
        commands[command_id] = entry
        items.append(MenuItemPlan(label, flags, command_id))
    return tuple(items)


def load_icon_bgra(path: Path, size: int) -> Optional[bytes]:
    """Decode the image at ``path`` into ``size`` x ``size`` icon pixels.

    Args:
        path: The image file.
        size: Edge length in pixels.

    Returns:
        Top-down BGRA rows with straight alpha, or ``None`` when the file
        cannot be decoded.
    """
    import skia

    data = skia.Data.MakeFromFileName(str(path))
    image = skia.Image.MakeFromEncoded(data) if data is not None else None
    if image is None:
        return None
    if (image.width(), image.height()) != (size, size):
        image = image.resize(size, size, skia.SamplingOptions(skia.FilterMode.kLinear))
    info = skia.ImageInfo.Make(size, size, skia.kBGRA_8888_ColorType, skia.kUnpremul_AlphaType)
    pixels = bytearray(size * size * 4)
    if not image.readPixels(info, pixels, size * 4):
        return None
    return bytes(pixels)
