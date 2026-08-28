"""The harness builds the app, not a stripped-down cousin of it (#547).

``nv.App`` *is* ``MaterialApp``, so a screen an author writes runs under a
Material overlay, a Material theme and a Material navigator. A harness that
built the core ``App`` instead turned that screen red for a setup step the real
app never needs -- and the error named ``App(...)``, which the test never calls.
"""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.runtime.app import App
from nuiitivet.testing import AppHarness
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import ComposableWidget, Widget


SIZE = (400, 300)


class Screen(ComposableWidget):
    """A screen that reaches for the Material overlay, as an app author would."""

    def build(self) -> Widget:
        return Container(width="wt", height="wt")

    def confirm(self) -> None:
        MaterialOverlay.of(self).show(Container(width=100, height=80), backdrop=True)


def test_a_screen_reaches_the_material_overlay_with_no_setup() -> None:
    """The failure this issue is about: no ``overlay_factory`` anywhere."""
    screen = Screen()
    with AppHarness(screen, size=SIZE) as app:
        screen.confirm()
        app.settle()

        assert len(app.open_overlays) == 1


def test_the_default_app_matches_the_one_the_author_runs() -> None:
    """Overlay, theme and navigator all -- fixing one of three would still lie."""
    screen = Screen()
    with AppHarness(screen, size=SIZE) as app:
        assert isinstance(app.app, MaterialApp)
        assert isinstance(app.window.overlay, MaterialOverlay)
        assert isinstance(app.window.navigator, MaterialNavigator)
        assert Theme.of(screen).extension(MaterialThemeData) is not None


def test_app_selects_the_class_to_build() -> None:
    """``app=App`` is the same downgrade the app itself would be making."""
    with AppHarness(Screen(), size=SIZE, app=App) as app:
        assert not isinstance(app.app, MaterialApp)
        assert isinstance(app.window.overlay, Overlay)
        assert not isinstance(app.window.overlay, MaterialOverlay)


def test_app_kwargs_reach_the_selected_class() -> None:
    """``overlay_factory`` belongs to core ``App`` and still passes through."""
    with AppHarness(
        Screen(),
        size=SIZE,
        app=App,
        overlay_factory=lambda: MaterialOverlay(intents={}),
    ) as app:
        assert isinstance(app.window.overlay, MaterialOverlay)
