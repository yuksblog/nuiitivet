"""Build-time helpers for widgets."""

from __future__ import annotations

import inspect
import itertools
import logging
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, TYPE_CHECKING, runtime_checkable

from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from .callbacks import report_contained

_logger = logging.getLogger(__name__)


_SCOPED_FRAGMENT_CLASS = None


def _make_scope_queue_finalizer(key: int):
    def _cleanup(_ref):
        _pending_scope_recompositions.pop(key, None)

    return _cleanup


def _get_scoped_fragment_class():
    global _SCOPED_FRAGMENT_CLASS
    if _SCOPED_FRAGMENT_CLASS is not None:
        return _SCOPED_FRAGMENT_CLASS
    from .widget import ComposableWidget, Widget

    class ScopedFragment(ComposableWidget):
        def __init__(self, *, scope_id: str, factory: Callable[[], "Widget"]) -> None:
            super().__init__()
            self._scope_id = scope_id
            self._factory = factory

        @property
        def scope_id(self) -> str:
            return self._scope_id

        def build(self) -> "Widget":
            widget = self._factory()
            return _require_widget_instance(widget)

        def update_factory(self, factory: Callable[[], "Widget"]) -> None:
            self._factory = factory

        def _current_child(self) -> Optional["Widget"]:
            child = getattr(self, "built_child", None)
            from .widget import Widget

            if isinstance(child, Widget):
                return child
            return None

        # Layout metadata (sizing / alignment) needs no syncing here: the
        # fragment derives undeclared metadata from its built child, like any
        # ComposableWidget (SIZE_POLICY.md §1.2), and it never declares its own.

        def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
            child = self._current_child()
            if child is None:
                return (0, 0)
            return measure_preferred_size(child, max_width=max_width, max_height=max_height)

        def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
            child = self._current_child()
            if child is None:
                return
            child.paint(canvas, x, y, width, height)

        def hit_test(self, x: int, y: int):
            child = self._current_child()
            if child is not None:
                hit = child.hit_test(x, y)
                if hit is not None:
                    return hit
            return super().hit_test(x, y)

    _SCOPED_FRAGMENT_CLASS = ScopedFragment
    return ScopedFragment


def _normalize_scope_factory(factory: Callable[[], "Widget"]) -> Callable[[], "Widget"]:
    def _wrapped() -> "Widget":
        widget = factory()
        return _require_widget_instance(widget)

    return _wrapped


def _require_widget_instance(widget):
    from .widget import Widget

    if not isinstance(widget, Widget):
        raise TypeError("render_scope() factory must return a Widget instance.")
    return widget


@dataclass
class ScopeMetadata:
    """Metadata captured for each registered scope."""

    scope_id: str
    factory: Callable[[], "Widget"]
    _child_ref: Optional[weakref.ReferenceType["Widget"]] = field(default=None, repr=False)
    layout_dependencies: Tuple[str, ...] = ()
    paint_dependencies: Tuple[str, ...] = ()

    @property
    def child(self) -> Optional["Widget"]:
        if self._child_ref is None:
            return None
        try:
            return self._child_ref()
        except Exception:
            exception_once(
                _logger,
                "scope_metadata_child_weakref_exc",
                "Failed to dereference child weakref in scope metadata",
            )
            return None


class RecomposeScope:
    """Internal tree node used to track fine-grained build scopes."""

    _ids = itertools.count()

    def __init__(
        self,
        name: str,
        *,
        parent: Optional["RecomposeScope"] = None,
        invalidate_cb: Optional[Callable[["RecomposeScope"], None]] = None,
    ) -> None:
        self.name = name or "root"
        self.parent = parent
        self._invalidate_cb = invalidate_cb
        self._id = next(self._ids)
        self.children: Dict[str, RecomposeScope] = {}

    @property
    def identifier(self) -> str:
        if self.parent is None:
            return f"scope:{self._id}"
        return f"{self.parent.identifier}/{self.name}"

    def handle(self) -> "ScopeHandle":
        return ScopeHandle(self, self._invalidate_cb)

    def child(self, name: str) -> "RecomposeScope":
        key = name or "child"
        scope = self.children.get(key)
        if scope is None:
            scope = RecomposeScope(key, parent=self, invalidate_cb=self._invalidate_cb)
            self.children[key] = scope
        return scope


class ScopeHandle:
    """Handle returned to widgets so they can invalidate a specific scope."""

    def __init__(
        self,
        scope: RecomposeScope,
        invalidate_cb: Optional[Callable[[RecomposeScope], None]] = None,
    ) -> None:
        self._scope = scope
        self._invalidate_cb = invalidate_cb

    @property
    def id(self) -> str:
        return self._scope.identifier

    @property
    def name(self) -> str:
        return self._scope.name

    @property
    def scope(self) -> RecomposeScope:
        return self._scope

    def invalidate(self) -> None:
        if self._invalidate_cb is not None:
            try:
                self._invalidate_cb(self._scope)
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_scope_handle_invalidate_exc",
                    "Exception in scope invalidation callback: scope_id=%s",
                    self._scope.identifier,
                )


class BuildScopeContext:
    """Context helper used during build() to enter/exit named scopes."""

    def __init__(
        self,
        root_scope: RecomposeScope,
        *,
        invalidate_cb: Optional[Callable[[RecomposeScope], None]] = None,
        register_cb: Optional[Callable[[RecomposeScope], None]] = None,
    ) -> None:
        self._root = root_scope
        self._stack: List[RecomposeScope] = [root_scope]
        self._invalidate_cb = invalidate_cb
        self._register_cb = register_cb

    @property
    def current(self) -> RecomposeScope:
        return self._stack[-1]

    def scope(self, name: str) -> "_ScopeContextManager":
        return _ScopeContextManager(self, name)

    def _enter(self, name: str) -> ScopeHandle:
        parent = self.current
        scope = parent.child(name)
        if self._register_cb is not None:
            try:
                self._register_cb(scope)
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_register_scope_exc",
                    "Exception in scope register callback: scope_id=%s",
                    scope.identifier,
                )
        self._stack.append(scope)
        return ScopeHandle(scope, self._invalidate_cb or scope._invalidate_cb)

    def _exit(self) -> None:
        if len(self._stack) > 1:
            self._stack.pop()


class _ScopeContextManager:
    def __init__(self, ctx: BuildScopeContext, name: str) -> None:
        self._ctx = ctx
        self._name = name
        self._handle: Optional[ScopeHandle] = None

    def __enter__(self) -> ScopeHandle:
        self._handle = self._ctx._enter(self._name)
        return self._handle

    def __exit__(self, exc_type, exc, tb) -> None:
        self._ctx._exit()
        self._handle = None


if TYPE_CHECKING:  # pragma: no cover - typing helpers only
    from .widget import Widget


@runtime_checkable
class BuildContext(Protocol):  # pragma: no cover - extension hook marker
    """Placeholder for future diff-build context."""

    def invalidate(self) -> None: ...


_PendingScopeEntry = Tuple[weakref.ReferenceType["BuilderHostMixin"], Set[str]]
_pending_scope_recompositions: Dict[int, _PendingScopeEntry] = {}


def _queue_scope_recomposition(widget: "BuilderHostMixin", scope_id: str) -> bool:
    key = id(widget)
    entry = _pending_scope_recompositions.get(key)
    if entry is None:
        ref = weakref.ref(widget, _make_scope_queue_finalizer(key))
        scopes: Set[str] = set()
        _pending_scope_recompositions[key] = (ref, scopes)
        first_insert = True
    else:
        scopes = entry[1]
        first_insert = False
    scopes.add(scope_id)
    return first_insert


def flush_scope_recompositions() -> None:
    if not _pending_scope_recompositions:
        return
    pending = list(_pending_scope_recompositions.items())
    _pending_scope_recompositions.clear()
    for _, (ref, scopes) in pending:
        host = ref()
        if host is None or not scopes:
            continue
        handler = getattr(host, "_process_scope_recompositions", None)
        if not callable(handler):
            continue
        try:
            handler(set(scopes))
        except Exception as exc:
            exception_once(
                _logger,
                "widget_builder_flush_scope_recompositions_exc",
                "Scope recomposition handler raised",
            )
            report_contained(
                exc,
                owner=type(host).__name__,
                site="_process_scope_recompositions",
            )


class BuilderHostMixin:
    """Provides build()/rebuild() lifecycle for Widget subclasses."""

    # :meth:`on_mount` below runs ``build()``, so a skipped ``super()`` costs the subtree.
    _requires_on_mount_chain: bool = True

    _built: Optional["Widget"]

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)
        self._built = None
        self._scope_root: Optional[RecomposeScope] = None
        self._build_ctx: Optional[BuildScopeContext] = None
        self._scope_registry: Dict[str, RecomposeScope] = {}
        self._scope_nodes: Dict[str, Any] = {}
        self._active_scope_ids: Set[str] = set()
        self._scope_metadata: Dict[str, ScopeMetadata] = {}
        self._dependency_scope_index: Dict[str, Set[str]] = {}
        # Scopes whose inputs were invalidated and must be rebuilt on the next
        # render. A scope rebuilds only when it is new, unbuilt, or dirty — not
        # whenever the host's build() re-runs (idempotent recomposition).
        self._dirty_scopes: Set[str] = set()

    @property
    def built_child(self) -> Optional["Widget"]:
        return self._built

    # --- Extension hooks ---------------------------------------------------
    def create_build_context(self) -> Optional[BuildContext]:  # pragma: no cover - forward-looking hook
        """Reserved for future diff-build infrastructure."""

        self._scope_registry = {}
        self._active_scope_ids.clear()
        root = self._scope_root
        if root is None:
            root = RecomposeScope("root", invalidate_cb=self._invalidate_scope)
            self._scope_root = root
        self._register_scope(root)
        ctx = BuildScopeContext(
            root,
            invalidate_cb=self._invalidate_scope,
            register_cb=self._register_scope,
        )
        self._build_ctx = ctx
        return ctx  # type: ignore[return-value]

    # --- Build entrypoints -------------------------------------------------
    def build(self) -> "Widget":  # pragma: no cover - override in builder-style widgets
        raise NotImplementedError("ComposableWidget.build() must be implemented and must return a Widget")

    def evaluate_build(self) -> "Widget":
        from nuiitivet.theme.dependency import pop_theme_reader, push_theme_reader

        ctx = self.create_build_context()
        self._current_build_context = ctx  # type: ignore[attr-defined]
        # An ambient value read while building belongs to this host, not to
        # whichever widget was passed as the context: a change to it has to
        # rebuild what the build produced. See nuiitivet/theme/dependency.py.
        push_theme_reader(self)
        try:
            result = self.build()
        except NotImplementedError:
            raise
        except Exception:
            exception_once(
                _logger,
                f"widget_builder_evaluate_build_exc:{type(self).__name__}",
                "Widget.build raised (widget=%s)",
                type(self).__name__,
            )
            result = None
        finally:
            pop_theme_reader()
            try:
                self._prune_unused_scopes()
            finally:
                self._active_scope_ids.clear()
        if result is None:
            raise TypeError(
                f"{self.__class__.__name__}.build() must return a Widget (None is not allowed).",
            )
        from .widget import Widget

        if isinstance(result, Widget):
            return result
        raise TypeError(
            f"{self.__class__.__name__}.build() must return a Widget, got {type(result).__name__}.",
        )

    def _adopt_built(self, built: "Widget") -> None:
        """Make ``built`` point back at this host as its parent.

        A build result is only reachable from the tree through this link, and
        ``X.of(context)`` resolves by walking it upward. Parenting therefore
        happens as soon as the subtree exists -- not at mount -- so that a
        composable measured before it is mounted still resolves its ancestors
        instead of looking like a detached widget (#476).

        A host whose ``build()`` returns ``self`` -- ``Card`` decorates itself
        and returns itself -- is skipped. Parenting it to itself would make
        ``find_ancestor`` walk a one-node cycle forever, and it needs no link
        anyway: it is already in the tree in its own right.

        Args:
            built: The widget returned by :meth:`build`.
        """
        if built is self:
            return
        try:
            built._parent = self  # type: ignore[assignment]
        except Exception:
            exception_once(
                _logger,
                "widget_builder_adopt_built_set_parent_exc",
                "Failed to set built._parent",
            )

    def _release_built(self, built: Optional["Widget"]) -> None:
        """Drop the parent link taken by :meth:`_adopt_built`.

        Only clears the link when it still points here: by the time a discarded
        subtree is released it may already have been re-parented elsewhere, and
        stealing that newer link would detach a live widget.

        Args:
            built: The widget being discarded, or ``None``.
        """
        if built is None or built is self:
            return
        try:
            if getattr(built, "_parent", None) is self:
                built._parent = None  # type: ignore[assignment]
        except Exception:
            exception_once(
                _logger,
                "widget_builder_release_built_clear_parent_exc",
                "Failed to clear built._parent",
            )

    def _mount_built(self, built: Optional["Widget"]) -> None:
        if built is None:
            self._built = None
            return
        from .widget import Widget

        if isinstance(built, Widget):
            self._adopt_built(built)
            try:
                built.mount(getattr(self, "_app", None))
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_mount_built_mount_exc",
                    "built.mount raised in _mount_built",
                )
            self._built = built
            try:
                scope = self._build_ctx.current if self._build_ctx else None
                if scope is not None:
                    self._register_scope(scope)
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_mount_built_register_scope_exc",
                    "Failed to register scope in _mount_built",
                )

    def _unmount_built(self) -> None:
        built = getattr(self, "_built", None)
        if built is None:
            return
        try:
            built.unmount()
        except Exception:
            exception_once(
                _logger,
                "widget_builder_unmount_built_exc",
                "built.unmount raised in _unmount_built",
            )
        self._release_built(built)
        self._built = None
        self._build_ctx = None
        self._scope_registry = {}
        self._scope_nodes.clear()
        self._active_scope_ids.clear()
        self._scope_metadata.clear()
        self._dependency_scope_index.clear()
        self._dirty_scopes.clear()

    # --- Lifecycle & Rendering (Mixin overrides) --------------------------
    def on_mount(self) -> None:
        super().on_mount()  # type: ignore
        # If this widget is a composition (uses build), build it now.
        built = self.evaluate_build()
        if built is not None and built is not self:
            self._mount_built(built)

    def on_unmount(self) -> None:
        self._unmount_built()
        super().on_unmount()  # type: ignore

    def layout(self, width: int, height: int) -> None:
        # Delegate to super (WidgetKernel) to store layout_rect and layout children
        super().layout(width, height)  # type: ignore
        # Delegate to built child (composition)
        if self._built:
            self._built.layout(width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        if self._built:
            self._built.paint(canvas, x, y, width, height)
        else:
            super().paint(canvas, x, y, width, height)  # type: ignore

    def hit_test(self, x: int, y: int):
        if self._built:
            hit = self._built.hit_test(x, y)
            if hit:
                return hit
        return super().hit_test(x, y)  # type: ignore

    async def handle_back_event(self) -> bool:
        if self._built is not None:
            handler = getattr(self._built, "handle_back_event", None)
            if callable(handler):
                try:
                    result = handler()
                    if inspect.isawaitable(result):
                        return bool(await result)
                    return bool(result)
                except Exception:
                    # Fail open to avoid trapping navigation.
                    exception_once(
                        _logger,
                        "widget_builder_handle_back_event_exc",
                        "handle_back_event raised (child=%s)",
                        type(self._built).__name__,
                    )
                    return True
        return True

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        if self._built:
            return measure_preferred_size(self._built, max_width=max_width, max_height=max_height)

        # Measuring must be side-effect-free (issue #244). When mounted, the live
        # subtree already exists — either as ``_built`` (handled above) or, for
        # widgets whose ``build()`` returns ``self`` (e.g. Card), as mounted
        # children. Measure those directly; never call ``build()`` here, since
        # rebuilding a scoped fragment would unmount the subtree and cancel an
        # in-progress pointer gesture.
        if getattr(self, "_app", None) is not None:
            return super().preferred_size(max_width=max_width, max_height=max_height)  # type: ignore

        # Unmounted composables still need intrinsic sizing (e.g. App auto window
        # sizing before mount). There is no live subtree to harm, so evaluate
        # build once and measure the returned subtree directly.
        try:
            built = self.evaluate_build()
        except Exception:
            return super().preferred_size(max_width=max_width, max_height=max_height)  # type: ignore

        if built is not None and built is not self:
            self._adopt_built(built)
            return measure_preferred_size(built, max_width=max_width, max_height=max_height)

        return super().preferred_size(max_width=max_width, max_height=max_height)  # type: ignore

    def rebuild(self) -> None:
        app = getattr(self, "_app", None)
        try:
            self._unmount_built()
        except Exception:
            exception_once(
                _logger,
                "widget_builder_rebuild_unmount_exc",
                "_unmount_built raised in rebuild",
            )
        built = self.evaluate_build()
        if built is self:
            # A host that decorates itself and returns itself (Card) has no
            # separate subtree to hold. Storing it as ``_built`` would make
            # layout, paint and hit-testing recurse into this same widget
            # forever -- the same reason :meth:`on_mount` skips it.
            pass
        elif app is None:
            # Not mounted, so there is nothing to mount the subtree against --
            # but it still needs its upward link, or measuring it would resolve
            # ancestors from a detached widget. See :meth:`_adopt_built`.
            self._adopt_built(built)
            self._built = built
        else:
            self._mount_built(built)

        # Request layout update since content changed
        marker = getattr(self, "mark_needs_layout", None)
        if callable(marker):
            marker()

    # --- Scope helpers ----------------------------------------------------
    def render_scope(self, name: str, factory: Callable[[], "Widget"]) -> "Widget":
        """Render ``factory`` inside a named, independently-recomposable scope.

        Recomposition is idempotent: the scope's subtree is rebuilt only when the
        scope is invalidated (``invalidate_scope_id`` / a tracked dependency), not
        merely because the host's ``build()`` re-runs. Callers that mutate the
        factory's inputs must invalidate the scope; relying on a host rebuild to
        refresh an un-invalidated scope will not work.
        """
        ctx = self._build_ctx
        if ctx is None:
            return _require_widget_instance(factory())
        manager = ctx.scope(name)
        handle = manager.__enter__()
        try:
            return self.render_scope_with_handle(handle, factory)
        finally:
            manager.__exit__(None, None, None)

    def render_scope_with_handle(self, handle: ScopeHandle, factory: Callable[[], "Widget"]) -> "Widget":
        scope = handle.scope
        scope_id = handle.id
        return self._render_scope_entry(scope_id, scope, factory)

    def _render_scope_entry(
        self,
        scope_id: str,
        scope: RecomposeScope,
        factory: Callable[[], "Widget"],
    ) -> "Widget":
        normalized_factory = _normalize_scope_factory(factory)
        self._register_scope(scope)
        self._active_scope_ids.add(scope_id)
        fragment = self._scope_nodes.get(scope_id)
        ScopedFragment = _get_scoped_fragment_class()
        if fragment is None:
            fragment = ScopedFragment(scope_id=scope_id, factory=normalized_factory)
            self._scope_nodes[scope_id] = fragment
            needs_build = True
        else:
            # Always refresh the stored factory so a later invalidation rebuilds
            # against current host state, even when we skip rebuilding now.
            fragment.update_factory(normalized_factory)
            # Idempotent recomposition (issue #244): rebuild only when the scope
            # was explicitly invalidated or has no built subtree yet. Re-entering
            # build() (e.g. on every measure) must not tear down the live subtree.
            needs_build = scope_id in self._dirty_scopes or fragment.built_child is None

        if needs_build:
            try:
                fragment.rebuild()
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_scope_fragment_rebuild_exc",
                    "Scoped fragment rebuild raised",
                )
            self._dirty_scopes.discard(scope_id)
        self._capture_scope_metadata(scope_id, factory, fragment)
        return fragment

    def scope(self, name: str) -> _ScopeContextManager:
        if self._build_ctx is None:
            raise RuntimeError("scope() is only available during build().")
        return self._build_ctx.scope(name)

    def _register_scope(self, scope: RecomposeScope) -> None:
        self._scope_registry[scope.identifier] = scope

    def _prune_unused_scopes(self) -> None:
        if not self._scope_nodes:
            return
        active: Set[str] = getattr(self, "_active_scope_ids", set())
        stale = [scope_id for scope_id in self._scope_nodes.keys() if scope_id not in active]
        for scope_id in stale:
            fragment = self._scope_nodes.pop(scope_id)
            self._dirty_scopes.discard(scope_id)
            try:
                fragment.unmount()
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_prune_scope_fragment_unmount_exc",
                    "Scoped fragment unmount raised during pruning",
                )
            self._remove_scope_metadata(scope_id)

    def _invalidate_scope(self, scope: RecomposeScope) -> None:
        self._register_scope(scope)
        if self._schedule_scope_recomposition(scope.identifier):
            return
        invalidate = getattr(self, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_invalidate_scope_invalidate_exc",
                    "invalidate() raised during scope invalidation",
                )

    def invalidate_scope_id(self, scope_id: str) -> None:
        if self._schedule_scope_recomposition(scope_id):
            return
        invalidate = getattr(self, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_invalidate_scope_id_invalidate_exc",
                    "invalidate() raised during scope_id invalidation",
                )

    def _handle_scope_invalidation(self, scope_id: str) -> bool:
        return self._schedule_scope_recomposition(scope_id)

    def _schedule_scope_recomposition(self, scope_id: str) -> bool:
        if scope_id not in self._scope_nodes:
            return False
        # Single funnel for every scope invalidation: mark the scope dirty so the
        # next render (in-line or via _perform_scope_rebuild) rebuilds it.
        self._dirty_scopes.add(scope_id)
        first_insert = _queue_scope_recomposition(self, scope_id)
        if first_insert:
            invalidate = getattr(self, "invalidate", None)
            if callable(invalidate):
                try:
                    invalidate()
                except Exception:
                    exception_once(
                        _logger,
                        "widget_builder_schedule_scope_recomposition_invalidate_exc",
                        "invalidate() raised while scheduling scope recomposition",
                    )
        if getattr(self, "_app", None) is None:
            flush_scope_recompositions()
        return True

    def _process_scope_recompositions(self, scope_ids: Set[str]) -> None:
        if not scope_ids:
            return
        for scope_id in list(scope_ids):
            try:
                self._perform_scope_rebuild(scope_id)
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_process_scope_rebuild_exc",
                    "_perform_scope_rebuild raised",
                )

    def _perform_scope_rebuild(self, scope_id: str) -> bool:
        fragment = self._scope_nodes.get(scope_id)
        if fragment is None:
            return False
        try:
            fragment.rebuild()
        except Exception:
            exception_once(
                _logger,
                "widget_builder_perform_scope_rebuild_exc",
                "Scoped fragment rebuild raised in _perform_scope_rebuild",
            )
            return False
        self._dirty_scopes.discard(scope_id)
        factory: Optional[Callable[[], "Widget"]]
        metadata = self._scope_metadata.get(scope_id)
        if metadata is not None:
            factory = metadata.factory
        else:
            factory = getattr(fragment, "_factory", None)
        if callable(factory):
            self._capture_scope_metadata(scope_id, factory, fragment)
        return True

    def get_scope_metadata(self, scope_id: str) -> Optional[ScopeMetadata]:
        return self._scope_metadata.get(scope_id)

    def _lookup_scope_ids_for_dependency(self, dependency: str) -> Tuple[str, ...]:
        scopes = self._dependency_scope_index.get(dependency)
        if not scopes:
            return tuple()
        return tuple(scopes)

    def _handle_scope_dependency(self, dependency: str) -> bool:
        scope_ids = self._lookup_scope_ids_for_dependency(dependency)
        if not scope_ids:
            return False
        handled = False
        for scope_id in scope_ids:
            try:
                scheduled = self._schedule_scope_recomposition(scope_id)
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_handle_scope_dependency_exc",
                    "Scheduling scope recomposition raised (dependency=%s)",
                    dependency,
                )
                scheduled = False
            if scheduled:
                handled = True
        return handled

    def _capture_scope_metadata(
        self,
        scope_id: str,
        factory: Callable[[], "Widget"],
        fragment: "Widget",
    ) -> None:
        child = None
        getter = getattr(fragment, "_current_child", None)
        if callable(getter):
            try:
                child = getter()
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_capture_child_exc",
                    "Failed to read _current_child from fragment (fragment=%s)",
                    type(fragment).__name__,
                )
                child = None
        layout_deps: Tuple[str, ...] = ()
        paint_deps: Tuple[str, ...] = ()
        if child is not None:
            child_type = type(child)
            try:
                layout_deps = tuple(getattr(child_type, "_layout_dependencies", tuple()))
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_layout_deps_exc",
                    "Failed to read _layout_dependencies (child_type=%s)",
                    child_type.__name__,
                )
                layout_deps = ()
            try:
                paint_deps = tuple(getattr(child_type, "_paint_dependencies", tuple()))
            except Exception:
                exception_once(
                    _logger,
                    "widget_builder_paint_deps_exc",
                    "Failed to read _paint_dependencies (child_type=%s)",
                    child_type.__name__,
                )
                paint_deps = ()
        self._clear_dependency_index(scope_id)
        metadata = ScopeMetadata(
            scope_id=scope_id,
            factory=factory,
            _child_ref=weakref.ref(child) if child is not None else None,
            layout_dependencies=layout_deps,
            paint_dependencies=paint_deps,
        )
        self._scope_metadata[scope_id] = metadata
        self._index_scope_dependencies(scope_id, layout_deps, paint_deps)

    def _remove_scope_metadata(self, scope_id: str) -> None:
        metadata = self._scope_metadata.pop(scope_id, None)
        if metadata is None:
            return
        self._clear_dependency_index(scope_id, metadata)

    def _index_scope_dependencies(
        self,
        scope_id: str,
        layout_deps: Tuple[str, ...],
        paint_deps: Tuple[str, ...],
    ) -> None:
        for name in itertools.chain(layout_deps, paint_deps):
            key = str(name).strip()
            if not key:
                continue
            scopes = self._dependency_scope_index.setdefault(key, set())
            scopes.add(scope_id)

    def _clear_dependency_index(
        self,
        scope_id: str,
        metadata: Optional[ScopeMetadata] = None,
    ) -> None:
        data = metadata or self._scope_metadata.get(scope_id)
        if data is None:
            return
        dep_names = set(data.layout_dependencies) | set(data.paint_dependencies)
        for name in dep_names:
            scopes = self._dependency_scope_index.get(name)
            if scopes is None:
                continue
            scopes.discard(scope_id)
            if not scopes:
                self._dependency_scope_index.pop(name, None)
