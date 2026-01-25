"""Material Symbols icon widget with generated symbol constants."""

from __future__ import annotations

from typing import Any, Optional, Tuple, TYPE_CHECKING
import logging
import os

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgets.icon import IconBase
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.skia import (
    get_typeface,
    make_font,
    make_text_blob,
    typeface_from_bytes,
    typeface_from_file,
)
from nuiitivet.rendering.sizing import SizingLike, parse_sizing
from nuiitivet.material.symbols import Symbol, Symbols
from nuiitivet.observable import ReadOnlyObservableProtocol

if TYPE_CHECKING:
    from nuiitivet.material.styles.icon_style import IconStyle

DEFAULT_ICON_PX = 24


logger = logging.getLogger(__name__)


def _pixel_size_from_sizing(size: SizingLike) -> int:
    """Resolve the pixel size used for painting an icon."""

    try:
        parsed = parse_sizing(size, default=None)
    except Exception:
        exception_once(logger, "icon_parse_sizing_exc", "parse_sizing failed for icon size")
        return DEFAULT_ICON_PX

    if parsed.kind == "fixed":
        return max(1, int(parsed.value))

    # For flex/auto sizing, icon cannot resolve without parent context.
    # Fall back to default size.
    if parsed.kind in ("flex", "auto"):
        return DEFAULT_ICON_PX

    # If parsed is None or unknown kind, try numeric coercion as last resort.
    try:
        return max(1, int(size))  # type: ignore[arg-type]
    except Exception:
        exception_once(logger, "icon_int_size_exc", "Failed to coerce icon size to int")
        return DEFAULT_ICON_PX


class Icon(IconBase):
    """Material Symbols icon widget (M3準拠).

    Parameters:
    - name: Ligature name (e.g. "home", "menu") or Symbol
    - size: Icon visual size in pixels (default 24dp)
    - padding: Space around icon (M3: "space between UI elements")
    - style: IconStyle for customization (defaults to theme style)
    """

    def __init__(
        self,
        name: Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str],
        size: SizingLike = 24,
        padding: Optional[Tuple[int, int, int, int] | Tuple[int, int] | int] = None,
        style: Optional["IconStyle"] = None,
    ):
        """Create a Material-like icon by ligature name.

        Args:
            name: Ligature name such as "home", "menu", "search", a Symbol,
                  or an Observable that yields either.
            size: Logical pixel size of the icon (font size used for the glyph).
            padding: Space around the icon (M3: "space between UI elements").
            style: IconStyle for customization (defaults to theme style).
        """
        # Store style (use provided or get from theme lazily)
        self._style = style

        # Resolve padding
        final_padding = padding
        if final_padding is None:
            if style is not None:
                final_padding = style.padding
            else:
                final_padding = 0

        # Treat `size` as a SizingLike and use it for layout via the
        # base Widget's width/height. Also compute a pixel fallback stored
        # in self._size for paint-time operations.
        super().__init__(size=size, padding=final_padding)

        self._user_padding = padding

        self._name_source: Any = name
        self._symbol: Optional["Symbol"] = None
        self._symbol_codepoint: Optional[str] = None

        resolved_name: Symbol | str
        if hasattr(name, "value"):
            try:
                resolved_name = name.value  # type: ignore[assignment]
            except Exception:
                exception_once(logger, "icon_name_value_exc", "Failed to read icon name.value")
                resolved_name = str(name)
        else:
            resolved_name = name  # type: ignore[assignment]

        self._apply_name(resolved_name)

        self._size = _pixel_size_from_sizing(size)

        # Optional font_file path or filename (relative to package symbols/)
        self.font_file: Optional[str] = None
        self._font_file_candidates: Tuple[str, ...] = ("MaterialIcons-Regular.ttf",)
        # Cache typeface to avoid repeated _load_typeface calls on every paint
        self._cached_typeface: Optional[object] = None

    _paint_dependencies: Tuple[str, ...] = ("name",)

    def _apply_name(self, value: Symbol | str) -> None:
        """Apply a new name value and update derived symbol state."""

        self._symbol = None
        self._symbol_codepoint = None

        if isinstance(value, Symbol):
            self._symbol = value
            self.name = value.ligature()
            glyph = value.glyph()
            self._symbol_codepoint = glyph if glyph else None
            return

        self.name = str(value)
        resolved = Symbols.from_name(self.name)
        if resolved is not None:
            self._symbol = resolved
            self._symbol_codepoint = resolved.glyph()

    @property
    def family(self) -> str:
        """Return the style-driven icon family.

        The family is sourced from `IconStyle.family` (explicit `style=` or
        theme-resolved style). If style resolution fails, this falls back to
        "outlined".
        """

        try:
            return str(self.style.family)
        except Exception:
            return "outlined"

    @classmethod
    def file(
        cls,
        name: Symbol | str,
        file: str,
        size: SizingLike = 24,
        padding: Optional[Tuple[int, int, int, int] | Tuple[int, int] | int] = None,
        style: Optional["IconStyle"] = None,
    ) -> "Icon":
        """Create an icon using a specific font file.

        Args:
            name: Ligature name or Symbol.
            file: Path to the font file.
            size: Icon size.
            padding: Padding around the icon.
            style: IconStyle for customization.
        """
        icon = cls(name, size=size, padding=padding, style=style)
        icon.font_file = file
        return icon

    def on_mount(self) -> None:
        super().on_mount()

        # Subscribe to Observable name sources.
        src = self._name_source
        if hasattr(src, "subscribe"):
            try:
                self.bind_to(src, self._apply_name, dependency="name")
            except Exception:
                exception_once(logger, "icon_name_bind_exc", "Failed to bind icon name observable")

        # If padding was not provided by user, update it from theme style
        if self._user_padding is None and self._style is None:
            try:
                style = self.style  # This resolves from theme
                if style.padding != 0:
                    self.padding = style.padding
                    self.invalidate()
            except Exception:
                pass

    @property
    def style(self):
        if self._style is not None:
            return self._style
        from nuiitivet.theme.manager import manager
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme = manager.current.extension(MaterialThemeData)
        if theme is None:
            raise ValueError("MaterialThemeData not found in current theme")
        return theme.icon_style

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
        """Return preferred size including padding (M3準拠)."""
        # Respect explicit Sizing overrides when provided on the widget.
        # Icons are square by default (size x size) when no fixed Sizing
        # is provided.
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = self._size

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = self._size

        # Add padding (M3: space between UI elements)
        l, t, r, b = self.padding
        total_w = int(width) + int(l) + int(r)
        total_h = int(height) + int(t) + int(b)

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    @staticmethod
    def _font_directories() -> Tuple[str, ...]:
        """Return candidate font directories in priority order."""
        base_dir = os.path.dirname(__file__)
        symbols_dir = os.path.abspath(os.path.join(base_dir, "symbols"))
        return (symbols_dir,)

    @classmethod
    def _existing_font_directories(cls) -> Tuple[str, ...]:
        dirs = tuple(path for path in cls._font_directories() if os.path.isdir(path))
        return dirs if dirs else cls._font_directories()

    @classmethod
    def _first_available_font_file(cls, filename: str) -> Optional[str]:
        for directory in cls._existing_font_directories():
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path
        return None

    def _candidate_families(self):
        # Use style to get font family priority, fallback to legacy behavior
        family_lower = (self.family or "").lower()

        # Get family from style based on the resolved family
        try:
            primary_family = self.style.get_font_family(family_lower)
            if primary_family:
                primary = [primary_family]
            else:
                # Fallback to default based on family
                if family_lower == "rounded":
                    primary = ["Material Symbols Rounded"]
                elif family_lower == "sharp":
                    primary = ["Material Symbols Sharp"]
                elif family_lower == "icons":
                    primary = ["Material Icons"]
                else:
                    primary = ["Material Symbols Outlined"]
        except Exception:
            # Fallback to legacy behavior if style access fails
            if family_lower == "rounded":
                primary = ["Material Symbols Rounded"]
            elif family_lower == "sharp":
                primary = ["Material Symbols Sharp"]
            elif family_lower == "icons":
                primary = ["Material Icons"]
            else:
                primary = ["Material Symbols Outlined"]

        # Use style's font_family_priority for fallbacks
        try:
            fallbacks = list(self.style.font_family_priority)
        except Exception:
            fallbacks = [
                "Material Symbols Outlined",
                "Material Symbols Rounded",
                "Material Symbols Sharp",
                "Material Icons",
            ]

        # Preserve order, unique
        seen = set()
        out = []
        for fam in [*primary, *fallbacks]:
            if fam not in seen:
                out.append(fam)
                seen.add(fam)
        return out

    def _load_typeface(self):
        # Use shared get_typeface helper which handles file candidates,
        # family matching and caching. This keeps the complex try/except
        # logic centralized in the rendering layer.
        font_dirs = list(self._existing_font_directories())
        pkg_font_dir = font_dirs[0] if font_dirs else None

        # Attempt resource-based loading from package `nuiitivet.material.symbols`
        try:
            import importlib.resources as resources

            try:
                symbols_root = resources.files("nuiitivet.material").joinpath("symbols")
            except Exception:
                exception_once(logger, "icon_resources_symbols_root_exc", "Failed to locate symbols resources root")
                symbols_root = None
        except Exception:
            exception_once(logger, "icon_importlib_resources_exc", "Failed to import importlib.resources")
            resources = None
            symbols_root = None

        # Helper to try loading font bytes via importlib.resources and create a
        # Typeface from them.
        def _try_load_from_resources(filename: str):
            if symbols_root is None:
                return None
            try:
                blob_path = symbols_root.joinpath(filename)
                # read_bytes works both for filesystem and zip packages
                data_bytes = blob_path.read_bytes()
            except Exception:
                exception_once(
                    logger,
                    "icon_resources_read_bytes_exc",
                    "Failed to read icon font bytes from package resources (file=%s)",
                    filename,
                )
                return None
            try:
                return typeface_from_bytes(data_bytes)
            except Exception:
                exception_once(
                    logger,
                    "icon_typeface_from_bytes_exc",
                    "typeface_from_bytes failed for packaged font (file=%s)",
                    filename,
                )
                return None

        # Build file candidates similar to previous implementation
        symbol_style_map = {
            "outlined": ["MaterialSymbolsOutlined[FILL,GRAD,opsz,wght].ttf"],
            "rounded": ["MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf"],
            "sharp": ["MaterialSymbolsSharp[FILL,GRAD,opsz,wght].ttf"],
        }
        legacy_style_map = {
            "outlined": ["MaterialIconsOutlined-Regular.otf"],
            "rounded": ["MaterialIconsRound-Regular.otf"],
            "sharp": ["MaterialIconsSharp-Regular.otf"],
            "twotone": ["MaterialIconsTwoTone-Regular.otf"],
            "two-tone": ["MaterialIconsTwoTone-Regular.otf"],
            "icons": ["MaterialIcons-Regular.ttf"],
        }

        def dedupe(seq):
            seen: set[str] = set()
            for item in seq:
                if item and item not in seen:
                    seen.add(item)
                    yield item

        candidates: list[str] = []

        def add_candidate(path: str) -> None:
            norm = os.path.abspath(path)
            if norm not in candidates:
                candidates.append(norm)

        raw_family = (self.family or "").lower()
        normalized_family = raw_family
        if normalized_family in {"two-tone", "twotone"}:
            normalized_family = "outlined"

        symbol_files = symbol_style_map.get(normalized_family) or symbol_style_map["outlined"]
        legacy_files = legacy_style_map.get(raw_family, [])
        combined_files = list(dedupe([*symbol_files, *legacy_files, "MaterialIcons-Regular.ttf"]))
        self._font_file_candidates = tuple(combined_files)

        logger.debug("Icon font candidates=%s dirs=%s family=%s", combined_files, font_dirs, self.family)

        for fn in combined_files:
            for font_dir in font_dirs:
                add_candidate(os.path.join(font_dir, fn))

        # Always include any discovered legacy/common fallback (already covered by combined_files)

        # If caller specified a font_file, try it first (absolute or relative)
        if self.font_file:
            if os.path.isabs(self.font_file):
                add_candidate(self.font_file)
            else:
                for font_dir in font_dirs:
                    add_candidate(os.path.join(font_dir, self.font_file))

        # Add any other ttf/otf in the directory as fallbacks
        for font_dir in font_dirs:
            try:
                for fn in os.listdir(font_dir):
                    if fn.lower().endswith((".ttf", ".otf")):
                        add_candidate(os.path.join(font_dir, fn))
            except Exception:
                exception_once(logger, "icon_listdir_fonts_exc", "os.listdir failed while scanning fonts")
                continue

        # If packaged symbols are available, try loading them by resource
        # name before attempting filesystem lookups. This covers the case
        # where fonts are bundled inside the package (wheel/zip).
        if symbols_root is not None:
            # Try explicit font_file first
            if self.font_file:
                fname = os.path.basename(self.font_file)
                tf = _try_load_from_resources(fname)
                if tf is not None:
                    return tf

            # Try style-specific files
            for fn in combined_files:
                tf = _try_load_from_resources(fn)
                if tf is not None:
                    return tf

            # Try default legacy filename
            tf = _try_load_from_resources("MaterialIcons-Regular.ttf")
            if tf is not None:
                return tf

        # Family candidates from _candidate_families()
        family_candidates = tuple(self._candidate_families())

        # Use get_typeface: it returns a Typeface or None
        try:
            tf = get_typeface(
                candidate_files=tuple(candidates),
                family_candidates=family_candidates,
                pkg_font_dir=pkg_font_dir,
                fallback_to_default=True,
            )
            if tf is None:
                logger.debug("Icon get_typeface returned None (candidates=%s)", candidates)
            return tf
        except Exception as exc:
            logger.exception("Icon get_typeface raised", exc_info=exc)
            return None

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Paint icon with padding support (M3準拠)."""
        # Apply padding to get content area (M3: space between UI elements)
        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        # Determine size to draw (contain behavior).
        # Use the smaller dimension of the content area to maintain aspect ratio.
        draw_size = min(cw, ch)
        if draw_size <= 0:
            return

        # Use cached typeface if available, otherwise load and cache it
        tf = self._cached_typeface
        if tf is None:
            tf = self._load_typeface()
            self._cached_typeface = tf
        # Prefer the resolved typeface. If none was found, try to load a
        # packaged legacy MaterialIcons font before falling back to a
        # Font constructed without an explicit typeface.
        font = None
        if tf is not None:
            try:
                font = make_font(tf, draw_size)
            except Exception:
                exception_once(logger, "icon_make_font_exc", "make_font failed for resolved typeface")
                font = None

        if font is None:
            try:
                legacy_tf = None
                fallback_names = getattr(self, "_font_file_candidates", ("MaterialIcons-Regular.ttf",))
                for fallback_name in fallback_names:
                    legacy_fp = self._first_available_font_file(fallback_name)
                    if legacy_fp and os.path.isfile(legacy_fp):
                        try:
                            legacy_tf = typeface_from_file(legacy_fp)
                        except Exception:
                            exception_once(
                                logger,
                                "icon_typeface_from_file_primary_exc",
                                "typeface_from_file failed (file=%s)",
                                os.path.basename(legacy_fp),
                            )
                            legacy_tf = None
                    if legacy_tf is not None:
                        break
                if legacy_tf is not None:
                    font = make_font(legacy_tf, draw_size)
                else:
                    font = make_font(None, draw_size)
            except Exception:
                try:
                    font = make_font(None, draw_size)
                except Exception:
                    exception_once(logger, "icon_make_font_fallback_exc", "make_font(None) failed")
                    return

        # Use ligature name as text; Material fonts may convert to glyphs.
        try:
            blob = make_text_blob(self.name, font)
        except Exception:
            exception_once(logger, "icon_make_text_blob_exc", "make_text_blob failed for icon ligature")
            blob = None

        # If we have a mapping for this name, prefer rendering the mapped
        # PUA codepoint with the packaged legacy MaterialIcons font when
        # possible. This is a pragmatic default that makes common icons
        # reliably visible across different Material font variants.
        cp = self._symbol_codepoint
        if cp:
            try:
                # Try current typeface first
                try:
                    cp_blob = make_text_blob(cp, font)
                except Exception:
                    exception_once(logger, "icon_make_text_blob_codepoint_exc", "make_text_blob failed for codepoint")
                    cp_blob = None

                def blob_has_height(b):
                    try:
                        return b is not None and b.bounds().height() > 0.5
                    except Exception:
                        exception_once(logger, "icon_blob_bounds_exc", "Failed to read text blob bounds")
                        return False

                if blob_has_height(cp_blob):
                    blob = cp_blob
                else:
                    # Try packaged legacy font
                    try:
                        fallback_names = getattr(self, "_font_file_candidates", ("MaterialIcons-Regular.ttf",))
                        legacy_tf = None
                        for fallback_name in fallback_names:
                            legacy_fp = self._first_available_font_file(fallback_name)
                            if legacy_fp and os.path.isfile(legacy_fp):
                                try:
                                    legacy_tf = typeface_from_file(legacy_fp)
                                except Exception:
                                    exception_once(
                                        logger,
                                        "icon_typeface_from_file_exc",
                                        "typeface_from_file failed",
                                    )
                                    legacy_tf = None
                            if legacy_tf is not None:
                                break
                        if legacy_tf is not None:
                            legacy_font = make_font(legacy_tf, draw_size)
                            try:
                                legacy_blob = make_text_blob(cp, legacy_font)
                                if blob_has_height(legacy_blob):
                                    blob = legacy_blob
                            except Exception:
                                exception_once(
                                    logger,
                                    "icon_make_text_blob_legacy_exc",
                                    "make_text_blob failed for legacy font",
                                )
                    except Exception:
                        exception_once(
                            logger,
                            "icon_legacy_font_fallback_exc",
                            "Icon legacy font fallback failed",
                        )
            except Exception:
                # if still no blob, leave as-is (no-op)
                exception_once(logger, "icon_paint_codepoint_exc", "Icon paint failed")
        if blob is None:
            return

        # Use IconBase to draw the blob
        from nuiitivet.theme.manager import manager

        color = self.style.color
        resolved_color = resolve_color_to_rgba(color, theme=manager.current)
        self.draw_blob(canvas, blob, resolved_color, x, y, width, height)
