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
from nuiitivet.menubar import (
    MenuBar,
    MenuBarArea,
    MenuBarStyle,
    MenuBarThemeData,
)
from nuiitivet.menus import MenuEntry, MenuRole

# Primitives / Widgets
from nuiitivet.rendering.sizing import Sizing, SizingKind, SizingLike
from nuiitivet.widgeting.widget import Widget, ComposableWidget
from nuiitivet.widgets.box import Box

# Input filters (rules applied to text as the user types it)
from nuiitivet.widgets.input_filter import (
    InputFilter,
    InputFilterLike,
    allow,
    deny,
    digits_only,
    matching,
    max_length,
)

# Geometry (container-scoped measured size)
from nuiitivet.layout.geometry import Geometry
from nuiitivet.rendering.size import Size

# Navigation
from nuiitivet.navigation import Navigator, NavigatorProtocol, Route, Transitions

# Overlay
from nuiitivet.overlay import OverlayAware, OverlayProtocol

# State Management
from nuiitivet.observable import (
    CancelToken,
    Clock,
    ClockCallback,
    Observable,
    batch,
    combine,
)
from nuiitivet.observable.clocks import Clocks

# Input (keyboard-modifier masks for ``on_key`` / ``on_key_up`` handlers and
# backend-neutral pointer button codes for ``PointerEvent.button``)
from nuiitivet.input.codes import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
    MOD_ACCEL,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
)
from nuiitivet.input.events import FileDropEvent
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.input.shortcut import Shortcut, ShortcutBinding, ShortcutScope

# Second argument of every ``on_focus_change`` callback -- ``focusable()`` and
# the text inputs alike -- so it belongs to the public surface with them.
from nuiitivet.widgets.interaction import FocusSource

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
    absorb_pointer,
    background,
    block_focus_traversal,
    block_pointer,
    border,
    clickable,
    clip,
    context_menu,
    corner_radius,
    defer_pointer,
    drop_target,
    focusable,
    hoverable,
    key_shortcut,
    keyed,
    popup,
    on_mount,
    on_size_changed,
    on_unmount,
    opacity,
    passthrough_pointer,
    pointer_input,
    rotate,
    scale,
    shadow,
    stick,
    tooltip,
    translate,
    visible,
    will_pop,
)

# Platform services
from nuiitivet.platform.desktop import Desktop
from nuiitivet.platform.file_dialog import FileDialog, FileDialogError
from nuiitivet.platform.tray import TrayIcon

# Window / runtime
from nuiitivet.runtime.app import AppScope, ExitPolicy
from nuiitivet.runtime.chrome import OSChrome, CustomChrome, Border
from nuiitivet.runtime.window import Window, WindowScope
from nuiitivet.runtime.window_intents import (
    CloseWindowIntent,
    HideWindowIntent,
    MinimizeWindowIntent,
    ShowWindowIntent,
)

# Configuration
from nuiitivet.rendering.fonts import Fonts
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
    "MenuBar",
    "MenuBarArea",
    "MenuEntry",
    "MenuRole",
    "MenuBarStyle",
    "MenuBarThemeData",
    "ForEach",
    # Primitives / Widgets
    "Sizing",
    "SizingKind",
    "SizingLike",
    "Widget",
    "ComposableWidget",
    "Box",
    # Input filters
    "InputFilter",
    "InputFilterLike",
    "allow",
    "deny",
    "digits_only",
    "matching",
    "max_length",
    # Geometry
    "Geometry",
    "Size",
    # Navigation
    "Navigator",
    "NavigatorProtocol",
    "Route",
    "Transitions",
    # Overlay
    "OverlayAware",
    "OverlayProtocol",
    # State Management
    "Observable",
    "CancelToken",
    "batch",
    "combine",
    "Clock",
    "ClockCallback",
    "Clocks",
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
    "absorb_pointer",
    "background",
    "block_focus_traversal",
    "block_pointer",
    "border",
    "clickable",
    "clip",
    "context_menu",
    "corner_radius",
    "defer_pointer",
    "drop_target",
    "focusable",
    "hoverable",
    "key_shortcut",
    "keyed",
    "popup",
    "on_mount",
    "on_size_changed",
    "on_unmount",
    "opacity",
    "passthrough_pointer",
    "pointer_input",
    "rotate",
    "scale",
    "shadow",
    "stick",
    "tooltip",
    "translate",
    "visible",
    "will_pop",
    # Input
    "MOD_SHIFT",
    "MOD_CTRL",
    "MOD_ALT",
    "MOD_META",
    "MOD_ACCEL",
    "BUTTON_LEFT",
    "BUTTON_MIDDLE",
    "BUTTON_RIGHT",
    "FileDropEvent",
    "FocusSource",
    "PointerEvent",
    "PointerEventType",
    "Shortcut",
    "ShortcutBinding",
    "ShortcutScope",
    # Platform services
    "Desktop",
    "FileDialog",
    "FileDialogError",
    "TrayIcon",
    # Window / runtime
    "AppScope",
    "ExitPolicy",
    "Window",
    "WindowScope",
    "OSChrome",
    "CustomChrome",
    "Border",
    "CloseWindowIntent",
    "HideWindowIntent",
    "MinimizeWindowIntent",
    "ShowWindowIntent",
    # Configuration
    "Fonts",
    "RendererMode",
]
