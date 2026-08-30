"""Window lifecycle: open/close, parent/child, modality, exit policy.

The contract from ``docs/design/APP_WINDOW.md``: a Window is a model until
``open()``, one object is one window lifetime, children close with their
parent, a modal child blocks input to its parent chain, and the App's
``ExitPolicy`` decides when the application exits.
"""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.runtime.app import App, ExitPolicy
from nuiitivet.runtime.window import Window, WindowScope
from nuiitivet.widgeting.widget import Widget


class _Probe(Widget):
    def build(self) -> Widget:
        return self


def _app() -> App:
    """Create an App; the caller must bind the result (``_ = _app()`` at least).

    ``current_app()`` holds only a weakref, and the App/Window reference cycle
    is collectable -- an unlucky gc pass between a bare ``_app()`` and the
    ``Window.open()`` that follows would make ``current_app()`` return ``None``.
    """
    return App(Window(content=Container()))


# --- construction ----------------------------------------------------------


def test_app_requires_a_window() -> None:
    with pytest.raises(TypeError):
        App()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        # Content is not a window; it must be wrapped in one.
        App(Container())  # type: ignore[arg-type]


def test_modal_requires_a_parent() -> None:
    with pytest.raises(ValueError):
        Window(content=Container(), modal=True)


def test_construction_builds_no_tree() -> None:
    window = Window(content=Container)
    assert not hasattr(window, "root")
    assert window.is_open.value is False


def test_accepts_first_mouse_defaults_on_with_opt_out() -> None:
    # macOS-only in effect (the Cocoa acceptsFirstMouse: patch reads it),
    # but the model attribute exists on every platform.
    assert Window(content=Container()).accepts_first_mouse is True
    assert Window(content=Container(), accepts_first_mouse=False).accepts_first_mouse is False


# --- open / close ----------------------------------------------------------


def test_open_registers_and_mounts() -> None:
    app = _app()
    window = Window(content=Container()).open()

    assert window in app.windows
    assert window.app is app
    assert window.is_open.value is True
    assert window.root._mounted is True
    assert window.is_main is False
    assert app.main_window.is_main is True


def test_window_ids_are_distinct() -> None:
    app = _app()
    window = Window(content=Container()).open()
    assert window.id != app.main_window.id


def test_open_twice_raises_and_closed_is_final() -> None:
    _ = _app()
    window = Window(content=Container()).open()
    with pytest.raises(RuntimeError):
        window.open()

    window.close()
    assert window.is_open.value is False
    with pytest.raises(RuntimeError):
        window.open()


def test_instrument_window_hook_runs_once_per_new_window() -> None:
    """The dev seam: per-window instrumentation follows every open."""
    app = _app()
    seen: list[Window] = []
    app._instrument_window_hook = seen.append

    window = Window(content=Container()).open()

    assert seen == [window]


def test_unregister_window_hook_runs_once_per_close() -> None:
    """The dev seam's counterpart: every close path reaches the hook (#622)."""
    app = _app()
    seen: list[Window] = []
    app._unregister_window_hook = seen.append

    window = Window(content=Container()).open()
    window.close()
    # Closing again is a no-op and must not re-fire the hook.
    window.close()

    assert seen == [window]


def test_unregister_window_hook_covers_parent_cascade() -> None:
    app = _app()
    seen: list[Window] = []
    app._unregister_window_hook = seen.append

    parent = Window(content=Container()).open()
    child = Window(content=Container(), parent=parent).open()

    parent.close()

    # Children close first, transitively, and each close reaches the hook.
    assert seen == [child, parent]


def test_unregister_window_hook_exception_does_not_break_close() -> None:
    app = _app()

    def _boom(window: Window) -> None:
        raise RuntimeError("hook failed")

    app._unregister_window_hook = _boom
    window = Window(content=Container()).open()
    window.close()

    assert window not in app.windows
    assert window.is_open.value is False


def test_close_unmounts_and_unregisters() -> None:
    app = _app()
    window = Window(content=Container()).open()
    root = window.root

    window.close()

    assert window not in app.windows
    assert root._mounted is False
    # Closing again is a no-op.
    window.close()


def test_close_cascades_to_children_first() -> None:
    app = _app()
    parent = Window(content=Container()).open()
    child = Window(content=Container(), parent=parent).open()
    grandchild = Window(content=Container(), parent=child).open()

    parent.close()

    assert parent not in app.windows
    assert child.is_open.value is False
    assert grandchild.is_open.value is False


# --- scope resolution ------------------------------------------------------


def test_window_of_resolves_to_the_owning_window() -> None:
    _ = _app()
    probe = _Probe()
    window = Window(content=probe).open()

    assert Window.of(probe) is window


def test_each_window_has_its_own_navigator_and_overlay() -> None:
    app = _app()
    second = Window(content=Container()).open()

    assert second.navigator is not app.main_window.navigator
    assert second.overlay is not app.main_window.overlay


def test_root_is_wrapped_appscope_then_windowscope() -> None:
    _ = _app()
    window = Window(content=Container()).open()
    from nuiitivet.runtime.app import AppScope

    assert isinstance(window.root, AppScope)
    assert isinstance(window.root.children_snapshot()[0], WindowScope)


# --- modality --------------------------------------------------------------


def test_modal_child_blocks_the_parent_chain_only() -> None:
    app = _app()
    parent = Window(content=Container()).open()
    sibling = Window(content=Container()).open()
    modal = Window(content=Container(), parent=parent, modal=True).open()

    assert parent._modal_blocked() is True
    assert sibling._modal_blocked() is False
    assert modal._modal_blocked() is False
    assert app.main_window._modal_blocked() is False

    modal.close()
    assert parent._modal_blocked() is False


def test_modal_gate_swallows_input() -> None:
    _ = _app()
    parent = Window(content=Container()).open()
    Window(content=Container(), parent=parent, modal=True).open()

    # Key input is consumed (True) so backend defaults never fire; pointer
    # input is dropped.
    assert parent._dispatch_key_press("a") is True
    assert parent._dispatch_text("a") is True
    assert parent._dispatch_mouse_scroll(1, 1, 0.0, 1.0) is None


# --- exit policy -----------------------------------------------------------


def test_main_window_closed_policy_closes_everything() -> None:
    app = App(Window(content=Container()), exit_policy=ExitPolicy.MAIN_WINDOW_CLOSED)
    secondary = Window(content=Container()).open()

    app.main_window.close()

    assert secondary.is_open.value is False
    assert app.windows == ()


def test_last_window_closed_policy_keeps_running_until_empty() -> None:
    app = App(Window(content=Container()))
    secondary = Window(content=Container()).open()

    secondary.close()
    assert app._exiting is False

    app.main_window.close()
    assert app.windows == ()


def test_explicit_policy_survives_all_windows_closing() -> None:
    app = App(Window(content=Container()), exit_policy=ExitPolicy.EXPLICIT)
    app.main_window.close()

    assert app.windows == ()
    assert app._exiting is False

    # A new window can still be opened from app-held state.
    reopened = Window(content=Container()).open()
    assert app.windows == (reopened,)


def test_exit_closes_windows_in_reverse_order() -> None:
    app = App(Window(content=Container()), exit_policy=ExitPolicy.EXPLICIT)
    second = Window(content=Container()).open()

    app.exit(3)

    assert app.windows == ()
    assert app._exit_code == 3
    assert second.is_open.value is False
    assert app.main_window.is_open.value is False


# --- closed awaitable ------------------------------------------------------


def test_closed_resolves_when_the_window_closes() -> None:
    _ = _app()
    window = Window(content=Container()).open()

    async def scenario() -> bool:
        waiter = asyncio.ensure_future(window.closed)
        await asyncio.sleep(0)
        assert not waiter.done()
        window.close()
        await asyncio.wait_for(waiter, timeout=1.0)
        return True

    assert asyncio.run(scenario()) is True


def test_closed_resolves_immediately_for_a_closed_window() -> None:
    _ = _app()
    window = Window(content=Container()).open()
    window.close()

    async def scenario() -> bool:
        await asyncio.wait_for(window.closed, timeout=1.0)
        return True

    assert asyncio.run(scenario()) is True
