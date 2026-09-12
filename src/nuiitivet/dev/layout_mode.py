"""Layout mode: the human drags a widget's corner, and the runner edits the source.

The sibling of :mod:`.select_mode`, on the same real input handlers, with the
opposite division of labour. Select mode is how the human *says* something to
the assistant; this is how they *do* something with no assistant in the loop:
a corner drag resolves to ``width`` / ``height`` / ``size`` as ``int``,
``"auto"`` or ``"wt"`` (:mod:`.landing`), release writes the keyword into the
call that built the widget (:mod:`.source_edit`), and the hot reload that
follows is what applies it. The tree is never touched directly: what is on
screen always came from the code.

Latched on ``Ctrl+Shift+E``, off on ``Esc``. Its chord and select mode's
switch directly, each mode closing the other on entry. There is no commit:
every release writes, so ``Ctrl+Z`` is what "I did not mean that" reaches for.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import global_visual_rect
from nuiitivet.input.codes import MOD_ALT, resolve_modifiers

from . import landing
from .gesture import accel_held, child_toward, chord_held, invalidate, parent_of, pick, travelled, weak
from .snapshot import Path, path_of, widgets_by_path
from .source import construction_frame, site_owner, widgets_built_at
from .source_edit import Edit, EditLog, Refusal, Value, is_project_file, plan_keywords

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]

# The key that enters the mode. ``E`` keeps the chord under the left hand while
# the right is on the mouse, and reads as *edit*, which is the name the mode
# takes if it ever grows past layout.
_ENTER_KEY = "e"
# Select mode's key. Its chord is let through while this mode is latched, so
# the two switch directly; the mode that enters closes the other.
_SELECT_KEY = "c"
# Logical pixels around each corner of the candidate within which a press is a
# grab of that corner rather than a click.
_CORNER_GRAB = 10.0


@dataclass
class Ghost:
    """One proposed rect the overlay draws, with its caption."""

    rect: Rect
    caption: str


@dataclass
class _Drag:
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


class LayoutMode:
    """Latched resize mode for one window.

    Attach as ``app._layout_mode``; the backend's real input handlers call the
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
        # Where a non-corner press landed, so release can tell a click from a
        # body drag.
        self._press: Optional[tuple[float, float]] = None
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

    # --- state for the overlay -------------------------------------------

    @property
    def active(self) -> bool:
        """Whether the mode is latched on."""
        return self._active

    @property
    def hovered(self) -> Optional[Any]:
        """The widget under the cursor."""
        return self._hover() if self._hover is not None else None

    @property
    def selected(self) -> Optional[Any]:
        """The widget a click chose, walked by ``↑`` / ``↓``.

        Held only while the pointer stays on it: a selection exists so a
        container can be grabbed through its children, and moving off it is
        how it is released.
        """
        return self._selected() if self._selected is not None else None

    @property
    def candidate(self) -> Optional[Any]:
        """The widget a corner drag would resize: the selection, else the hover."""
        return self.selected or self.hovered

    @property
    def dragging(self) -> bool:
        """Whether a corner drag is in flight."""
        return self._drag is not None

    @property
    def ghosts(self) -> list[Ghost]:
        """The rects the current or pending edit will produce. Empty once it landed."""
        if self._drag is not None:
            return self._drag_ghosts(self._drag)
        if self._edits.pending is None:
            self._ghosts = []
        return list(self._ghosts)

    @property
    def notice(self) -> Optional[str]:
        """A refusal, an undo, or what the last reload reported. Transient."""
        return self._notice or self._edits.outcome

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
        elif key == "z" and accel:
            self._undo(app)
        elif key == "up":
            self._walk_up(app)
        elif key == "down":
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
        """Grab a corner of the candidate, or start a click. ``True`` when consumed."""
        if not self._active:
            return False
        self._clear_notice()
        candidate = self.candidate
        if candidate is not None:
            corner = _corner_at(candidate, float(x), float(y))
            if corner is not None:
                self._begin_drag(app, candidate, corner, float(x), float(y), modifier_keys)
                return True
        self._press = (float(x), float(y))
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Finish a drag, or select on a click. ``True`` when consumed.

        A body drag -- travel from a press that grabbed no corner -- has no
        meaning yet and does nothing.
        """
        if not self._active:
            return False
        drag, self._drag = self._drag, None
        if drag is not None:
            self._finish_drag(app, drag, float(x), float(y), modifier_keys)
            return True
        press, self._press = self._press, None
        if press is None:
            return True
        if travelled(press, x, y):
            return True
        self._select(_target(app, press[0], press[1]), getattr(app, "root", None))
        invalidate(app)
        return True

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Track the hover candidate, or the drag in flight. ``True`` when consumed."""
        if not self._active:
            return False
        self._pointer = (float(x), float(y))
        if self._drag is not None:
            self._update_drag(app, self._drag, float(x), float(y), modifier_keys)
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

    def _begin_drag(self, app: Any, node: Any, corner: tuple[int, int], x: float, y: float, mods: int) -> None:
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
        drag = _Drag(node, corner, rect, (x, y), axes, instances or [node])
        self._update_drag(app, drag, x, y, mods)
        self._drag = drag

    def _update_drag(self, app: Any, drag: _Drag, x: float, y: float, mods: int) -> None:
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
        drag.landings = self._land(drag.node, drag.axes, width, height, snap=drag.snap)
        invalidate(app)

    def _land(
        self, node: Any, axes: dict[str, str], width: float, height: float, *, snap: bool
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
            out[axis] = landing.resolve(proposed, natural, weight, snap=snap)
        return out

    def _finish_drag(self, app: Any, drag: _Drag, x: float, y: float, mods: int) -> None:
        self._update_drag(app, drag, x, y, mods)
        if not travelled(drag.start, x, y):
            self._select(drag.node, getattr(app, "root", None))
            invalidate(app)
            return
        planned = self._plan(drag)
        if isinstance(planned, Refusal):
            self._notice = planned.reason
            invalidate(app)
            return
        try:
            self._edits.apply(planned)
        except OSError as exc:
            self._notice = f"cannot write {planned.file}: {exc}"
            invalidate(app)
            return
        self._ghosts = self._drag_ghosts(drag)
        # The resized widget stays the candidate through the reload, so the
        # next drag needs no re-aim.
        self._select(drag.node, getattr(app, "root", None))
        if self._request_reload is not None:
            self._request_reload(planned.file)
        invalidate(app)

    def _plan(self, drag: _Drag) -> Edit | Refusal:
        """The edit a finished drag asks for, or why there is none."""
        changes = self._changes(drag)
        if not changes:
            return Refusal("unchanged")
        frame = construction_frame(drag.node)
        if frame is None:
            return Refusal("no source recorded for this widget")
        if not is_project_file(frame.file):
            return Refusal(f"built outside the project, in {os.path.basename(frame.file)}")
        try:
            with open(frame.file, encoding="utf-8", newline="") as handle:
                text = handle.read()
        except OSError as exc:
            return Refusal(f"cannot read {frame.file}: {exc}")
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

    def _changes(self, drag: _Drag) -> dict[str, Value]:
        """The keywords to write, skipping any axis the drag left as declared."""
        changes: dict[str, Value] = {}
        for axis, land in drag.landings.items():
            if land.value == landing.declared(drag.node, axis):
                continue
            changes[drag.axes[axis]] = land.value
        return changes

    def _drag_ghosts(self, drag: _Drag) -> list[Ghost]:
        """One ghost per instance; the dragged one carries the caption."""
        ghosts = [Ghost(_anchored(drag.origin, drag.corner, drag.proposed), _caption(drag))]
        for node in drag.instances:
            if node is drag.node:
                continue
            rect = global_visual_rect(node)
            if rect is not None:
                ghosts.append(Ghost((rect[0], rect[1], drag.proposed[0], drag.proposed[1]), ""))
        return ghosts

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

    # --- ancestor walk ----------------------------------------------------

    def _walk_up(self, app: Any) -> None:
        """Step to the parent -- or, for a parent the same call built, to its owner."""
        current = self.selected
        parent = parent_of(current) if current is not None else None
        if parent is not None:
            self._step(app, site_owner(parent))

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


def _caption(drag: _Drag) -> str:
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
    return "  ·  ".join(parts)


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


__all__ = ["Ghost", "LayoutMode"]
