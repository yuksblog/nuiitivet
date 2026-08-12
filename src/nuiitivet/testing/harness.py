"""``AppHarness`` -- drive a whole screen in-process, with no window."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from nuiitivet._interaction import action as _action

from ._support import _HarnessBase
from .errors import ActionNotHandledError


class AppHarness(_HarnessBase):
    """A real ``App``, arranged for a test: fixed size, settled, drivable.

    Everything a window would otherwise decide is pinned, so the same test gives
    the same answer on every machine::

        with AppHarness(CounterScreen(), size=(800, 600)) as app:
            app.click(key="increment")
            assert app.get(key="count").text == "Count: 1"

    Under pytest, prefer the ``nuiitivet_app`` fixture, which owns the ``with``
    on the test's behalf -- the harness must be closed, and a test that forgets
    leaves its tree mounted and subscribed.

    The action verbs are the dev bridge's, one for one, targeting by the same
    ``key`` / ``label``, so what an author learns writing E2E carries straight
    down. Two things differ, both because a test cannot read a result and judge
    the way an assistant can: an ambiguous target raises instead of silently
    taking the first match, and a verb nothing consumed raises
    :class:`~nuiitivet.testing.errors.ActionNotHandledError` instead of reporting
    ``handled: False``.

    Not named ``TestApp``: pytest would try to collect it, and warn on the import
    line of every module that imported it.
    """

    __test__ = False

    def __init__(
        self,
        content: Any,
        *,
        size: Tuple[float, float],
        theme: Optional[Any] = None,
        leak_check: Optional[str] = None,
        callback_errors: Optional[str] = None,
        **app_kwargs: Any,
    ) -> None:
        """Build an ``App`` around ``content`` and mount it at ``size``.

        Args:
            content: The screen under test -- a ``Widget`` instance (the normal
                form: the test keeps it and asserts on its ``Observable``s) or a
                zero-argument factory returning one, for the rebuild path.
            size: ``(width, height)``, **required**. There is no default on
                purpose: ``App`` would otherwise resolve ``"auto"`` against the
                root's preferred size, which is a machine-dependent number nobody
                chose, and every geometry failure downstream would read as a
                harness bug.
            theme: The theme to install. Defaults to the App's own default.
            leak_check: ``"error"``, ``"warn"`` or ``"off"`` for the
                subscription-leak check at teardown, overriding the suite default
                in ``[tool.nuiitivet.testing]`` and the test's ``nuiitivet``
                marker. The narrowest of the three wins.
            callback_errors: ``"error"``, ``"warn"`` or ``"off"`` for the check
                that a callback the framework contained fails the test, scoped
                and overridden the same way.
            **app_kwargs: Passed through to ``App`` (``overlay_factory``, ...).
        """
        from nuiitivet.runtime.app import App

        width, height = size
        super().__init__(leak_check=leak_check, callback_errors=callback_errors)
        # Before the App exists: constructing one mounts the whole tree, and
        # anything it schedules on the way must land on a clock we can pump
        # rather than on a timer thread.
        self._ensure_clock()
        try:
            self._app = App(
                content,
                width=int(width),
                height=int(height),
                title=None,
                chrome=None,
                theme=theme,
                **app_kwargs,
            )
        except BaseException:
            # Nothing else will: the harness never reached the open-harness
            # registry, so no teardown sweep knows about its task observer.
            self._stop_observing()
            raise
        # Registered as soon as there is a mounted tree to tear down, so a
        # screen whose first settle raises is still cleaned up.
        self._register()
        self.settle()

    # -- harness surface ---------------------------------------------------

    @property
    def app(self) -> Any:
        """The underlying ``App``. The escape hatch, greppable on purpose."""
        self._require_open()
        return self._app

    @property
    def _settle_target(self) -> Any:
        return self._app

    @property
    def _query_root(self) -> Any:
        return self._app.root

    @property
    def size(self) -> Tuple[float, float]:
        """The size the tree is laid out at."""
        return (self._app.width, self._app.height)

    # -- action verbs ------------------------------------------------------
    #
    # Each core verb settles on its own -- non-strict, because the bridge must
    # survive a bad frame. The harness settles again afterwards, strictly and
    # pumping the clock, and that second settle is the one the test observes: a
    # layout error the bridge's settle swallowed is raised by ours on the next
    # pass, and a dispatch_to_ui write the action produced is applied.

    def click(
        self,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        button: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Press and release at a target, or at raw root coordinates.

        Raises:
            TargetNotFoundError: The identifier matched nothing, or matched a
                widget with no layout rect.
            TargetNotVisibleError: The target is scrolled out of view or covered.
                ``scroll_into_view`` is the verb that fixes it.
        """
        return self._act(
            "click",
            lambda: _action.click(self._app, key=key, label=label, x=x, y=y, button=button),
            key=key,
            label=label,
        )

    def scroll(
        self,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        dx: float = 0.0,
        dy: float = 0.0,
    ) -> Dict[str, Any]:
        """Send wheel notches to a scroll *region*.

        The target is the region itself, never a row inside it -- naming a row
        raises with the region to use instead, which is a diagnostic worth
        keeping rather than a restriction to work around.
        """
        return self._act(
            "scroll",
            lambda: _action.scroll(self._app, key=key, label=label, dx=dx, dy=dy),
            key=key,
            label=label,
        )

    def scroll_into_view(
        self,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        align: str = "nearest",
    ) -> Dict[str, Any]:
        """Scroll until the target is reachable -- the fix for a ``False``
        :attr:`~nuiitivet.testing.node.Node.is_reachable`."""
        return self._act(
            "scroll_into_view",
            lambda: _action.scroll_into_view(self._app, key=key, label=label, align=align),
            key=key,
            label=label,
        )

    def type(
        self,
        text: str,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        require_handled: bool = True,
    ) -> Dict[str, Any]:
        """Type ``text``, optionally clicking a target to focus it first.

        Text is injected into whatever is *focused*, which is a precondition the
        bridge states nowhere and an author arriving from E2E has a human's
        memory of having satisfied. Passing ``key=`` / ``label=`` clicks the
        target and then types, in one call with no hidden ordering.

        Raises:
            ActionNotHandledError: Nothing was focused, so the text went nowhere.
                Pass ``require_handled=False`` to get the result dict instead and
                assert on the negative deliberately.
        """
        if key is not None or label is not None:
            self.click(key=key, label=label)
        return self._act(
            "type",
            lambda: _action.type_text(self._app, text),
            require_handled=require_handled,
            what=f"type({text!r})",
        )

    def key(
        self,
        name: str,
        modifiers: Any = 0,
        *,
        require_handled: bool = True,
    ) -> Dict[str, Any]:
        """Press and release a key (``"enter"``, ``"tab"``, ``"a"``).

        ``modifiers`` takes an int mask or names (``["accel", "shift"]``), so
        shortcuts and focus traversal behave as they do under real input.

        Raises:
            ActionNotHandledError: Nothing consumed the keystroke. Pass
                ``require_handled=False`` to assert on that deliberately.
        """
        return self._act(
            "key",
            lambda: _action.press_key(self._app, name, modifiers),
            require_handled=require_handled,
            what=f"key({name!r})",
        )

    def resize(self, width: float, height: float) -> None:
        """Re-lay-out at a new size, running the size-change callbacks.

        The only way to reach the code path that runs when a size *changes* --
        ``on_size_changed`` and everything derived from it -- without launching a
        window and dragging its edge.
        """
        self._require_open()
        self._app.width = int(width)
        self._app.height = int(height)
        self._last_action.description = f"resize({int(width)}, {int(height)})"
        self.settle()

    # -- plumbing ----------------------------------------------------------

    def _act(
        self,
        verb: str,
        call: Callable[[], Dict[str, Any]],
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        require_handled: bool = False,
        what: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_open()
        description = what
        if description is None:
            target = ""
            if key is not None:
                target = f"key={key!r}"
            elif label is not None:
                target = f"label={label!r}"
            description = f"{verb}({target})"
        self._last_action.description = description
        result = call()
        self.settle()
        if require_handled and not result.get("handled", True):
            raise ActionNotHandledError(
                f"{description} was dispatched and nothing consumed it "
                f"(handled={result.get('handled')!r}). "
                + (
                    "Text goes to the focused widget: click the field first, or "
                    "pass the target as .type(text, key=...). "
                    if verb == "type"
                    else "Nothing is bound to that key in the focused subtree. "
                )
                + "Pass require_handled=False if the test means to assert that."
            )
        return result

    # -- navigation / overlay ----------------------------------------------
    #
    # Deliberately absent: asserting on the route stack or on what is open needs
    # a public accessor the framework does not have yet (Navigator.snapshot_stack
    # is the hot-reload restore log, not the stack, and Overlay exposes nothing),
    # which is a framework API change rather than a harness one. Reach through
    # `.app` in the meantime.

    def _teardown(self) -> None:
        root = getattr(self._app, "root", None)
        if root is not None:
            root.unmount()


__all__ = ["AppHarness"]
