"""The D-Bus-free half of the Linux tray backend.

What the dbusmenu layout and the icon pixmap will be, computed without a
bus, so it runs and is tested on every platform. ``tray_sni`` puts the
results on the wire. A variant is written as a ``(signature, value)`` pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from nuiitivet.menus import MenuEntry

Variant = Tuple[str, Any]
Pixmap = Tuple[int, int, bytes]

ROOT_ID = 0
LAYOUT_SIGNATURE = "(ia{sv}av)"

# Hosts scale the pixmap to the panel; a larger one only grows the message.
_MAX_ICON_EDGE = 128
_PLACEHOLDER_EDGE = 22


@dataclass(frozen=True)
class MenuNode:
    """One dbusmenu item.

    Attributes:
        id: The item id; the root is ``ROOT_ID``.
        properties: The dbusmenu properties as variants.
        children: The submenu's items.
    """

    id: int
    properties: Dict[str, Variant]
    children: Tuple["MenuNode", ...] = ()


def plan_menu(entries: Sequence[MenuEntry]) -> Tuple[MenuNode, Dict[int, MenuEntry]]:
    """Plan the dbusmenu tree for ``entries`` as they are now.

    Ids follow the tree's order, so the same tree always yields the same ids.

    Args:
        entries: The tray menu's top-level entries.

    Returns:
        The root node, and the entry each action's id activates.
    """
    commands: Dict[int, MenuEntry] = {}
    counter = [ROOT_ID]
    children = _plan_level(entries, commands, counter)
    return MenuNode(ROOT_ID, {"children-display": ("s", "submenu")}, children), commands


def _plan_level(
    entries: Sequence[MenuEntry], commands: Dict[int, MenuEntry], counter: List[int]
) -> Tuple[MenuNode, ...]:
    nodes = []
    for entry in entries:
        counter[0] += 1
        item_id = counter[0]
        if entry.is_separator:
            nodes.append(MenuNode(item_id, {"type": ("s", "separator")}))
            continue
        properties: Dict[str, Variant] = {
            # A lone "_" would mark the next character as a mnemonic.
            "label": ("s", entry.resolved_label().replace("_", "__")),
            "enabled": ("b", entry.resolved_enabled()),
        }
        if entry.submenu is not None:
            properties["children-display"] = ("s", "submenu")
            nodes.append(MenuNode(item_id, properties, _plan_level(entry.submenu, commands, counter)))
            continue
        if entry.checked is not None:
            properties["toggle-type"] = ("s", "checkmark")
            properties["toggle-state"] = ("i", 1 if entry.checked.value else 0)
        commands[item_id] = entry
        nodes.append(MenuNode(item_id, properties))
    return tuple(nodes)


def find_node(root: MenuNode, item_id: int) -> Optional[MenuNode]:
    """Return the node with ``item_id`` under ``root``, or ``None``."""
    if root.id == item_id:
        return root
    for child in root.children:
        found = find_node(child, item_id)
        if found is not None:
            return found
    return None


def flatten(root: MenuNode) -> List[MenuNode]:
    """Return ``root`` and every node under it, in tree order."""
    nodes = [root]
    for child in root.children:
        nodes.extend(flatten(child))
    return nodes


def select_properties(node: MenuNode, names: Sequence[str]) -> Dict[str, Variant]:
    """Return the properties of ``node`` named in ``names``; all of them when it is empty."""
    if not names:
        return dict(node.properties)
    return {name: value for name, value in node.properties.items() if name in names}


def encode_layout(node: MenuNode, depth: int, names: Sequence[str]) -> Tuple[int, Dict[str, Variant], List[Variant]]:
    """Encode ``node`` as the ``(ia{sv}av)`` structure ``GetLayout`` returns.

    Args:
        node: The subtree's root.
        depth: Levels of children to include; negative for all of them.
        names: Property names to include; empty for all of them.
    """
    children: List[Variant] = []
    if depth != 0:
        children = [(LAYOUT_SIGNATURE, encode_layout(child, depth - 1, names)) for child in node.children]
    return node.id, select_properties(node, names), children


def load_icon_argb(path: Path) -> Optional[Pixmap]:
    """Decode the image at ``path`` into a StatusNotifierItem pixmap.

    Args:
        path: The image file.

    Returns:
        Width, height and top-down ARGB rows in network byte order with
        straight alpha, or ``None`` when the file cannot be decoded.
    """
    import skia

    data = skia.Data.MakeFromFileName(str(path))
    image = skia.Image.MakeFromEncoded(data) if data is not None else None
    if image is None:
        return None
    width, height = image.width(), image.height()
    longest = max(width, height)
    if longest > _MAX_ICON_EDGE:
        width = max(1, width * _MAX_ICON_EDGE // longest)
        height = max(1, height * _MAX_ICON_EDGE // longest)
        image = image.resize(width, height, skia.SamplingOptions(skia.FilterMode.kLinear))
    info = skia.ImageInfo.Make(width, height, skia.kRGBA_8888_ColorType, skia.kUnpremul_AlphaType)
    rgba = bytearray(width * height * 4)
    if not image.readPixels(info, rgba, width * 4):
        return None
    argb = bytearray(len(rgba))
    argb[0::4] = rgba[3::4]
    argb[1::4] = rgba[0::4]
    argb[2::4] = rgba[1::4]
    argb[3::4] = rgba[2::4]
    return width, height, bytes(argb)


def placeholder_icon() -> Pixmap:
    """A neutral grey square, for a tray that has no usable icon file."""
    pixels = bytes((255, 128, 128, 128)) * (_PLACEHOLDER_EDGE * _PLACEHOLDER_EDGE)
    return _PLACEHOLDER_EDGE, _PLACEHOLDER_EDGE, pixels
