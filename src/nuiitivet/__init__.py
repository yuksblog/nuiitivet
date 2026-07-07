"""nuiitivet core package.

This module is the single source of truth for all public *core* symbols
(layout, widgets, state management, theming, animation, modifiers, ...).

Applications should not import from this package directly. Instead they pick a
UI design system root — currently only :mod:`nuiitivet.material` — which
re-exports everything here plus its own widgets::

    import nuiitivet.material as nv

    nv.Column(...)   # core symbol, re-exported here
    nv.Button(...)   # material symbol

See the "Imports" section of ``docs/guide/index.md`` for the import policy.
Reaching into the internal modules below (``nuiitivet.layout.column``,
``nuiitivet.widgeting.widget``, ...) is unsupported and may break without notice.
"""

# Layout
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.spacer import Spacer
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.scrollable import VerticalScrollable, HorizontalScrollable
from nuiitivet.layout.for_each import ForEach
from nuiitivet.scrolling import ScrollbarBehavior

# Primitives / Widgets
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget, ComposableWidget
from nuiitivet.widgets.box import Box

# Navigation
from nuiitivet.navigation import Navigator, Route, Transitions

# Overlay
from nuiitivet.overlay import OverlayAware

# State Management
from nuiitivet.observable import Observable, batch, combine, clock

# Theme
from nuiitivet.theme.theme import Theme
from nuiitivet.theme.type_scale import TypeScale, TypeScaleToken
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.types import ThemeExtension
from nuiitivet.theme.intents import ThemeModeIntent, ThemeRegistryIntent

# Animation
from nuiitivet.animation import (
    Animatable,
    Motion,
    LinearMotion,
    BezierMotion,
    SpringMotion,
)
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import (
    FadePattern,
    SlidePattern,
    ScalePattern,
    FractionalSlidePattern,
)

# Modifiers (exposed flat: ``nv.background(...)``, ``nv.corner_radius(...)``, ...)
from nuiitivet.modifiers import (
    background,
    border,
    clickable,
    clip,
    corner_radius,
    focusable,
    hoverable,
    ignore_pointer,
    light_dismiss,
    modeless,
    opacity,
    rotate,
    scale,
    shadow,
    stick,
    tooltip,
    translate,
    visible,
    will_pop,
)

# Window / runtime
from nuiitivet.runtime.app import AppScope
from nuiitivet.runtime.chrome import OSChrome, CustomChrome, Border
from nuiitivet.runtime.intents import CloseWindowIntent, MinimizeWindowIntent

# Configuration
from nuiitivet.rendering.skia.font import set_default_font_family, register_font
from nuiitivet.runtime.renderer import RendererMode

__all__: list[str] = [
    # Layout
    "Column",
    "Row",
    "Stack",
    "Container",
    "Flow",
    "UniformFlow",
    "Grid",
    "GridItem",
    "Spacer",
    "CrossAligned",
    "Deck",
    "Collapsible",
    "VerticalScrollable",
    "HorizontalScrollable",
    "ScrollbarBehavior",
    "ForEach",
    # Primitives / Widgets
    "Sizing",
    "Widget",
    "ComposableWidget",
    "Box",
    # Navigation
    "Navigator",
    "Route",
    "Transitions",
    # Overlay
    "OverlayAware",
    # State Management
    "Observable",
    "batch",
    "combine",
    "clock",
    # Theme
    "Theme",
    "TypeScale",
    "TypeScaleToken",
    "ThemeManager",
    "ThemeExtension",
    "ThemeModeIntent",
    "ThemeRegistryIntent",
    # Animation
    "Animatable",
    "Motion",
    "LinearMotion",
    "BezierMotion",
    "SpringMotion",
    "TransitionDefinition",
    "FadePattern",
    "SlidePattern",
    "ScalePattern",
    "FractionalSlidePattern",
    # Modifiers
    "background",
    "border",
    "clickable",
    "clip",
    "corner_radius",
    "focusable",
    "hoverable",
    "ignore_pointer",
    "light_dismiss",
    "modeless",
    "opacity",
    "rotate",
    "scale",
    "shadow",
    "stick",
    "tooltip",
    "translate",
    "visible",
    "will_pop",
    # Window / runtime
    "AppScope",
    "OSChrome",
    "CustomChrome",
    "Border",
    "CloseWindowIntent",
    "MinimizeWindowIntent",
    # Configuration
    "set_default_font_family",
    "register_font",
    "RendererMode",
]
