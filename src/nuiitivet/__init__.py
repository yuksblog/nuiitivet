"""nuiitivet package.

Core functionality and configuration primitives are exposed here.
"""

# Layouts
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.spacer import Spacer
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.deck import Deck

# Primitives / Widgets
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget, ComposableWidget
from nuiitivet.navigation import Navigator, PageRoute

# State Management
from nuiitivet.observable import Observable, batch

# Configuration
from nuiitivet.rendering.skia.font import set_default_font_family
from nuiitivet.runtime.title_bar import DefaultTitleBar, CustomTitleBar

__all__: list[str] = [
    "Column",
    "Row",
    "Stack",
    "Container",
    "Flow",
    "Grid",
    "GridItem",
    "Spacer",
    "CrossAligned",
    "DefaultTitleBar",
    "CustomTitleBar",
    "Deck",
    "Sizing",
    "Widget",
    "ComposableWidget",
    "Navigator",
    "PageRoute",
    "Observable",
    "batch",
    "set_default_font_family",
]
