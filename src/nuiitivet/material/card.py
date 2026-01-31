"""Material Design Card widgets."""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from ..widgeting.widget import ComposableWidget, Widget
from ..rendering.sizing import SizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.material.theme.color_role import ColorRole
from ..widgets.box import Box
from nuiitivet.material.styles.card_style import CardStyle

ChildSpec = Union[Widget, Callable[[], Widget], None]
PaddingLike = Union[int, Tuple[int, int], Tuple[int, int, int, int]]
AlignmentLike = Union[str, Tuple[str, str]]

_logger = logging.getLogger(__name__)


class Card(ComposableWidget, Box):
    """Base class for Material Design cards."""

    @property
    def style(self) -> CardStyle:
        if hasattr(self, "_user_style") and self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.styles.card_style import CardStyle

        variant = getattr(self, "_variant", "filled")
        return CardStyle.from_theme(manager.current, variant)

    def __init__(
        self,
        child: ChildSpec,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        alignment: AlignmentLike = "start",
        style: Optional[CardStyle] = None,
    ) -> None:
        """Initialize Card.

        Args:
            child: The child widget or factory.
            width: Width specification.
            height: Height specification.
            padding: Padding around the content.
            alignment: Alignment of the content.
            style: Optional CardStyle override.
        """
        self._child_spec: ChildSpec = child
        self._user_style = style

        if not hasattr(self, "_variant"):
            self._variant = "filled"

        # Resolve style
        final_style = self.style

        # Resolve shadow
        shadow_col, shadow_off, shadow_blur = self._resolve_shadow(final_style.elevation, final_style.shadow_color)

        # Pass raw colors to Box; it will resolve them lazily via BackgroundRenderer
        super().__init__(
            child=None,
            width=width,
            height=height,
            padding=padding,
            background_color=final_style.background,
            border_width=final_style.border_width,
            border_color=final_style.border_color,
            corner_radius=final_style.border_radius,
            shadow_blur=shadow_blur,
            shadow_color=shadow_col,
            shadow_offset=shadow_off,
            alignment=alignment,
        )

        self._content_scope_id: Optional[str] = None
        self._theme_subscription: Optional[Callable[[object], None]] = None

        if isinstance(child, Widget):
            super().add_child(child)

    @staticmethod
    def _resolve_shadow(
        elevation: float, shadow_color_spec: Optional[ColorSpec]
    ) -> Tuple[Optional[ColorSpec], Tuple[float, float], float]:
        shadow_color: Optional[ColorSpec] = None
        shadow_offset: Tuple[float, float] = (0.0, 0.0)
        shadow_blur: float = 0.0

        if elevation <= 0:
            return None, (0.0, 0.0), 0.0

        try:
            from ..rendering.elevation import Elevation

            e = Elevation.from_level(elevation)

            # Use provided shadow color or default to SHADOW role with alpha from Elevation
            if shadow_color_spec:
                shadow_color = shadow_color_spec
            else:
                shadow_color = (ColorRole.SHADOW, e.alpha)

            shadow_offset = e.offset
            shadow_blur = e.blur
        except Exception:
            exception_once(_logger, "card_resolve_shadow_exc", "Failed to resolve elevation shadow")
            shadow_color = None

        return shadow_color, shadow_offset, shadow_blur

    # --- Build / scope integration (Same as MaterialContainer) ----------------
    def build(self) -> Widget:
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


class ElevatedCard(Card):
    """Elevated Card implementation."""

    def __init__(
        self,
        child: ChildSpec,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        alignment: AlignmentLike = "start",
        style: Optional[CardStyle] = None,
    ) -> None:
        """Initialize ElevatedCard.

        Args:
            child: The child widget or factory.
            width: Width specification.
            height: Height specification.
            padding: Padding around the content.
            alignment: Alignment of the content.
            style: Optional CardStyle override.
        """
        self._variant = "elevated"
        super().__init__(
            child=child,
            width=width,
            height=height,
            padding=padding,
            alignment=alignment,
            style=style,
        )


class FilledCard(Card):
    """Filled Card implementation."""

    def __init__(
        self,
        child: ChildSpec,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        alignment: AlignmentLike = "start",
        style: Optional[CardStyle] = None,
    ) -> None:
        """Initialize FilledCard.

        Args:
            child: The child widget or factory.
            width: Width specification.
            height: Height specification.
            padding: Padding around the content.
            alignment: Alignment of the content.
            style: Optional CardStyle override.
        """
        self._variant = "filled"
        super().__init__(
            child=child,
            width=width,
            height=height,
            padding=padding,
            alignment=alignment,
            style=style,
        )


class OutlinedCard(Card):
    """Outlined Card implementation."""

    def __init__(
        self,
        child: ChildSpec,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        alignment: AlignmentLike = "start",
        style: Optional[CardStyle] = None,
    ) -> None:
        """Initialize OutlinedCard.

        Args:
            child: The child widget or factory.
            width: Width specification.
            height: Height specification.
            padding: Padding around the content.
            alignment: Alignment of the content.
            style: Optional CardStyle override.
        """
        self._variant = "outlined"
        super().__init__(
            child=child,
            width=width,
            height=height,
            padding=padding,
            alignment=alignment,
            style=style,
        )
