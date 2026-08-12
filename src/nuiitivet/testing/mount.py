"""``mount(widget)`` -- test one widget, with no App stack under it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional, cast

from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.plain_theme import PlainTheme

from ._support import _HarnessBase

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App


class Invalidation(NamedTuple):
    """One recorded repaint request, with the flags it carried."""

    immediate: bool
    content: bool


class WidgetHost(_HarnessBase):
    """The minimal app a mounted widget is hosted by.

    Implements the whole host contract a widget can reach for -- the full
    ``invalidate`` signature, a ``ThemeManager`` behind an ``AppScope``, and the
    ``root`` / ``width`` / ``height`` the interaction core settles against -- so
    nobody has to reverse-engineer it from whichever widget they happen to be
    testing. Construct it through :func:`mount`.

    It observes; it does not drive. The action verbs go through an ``App``'s own
    pointer dispatch, which this deliberately does not reimplement, so clicking
    and typing are :class:`~nuiitivet.testing.AppHarness`'s half of the package.
    """

    __test__ = False

    def __init__(
        self,
        widget: Any,
        *,
        theme: Optional[Any] = None,
        scope: bool = True,
        leak_check: Optional[str] = None,
    ) -> None:
        if theme is not None and not scope:
            raise ValueError(
                "theme= and scope=False contradict each other: scope=False mounts "
                "the widget with no AppScope, so there is no provider for a theme "
                "to be served through. Pass one or the other."
            )
        super().__init__(leak_check=leak_check)

        self.width: Optional[float] = None
        self.height: Optional[float] = None
        self.invalidations: List[Invalidation] = []
        self.intents: List[Any] = []

        self._theme_manager = ThemeManager(initial=theme or PlainTheme.light())
        self._scope_installed = scope
        self._widget = widget

        if scope:
            from nuiitivet.geometry import Geometry
            from nuiitivet.runtime.app import AppScope

            # The same wrapping the App builds, for the same reason: Theme.of and
            # Geometry.of must resolve here exactly as they do in a real app, or a
            # widget passes its test against a fallback it never runs against.
            #
            # The cast is the point of this class. AppScope needs a weak-referenceable
            # object with ``_theme_manager``, ``invalidate`` and ``dispatch`` -- its
            # own comment says "tests scope a stub app" -- and this host implements
            # all of them. Casting once here is what spares every author the
            # ``type: ignore`` they would otherwise write at their own call site.
            self.root: Any = AppScope(app=cast("App", self), child=Geometry(widget))
        else:
            self.root = widget

        # Registered before the mount, so a widget whose ``on_mount`` raises is
        # still unmounted at teardown rather than left attached.
        self._register()
        self.root.mount(self)

    # -- the host contract -------------------------------------------------

    def invalidate(self, immediate: bool = False, content: bool = True) -> None:
        """Record a repaint request. The full signature, so nothing has to guess."""
        self.invalidations.append(Invalidation(immediate=immediate, content=content))

    def dispatch(self, intent: Any) -> None:
        """Record an intent the widget dispatched.

        A widget reaches this through ``AppScope``'s ``AppProxy``. With no real
        app there is nothing to route an intent *to*, so the host records it --
        which is also the assertion a widget test wants: "tapping this dispatched
        that". Read :attr:`intents`.
        """
        self.intents.append(intent)

    @property
    def invalidate_count(self) -> int:
        """How many repaints were requested since mount.

        Assert ``> 0`` or ``== 0``. An exact count is an implementation detail:
        coalesce two invalidations into one and ``== 2`` breaks with no change in
        behaviour. What the counter is genuinely for is "this must not repaint per
        keystroke", which ``== 0`` says and a number does not.
        """
        return len(self.invalidations)

    @property
    def theme_manager(self) -> ThemeManager:
        """The manager behind the ``AppScope``. Push a theme to test adoption."""
        return self._theme_manager

    @property
    def widget(self) -> Any:
        """The widget under test, as passed to :func:`mount`."""
        return self._widget

    # -- harness surface ---------------------------------------------------

    @property
    def _settle_target(self) -> Any:
        return self

    @property
    def _query_root(self) -> Any:
        return self.root

    def layout(self, width: float, height: float) -> None:
        """Lay the tree out at this size, then settle.

        Explicit, with no default, on purpose: a size nobody chose makes every
        geometry failure -- and every ``TargetNotFoundError`` on a widget that was
        never laid out -- read as a harness bug rather than a missing call. Call
        it again to re-lay-out at a new size.
        """
        self._require_open()
        self.width = float(width)
        self.height = float(height)
        self.settle()

    def settle(self) -> None:
        self._require_open()
        if self.width is None or self.height is None:
            raise RuntimeError(
                "nothing has been laid out yet: call host.layout(width, height) "
                "before settling. mount() gives the widget no size of its own, so "
                "there is no geometry to flush into."
            )
        super().settle()

    def push_theme(self, theme: Any) -> None:
        """Install a new theme and settle, so adoption is observable.

        The question this answers is "does my widget follow a theme change",
        which is a different one from "did it pick the theme up at mount".
        """
        self._require_open()
        self._theme_manager.set_theme(theme)
        self.settle()

    def _teardown(self) -> None:
        self.root.unmount()


def mount(
    widget: Any,
    *,
    theme: Optional[Any] = None,
    scope: bool = True,
    leak_check: Optional[str] = None,
) -> WidgetHost:
    """Mount ``widget`` on a minimal host, for a single-widget test.

    Use it as a context manager; the widget is unmounted on exit, so a test
    cannot leave one subscribed to a live observable for the rest of the
    session::

        with mount(card) as host:
            host.layout(400, 200)
            card.expanded.value = True
            host.settle()
            assert host.get(key="body").is_reachable

    Args:
        widget: The widget under test.
        theme: The theme served to it. Defaults to the light theme -- **not** to
            no theme: ``Theme.of`` falls back silently when no ``AppScope`` is
            reachable, so a themeless host does not fail, it reports the wrong
            theme and the test goes green against a default the app never runs.
        scope: Whether to install the ``AppScope`` / ``Geometry`` providers a real
            app installs. ``False`` mounts the widget bare, which is what a test
            of the detached path -- a widget deliberately measured outside an App,
            as offscreen sizing does -- actually wants. Passing ``theme=`` with
            ``scope=False`` is a contradiction and raises.
        leak_check: ``"error"``, ``"warn"`` or ``"off"`` for the
            subscription-leak check at teardown, overriding the suite default in
            ``[tool.nuiitivet.testing]`` and the test's ``nuiitivet`` marker. The
            narrowest of the three wins.

    Returns:
        The :class:`WidgetHost`, which is also the query surface.
    """
    return WidgetHost(widget, theme=theme, scope=scope, leak_check=leak_check)


__all__ = ["Invalidation", "WidgetHost", "mount"]
