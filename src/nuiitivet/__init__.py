"""nuiitivet package.

Core functionality and configuration primitives are exposed here.
"""

# Layouts
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

# Primitives / Widgets
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget, ComposableWidget
from nuiitivet.navigation import Navigator

# State Management
from nuiitivet.observable import Observable, batch

# Configuration
from nuiitivet.rendering.skia.font import set_default_font_family, register_font
from nuiitivet.runtime.chrome import OSChrome, CustomChrome, Border

__all__: list[str] = [
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
    "OSChrome",
    "CustomChrome",
    "Border",
    "Deck",
    "Collapsible",
    "VerticalScrollable",
    "HorizontalScrollable",
    "Sizing",
    "Widget",
    "ComposableWidget",
    "Navigator",
    "Observable",
    "batch",
    "set_default_font_family",
    "register_font",
]
