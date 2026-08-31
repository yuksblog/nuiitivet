"""Material Design Card widget.

The :class:`Card` widget is unified across all visual variants. The visual
variant (filled, outlined, elevated) is expressed entirely through the
``style`` argument. Use :class:`CardStyle` factory methods to obtain
variant presets: ``CardStyle.filled()``, ``CardStyle.outlined()``,
``CardStyle.elevated()``.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union

from ..widgeting.widget import ComposableWidget, Widget
from .theme.elevation import md3_elevation_to_shadow
from ..rendering.padding import PaddingLike
from ..rendering.sizing import SizingLike
from ..widgets.box import Box
from nuiitivet.material.styles.card_style import CardStyle
from ..theme.theme import Theme

ChildSpec = Union[Widget, Callable[[], Widget], None]
AlignmentLike = Union[str, Tuple[str, str]]

_logger = logging.getLogger(__name__)


class Card(ComposableWidget, Box):
    """Unified Material Design 3 card.

    The visual variant (filled, outlined, elevated) is expressed entirely
    through the ``style`` argument, which accepts any :class:`CardStyle`
    instance. Use the :class:`CardStyle` factory methods to obtain
    variant presets: ``CardStyle.filled()``, ``CardStyle.outlined()``,
    ``CardStyle.elevated()``.

    When ``style`` is not provided, the theme's filled card style is used
    as the default.
    """

    @property
    def style(self) -> CardStyle:
        """Return the style currently in effect.

        This is the explicit ``style`` when one was given, otherwise the theme's
        filled card style — pushed in by :meth:`on_mount` and kept current by the
        theme subscription. It is *not* pulled from ``Theme.of``, which cannot
        answer before the card is attached.
        """
        return self._effective_style

    def __init__(
        self,
        child: ChildSpec,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        alignment: AlignmentLike = "start",
        style: Optional[CardStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize Card.

        Args:
            child: The child widget or factory.
            width: Width specification.
            height: Height specification.
            padding: Padding around the content.
            alignment: Alignment of the content.
            style: Visual style preset. Defaults to the theme's filled card
                style. Use :meth:`CardStyle.filled`, :meth:`CardStyle.outlined`,
                or :meth:`CardStyle.elevated` for the standard M3 variants.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        self._child_spec: ChildSpec = child
        self._user_style: Optional[CardStyle] = style

        # The theme is unreachable here: the widget has no parent link until it
        # is attached, so ``Theme.of`` would return the light default and freeze
        # it forever. Start from the framework preset -- the same value
        # ``CardStyle.from_theme`` falls back to when no Material theme is
        # installed -- and re-apply the theme's style once mounted.
        initial_style = style if style is not None else CardStyle.filled()
        self._effective_style: CardStyle = initial_style
        _shadow = md3_elevation_to_shadow(initial_style.elevation)

        # Pass raw colors to Box; it will resolve them lazily via BackgroundRenderer
        super().__init__(
            child=None,
            width=width,
            height=height,
            padding=padding,
            background_color=initial_style.background,
            border_width=initial_style.border_width,
            border_color=initial_style.border_color,
            corner_radius=initial_style.border_radius,
            shadow_blur=_shadow.sigma,
            shadow_color=_shadow.color,
            shadow_offset=_shadow.offset,
            alignment=alignment,
            key=key,
        )

        self._content_scope_id: Optional[str] = None

        if isinstance(child, Widget):
            super().add_child(child)

    # --- Theme integration ----------------------------------------------------
    def _resolve_card_style(self) -> None:
        """Resolve the theme's card style and push it onto the Box properties.

        Called from :meth:`build`, which is where a widget that composes reads
        the theme. The read registers a dependency, so a theme change rebuilds
        this card and lands here again -- there is nothing to subscribe to and
        nothing to unsubscribe from. See ``docs/design/THEME_CONSUMPTION.md``.
        """
        if self._user_style is not None:
            return
        self._apply_card_style(CardStyle.from_theme(Theme.of(self)))

    def _apply_card_style(self, style: CardStyle) -> None:
        """Push ``style`` onto the underlying :class:`Box` visual properties."""
        self._effective_style = style
        shadow = md3_elevation_to_shadow(style.elevation)
        self.bgcolor = style.background
        self.border_width = style.border_width
        self.border_color = style.border_color
        self.corner_radius = style.border_radius
        self.shadow_blur = shadow.sigma
        self.shadow_color = shadow.color
        self.shadow_offset = shadow.offset

    # --- Build / scope integration (Same as MaterialContainer) ----------------
    def build(self) -> Widget:
        self._resolve_card_style()
        fragment = self._build_scoped_child()
        self._sync_child(fragment)
        return self

    def set_child(self, child: ChildSpec) -> None:
        self._child_spec = child
        self._invalidate_content_scope()

    def _build_scoped_child(self) -> Optional[Widget]:
        if self._child_spec is None:
            self._content_scope_id = None
            return None

        def factory() -> Widget:
            return self._materialize_child()

        with self.scope("content") as handle:
            fragment = self.render_scope_with_handle(handle, factory)
            self._content_scope_id = handle.id
        return fragment

    def _sync_child(self, child: Optional[Widget]) -> None:
        current = self.children_snapshot()
        existing = current[0] if current else None
        if child is None:
            if existing is not None:
                self.clear_children()
            return
        if existing is child:
            return
        self.clear_children()
        self.add_child(child)

    def _materialize_child(self) -> Widget:
        spec = self._child_spec
        if spec is None:
            from ..widgets.box import Box

            return Box(width=0, height=0)
        if isinstance(spec, Widget):
            return spec
        if callable(spec):
            return spec()
        return spec  # type: ignore

    def _invalidate_content_scope(self) -> None:
        if self._content_scope_id:
            self.invalidate_scope_id(self._content_scope_id)
