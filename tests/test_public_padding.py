"""Every public widget that occupies a rect accepts ``padding``.

The box model gives every widget a ``padding`` attribute; this test pins the
public surface so a new widget cannot ship without exposing it. The exemptions
are widgets that occupy no rect of their own, or hosts sized by their parent.
"""

import inspect

import pytest

import nuiitivet.material as nv
from nuiitivet.widgeting.widget import Widget

EXEMPT: dict[str, str] = {
    "ForEach": "provider: its children are lifted into the parent layout",
    "RailItem": "descriptor: NavigationRail renders it through its own item buttons",
    "GroupButton": "sized by its button group, which owns the outer space",
    "AppScope": "host filled by the window",
    "WindowScope": "host filled by the window",
    "Navigator": "host filled by its parent",
    "Overlay": "host filled by its parent",
    "MenuBarArea": "slot filled by the window chrome",
}


def _public_widget_classes() -> list[tuple[str, type]]:
    out: list[tuple[str, type]] = []
    for name in sorted(dir(nv)):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(nv, name)
        except Exception:
            continue
        if inspect.isclass(obj) and issubclass(obj, Widget):
            out.append((name, obj))
    return out


_PUBLIC = _public_widget_classes()


def test_exempt_list_names_only_public_widgets() -> None:
    public_names = {name for name, _ in _PUBLIC}
    assert set(EXEMPT) <= public_names


@pytest.mark.parametrize("name,cls", _PUBLIC, ids=[name for name, _ in _PUBLIC])
def test_public_widget_accepts_padding(name: str, cls: type) -> None:
    if name in EXEMPT:
        pytest.skip(EXEMPT[name])
    params = inspect.signature(cls).parameters
    accepts = "padding" in params or any(p.kind is p.VAR_KEYWORD for p in params.values())
    assert accepts, f"{name} does not accept padding"
