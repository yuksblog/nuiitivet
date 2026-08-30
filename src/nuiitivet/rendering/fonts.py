"""Font configuration, exposed as the ``Fonts`` namespace.

The ``Fonts`` class is a namespace, not something to instantiate — the same
convention as :class:`~nuiitivet.platform.desktop.Desktop` and
:class:`~nuiitivet.platform.file_dialog.FileDialog`. It scopes application-wide
font configuration, which is called a few times at startup rather than inline
in widget code.
"""

from __future__ import annotations

from typing import Optional

from nuiitivet.rendering.skia.font import register_font as _register_font
from nuiitivet.rendering.skia.font import set_default_font_family as _set_default_font_family


class Fonts:
    """Application-wide font configuration (default family, bundled fonts)."""

    @staticmethod
    def set_default_family(family_name: Optional[str]) -> None:
        """Set the application-wide default font family.

        The family is prioritized over locale-based defaults wherever no
        explicit ``font_family`` is given. Pass ``None`` to reset to automatic
        locale detection.
        """
        _set_default_font_family(family_name)

    @staticmethod
    def register(path: str, family_name: str) -> None:
        """Register a font file under a custom family name.

        Call at application startup, before any widget is rendered. Once
        registered, the family name can be used wherever a ``font_family`` is
        accepted (e.g. ``TextStyle(font_family=...)``,
        ``Icon(..., font_family=...)``). The file is loaded lazily on first
        use and cached.

        Args:
            path: Absolute or relative path to a ``.ttf`` or ``.otf`` file.
            family_name: The name to associate with this font.
        """
        _register_font(path, family_name)
