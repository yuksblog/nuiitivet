import sys
import types
from nuiitivet.runtime.app import App
from nuiitivet.layout.column import Column
from nuiitivet.material import Checkbox


def test_focus_traversal_and_shift_tab():
    cb1 = Checkbox()
    cb2 = Checkbox(disabled=True)
    cb3 = Checkbox()
    root = Column([cb1, cb2, cb3])
    app = App(root)
    assert getattr(app, "_focused_target", None) is None
    handled = app._dispatch_key_press("tab")
    assert handled is True
    assert app._focused_target is cb1
    assert getattr(cb1, "_focused", False) is True
    handled = app._dispatch_key_press("tab")
    assert handled is True
    assert app._focused_target is cb3
    assert getattr(cb3, "_focused", False) is True
    orig_pyglet = sys.modules.get("pyglet")
    try:
        fake_key = types.SimpleNamespace(MOD_SHIFT=1)
        fake_window = types.SimpleNamespace(key=fake_key)
        fake_pyglet = types.SimpleNamespace(window=fake_window)
        sys.modules["pyglet"] = fake_pyglet
        handled = app._dispatch_key_press("tab", modifiers=1)
        assert handled is True
        assert app._focused_target is cb1
        assert getattr(cb1, "_focused", False) is True
    finally:
        if orig_pyglet is None:
            try:
                del sys.modules["pyglet"]
            except Exception:
                pass
        else:
            sys.modules["pyglet"] = orig_pyglet
