"""Every public widget accepts ``key`` in its constructor.

``key`` is a widget's stable, layout-independent identity — the dev bridge
targets widgets by it (``click(key=...)``) and hot reload anchors observable
snapshots to it. It replaced the ``keyed()`` modifier, so it must be reachable
from every public widget's constructor: this test walks the public surface
(``nuiitivet.material.__all__``, the only import policy apps may use) and
requires an explicit ``key`` parameter on each concrete widget class.

An explicit parameter is required — a bare ``**kwargs`` passthrough would pass a
signature check without proving the value reaches ``Widget.__init__``. Only
abstract composition bases whose ``__init__`` is a pure ``*args``/``**kwargs``
relay are allow-listed.
"""
from __future__ import annotations

import inspect

import nuiitivet.material as md
from nuiitivet.widgeting.widget import Widget

# Pure *args/**kwargs relays: subclasses define their own __init__ and pass
# key= through; there is no explicit parameter to require here.
_PASSTHROUGH_BASES = frozenset({"ComposableWidget"})


def _public_widget_classes() -> list[tuple[str, type]]:
    classes: list[tuple[str, type]] = []
    for name in sorted(md.__all__):
        obj = getattr(md, name)
        if inspect.isclass(obj) and issubclass(obj, Widget):
            classes.append((name, obj))
    assert classes, "public surface enumeration returned no widget classes"
    return classes


def test_every_public_widget_accepts_key() -> None:
    missing: list[str] = []
    for name, cls in _public_widget_classes():
        if name in _PASSTHROUGH_BASES:
            continue
        params = inspect.signature(cls).parameters
        if "key" not in params:
            missing.append(name)
    assert missing == [], (
        "Public widgets missing an explicit `key` constructor parameter "
        ": " + ", ".join(missing)
    )


def test_key_is_keyword_only_with_none_default() -> None:
    offenders: list[str] = []
    for name, cls in _public_widget_classes():
        params = inspect.signature(cls).parameters
        param = params.get("key")
        if param is None:
            continue  # absence is test_every_public_widget_accepts_key's job
        if param.kind is not inspect.Parameter.KEYWORD_ONLY or param.default is not None:
            offenders.append(name)
    assert offenders == [], (
        "`key` must be keyword-only with a None default: " + ", ".join(offenders)
    )


def test_key_reaches_widget_attribute() -> None:
    """The parameter is not just cosmetic: it must land on ``widget.key``.

    Instantiating all public widgets generically is impractical, so this spot
    checks the three constructor chains the parameter threads through:
    a direct ``Widget`` subclass chain (Text), the ``Clickable``/``Box``
    ``**kwargs`` relay (Button), and an item type that previously could not be
    keyed at all because ``modifier()`` broke its static type (RailItem).
    """
    from nuiitivet.material.buttons import Button
    from nuiitivet.material.navigation_rail import RailItem
    from nuiitivet.material.text import Text

    assert Text("t", key="text-key").key == "text-key"
    assert Button("b", key="button-key").key == "button-key"
    assert RailItem("home", "Home", key="rail-key").key == "rail-key"


def test_key_stays_targetable_under_a_wrapping_modifier(nuiitivet_app) -> None:
    """A wrapped widget keeps its key-targetability.

    Under the old ``keyed()`` modifier the convention was "apply keyed last so
    the key lands on the outermost node". With the constructor parameter the
    key stays on the *inner* widget while a wrapping modifier adds a node above
    it — this pins down that the harness (and the dev bridge, which shares the
    resolver) still finds and drives the widget by key through the wrapper.
    """
    from nuiitivet.layout.column import Column
    from nuiitivet.material.buttons import Button
    from nuiitivet.modifiers.background import background

    clicks: list[int] = []

    def screen():
        return Column(
            children=[
                Button("go", on_click=lambda: clicks.append(1), key="go").modifier(
                    background((240, 240, 240, 255))
                ),
            ]
        )

    app = nuiitivet_app(screen, size=(800, 600))
    node = app.get(key="go")
    assert node.rect is not None
    app.click(key="go")
    assert clicks == [1]
