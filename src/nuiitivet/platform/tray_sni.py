"""Linux tray icon: ``TrayIcon`` model → StatusNotifierItem over D-Bus.

The bridge exports the item and its dbusmenu on the session bus and registers
with the desktop's StatusNotifierWatcher; the desktop draws the icon and the
menu. A receiver thread serves the desktop's calls, and activations hop onto
the UI thread through the runtime clock before they touch the model.

Without a watcher on the bus ``install()`` raises, and the ``TrayIcon`` model
turns that into a logged no-op with ``installed`` staying ``False``.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, Tuple

if sys.platform != "linux":  # pragma: no cover - guards the Linux-only dependency
    raise ImportError("tray_sni is only available on Linux")

from jeepney import DBusAddress, HeaderFields, MatchRule, MessageFlag, MessageType
from jeepney import message_bus, new_error, new_method_call, new_method_return, new_signal
from jeepney.io.blocking import Proxy, open_dbus_connection

from nuiitivet.menus import MenuEntry, read_value
from nuiitivet.observable import ObservableBase, runtime

from .tray_sni_plan import (
    LAYOUT_SIGNATURE,
    ROOT_ID,
    Pixmap,
    Variant,
    encode_layout,
    find_node,
    flatten,
    load_icon_argb,
    placeholder_icon,
    plan_menu,
    select_properties,
)

if TYPE_CHECKING:
    from .tray import TrayIcon

logger = logging.getLogger(__name__)

_BUS_NAME = "org.freedesktop.DBus"
_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
_WATCHER_NAME = "org.kde.StatusNotifierWatcher"
_WATCHER = DBusAddress("/StatusNotifierWatcher", bus_name=_WATCHER_NAME, interface=_WATCHER_NAME)
_ITEM = DBusAddress("/StatusNotifierItem", interface="org.kde.StatusNotifierItem")
_MENU = DBusAddress("/MenuBar", interface="com.canonical.dbusmenu")

_ERROR_UNKNOWN_METHOD = "org.freedesktop.DBus.Error.UnknownMethod"
_ERROR_INVALID_ARGS = "org.freedesktop.DBus.Error.InvalidArgs"

_REPLY_TIMEOUT = 5.0
_STOP_TIMEOUT = 2.0

_PIXMAPS_SIGNATURE = "a(iiay)"

# A method's reply: the body signature and the body.
_Reply = Tuple[Optional[str], Tuple[Any, ...]]
_NO_VALUE: _Reply = (None, ())


class TraySniBridge:
    """Installs a :class:`TrayIcon` as a StatusNotifierItem. Framework-internal."""

    def __init__(self, tray: "TrayIcon") -> None:
        self._tray = tray
        self._conn: Any = None
        self._thread: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()
        self._subscriptions: List[Any] = []
        self._commands: Dict[int, MenuEntry] = {}
        self._icon: Pixmap = placeholder_icon()
        self._revision = 1
        self._register_serial = 0
        self._register_error: Optional[str] = None
        self._registered = threading.Event()

    def install(self) -> None:
        """Show the icon; raises when the session has no bus or no tray host."""
        conn = open_dbus_connection(bus="SESSION")
        try:
            bus = Proxy(message_bus, conn, timeout=_REPLY_TIMEOUT)
            if not bus.NameHasOwner(_WATCHER_NAME)[0]:
                raise RuntimeError("no StatusNotifierWatcher on the session bus; the desktop hosts no tray icons")
            # A restarted desktop shell forgets every item; this signal says when to register again.
            watcher_changes = MatchRule(
                type="signal", sender=_BUS_NAME, interface=_BUS_NAME, member="NameOwnerChanged"
            )
            watcher_changes.add_arg_condition(0, _WATCHER_NAME)
            bus.AddMatch(watcher_changes)
        except Exception:
            conn.close()
            raise

        _, self._commands = plan_menu(self._tray.menu)
        self._icon = self._load_icon()
        self._conn = conn
        self._thread = threading.Thread(target=self._run, args=(conn,), name="nuiitivet-tray", daemon=True)
        self._thread.start()

        self._register()
        if not self._registered.wait(timeout=_REPLY_TIMEOUT) or self._register_error is not None:
            error = self._register_error or "no reply"
            self.uninstall()
            raise RuntimeError(f"StatusNotifierWatcher refused the tray icon: {error}")
        self._subscribe()

    def uninstall(self) -> None:
        """Remove the icon and stop the receiver thread."""
        subscriptions, self._subscriptions = self._subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()
        conn, self._conn = self._conn, None
        thread, self._thread = self._thread, None
        if conn is None:
            return
        try:
            # Wakes the receiver out of its blocking read; the bus drops the item with the connection.
            conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        if thread is not None:
            thread.join(timeout=_STOP_TIMEOUT)
        conn.close()

    # ---- Model → desktop ----------------------------------------------------

    def _subscribe(self) -> None:
        tooltip = self._tray.tooltip
        if isinstance(tooltip, ObservableBase):

            def on_tooltip(_value: Any) -> None:
                self._send(new_signal(_ITEM, "NewTitle"))
                self._send(new_signal(_ITEM, "NewToolTip"))

            self._subscriptions.append(tooltip.subscribe(on_tooltip))

        def on_menu(_value: Any) -> None:
            self._revision += 1
            self._send(new_signal(_MENU, "LayoutUpdated", "ui", (self._revision, ROOT_ID)))

        def walk(entries: Sequence[MenuEntry]) -> None:
            for entry in entries:
                for prop in (entry.label, entry.enabled, entry.checked):
                    if isinstance(prop, ObservableBase):
                        self._subscriptions.append(prop.subscribe(on_menu))
                if entry.submenu is not None:
                    walk(entry.submenu)

        walk(self._tray.menu)

    def _load_icon(self) -> Pixmap:
        path = self._tray.icon_path
        if path is not None:
            try:
                pixmap = load_icon_argb(path)
            except Exception:
                pixmap = None
            if pixmap is not None:
                return pixmap
            logger.warning("Tray icon image failed to load: %s", path)
        return placeholder_icon()

    def _send(self, message: Any, serial: Optional[int] = None) -> None:
        conn = self._conn
        if conn is None:
            return
        try:
            with self._send_lock:
                conn.send(message, serial=serial)
        except OSError:
            logger.debug("Tray D-Bus send failed", exc_info=True)

    def _register(self) -> None:
        conn = self._conn
        if conn is None:
            return
        # The reply arrives on the receiver thread, matched by this serial.
        self._register_serial = next(conn.outgoing_serial)
        call = new_method_call(_WATCHER, "RegisterStatusNotifierItem", "s", (_ITEM.object_path,))
        self._send(call, serial=self._register_serial)

    # ---- Receiver thread ------------------------------------------------------

    def _run(self, conn: Any) -> None:
        while True:
            try:
                message = conn.receive()
            except Exception:
                # The socket was shut down by uninstall(), or the bus went away.
                return
            try:
                self._dispatch(message)
            except Exception:
                logger.exception("tray D-Bus message handling raised")

    def _dispatch(self, message: Any) -> None:
        header = message.header
        fields = header.fields
        kind = header.message_type
        if kind is MessageType.method_call:
            self._answer(message)
        elif kind is MessageType.signal:
            if fields.get(HeaderFields.member) == "NameOwnerChanged" and message.body[2]:
                self._register()
        elif fields.get(HeaderFields.reply_serial) == self._register_serial:
            if kind is MessageType.error:
                self._register_error = str(fields.get(HeaderFields.error_name))
            self._registered.set()

    def _answer(self, call: Any) -> None:
        fields = call.header.fields
        path = fields.get(HeaderFields.path)
        interface = fields.get(HeaderFields.interface)
        member = fields.get(HeaderFields.member)
        reply: Any
        try:
            result = self._call(path, interface, member, call.body)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            reply = new_error(call, _ERROR_INVALID_ARGS, "s", (str(exc),))
        else:
            if result is None:
                reply = new_error(call, _ERROR_UNKNOWN_METHOD, "s", (f"{interface}.{member}",))
            else:
                reply = new_method_return(call, result[0], result[1])
        if not call.header.flags & MessageFlag.no_reply_expected:
            self._send(reply)

    def _call(self, path: str, interface: str, member: str, body: Tuple[Any, ...]) -> Optional[_Reply]:
        """Run one method call; ``None`` for a method this object does not have."""
        if interface == _PROPERTIES_INTERFACE:
            properties = self._item_properties() if path == _ITEM.object_path else self._menu_properties()
            if member == "Get":
                return "v", (properties[body[1]],)
            if member == "GetAll":
                return "a{sv}", (properties,)
            return None
        if path == _ITEM.object_path and interface == _ITEM.interface:
            return self._item_call(member)
        if path == _MENU.object_path and interface == _MENU.interface:
            return self._menu_call(member, body)
        return None

    def _item_call(self, member: str) -> Optional[_Reply]:
        if member == "Activate":
            self._hop(self._tray._fire_activate)
            return _NO_VALUE
        if member in ("SecondaryActivate", "ContextMenu", "Scroll"):
            return _NO_VALUE
        return None

    def _menu_call(self, member: str, body: Tuple[Any, ...]) -> Optional[_Reply]:
        if member == "GetLayout":
            parent, depth, names = body
            root, _ = plan_menu(self._tray.menu)
            node = find_node(root, parent)
            if node is None:
                raise KeyError(f"no menu item {parent}")
            return "u" + LAYOUT_SIGNATURE, (self._revision, encode_layout(node, depth, names))
        if member == "GetGroupProperties":
            ids, names = body
            root, _ = plan_menu(self._tray.menu)
            nodes = [node for node in flatten(root) if not ids or node.id in ids]
            return "a(ia{sv})", ([(node.id, select_properties(node, names)) for node in nodes],)
        if member == "GetProperty":
            root, _ = plan_menu(self._tray.menu)
            node = find_node(root, body[0])
            if node is None:
                raise KeyError(f"no menu item {body[0]}")
            return "v", (node.properties[body[1]],)
        if member == "Event":
            self._menu_event(body[0], body[1])
            return _NO_VALUE
        if member == "EventGroup":
            for event in body[0]:
                self._menu_event(event[0], event[1])
            return "ai", ([],)
        if member == "AboutToShow":
            return "b", (False,)
        if member == "AboutToShowGroup":
            return "aiai", ([], [])
        return None

    def _menu_event(self, item_id: int, event: str) -> None:
        entry = self._commands.get(item_id)
        if event == "clicked" and entry is not None:
            tray = self._tray
            self._hop(lambda: tray._activate_item(entry))

    def _item_properties(self) -> Dict[str, Variant]:
        tray = self._tray
        title = str(read_value(tray.tooltip) or "")
        no_pixmaps: Variant = (_PIXMAPS_SIGNATURE, [])
        return {
            "Category": ("s", "ApplicationStatus"),
            "Id": ("s", Path(sys.argv[0]).stem or "nuiitivet"),
            "Title": ("s", title),
            "Status": ("s", "Active"),
            "WindowId": ("i", 0),
            "IconThemePath": ("s", ""),
            "IconName": ("s", ""),
            "IconPixmap": (_PIXMAPS_SIGNATURE, [self._icon]),
            "OverlayIconName": ("s", ""),
            "OverlayIconPixmap": no_pixmaps,
            "AttentionIconName": ("s", ""),
            "AttentionIconPixmap": no_pixmaps,
            "AttentionMovieName": ("s", ""),
            "ToolTip": ("(s" + _PIXMAPS_SIGNATURE + "ss)", ("", [], title, "")),
            # With no activate handler the primary click has nothing to do but open the menu.
            "ItemIsMenu": ("b", bool(tray.menu) and tray._on_activate is None),
            "Menu": ("o", _MENU.object_path),
        }

    def _menu_properties(self) -> Dict[str, Variant]:
        return {
            "Version": ("u", 3),
            "TextDirection": ("s", "ltr"),
            "Status": ("s", "normal"),
            "IconThemePath": ("as", []),
        }

    def _hop(self, fn: Callable[[], None]) -> None:
        """Run ``fn`` on the UI thread."""
        runtime.clock.schedule_once(lambda _dt: fn(), 0.0)
