"""Layout edit mode: the human drags a widget, and the runner edits the source.

The sibling of :mod:`.select_mode`, on the same real input handlers, with the
opposite division of labour. Select mode is how the human *says* something to
the assistant; this is how they *do* something with no assistant in the loop.
A corner drag resolves to ``width`` / ``height`` / ``size`` as ``int``,
``"auto"`` or ``"wt"`` (:mod:`.landing`); a body drag resolves to a slot among
the widget's siblings, a cell, or another container's children
(:mod:`.reorder`) -- or, when it keeps the widget's place, to its container's
alignment (:mod:`.align`). Release writes the keyword, or moves the element,
in the calls that built them (:mod:`.source_edit`), and the hot reload that
follows is what applies it. The tree is never touched directly: what is on
screen always came from the code.

``Delete`` on the selection removes its expression the same way, with no
confirmation. Latched on ``Ctrl+Shift+E``, off on ``Esc``. Its chord and
select mode's switch directly, each mode closing the other on entry. There is
no commit: every release writes, so ``Ctrl+Z`` is what "I did not mean that"
reaches for, and ``Ctrl+Shift+Z`` takes it back.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from nuiitivet._interaction.perception import ancestors, global_visual_rect
from nuiitivet.input.codes import MOD_ALT, resolve_modifiers
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.grid import Grid
from nuiitivet.layout.stack import Stack

from . import align, landing, reorder
from .gesture import accel_held, child_toward, chord_held, invalidate, parent_of, pick, travelled, weak
from .hud import SEPARATOR, Placement
from .snapshot import Path, path_of, widgets_by_path
from .source import Frame, construction_frame, site_owner, widgets_built_at
from .source_edit import (
    SNAP_BAND,
    Edit,
    EditLog,
    Refusal,
    Value,
    cell_refusal,
    children_list,
    discarded_keywords,
    grid_item_name,
    host_child_refusal,
    is_project_file,
    plan_alignment,
    plan_area,
    plan_cell,
    plan_delete,
    plan_keywords,
    plan_move,
    plan_move_across,
    written_alignment,
)

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]

# The key that enters the mode. ``E`` for *edit*, and it keeps the chord under
# the left hand while the right is on the mouse.
_ENTER_KEY = "e"
# Select mode's key, ``D`` for *designate*. Its chord is let through while this
# mode is latched, so the two switch directly; the mode that enters closes the
# other.
_SELECT_KEY = "d"
# Logical pixels around each corner of the candidate within which a press is a
# grab of that corner rather than a click.
_CORNER_GRAB = 10.0
# Both, since a Mac keyboard has no Delete key.
_DELETE_KEYS = ("delete", "backspace")
# The keys a drag answers to: under the left hand while the right holds the
# mouse. During a corner drag each moves the grabbed corner one pixel.
_NUDGE_KEYS = {"w": (0.0, -1.0), "a": (-1.0, 0.0), "s": (0.0, 1.0), "d": (1.0, 0.0)}


@dataclass
class Ghost:
    """One shape the overlay draws for a proposed edit, with its caption.

    A resize's ghost is a ``"rect"``, the proposed one. A reorder's is a
    ``"line"`` -- the insertion line, given as a rect with no thickness on the
    axis it crosses -- under a ``"wash"`` over the list the child would land
    in; in a grid the line is a ``"cell"``, the one it would take.
    """

    rect: Rect
    caption: str
    shape: str = "rect"


@dataclass
class _Resize:
    node: Any
    # Which corner is held: -1 for left / top, +1 for right / bottom.
    corner: tuple[int, int]
    origin: Rect
    start: tuple[float, float]
    axes: dict[str, str]
    # Every widget built from the same site, the dragged one included: the
    # edit changes them all, so each gets a ghost.
    instances: list[Any]
    proposed: tuple[float, float] = (0.0, 0.0)
    landings: dict[str, landing.Landing] = field(default_factory=dict)
    snap: bool = True
    # The pointer the drag reads: the mouse until a key moves it, the keys'
    # own from then on, so a nudge is never undone by the hand.
    pointer: tuple[float, float] = (0.0, 0.0)
    nudged: bool = False


@dataclass
class _Move:
    node: Any
    # The container's direct child on ``node``'s path -- ``node`` itself unless
    # a composable wrapper stands between -- and its current index.
    member: Any
    container: Any
    siblings: list[Any]
    index: int
    start: tuple[float, float]
    # Every container built from the same site, this one included: the edit
    # moves the child in all of them, so each gets a ghost.
    instances: list[Any]
    # The slot the pointer is over, or ``None`` while the drag does not read
    # as a reorder; and the pointer itself, which picks where the line sits
    # when a slot has two places.
    slot: Optional[int] = None
    pointer: tuple[float, float] = (0.0, 0.0)
    # Set instead of ``slot`` while the pointer is over another container:
    # the drag reads as a move into it, at ``dest_slot`` among its children.
    destination: Optional[Any] = None
    dest_children: list[Any] = field(default_factory=list)
    dest_slot: Optional[int] = None
    # Every container built from the destination's site, itself included,
    # found once per destination rather than once per frame.
    dest_instances: list[Any] = field(default_factory=list)
    # Why the child cannot leave its list, read from the source once at the
    # start; and the last container the pointer entered with why it cannot
    # take a child, read once on entry. Either is the badge while the pointer
    # is over another container, so the human learns it before releasing.
    leave: Optional[str] = None
    target: Optional[Any] = None
    target_refusal: Optional[str] = None
    blocked: Optional[str] = None
    # In a grid: where the item sits -- ``(row, column, row_span,
    # column_span)`` -- the cell under the pointer in its own grid, or in the
    # destination grid, and why its placement cannot be rewritten. The
    # destination's ``GridItem`` spelling is read once on entry, and the
    # keywords an unwrap would drop are noted after the write.
    home: Optional[tuple[int, int, int, int]] = None
    cell: Optional[reorder.Cell] = None
    dest_cell: Optional[reorder.Cell] = None
    cell_block: Optional[str] = None
    dest_wrapper: str = ""
    discards: list[str] = field(default_factory=list)
    # The alignment reading, live while the drag keeps the child's place:
    # what it writes and where, the box the child aligns in, why the value
    # cannot be written, and -- while the reading is live -- the new value per
    # axis, ``None`` when it is the value already there.
    align_target: Optional[align.Target] = None
    align_box: Optional[Rect] = None
    align_written: Optional[align.Spelled] = None
    align_block: Optional[str] = None
    aligning: bool = False
    alignment: Optional[dict[str, str]] = None
    # The stack the pointer is in, its layers bottom to top, the layer the
    # drag reads within (``len(layers)`` for a new one on top), and the layers
    # the human chose with a key, per stack by ``id``, each kept until the
    # pointer leaves that stack.
    stack: Optional[Any] = None
    layers: list[Any] = field(default_factory=list)
    layer: int = 0
    choices: dict[int, int] = field(default_factory=dict)


@dataclass
class LayerList:
    """The layers of the stack a body drag is over, for the overlay to list.

    ``names`` run bottom to top, ``landing`` indexes the one the drag reads
    within -- ``len(names)`` for a new layer on top -- and ``own`` the layer
    the dragged widget lives in, or ``None`` when it comes from outside.
    """

    rect: Rect
    names: list[str]
    landing: int
    own: Optional[int]


_Drag = Union[_Resize, _Move]


class LayoutEditMode:
    """Latched layout edit mode for one window: corner drags resize, body drags reorder, move or align.

    Attach as ``app._layout_edit_mode``; the backend's real input handlers call the
    ``on_*`` hooks and honour a ``True`` return as "consumed". While latched
    every event is consumed, like select mode. All hooks run on the UI thread.
    """

    def __init__(self, edits: EditLog, *, request_reload: Optional[Callable[[str], None]] = None) -> None:
        self._edits = edits
        self._request_reload = request_reload
        self._active = False
        # The window, kept only to re-resolve hover and selection after a
        # reload replaces the tree under them.
        self._app: Optional[Callable[[], Any]] = None
        self._pointer: Optional[tuple[float, float]] = None
        # Where a non-corner press landed and on what, so travel can start a
        # body drag and release can tell a click from one.
        self._press: Optional[tuple[float, float]] = None
        self._press_node: Optional[Callable[[], Any]] = None
        self._drag: Optional[_Drag] = None
        # Weak throughout: the mode must never keep a detached subtree alive.
        self._hover: Optional[Callable[[], Any]] = None
        self._selected: Optional[Callable[[], Any]] = None
        # The selection's structural path, which is what survives a reload.
        self._selected_path: Optional[Path] = None
        # Where the ancestor walk started, so ``down`` can retrace ``up``.
        self._anchor: Optional[Callable[[], Any]] = None
        edits.on_reloaded(self._reloaded)
        # Ghosts kept after release until the reload lands.
        self._ghosts: list[Ghost] = []
        self._notice: Optional[str] = None
        self._placement = Placement()

    # --- state for the overlay -------------------------------------------

    @property
    def active(self) -> bool:
        """Whether the mode is latched on."""
        return self._active

    @property
    def pointer(self) -> Optional[tuple[float, float]]:
        """Where the pointer last was, for the badge to keep out of its way."""
        return self._pointer

    @property
    def placement(self) -> Placement:
        """Where the badge sits, kept across frames."""
        return self._placement

    @property
    def exit(self) -> str:
        """What ``Esc`` does right now, for the badge's first line."""
        return "Esc cancel" if self._drag is not None else "Esc leave"

    @property
    def hints(self) -> tuple[str, ...]:
        """The gestures and keys that mean something right now, for the badge.

        A key appears the moment pressing it would do something, and not
        before: the badge is the only place a human can learn them, and one
        that lists everything at once teaches nothing.
        """
        drag = self._drag
        if isinstance(drag, _Resize):
            return ("WASD nudge", "Alt no snap")
        if drag is not None:
            return ()
        parts: list[str] = []
        if self.candidate is not None:
            parts += ["drag a corner resize", "drag reorder / move / align", "click select", "Ctrl+Shift+Click source"]
        if self.selected is not None:
            parts += ["W/S parent/child", "Del/Backspace delete"]
        if self._edits.undoable:
            parts.append("Ctrl+Z undo")
        if self._edits.redoable:
            parts.append("Ctrl+Shift+Z redo")
        return tuple(parts)

    @property
    def hovered(self) -> Optional[Any]:
        """The widget under the cursor."""
        return self._hover() if self._hover is not None else None

    @property
    def selected(self) -> Optional[Any]:
        """The widget a click chose, walked by ``W`` / ``S``.

        Held only while the pointer stays on it: a selection exists so a
        container can be grabbed through its children, and moving off it is
        how it is released.
        """
        return self._selected() if self._selected is not None else None

    @property
    def candidate(self) -> Optional[Any]:
        """The widget a drag would edit: the selection, else the hover."""
        return self.selected or self.hovered

    @property
    def dragging(self) -> bool:
        """Whether a drag is in flight."""
        return self._drag is not None

    @property
    def ghosts(self) -> list[Ghost]:
        """What the current or pending edit will produce. Empty once it landed."""
        if isinstance(self._drag, _Resize):
            return self._resize_ghosts(self._drag)
        if isinstance(self._drag, _Move):
            return self._move_ghosts(self._drag)
        if self._edits.pending is None:
            self._ghosts = []
        return list(self._ghosts)

    @property
    def notice(self) -> Optional[str]:
        """A refusal, an undo, or what the last reload reported. Transient."""
        return self._notice or self._edits.outcome

    @property
    def layers(self) -> Optional[LayerList]:
        """The layers of the stack a body drag is over, or ``None``."""
        drag = self._drag
        if not isinstance(drag, _Move) or drag.stack is None:
            return None
        rect = global_visual_rect(drag.stack)
        if rect is None:
            return None
        own = None
        if drag.stack is drag.container:
            own = drag.layers.index(drag.member) if drag.member in drag.layers else None
        else:
            for node in (drag.container, *ancestors(drag.container)):
                if node in drag.layers:
                    own = drag.layers.index(node)
                    break
        return LayerList(rect, [_name(_shown(layer)) for layer in drag.layers], drag.layer, own)

    # --- keys -------------------------------------------------------------

    def on_key_press(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Handle a key. Returns ``True`` when the mode consumed it."""
        key = str(name).strip().lower()
        accel = accel_held(modifier_keys)
        chord = chord_held(modifier_keys)

        if not self._active:
            if key == _ENTER_KEY and chord:
                self._enter(app)
                return True
            return False

        if key == _SELECT_KEY and chord and getattr(app, "_select_mode", None) is not None:
            return False
        self._clear_notice()
        if key == "escape":
            if self._drag is not None:
                self._drag = None
                invalidate(app)
            else:
                self.leave(app)
        elif key == "z" and chord:
            self._redo(app)
        elif key == "z" and accel:
            self._undo(app)
        elif key in _DELETE_KEYS and self._drag is None:
            self._delete(app)
        elif isinstance(self._drag, _Resize) and key in _NUDGE_KEYS:
            self._nudge(app, self._drag, key, modifier_keys)
        elif isinstance(self._drag, _Move) and self._drag.stack is not None:
            self._pick_layer(app, self._drag, key)
        elif key == "w":
            self._walk_up(app)
        elif key == "s":
            self._walk_down(app)
        return True

    def on_key_release(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Swallow the key-up half while latched. ``True`` when consumed."""
        return self._active

    def _enter(self, app: Any) -> None:
        other = getattr(app, "_select_mode", None)
        if other is not None and other.active:
            other.commit(app)
        self._active = True
        self._app = weak(app)
        self._reset()
        self._placement.reset()
        invalidate(app)

    def leave(self, app: Any) -> None:
        """Drop any drag in flight and switch the mode off. No-op when off."""
        if not self._active:
            return
        self._active = False
        self._reset()
        self._notice = None
        invalidate(app)

    def _reset(self) -> None:
        self._press = None
        self._press_node = None
        self._drag = None
        self._hover = None
        self._select(None, None)

    def _select(self, node: Optional[Any], root: Optional[Any]) -> None:
        self._selected = weak(node)
        self._anchor = weak(node)
        self._selected_path = path_of(root, node) if node is not None and root is not None else None

    def _reloaded(self) -> None:
        """Re-resolve hover and selection against the tree a reload just built.

        The old widgets stay alive for a while and still answer with their old
        rects, so without this the brackets would show the size from before
        the edit until the pointer moved.
        """
        app = self._app() if self._app is not None else None
        if not self._active or app is None:
            return
        root = getattr(app, "root", None)
        selected = None
        if root is not None and self._selected_path is not None:
            try:
                selected = widgets_by_path(root).get(self._selected_path)
            except Exception:
                logger.debug("layout: re-resolving the selection failed", exc_info=True)
        self._select(selected, root)
        pointer = self._pointer
        self._hover = weak(_target(app, *pointer)) if pointer is not None else None
        invalidate(app)

    def _clear_notice(self) -> None:
        self._notice = None
        self._edits.outcome = None

    # --- pointer ----------------------------------------------------------

    def on_mouse_press(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Grab a corner of the candidate, or start a click or body drag. ``True`` when consumed."""
        if not self._active:
            return False
        self._clear_notice()
        candidate = self.candidate
        if candidate is not None:
            corner = _corner_at(candidate, float(x), float(y))
            if corner is not None:
                self._begin_resize(app, candidate, corner, float(x), float(y), modifier_keys)
                return True
        self._press = (float(x), float(y))
        self._press_node = weak(candidate)
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Finish a drag, or select on a click. ``True`` when consumed."""
        if not self._active:
            return False
        press, self._press = self._press, None
        if self._drag is None and press is not None and travelled(press, x, y):
            self._begin_move(app, press, float(x), float(y))
        drag, self._drag = self._drag, None
        if isinstance(drag, _Resize):
            self._finish_resize(app, drag, float(x), float(y), modifier_keys)
            return True
        if isinstance(drag, _Move):
            self._finish_move(app, drag, float(x), float(y))
            return True
        if press is None:
            return True
        self._select(_target(app, press[0], press[1]), getattr(app, "root", None))
        invalidate(app)
        return True

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Track the hover candidate, or the drag in flight. ``True`` when consumed."""
        if not self._active:
            return False
        self._pointer = (float(x), float(y))
        if self._placement.crosses(self._pointer):
            invalidate(app)
        if self._press is not None and self._drag is None and travelled(self._press, x, y):
            press, self._press = self._press, None
            self._begin_move(app, press, float(x), float(y))
        if isinstance(self._drag, _Resize):
            self._update_resize(app, self._drag, float(x), float(y), modifier_keys)
            return True
        if isinstance(self._drag, _Move):
            self._update_move(app, self._drag, float(x), float(y))
            return True
        if self._press is not None:
            return True
        selected = self.selected
        if selected is not None and not _on(selected, float(x), float(y)):
            self._select(None, None)
            invalidate(app)
        candidate = _target(app, float(x), float(y))
        if candidate is self.hovered:
            return True
        self._hover = weak(candidate)
        invalidate(app)
        return True

    # --- the resize drag --------------------------------------------------

    def _begin_resize(self, app: Any, node: Any, corner: tuple[int, int], x: float, y: float, mods: int) -> None:
        axes = landing.editable_axes(node)
        if not axes:
            self._notice = f"{type(node).__name__} has no width or height parameter"
            invalidate(app)
            return
        rect = global_visual_rect(node)
        if rect is None:
            return
        frame = construction_frame(node)
        root = getattr(app, "root", None)
        instances = (
            widgets_built_at(root, frame, type(node).__name__) if frame is not None and root is not None else [node]
        )
        drag = _Resize(node, corner, rect, (x, y), axes, instances or [node])
        self._update_resize(app, drag, x, y, mods)
        self._drag = drag

    def _update_resize(self, app: Any, drag: _Resize, x: float, y: float, mods: int) -> None:
        if drag.nudged:
            x, y = drag.pointer
        else:
            drag.pointer = (x, y)
        sx, sy = drag.corner
        dx, dy = (x - drag.start[0]) * sx, (y - drag.start[1]) * sy
        _ox, _oy, ow, oh = drag.origin
        if drag.axes.get("width") == "size":
            side = max(1.0, ow + max(dx, dy))
            width, height = side, side
        else:
            width = max(1.0, ow + dx) if "width" in drag.axes else ow
            height = max(1.0, oh + dy) if "height" in drag.axes else oh
        drag.snap = not (resolve_modifiers(int(mods)) & MOD_ALT)
        drag.proposed = (width, height)
        # A key moves one pixel at a time, so the bands would swallow its
        # steps: once nudged, ``auto`` and ``wt`` are hit only exactly.
        band = 0.0 if drag.nudged else SNAP_BAND
        drag.landings = self._land(drag.node, drag.axes, width, height, snap=drag.snap, band=band)
        invalidate(app)

    def _land(
        self, node: Any, axes: dict[str, str], width: float, height: float, *, snap: bool, band: float
    ) -> dict[str, landing.Landing]:
        container, _member = landing.layout_container(node)
        extent = landing.content_extent(container) if container is not None else None
        natural_w: Optional[int]
        natural_h: Optional[int]
        try:
            # Height's intrinsic size is measured at the proposed width: a
            # corner drag changes both, and wrapping text answers differently.
            natural_w = landing.intrinsic_size(node, max_width=extent[0] if extent else None)[0]
            natural_h = landing.intrinsic_size(node, max_width=int(round(width)))[1]
        except Exception:
            logger.debug("layout: measuring the intrinsic size failed", exc_info=True)
            natural_w = natural_h = None
        out: dict[str, landing.Landing] = {}
        for axis, proposed, natural in (("width", width, natural_w), ("height", height, natural_h)):
            if axis not in axes:
                continue
            weight = landing.weight_target(node, axis)
            out[axis] = landing.resolve(proposed, natural, weight, snap=snap, band=band)
        return out

    def _nudge(self, app: Any, drag: _Resize, key: str, mods: int) -> None:
        """Move the grabbed corner one pixel; from the first press the keys are the pointer."""
        dx, dy = _NUDGE_KEYS[key]
        px, py = drag.pointer
        drag.pointer = (px + dx, py + dy)
        drag.nudged = True
        self._update_resize(app, drag, px + dx, py + dy, mods)

    def _finish_resize(self, app: Any, drag: _Resize, x: float, y: float, mods: int) -> None:
        self._update_resize(app, drag, x, y, mods)
        if not drag.nudged and not travelled(drag.start, x, y):
            self._select(drag.node, getattr(app, "root", None))
            invalidate(app)
            return
        if self._write(app, self._plan_resize(drag), self._resize_ghosts(drag)):
            # The resized widget stays the candidate through the reload, so
            # the next drag needs no re-aim.
            self._select(drag.node, getattr(app, "root", None))
        invalidate(app)

    def _write(self, app: Any, planned: Edit | Refusal, ghosts: list[Ghost]) -> bool:
        """Apply a planned edit and ask for the reload; a refusal becomes the notice."""
        if isinstance(planned, Refusal):
            self._notice = planned.reason
            return False
        try:
            self._edits.apply(planned)
        except OSError as exc:
            self._notice = f"cannot write {planned.file}: {exc}"
            return False
        self._ghosts = ghosts
        if self._request_reload is not None:
            self._request_reload(planned.file)
        return True

    def _plan_resize(self, drag: _Resize) -> Edit | Refusal:
        """The edit a finished resize asks for, or why there is none."""
        changes = self._changes(drag)
        if not changes:
            return Refusal("unchanged")
        located = _source_of(drag.node, "this widget")
        if isinstance(located, Refusal):
            return located
        frame, text = located
        spans = plan_keywords(text, frame, changes)
        if isinstance(spans, Refusal):
            return spans
        container, _member = landing.layout_container(drag.node)
        return Edit(
            kind="resize",
            file=frame.file,
            site=frame,
            parent_layout=type(container).__name__ if container is not None else "",
            before={axis: int(drag.origin[2 if axis == "width" else 3]) for axis in drag.landings},
            after=changes,
            expected={axis: land.pixels for axis, land in drag.landings.items()},
            instances=len(drag.instances),
            spans=spans,
            widget=type(drag.node).__name__,
        )

    def _changes(self, drag: _Resize) -> dict[str, Value]:
        """The keywords to write, skipping any axis the drag left as declared."""
        changes: dict[str, Value] = {}
        for axis, land in drag.landings.items():
            if land.value == landing.declared(drag.node, axis):
                continue
            changes[drag.axes[axis]] = land.value
        return changes

    def _resize_ghosts(self, drag: _Resize) -> list[Ghost]:
        """One ghost per instance; the dragged one carries the caption."""
        ghosts = [Ghost(_anchored(drag.origin, drag.corner, drag.proposed), _caption(drag))]
        for node in drag.instances:
            if node is drag.node:
                continue
            rect = global_visual_rect(node)
            if rect is not None:
                ghosts.append(Ghost((rect[0], rect[1], drag.proposed[0], drag.proposed[1]), ""))
        return ghosts

    # --- the body drag ----------------------------------------------------

    def _begin_move(self, app: Any, press: tuple[float, float], x: float, y: float) -> None:
        node = self._press_node() if self._press_node is not None else None
        self._press_node = None
        if node is None:
            return
        container, member = reorder.container_of(node)
        if container is None:
            self._notice = f"{type(node).__name__} is not in a container a drag can read"
            invalidate(app)
            return
        children = reorder.siblings(container)
        if member not in children:
            return
        frame = construction_frame(container)
        instances = widgets_built_at(self._root(), frame, type(container).__name__) if frame else []
        drag = _Move(node, member, container, children, children.index(member), press, instances or [container])
        if reorder.is_host(container):
            drag.leave = _host_refusal(container, "source")
        else:
            drag.leave = _list_refusal(container, "source")
        if isinstance(container, Grid):
            drag.home = reorder.placement(container, member)
            drag.cell_block = _item_refusal(member)
            drag.leave = drag.leave or drag.cell_block
            drag.discards = _discards(member)
        drag.align_target = align.target(container, member)
        if drag.align_target is not None:
            drag.align_box = align.box(container, member)
            drag.align_written, drag.align_block = _align_written(drag.align_target)
        self._update_move(app, drag, x, y)
        self._drag = drag

    def _update_move(self, app: Any, drag: _Move, x: float, y: float) -> None:
        """Read the drag from where the pointer is: its own container, another, or neither.

        The deepest container under the pointer decides. The widget's own
        gives the in-place reading: a reorder along the main axis, the cell
        under the pointer in a grid, and -- whenever the drag keeps the
        child's place -- the alignment its container gives it. Any other
        container makes the drag a move into it, a stack taking the widget on
        top; none at all keeps the in-place reading, so a drag past the end
        of a list still lands at the end. Over a stack a key can choose the
        layer, and a layer that takes nothing gives its place in the stack.
        """
        drag.pointer = (x, y)
        drag.slot = drag.destination = drag.dest_slot = drag.blocked = None
        drag.cell = drag.dest_cell = drag.alignment = None
        drag.aligning = False
        drag.dest_children = []
        landing = reorder.resolve(app, x, y, exclude=drag.member, own=drag.container, choices=drag.choices)
        drag.choices = {id(stack): drag.choices[id(stack)] for stack in landing.path if id(stack) in drag.choices}
        drag.stack, drag.layers, drag.layer = landing.stack, landing.layers, landing.layer
        target = landing.container
        if target is None or target is drag.container:
            dx, dy = x - drag.start[0], y - drag.start[1]
            container = drag.container
            if landing.slot is not None:
                drag.slot = landing.slot
            elif isinstance(container, Grid):
                drag.cell = reorder.cell_at(container, x, y)
                if drag.cell is not None and drag.home is not None and drag.cell == drag.home[:2]:
                    self._read_alignment(drag, dx, dy)
                elif drag.cell is not None:
                    drag.blocked = drag.cell_block
            elif isinstance(container, reorder.REORDERABLE):
                slot = reorder.slot_at(container, drag.siblings, drag.member, x, y)
                if reorder.main_axis(container) is not None:
                    stays = not reorder.reorder_reading(container, dx, dy)
                else:
                    stays = slot == drag.index and (abs(dy) > abs(dx) or not reorder.one_axis(container))
                if stays:
                    self._read_alignment(drag, dx, dy)
                else:
                    drag.slot = slot
            else:
                self._read_alignment(drag, dx, dy)
        else:
            if target is not drag.target:
                self._enter_container(drag, target)
            drag.blocked = drag.leave or drag.target_refusal
            if drag.blocked is None:
                drag.destination = target
                drag.dest_children = reorder.siblings(target)
                if isinstance(target, Grid):
                    drag.dest_cell = reorder.cell_at(target, x, y)
                elif reorder.is_host(target):
                    drag.dest_slot = 0
                elif isinstance(target, Stack):
                    drag.dest_slot = landing.slot if landing.slot is not None else len(drag.dest_children)
                else:
                    drag.dest_slot = reorder.slot_at(target, drag.dest_children, None, x, y)
        self._notice = drag.blocked
        invalidate(app)

    def _read_alignment(self, drag: _Move, dx: float, dy: float) -> None:
        """Snap the dragged child within its box; the reading is live even when nothing would change."""
        target = drag.align_target
        if target is None or drag.align_box is None:
            return
        drag.aligning = True
        if drag.align_block is not None:
            drag.blocked = drag.align_block
            return
        child = align.aligned(drag.container, drag.member)
        rect = global_visual_rect(child)
        if rect is None:
            return
        axes = tuple(axis for axis in target.axes if not align.fills(child, drag.align_box, axis))
        if not axes:
            where = "its cell" if isinstance(drag.container, Grid) else type(drag.container).__name__
            drag.blocked = f"{_name(child)} fills {where}; nothing to align"
            return
        found = align.snap(drag.align_box, rect, (dx, dy), axes)
        now = align.current(target)
        drag.alignment = found if any(found[axis] != now.get(axis) for axis in axes) else None

    def _enter_container(self, drag: _Move, target: Any) -> None:
        """Once per container the pointer enters: whether its list can take a child, and what else its site built."""
        drag.target = target
        if reorder.is_host(target):
            drag.target_refusal = _host_refusal(target, "destination")
        else:
            drag.target_refusal = _list_refusal(target, "destination")
        if isinstance(target, Grid) and drag.target_refusal is None:
            drag.dest_wrapper, drag.target_refusal = _wrapper_of(target)
        frame = construction_frame(target)
        found = widgets_built_at(self._root(), frame, type(target).__name__) if frame else []
        drag.dest_instances = found or [target]

    def _finish_move(self, app: Any, drag: _Move, x: float, y: float) -> None:
        self._update_move(app, drag, x, y)
        if drag.destination is not None:
            if isinstance(drag.destination, Grid) and drag.dest_cell is None:
                invalidate(app)
                return
            planned = self._plan_move_across(drag)
            if self._write(app, planned, self._move_ghosts(drag)):
                self._select(None, None)
                notes = [_axis_note(drag.node, drag.container, drag.destination), _discard_note(drag)]
                self._notice = SEPARATOR.join(note for note in notes if note) or None
            invalidate(app)
            return
        if drag.aligning:
            if drag.alignment is not None and self._write(app, self._plan_align(drag), self._move_ghosts(drag)):
                # The aligned widget keeps its path, so it stays the candidate.
                self._select(drag.node, getattr(app, "root", None))
            invalidate(app)
            return
        if isinstance(drag.container, Grid):
            if drag.cell is not None and drag.home is not None and drag.cell != drag.home[:2]:
                if self._write(app, self._plan_cell(drag), self._move_ghosts(drag)):
                    self._select(None, None)
            invalidate(app)
            return
        if drag.slot is None or drag.slot == drag.index:
            invalidate(app)
            return
        if self._write(app, self._plan_move(drag), self._move_ghosts(drag)):
            # The moved widget's path changes with the reload, so the selection
            # is let go and hover takes over where the pointer is.
            self._select(None, None)
        invalidate(app)

    def _plan_align(self, drag: _Move) -> Edit | Refusal:
        """The edit a body drag that stayed put asks for, or why there is none."""
        target, value = drag.align_target, drag.alignment
        assert target is not None and value is not None
        located = _source_of(target.host, f"this {type(target.host).__name__}")
        if isinstance(located, Refusal):
            return located
        frame, text = located
        written = written_alignment(text, frame, target.keyword, target.position)
        if isinstance(written, Refusal):
            return written
        spelled = align.spell(target, written, value)
        spans = plan_alignment(text, frame, target.keyword, target.position, spelled)
        if isinstance(spans, Refusal):
            return spans
        child = align.aligned(drag.container, drag.member)
        rect = global_visual_rect(child) or (0.0, 0.0, 0.0, 0.0)
        landed = align.placed(drag.align_box or rect, rect, value)
        # What the check measures after the reload: the wrapper itself when it
        # is what the container places, else the host's child at its index.
        if isinstance(target.host, CrossAligned):
            index = -1
        elif target.host is not drag.container:
            index = 0
        else:
            index = drag.index
        return Edit(
            kind="align",
            file=frame.file,
            site=frame,
            parent_layout=type(drag.container).__name__,
            before={"x": int(rect[0]), "y": int(rect[1]), "index": index},
            after={target.keyword: align.describe(spelled)},
            expected={"x": int(landed[0]), "y": int(landed[1]), "index": index},
            instances=len(drag.instances),
            spans=spans,
            widget=type(target.host).__name__,
            child=type(child).__name__,
        )

    def _plan_cell(self, drag: _Move) -> Edit | Refusal:
        """The edit a body drag to another cell of its own grid asks for, or why there is none."""
        assert drag.cell is not None and drag.home is not None
        grid, item = drag.container, drag.member
        frame = construction_frame(grid)
        if frame is None:
            return Refusal("no source recorded for this Grid")
        located = _source_of(item, "this GridItem")
        if isinstance(located, Refusal):
            return located
        item_frame, text = located
        row, column = drag.cell
        area = reorder.area_at(grid, drag.cell)
        if getattr(item, "area", None):
            if area is None:
                return Refusal("the grid declares no area there")
            spans = plan_area(text, item_frame, area)
            after: dict[str, Value] = {"area": area}
        else:
            spans = plan_cell(text, item_frame, row, column)
            after = {"row": row, "column": column}
        if isinstance(spans, Refusal):
            return spans
        return Edit(
            kind="move",
            file=item_frame.file,
            site=frame,
            parent_layout="Grid",
            before={"row": drag.home[0], "column": drag.home[1]},
            after=after,
            expected={"row": row, "column": column},
            instances=len(drag.instances),
            spans=spans,
            widget="Grid",
            child=type(reorder.inner(item)).__name__,
        )

    def _plan_move(self, drag: _Move) -> Edit | Refusal:
        """The edit a finished body drag asks for, or why there is none."""
        if drag.slot is None or drag.slot == drag.index:
            return Refusal("unchanged")
        container = drag.container
        located = _source_of(container, f"this {type(container).__name__}")
        if isinstance(located, Refusal):
            return located
        frame, text = located
        spans = plan_move(text, frame, drag.index, drag.slot, len(drag.siblings))
        if isinstance(spans, Refusal):
            return spans
        return Edit(
            kind="move",
            file=frame.file,
            site=frame,
            parent_layout=type(container).__name__,
            before={"slot": drag.index},
            after={"slot": drag.slot},
            expected={"slot": drag.slot},
            instances=len(drag.instances),
            spans=spans,
            widget=type(container).__name__,
            child=type(reorder.visible(drag.member)).__name__,
        )

    def _plan_move_across(self, drag: _Move) -> Edit | Refusal:
        """The edit a body drag into another container asks for, or why there is none.

        Into a grid the element lands wrapped in a ``GridItem`` at the cell;
        out of one only the item's child travels.
        """
        assert drag.destination is not None
        container, target = drag.container, drag.destination
        located = _source_of(container, f"this {type(container).__name__}")
        if isinstance(located, Refusal):
            return located
        frame, text = located
        landed = _source_of(target, f"the {type(target).__name__}")
        if isinstance(landed, Refusal):
            return landed
        dest_frame, dest_text = landed
        same_file = dest_frame.file == frame.file
        wrap: Optional[tuple[str, str]] = None
        if isinstance(target, Grid):
            assert drag.dest_cell is not None
            slot, place = len(drag.dest_children), _place(drag.dest_cell)
            wrap = _wrapper(drag.dest_wrapper, drag.dest_cell, reorder.area_at(target, drag.dest_cell))
        else:
            assert drag.dest_slot is not None
            slot, place, wrap = drag.dest_slot, {"slot": drag.dest_slot}, None
        planned = plan_move_across(
            text,
            frame,
            drag.index,
            len(drag.siblings),
            text if same_file else dest_text,
            dest_frame,
            slot,
            len(drag.dest_children),
            unwrap=isinstance(container, Grid),
            wrap=wrap,
            from_host=reorder.is_host(container),
            into_host=reorder.is_host(target),
        )
        if isinstance(planned, Refusal):
            return planned
        removal, insertion = planned
        before: dict[str, int] = {"count": len(drag.siblings)}
        before.update(_place(drag.home[:2]) if drag.home is not None else {"slot": drag.index})
        return Edit(
            kind="move",
            file=frame.file,
            site=frame,
            parent_layout=type(container).__name__,
            before=before,
            after=dict(place),
            expected=place,
            instances=len(drag.instances),
            spans=removal + insertion if same_file else removal,
            widget=type(container).__name__,
            child=type(reorder.inner(drag.member)).__name__,
            destination=dest_frame,
            dest_widget=type(target).__name__,
            other_file="" if same_file else dest_frame.file,
            other_spans=() if same_file else insertion,
        )

    def _move_ghosts(self, drag: _Move) -> list[Ghost]:
        """A wash over the container the child would land in, and the change inside it.

        The wash is on the child's own container from the moment the drag
        starts, and on another container while the pointer is over it, so it
        reads as "this container" and shows the grab took; both cover every
        instance of the site. Inside it: an insertion line in the slot, a
        cell, or -- for an alignment -- a dashed rect where each moved child
        lands. The dragged one carries the caption. Nothing is drawn while
        the release would change nothing: the child's own slot, or the
        alignment already there.
        """
        if drag.blocked is not None:
            return []
        if drag.destination is not None:
            return self._across_ghosts(drag)
        ghosts: list[Ghost] = []
        instances = [c for c in drag.instances if c is drag.container or len(reorder.siblings(c)) == len(drag.siblings)]
        for container in instances:
            rect = global_visual_rect(container)
            if rect is not None:
                ghosts.append(Ghost(rect, "", shape="wash"))
        if drag.aligning:
            if drag.alignment is not None:
                ghosts.extend(_align_ghosts(drag, instances))
            return ghosts
        if isinstance(drag.container, Grid):
            if drag.cell is not None and drag.home is not None and drag.cell != drag.home[:2]:
                ghosts.extend(_cell_ghosts(drag, instances, drag.container, drag.cell, drag.home[2:], into=False))
            return ghosts
        if drag.slot is None or drag.slot == drag.index:
            return ghosts
        if isinstance(drag.container, Stack):
            for container in instances:
                landed = _landing_rect(drag, container)
                caption = _move_caption(drag) if container is drag.container else ""
                if landed is not None:
                    ghosts.append(Ghost(landed, caption, shape="rect"))
            return ghosts
        for container in instances:
            if container is drag.container:
                line = reorder.insertion_line(container, drag.siblings, drag.member, drag.slot, drag.pointer)
                caption = _move_caption(drag)
            else:
                children = reorder.siblings(container)
                line = reorder.insertion_line(container, children, children[drag.index], drag.slot)
                caption = ""
            if line is not None:
                ghosts.append(Ghost(line, caption, shape="line"))
        return ghosts

    def _across_ghosts(self, drag: _Move) -> list[Ghost]:
        target, slot = drag.destination, drag.dest_slot
        ghosts: list[Ghost] = []
        if isinstance(target, Grid):
            for grid in drag.dest_instances:
                rect = global_visual_rect(grid)
                if rect is not None:
                    ghosts.append(Ghost(rect, "", shape="wash"))
            if drag.dest_cell is not None:
                span = drag.home[2:] if drag.home is not None else (1, 1)
                ghosts.extend(_cell_ghosts(drag, drag.dest_instances, target, drag.dest_cell, span, into=True))
            return ghosts
        if target is None or slot is None:
            return []
        if reorder.is_host(target) or isinstance(target, Stack):
            return _placed_ghosts(drag, target)
        for container in drag.dest_instances:
            children = drag.dest_children if container is target else reorder.siblings(container)
            if len(children) != len(drag.dest_children):
                continue
            rect = global_visual_rect(container)
            pointer = drag.pointer if container is target else None
            line = reorder.insertion_line(container, children, None, slot, pointer)
            if rect is not None:
                ghosts.append(Ghost(rect, "", shape="wash"))
            if line is not None:
                caption = _across_caption(drag, len(drag.dest_instances)) if container is target else ""
                ghosts.append(Ghost(line, caption, shape="line"))
        return ghosts

    def _root(self) -> Any:
        app = self._app() if self._app is not None else None
        return getattr(app, "root", None)

    # --- undo ---------------------------------------------------------------

    def _undo(self, app: Any) -> None:
        try:
            edit, notice = self._edits.undo()
        except OSError as exc:
            edit, notice = None, f"cannot undo: {exc}"
        self._notice = notice
        if edit is not None and self._request_reload is not None:
            self._request_reload(edit.file)
        invalidate(app)

    def _redo(self, app: Any) -> None:
        try:
            edit, notice = self._edits.redo()
        except OSError as exc:
            edit, notice = None, f"cannot redo: {exc}"
        self._notice = notice
        if edit is not None and self._request_reload is not None:
            self._request_reload(edit.file)
        invalidate(app)

    # --- delete -----------------------------------------------------------

    def _delete(self, app: Any) -> None:
        """Remove the selection's expression from its container's call. A refusal becomes the notice."""
        node = self.selected
        if node is None:
            return
        container, member = reorder.container_of(node)
        if container is None:
            self._notice = f"{type(node).__name__} is not in a container an edit can read"
            invalidate(app)
            return
        children = reorder.siblings(container)
        if member not in children:
            return
        index = children.index(member)
        frame = construction_frame(container)
        instances = widgets_built_at(self._root(), frame, type(container).__name__) if frame else []
        planned = self._plan_delete(container, member, index, len(children), len(instances) or 1)
        if self._write(app, planned, _delete_ghosts(member, instances or [container], index)):
            self._select(None, None)
        invalidate(app)

    def _plan_delete(self, container: Any, member: Any, index: int, count: int, instances: int) -> Edit | Refusal:
        """The edit a delete asks for, or why there is none: the move's leaving half, with nowhere to go."""
        host = reorder.is_host(container)
        blocked = _host_refusal(container, "source") if host else _list_refusal(container, "source")
        if blocked is not None:
            return Refusal(blocked)
        located = _source_of(container, f"this {type(container).__name__}")
        if isinstance(located, Refusal):
            return located
        frame, text = located
        spans = plan_delete(text, frame, index, count, from_host=host)
        if isinstance(spans, Refusal):
            return spans
        before: dict[str, int] = {"count": count}
        home = reorder.placement(container, member) if isinstance(container, Grid) else None
        before.update(_place(home[:2]) if home is not None else {"slot": index})
        child = reorder.inner(member) if isinstance(container, Grid) else reorder.visible(member)
        return Edit(
            kind="delete",
            file=frame.file,
            site=frame,
            parent_layout=type(container).__name__,
            before=before,
            after={},
            expected={},
            instances=instances,
            spans=spans,
            widget=type(container).__name__,
            child=type(child).__name__,
        )

    # --- ancestor walk ----------------------------------------------------

    def _walk_up(self, app: Any) -> None:
        """Step to the parent -- or, for a parent the same call built, to its owner."""
        current = self.selected
        parent = parent_of(current) if current is not None else None
        if parent is not None:
            self._step(app, site_owner(parent))

    def _pick_layer(self, app: Any, drag: _Move, key: str) -> None:
        """Move the landing to another layer of the stack the drag is over: a step, or a layer by number."""
        top = len(drag.layers)
        if key == "w":
            index = min(top, drag.layer + 1)
        elif key == "s":
            index = max(0, drag.layer - 1)
        elif key.lstrip("_").isdigit():
            index = min(top, int(key.lstrip("_")))
        else:
            return
        drag.choices[id(drag.stack)] = index
        self._update_move(app, drag, *drag.pointer)

    def _walk_down(self, app: Any) -> None:
        """Step back toward the anchor, skipping widgets with no call of their own."""
        anchor = self._anchor() if self._anchor is not None else None
        node = self.selected
        while True:
            node = child_toward(node, anchor)
            if node is None:
                return
            if site_owner(node) is node:
                break
        self._step(app, node)

    def _step(self, app: Any, node: Any) -> None:
        """Move the selection along the walk, keeping its anchor."""
        self._selected = weak(node)
        self._selected_path = path_of(getattr(app, "root", None), node)
        invalidate(app)


def _source_of(node: Any, what: str) -> tuple[Frame, str] | Refusal:
    """The construction site of ``node`` and its file's text, or why an edit cannot reach it."""
    frame = construction_frame(node)
    if frame is None:
        return Refusal(f"no source recorded for {what}")
    if not is_project_file(frame.file):
        return Refusal(f"built outside the project, in {os.path.basename(frame.file)}")
    try:
        with open(frame.file, encoding="utf-8", newline="") as handle:
            return (frame, handle.read())
    except OSError as exc:
        return Refusal(f"cannot read {frame.file}: {exc}")


def _list_refusal(container: Any, role: str) -> Optional[str]:
    """Why ``container``'s children list cannot give (``role`` ``"source"``) or take a child, or ``None``."""
    located = _source_of(container, f"the {type(container).__name__}")
    if isinstance(located, Refusal):
        return located.reason
    frame, text = located
    found = children_list(text, frame, role)
    return found.reason if isinstance(found, Refusal) else None


def _align_written(target: align.Target) -> tuple[Optional[align.Spelled], Optional[str]]:
    """The alignment written where ``target`` writes, and why it cannot be rewritten, from its source."""
    located = _source_of(target.host, f"this {type(target.host).__name__}")
    if isinstance(located, Refusal):
        return (None, located.reason)
    frame, text = located
    written = written_alignment(text, frame, target.keyword, target.position)
    if isinstance(written, Refusal):
        return (None, written.reason)
    return (written, None)


def _align_ghosts(drag: _Move, instances: list[Any]) -> list[Ghost]:
    """A dashed rect where every moved child lands, per instance; the dragged child carries the caption."""
    target, value = drag.align_target, drag.alignment
    assert target is not None and value is not None
    ghosts = []
    for container in instances:
        if container is drag.container:
            member, own = drag.member, True
        else:
            children = reorder.siblings(container)
            member, own = children[drag.index], False
        host = align.target(container, member)
        if host is None:
            continue
        dragged = align.aligned(container, member)
        moved = align.moved(host, container, member, value)
        for child, rect in moved:
            caption = _align_caption(drag, target, value, len(moved)) if own and child is dragged else ""
            ghosts.append(Ghost(rect, caption, shape="rect"))
    return ghosts


def _placed_ghosts(drag: _Move, target: Any) -> list[Ghost]:
    """A wash over each empty box or stack built at the destination's site, and a dashed rect where the child lands."""
    ghosts = []
    for host in drag.dest_instances:
        extent = global_visual_rect(host)
        if extent is None:
            continue
        ghosts.append(Ghost(extent, "", shape="wash"))
        landed = _landing_rect(drag, host)
        if landed is not None:
            caption = _across_caption(drag, len(drag.dest_instances)) if host is target else ""
            ghosts.append(Ghost(landed, caption, shape="rect"))
    return ghosts


def _landing_rect(drag: _Move, host: Any) -> Optional[Rect]:
    """Where the dragged child sits once ``host`` -- a box or a stack -- aligns it, or ``None``."""
    child = align.aligned(drag.container, drag.member)
    rect = global_visual_rect(child)
    placed = align.target(host, None)
    box = align.box(host, None)
    if rect is None or placed is None or box is None:
        return None
    return align.placed(box, rect, align.current(placed))


def _align_caption(drag: _Move, target: align.Target, value: dict[str, str], moving: int) -> str:
    """The value that will be written, how many children move with it, and the instance count past one."""
    parts = [align.describe(align.spell(target, drag.align_written, value))]
    if target.container_level and moving > 1:
        total = len(drag.siblings)
        parts.append(f"all {total} children" if moving == total else f"{moving} of {total} children")
    if len(drag.instances) > 1:
        parts.append(f"{len(drag.instances)} widgets")
    return SEPARATOR.join(parts)


def _host_refusal(host: Any, role: str) -> Optional[str]:
    """Why ``host`` cannot give its only child (``role`` ``"source"``) or take one, from its source, or ``None``."""
    located = _source_of(host, f"this {type(host).__name__}")
    if isinstance(located, Refusal):
        return located.reason
    frame, text = located
    found = host_child_refusal(text, frame, role)
    return found.reason if found is not None else None


def _item_refusal(item: Any) -> Optional[str]:
    """Why the ``GridItem`` ``item`` cannot be placed elsewhere by an edit, or ``None``."""
    located = _source_of(item, "this GridItem")
    if isinstance(located, Refusal):
        return located.reason
    frame, text = located
    found = cell_refusal(text, frame)
    return found.reason if found is not None else None


def _discards(item: Any) -> list[str]:
    """The keywords unwrapping ``item`` would drop, read from its source."""
    located = _source_of(item, "this GridItem")
    if isinstance(located, Refusal):
        return []
    frame, text = located
    return discarded_keywords(text, frame)


def _wrapper_of(grid: Any) -> tuple[str, Optional[str]]:
    """How a ``GridItem`` is spelled where ``grid`` is written, or why it cannot be."""
    located = _source_of(grid, "the Grid")
    if isinstance(located, Refusal):
        return ("", located.reason)
    frame, text = located
    name = grid_item_name(text, frame)
    return ("", name.reason) if isinstance(name, Refusal) else (name, None)


def _wrapper(name: str, cell: reorder.Cell, area: Optional[str]) -> tuple[str, str]:
    """The text before and after an expression that puts it at ``cell`` -- or in ``area`` -- as a ``GridItem``."""
    if area is not None:
        return (f"{name}.named_area(", f', "{area}")')
    return (f"{name}(", f", row={cell[0]}, column={cell[1]})")


def _place(cell: tuple[int, ...]) -> dict[str, int]:
    return {"row": cell[0], "column": cell[1]}


def _delete_ghosts(member: Any, containers: list[Any], index: int) -> list[Ghost]:
    """A dashed rect over the child at ``index`` of every container built at the site; the selected one captioned."""
    ghosts = []
    for container in containers:
        children = reorder.siblings(container)
        rect = global_visual_rect(children[index]) if index < len(children) else None
        if rect is not None:
            ghosts.append(Ghost(rect, "delete" if children[index] is member else ""))
    return ghosts


def _discard_note(drag: _Move) -> Optional[str]:
    """That the unwrap dropped the item's own keywords, if it had any."""
    if not drag.discards or not isinstance(drag.container, Grid):
        return None
    return f"the GridItem's {', '.join(drag.discards)} did not move with it"


def _cell_ghosts(
    drag: _Move, grids: list[Any], target: Any, cell: reorder.Cell, span: tuple[int, ...], into: bool
) -> list[Ghost]:
    """One cell ghost per grid instance; the one under the pointer carries the caption."""
    ghosts = []
    for grid in grids:
        rect = reorder.cell_rect(grid, cell[0], cell[1], span[0], span[1])
        if rect is None:
            continue
        caption = _cell_caption(drag, target, cell, len(grids), into) if grid is target else ""
        ghosts.append(Ghost(rect, caption, shape="cell"))
    return ghosts


def _cell_caption(drag: _Move, grid: Any, cell: reorder.Cell, instances: int, into: bool) -> str:
    """The cell or area, who already sits there, and the instance count past one."""
    area = reorder.area_at(grid, cell)
    where = f"area {area}" if area is not None else f"row {cell[0]}, column {cell[1]}"
    parts = [f"into Grid, {where}" if into else where]
    others = reorder.occupants(grid, cell, drag.member)
    if others:
        parts.append("over " + ", ".join(_name(reorder.inner(item)) for item in others))
    if instances > 1:
        parts.append(f"{instances} widgets")
    return SEPARATOR.join(parts)


def _caption(drag: _Resize) -> str:
    """The landing values, the instance count past one, and whether snapping is off."""
    parts: list[str] = []
    if drag.axes.get("width") == "size" and "width" in drag.landings:
        parts.append(f"size {drag.landings['width'].value}")
    else:
        parts.extend(f"{axis[0]} {land.value}" for axis, land in drag.landings.items())
    if len(drag.instances) > 1:
        parts.append(f"{len(drag.instances)} widgets")
    if not drag.snap:
        parts.append("no snap")
    return SEPARATOR.join(parts)


def _across_caption(drag: _Move, instances: int) -> str:
    """The destination, which child the widget lands before, and the instance count past one."""
    target, slot = drag.destination, drag.dest_slot
    assert target is not None and slot is not None
    children = drag.dest_children
    if reorder.is_host(target):
        parts = [f"into {type(target).__name__}"]
    elif isinstance(target, Stack):
        parts = [f"into Stack, {_stack_place(children, slot)}"]
    else:
        where = f"before {_name(reorder.visible(children[slot]))}" if slot < len(children) else "to the end"
        parts = [f"into {type(target).__name__}, {where}"]
    if drag.stack is not None and target is not drag.stack and drag.layer < len(drag.layers):
        parts.append(f"layer {drag.layer}")
    if instances > 1:
        parts.append(f"{instances} widgets")
    return SEPARATOR.join(parts)


def _stack_place(others: list[Any], slot: int) -> str:
    """Where in a stack's layers the widget lands: below the one at ``slot``, or on top."""
    return f"below {_name(_shown(others[slot]))}" if slot < len(others) else "on top"


def _shown(layer: Any) -> Any:
    """The widget a layer reads as: what a ``.modifier()`` or a ``ForEach`` wraps, else the layer itself."""
    return reorder.inner(reorder.visible(reorder.unwrapped(layer)))


def _axis_note(node: Any, source: Any, target: Any) -> Optional[str]:
    """What a weight means after the move, when an axis changed from main to cross or back.

    The sizing moves as written; ``"wt"`` on a column child's width filled the
    cross axis, on a row child's it is a share of the main-axis leftover, and
    the human may want the corner next.
    """
    for axis in ("width", "height"):
        sizing = getattr(node, f"{axis}_sizing", None)
        if sizing is None or sizing.kind in ("fixed", "auto"):
            continue
        was, now = reorder.main_axis(source) == axis, reorder.main_axis(target) == axis
        if was != now:
            meaning = "a share of the leftover" if now else "the full cross axis"
            return f'{axis}="wt" now means {meaning} in {type(target).__name__}'
    return None


def _move_caption(drag: _Move) -> str:
    """Which sibling the child lands before, and the instance count past one."""
    others = [child for child in drag.siblings if child is not drag.member]
    slot = drag.slot if drag.slot is not None else drag.index
    if isinstance(drag.container, Stack):
        parts = [_stack_place(others, slot)]
    else:
        parts = [f"before {_name(reorder.visible(others[slot]))}" if slot < len(others) else "to the end"]
    if len(drag.instances) > 1:
        parts.append(f"{len(drag.instances)} widgets")
    return SEPARATOR.join(parts)


def _name(node: Any) -> str:
    """A widget's type and its key or label, as ``describe_tree`` names it."""
    from .interaction import resolve_target

    identity = resolve_target(node)
    name = identity.get("key") or identity.get("label")
    head = identity.get("type", type(node).__name__)
    return f"{head} {name}" if name else str(head)


def _target(app: Any, x: float, y: float) -> Optional[Any]:
    """The widget a pointer at ``(x, y)`` would resize.

    The deepest widget under the pointer is often one its parent built for
    itself -- a button's label -- and an edit to that site is an edit to the
    parent, so the parent is what the pointer means here.
    """
    picked = pick(app, x, y)
    return site_owner(picked) if picked is not None else None


def _on(node: Any, x: float, y: float) -> bool:
    """Whether the point is on ``node``, its corner grab zones included."""
    rect = global_visual_rect(node)
    if rect is None:
        return False
    rx, ry, rw, rh = rect
    return rx - _CORNER_GRAB <= x <= rx + rw + _CORNER_GRAB and ry - _CORNER_GRAB <= y <= ry + rh + _CORNER_GRAB


def _corner_at(node: Any, x: float, y: float) -> Optional[tuple[int, int]]:
    """Which corner of ``node`` the point is on, or ``None``."""
    rect = global_visual_rect(node)
    if rect is None:
        return None
    rx, ry, rw, rh = rect
    best: Optional[tuple[float, tuple[int, int]]] = None
    for sx, cx in ((-1, rx), (1, rx + rw)):
        for sy, cy in ((-1, ry), (1, ry + rh)):
            distance = max(abs(x - cx), abs(y - cy))
            if distance <= _CORNER_GRAB and (best is None or distance < best[0]):
                best = (distance, (sx, sy))
    return best[1] if best is not None else None


def _anchored(origin: Rect, corner: tuple[int, int], size: tuple[float, float]) -> Rect:
    """The proposed rect, pinned at the corner opposite the one being dragged."""
    x, y, w, h = origin
    sx, sy = corner
    nw, nh = size
    return (x if sx > 0 else x + w - nw, y if sy > 0 else y + h - nh, nw, nh)


__all__ = ["Ghost", "LayerList", "LayoutEditMode"]
