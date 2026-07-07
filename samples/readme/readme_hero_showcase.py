"""Hero showcase sample for README  E"Pulse" music app.

Visual goals (intended for a hero GIF):
    * MD3 Expressive look powered by ``MaterialThemeFactory.from_seed``
    * Persistent ``NavigationRail`` on the left that auto-cycles through
      sections to demonstrate ``Deck``-based navigation
    * Eye-catching "Now Playing" hero card with a continuously rotating
      and gently pulsing album-art tile (driven by reactive observables)
    * Filter chips, content cards and a FAB for typical app density

Usage:
uv run python -m samples.readme.readme_hero_showcase
uv run python -m samples.readme.readme_hero_showcase --no-autoplay
uv run python -m samples.readme.readme_hero_showcase --dark
uv run python -m samples.readme.readme_hero_showcase --seed "#FF5470"
uv run python -m samples.readme.readme_hero_showcase --png hero.png

The sample intentionally favours visual impact over feature breadth.
"""

from __future__ import annotations

import argparse
from enum import IntEnum
from typing import List

import nuiitivet.material as nv

# ---------------------------- Typography presets -------------------------
# Type-scale tokens supply typography (size). Colour lives on TextStyle.
# Sizes loosely follow Material 3 type scale roles.

DISPLAY = nv.TypeScaleToken.from_size(36)
HEADLINE = nv.TypeScaleToken.from_size(24)
TITLE_LG = nv.TypeScaleToken.from_size(20)
TITLE_MD = nv.TypeScaleToken.from_size(16)
LABEL = nv.TypeScaleToken.from_size(12)
BODY_LG = nv.TypeScaleToken.from_size(16)
BODY_MD = nv.TypeScaleToken.from_size(14)
BODY_SM = nv.TypeScaleToken.from_size(12)
TITLE_BAR_APP_SCALE = nv.TypeScaleToken.from_size(14)
TITLE_BAR_APP = nv.TextStyle(color=nv.ColorRole.ON_PRIMARY_CONTAINER)


# ------------------------------ Title bar --------------------------------


class PulseTitleBar(nv.ComposableWidget):
    """Custom Material-styled title bar for the Pulse showcase window."""

    def build(self) -> nv.Widget:
        branding = nv.Row(
            [
                nv.Icon(
                    "music_note",
                    size=16,
                    style=nv.IconStyle(color=nv.ColorRole.ON_PRIMARY_CONTAINER),
                ),
                nv.Text("Pulse", style=TITLE_BAR_APP, type_scale=TITLE_BAR_APP_SCALE),
            ],
            gap=6,
            cross_alignment="center",
        )

        controls = nv.Row(
            [
                nv.IconButton(
                    "remove",
                    style=nv.IconButtonStyle.standard("s"),
                    on_click=lambda: nv.App.of(self).dispatch(nv.MinimizeWindowIntent()),
                ),
                nv.IconButton(
                    "close",
                    style=nv.IconButtonStyle.standard("s"),
                    on_click=lambda: nv.App.of(self).dispatch(nv.CloseWindowIntent()),
                ),
            ],
            gap=2,
            cross_alignment="center",
        )

        return nv.Row(
            [branding, controls],
            main_alignment="space-between",
            cross_alignment="center",
            padding=(16, 0, 8, 0),
            width=nv.Sizing.flex(1),
            height=44,
        ).modifier(nv.background(nv.ColorRole.PRIMARY_CONTAINER))


# ----------------------------- Section model -----------------------------


class Section(IntEnum):
    HOME = 0
    DISCOVER = 1
    LIBRARY = 2
    SETTINGS = 3


SECTION_TITLES = {
    Section.HOME: "Now Playing",
    Section.DISCOVER: "Discover",
    Section.LIBRARY: "Your Library",
    Section.SETTINGS: "Settings",
}

SECTION_SUBTITLES = {
    Section.HOME: "Curated for your evening",
    Section.DISCOVER: "Fresh sounds, just dropped",
    Section.LIBRARY: "Albums, mixes & favorites",
    Section.SETTINGS: "Tune your experience",
}


# ----------------------------- Tiny helpers ------------------------------

# Each base color is paired with a complementary accent.  We fake a
# gradient by stacking a translucent oversized circle of the accent on
# top of the base color, then clipping the whole thing to a rounded rect.
_ACCENT_PAIRS: dict[str, str] = {
    "#7C4DFF": "#FF4081",
    "#FF4081": "#FFAB00",
    "#00BFA5": "#1E88E5",
    "#FFAB00": "#FF7043",
    "#26C6DA": "#9CCC65",
    "#9CCC65": "#26C6DA",
    "#FF7043": "#FF4081",
    "#8E24AA": "#EC407A",
    "#43A047": "#26C6DA",
    "#1E88E5": "#26C6DA",
    "#5C6BC0": "#7C4DFF",
    "#EC407A": "#FFAB00",
    "#26A69A": "#26C6DA",
    "#FFA726": "#FF7043",
    "#AB47BC": "#EC407A",
    "#42A5F5": "#26C6DA",
}


def _alpha_hex(hex_color: str, alpha: int = 0xCC) -> str:
    """Return ``#RRGGBBAA`` form of an ``#RRGGBB`` color (alpha 0-255).

    The framework parses 8-char hex as ``RRGGBBAA`` (alpha at end).
    """
    h = hex_color.lstrip("#")
    if len(h) == 8:  # already RRGGBBAA
        return f"#{h}"
    return f"#{h}{alpha:02X}"


def _gradient_box(
    color: str,
    *,
    width: nv.Sizing | int,
    height: nv.Sizing | int,
    radius: int = 20,
    bubble_dim: int = 220,
) -> nv.Widget:
    """A faux-photo gradient block: base color + translucent accent bubble.

    The bubble is anchored to the top-right and oversized so that, after
    clipping to the rounded rect, it appears as a soft radial highlight
    bleeding in from the corner  Egiving a vibrant, photo-like feel.

    ``bubble_dim`` should be tuned to be larger than the container in both
    axes; otherwise a hard circle becomes visible.
    """
    accent = _ACCENT_PAIRS.get(color, color)
    bubble = nv.Container(width=bubble_dim, height=bubble_dim).modifier(
        nv.background(_alpha_hex(accent, 0xCC)) | nv.corner_radius(bubble_dim // 2)
    )
    return nv.Container(
        child=nv.Stack(
            [bubble],
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            alignment=("end", "start"),
        ),
        width=width,
        height=height,
    ).modifier(nv.background(color) | nv.corner_radius(radius) | nv.clip())


def _accent_tile(color: str, size: int = 88, *, radius: int = 20) -> nv.Widget:
    """A rounded gradient square  Eused as faux album / cover art."""
    bubble = max(140, int(size * 1.8))
    return _gradient_box(color, width=size, height=size, radius=radius, bubble_dim=bubble)


def _track_card(title: str, artist: str, accent: str) -> nv.Widget:
    return nv.Card(
        nv.Row(
            [
                _accent_tile(accent, size=64),
                nv.Column(
                    [
                        nv.Text(title, type_scale=TITLE_MD),
                        nv.Text(artist, type_scale=BODY_MD),
                    ],
                    gap=4,
                    cross_alignment="start",
                ),
            ],
            gap=14,
            cross_alignment="center",
            padding=12,
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=24),
        width=nv.Sizing.flex(1),
    )


# ------------------------------ Hero panel -------------------------------


class HeroPanel(nv.ComposableWidget):
    """The "Now Playing" hero panel with a rotating, pulsing album tile."""

    _ROTATE_DEG_PER_SEC = 18.0
    _PULSE_PERIOD_SEC = 2.4

    def __init__(self) -> None:
        super().__init__()
        self.rotation = nv.Observable(0.0)
        self.pulse = nv.Observable(1.0)
        self._elapsed = 0.0
        self._tick_fn = self._tick

    def on_mount(self) -> None:  # pragma: no cover - visual only
        super().on_mount()
        nv.clock.schedule_interval(self._tick_fn, 1 / 60.0)

    def on_unmount(self) -> None:  # pragma: no cover - visual only
        try:
            nv.clock.unschedule(self._tick_fn)
        finally:
            super().on_unmount()

    def _tick(self, dt: float) -> None:
        self._elapsed += dt
        self.rotation.value = (self.rotation.value + self._ROTATE_DEG_PER_SEC * dt) % 360.0
        # Smooth pulse between ~0.94 and ~1.06.
        import math

        phase = (self._elapsed / self._PULSE_PERIOD_SEC) * 2 * math.pi
        self.pulse.value = 1.0 + 0.06 * math.sin(phase)

    def build(self) -> nv.Widget:
        # Circular album with a determinate progress arc wrapping it.
        ring_style = nv.CircularProgressIndicatorStyle.default().copy_with(
            track_thickness=8.0,
            active_indicator_color=nv.ColorRole.PRIMARY,
            track_color=nv.ColorRole.SURFACE_VARIANT,
        )
        ring = nv.CircularProgressIndicator(value=0.42, size=180, style=ring_style)

        # Inner circular "album" with a music glyph; gently rotates and pulses.
        disc = nv.Container(
            child=nv.Icon(
                "music_note",
                size=56,
                style=nv.IconStyle(color=nv.ColorRole.ON_PRIMARY),
            ),
            width=140,
            height=140,
            alignment=("center", "center"),
        ).modifier(
            nv.background(nv.ColorRole.PRIMARY)
            | nv.corner_radius(70)
            | nv.rotate(self.rotation)
            | nv.scale(self.pulse)
            | nv.shadow(blur=24, color="#33000000", offset=(0, 6))
        )

        cover = nv.Stack(
            [ring, disc],
            width=nv.Sizing.fixed(180),
            height=nv.Sizing.fixed(180),
            alignment=("center", "center"),
        )

        # --- Now-playing transport row (showcasing IconButton variants) ---
        controls = nv.Row(
            [
                nv.IconButton("shuffle", style=nv.IconButtonStyle.standard("s")),
                nv.IconButton("skip_previous", style=nv.IconButtonStyle.standard("m")),
                nv.IconButton("play_arrow", style=nv.IconButtonStyle.filled("m")),
                nv.IconButton("skip_next", style=nv.IconButtonStyle.standard("m")),
                nv.IconButton("repeat", style=nv.IconButtonStyle.standard("s")),
            ],
            gap=4,
            cross_alignment="center",
        )

        # --- Action row: Filled "Like" + Tonal "Add to mix" + IconToggle fav ---
        actions = nv.Row(
            [
                nv.Button("Like", icon="thumb_up", style=nv.ButtonStyle.filled("s")),
                nv.Button("Add to mix", icon="playlist_add", style=nv.ButtonStyle.tonal("s")),
                nv.IconToggleButton("favorite", selected=True),
            ],
            gap=8,
            cross_alignment="center",
        )

        # Linear progress + time labels.
        progress_style = nv.LinearProgressIndicatorStyle.default().copy_with(
            track_thickness=6.0,
        )
        progress_block = nv.Column(
            [
                nv.LinearProgressIndicator(
                    value=0.42,
                    width=nv.Sizing.flex(1),
                    style=progress_style,
                ),
                nv.Row(
                    [
                        nv.Text("1:42", type_scale=BODY_SM),
                        nv.Text("4:08", type_scale=BODY_SM),
                    ],
                    main_alignment="space-between",
                    width=nv.Sizing.flex(1),
                ),
            ],
            gap=4,
            width=nv.Sizing.flex(1),
            cross_alignment="start",
        )

        text_block = nv.Column(
            [
                nv.Text("NOW PLAYING", type_scale=LABEL),
                nv.Text("Midnight Drive", type_scale=HEADLINE),
                nv.Text("Aurora Lights · 2026", type_scale=BODY_LG),
                nv.Container(height=8),
                nv.Row(
                    [
                        nv.FilterChip("Synthwave", selected=True),
                        nv.FilterChip("Ambient"),
                        nv.FilterChip("Chillhop"),
                    ],
                    gap=8,
                ),
                nv.Container(height=10),
                progress_block,
                nv.Container(height=4),
                nv.Row(
                    [controls, actions],
                    main_alignment="space-between",
                    cross_alignment="center",
                    width=nv.Sizing.flex(1),
                ),
            ],
            gap=4,
            cross_alignment="start",
            width=nv.Sizing.flex(1),
        )

        return nv.Card(
            nv.Row(
                [cover, text_block],
                gap=28,
                cross_alignment="center",
                padding=24,
                width=nv.Sizing.flex(1),
            ),
            style=nv.CardStyle.filled().copy_with(
                border_radius=32,
                background=nv.ColorRole.PRIMARY_CONTAINER,
            ),
            width=nv.Sizing.flex(1),
        )


# --------------------------- Section builders ----------------------------


_TRACKS: List[tuple[str, str, str]] = [
    ("Neon Skyline", "Aurora Lights", "#7C4DFF"),
    ("Velvet Static", "Chrome Echo", "#FF4081"),
    ("Glass Horizon", "Lumen Drift", "#00BFA5"),
]

_ARTISTS: List[tuple[str, str]] = [
    ("Aurora Lights", "#7C4DFF"),
    ("Chrome Echo", "#FF4081"),
    ("Lumen Drift", "#00BFA5"),
    ("Night Atlas", "#FFAB00"),
    ("Vesper Bloom", "#26C6DA"),
    ("Solar Wake", "#9CCC65"),
]

_TOP_MIXES: List[tuple[str, str, str]] = [
    ("Late Night Drive", "32 tracks · 2h 14m", "#7C4DFF"),
    ("Sunday Reset", "24 tracks · 1h 38m", "#EC407A"),
]


def _home_section(hero: HeroPanel) -> nv.Widget:
    return nv.Column(
        [
            hero,
            nv.Container(height=8),
            nv.Row(
                [
                    nv.Text("Up Next", type_scale=TITLE_LG),
                    nv.AssistChip("See all", leading_icon="arrow_forward"),
                ],
                main_alignment="space-between",
                cross_alignment="center",
                width=nv.Sizing.flex(1),
            ),
            nv.Column(
                [_track_card(t, a, c) for (t, a, c) in _TRACKS],
                gap=10,
                width=nv.Sizing.flex(1),
                cross_alignment="start",
            ),
        ],
        gap=14,
        padding=24,
        cross_alignment="start",
        width=nv.Sizing.flex(1),
    )


def _grid_section(swatches: List[str]) -> nv.Widget:
    """Discover-style mix grid; the page heading lives in the global header."""
    return nv.Column(
        [
            nv.Flow(
                [
                    nv.Card(
                        nv.Column(
                            [
                                _accent_tile(c, size=140),
                                nv.Text(f"Mix #{i + 1:02d}", type_scale=TITLE_MD),
                                nv.Text("12 tracks · 48 min", type_scale=BODY_SM),
                            ],
                            gap=6,
                            padding=12,
                            cross_alignment="start",
                        ),
                        style=nv.CardStyle.filled().copy_with(border_radius=28),
                    )
                    for i, c in enumerate(swatches)
                ],
                main_gap=14,
                cross_gap=14,
            ),
        ],
        gap=8,
        padding=24,
        cross_alignment="start",
        width=nv.Sizing.flex(1),
    )


def _top_mix_card(title: str, meta: str, accent: str) -> nv.Widget:
    cover = _gradient_box(
        accent,
        width=nv.Sizing.flex(1),
        height=nv.Sizing.fixed(150),
        radius=20,
        bubble_dim=620,
    )
    return nv.Card(
        nv.Column(
            [
                cover,
                nv.Text(title, type_scale=TITLE_LG),
                nv.Text(meta, type_scale=BODY_SM),
                nv.Container(height=2),
                nv.Row(
                    [
                        nv.Button("Play", icon="play_arrow", style=nv.ButtonStyle.filled("s")),
                        nv.Button("Shuffle", icon="shuffle", style=nv.ButtonStyle.outlined("s")),
                    ],
                    gap=8,
                ),
            ],
            gap=8,
            padding=14,
            cross_alignment="start",
            width=nv.Sizing.flex(1),
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=28),
        width=nv.Sizing.flex(1),
    )


def _artist_avatar(name: str, color: str) -> nv.Widget:
    avatar = _gradient_box(color, width=72, height=72, radius=36, bubble_dim=130)
    return nv.Column(
        [avatar, nv.Text(name, type_scale=BODY_SM)],
        gap=6,
        cross_alignment="center",
    )


def _library_section() -> nv.Widget:
    """A more 'app-like' library layout: top mixes + artist avatars.

    Differentiated from Discover (which is a uniform mix grid) by mixing
    bigger 2-column hero cards with a horizontal artist avatar strip.
    """
    return nv.Column(
        [
            nv.Text("Top Mixes", type_scale=TITLE_LG),
            nv.Row(
                [_top_mix_card(t, m, c) for (t, m, c) in _TOP_MIXES],
                gap=14,
                cross_alignment="start",
                width=nv.Sizing.flex(1),
            ),
            nv.Container(height=4),
            nv.Text("Artists", type_scale=TITLE_LG),
            nv.Row(
                [_artist_avatar(n, c) for (n, c) in _ARTISTS],
                gap=18,
                cross_alignment="start",
            ),
        ],
        gap=10,
        padding=24,
        cross_alignment="start",
        width=nv.Sizing.flex(1),
    )


_EQ_BANDS: List[tuple[str, float]] = [
    ("60", 0.45),
    ("250", 0.62),
    ("1k", 0.78),
    ("4k", 0.55),
    ("16k", 0.40),
]


def _settings_section() -> nv.Widget:
    """Settings page (heading lives in the global header strip).

    Three cards: Playback, Theme (ConnectedButtonGroup), Equalizer (vertical Sliders).
    """
    volume = nv.Observable(0.65)

    playback_card = nv.Card(
        nv.Column(
            [
                nv.Text("Playback", type_scale=TITLE_LG),
                nv.Row(
                    [
                        nv.Text("Volume", type_scale=TITLE_MD),
                        nv.HorizontalSlider(
                            value=volume,
                            min_value=0.0,
                            max_value=1.0,
                            show_value_indicator=True,
                            width=nv.Sizing.fixed(220),
                        ),
                    ],
                    main_alignment="space-between",
                    cross_alignment="center",
                    width=nv.Sizing.flex(1),
                ),
                nv.HorizontalDivider(),
                nv.Row(
                    [
                        nv.Text("High-quality streaming", type_scale=TITLE_MD),
                        nv.Switch(checked=True),
                    ],
                    main_alignment="space-between",
                    cross_alignment="center",
                    width=nv.Sizing.flex(1),
                ),
                nv.HorizontalDivider(),
                nv.Row(
                    [
                        nv.Text("Crossfade", type_scale=TITLE_MD),
                        nv.Switch(checked=True),
                    ],
                    main_alignment="space-between",
                    cross_alignment="center",
                    width=nv.Sizing.flex(1),
                ),
            ],
            gap=10,
            padding=18,
            cross_alignment="start",
            width=nv.Sizing.flex(1),
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=28),
        width=nv.Sizing.flex(1),
    )

    theme_card = nv.Card(
        nv.Column(
            [
                nv.Text("Theme", type_scale=TITLE_LG),
                nv.ConnectedButtonGroup(
                    items=[
                        nv.GroupButton("Light", icon="light_mode"),
                        nv.GroupButton("Dark", icon="dark_mode", selected=True),
                        nv.GroupButton("Auto", icon="brightness_auto"),
                    ],
                    style=nv.ConnectedButtonGroupStyle.tonal("m"),
                ),
            ],
            gap=12,
            padding=18,
            cross_alignment="start",
            width=nv.Sizing.flex(1),
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=28),
        width=nv.Sizing.flex(1),
    )

    eq_columns: List[nv.Widget] = []
    for label, default in _EQ_BANDS:
        eq_columns.append(
            nv.Column(
                [
                    nv.VerticalSlider(
                        value=nv.Observable(default),
                        min_value=0.0,
                        max_value=1.0,
                        height=nv.Sizing.fixed(110),
                    ),
                    nv.Text(label, type_scale=BODY_SM),
                ],
                gap=6,
                cross_alignment="center",
            )
        )
    equalizer_card = nv.Card(
        nv.Column(
            [
                nv.Text("Equalizer", type_scale=TITLE_LG),
                nv.Row(
                    eq_columns,
                    gap=24,
                    cross_alignment="end",
                    main_alignment="center",
                    width=nv.Sizing.flex(1),
                ),
            ],
            gap=10,
            padding=18,
            cross_alignment="start",
            width=nv.Sizing.flex(1),
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=28),
        width=nv.Sizing.flex(1),
    )

    return nv.Column(
        [
            nv.Row(
                [playback_card, theme_card],
                gap=14,
                cross_alignment="start",
                width=nv.Sizing.flex(1),
            ),
            equalizer_card,
        ],
        gap=14,
        padding=24,
        cross_alignment="start",
        width=nv.Sizing.flex(1),
    )


# -------------------------------- Root -----------------------------------


class PulseApp(nv.ComposableWidget):
    """Showcase root widget  Eauto-cycles sections for the hero GIF."""

    _SECTION_INTERVAL_SEC = 3.0

    def __init__(self, *, autoplay: bool = True) -> None:
        super().__init__()
        self.section = nv.Observable(int(Section.HOME))
        self.rail_expanded = nv.Observable(True)
        self._autoplay = autoplay
        self._cycle_fn = self._advance_section

    def on_mount(self) -> None:  # pragma: no cover - visual only
        super().on_mount()
        if self._autoplay:
            nv.clock.schedule_interval(self._cycle_fn, self._SECTION_INTERVAL_SEC)

    def on_unmount(self) -> None:  # pragma: no cover - visual only
        try:
            nv.clock.unschedule(self._cycle_fn)
        finally:
            super().on_unmount()

    def _advance_section(self, _dt: float) -> None:
        self.section.value = (int(self.section.value) + 1) % len(Section)

    def build(self) -> nv.Widget:
        rail = nv.NavigationRail(
            children=[
                nv.RailItem(icon="home", label="Home"),
                nv.RailItem(icon="explore", label="Discover", small_badge=nv.Observable(True)),
                nv.RailItem(icon="library_music", label="Library", large_badge=nv.Observable("3")),
                nv.RailItem(icon="settings", label="Settings"),
            ],
            index=self.section,
            expanded=self.rail_expanded,
            show_menu_button=True,
            on_select=lambda idx: setattr(self.section, "value", int(idx)),
            height=nv.Sizing.flex(1),
        )

        hero = HeroPanel()
        content = nv.Deck(
            children=[
                _home_section(hero),
                _grid_section(
                    [
                        "#7C4DFF",
                        "#00BFA5",
                        "#FF4081",
                        "#FFAB00",
                        "#26C6DA",
                        "#9CCC65",
                        "#FF7043",
                        "#8E24AA",
                        "#43A047",
                        "#1E88E5",
                    ],
                ),
                _library_section(),
                _settings_section(),
            ],
            index=self.section,
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )

        # Floating action button anchored to the bottom-right via Stack alignment.
        # The FAB lives in a *small* container (FAB + padding) so it doesn't
        # overlay/eat clicks on the rest of the body. ``Stack`` aligns every
        # child by the same anchor; the body fills via ``flex(100)`` so the
        # alignment only visibly affects the small FAB child.
        fab = nv.Container(
            child=nv.Fab("play_arrow", style=nv.FabStyle.primary("m")),
            padding=24,
        )

        body = nv.Stack(
            [
                nv.Container(
                    child=nv.Row([rail, content], width=nv.Sizing.flex(1), height=nv.Sizing.flex(1)),
                    width=nv.Sizing.flex(100),
                    height=nv.Sizing.flex(100),
                ),
                fab,
            ],
            alignment=("end", "end"),
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )

        # Page title strip across the very top, sourced reactively from
        # the current section index.
        title_text = self.section.map(lambda i: SECTION_TITLES[Section(int(i))])
        subtitle_text = self.section.map(lambda i: SECTION_SUBTITLES[Section(int(i))])

        header = nv.Container(
            child=nv.Column(
                [
                    nv.Text(title_text, type_scale=HEADLINE),
                    nv.Text(subtitle_text, type_scale=BODY_MD),
                ],
                gap=2,
                cross_alignment="start",
            ),
            padding=(24, 14, 24, 14),
            width=nv.Sizing.flex(1),
            height=nv.Sizing.fixed(76),
        ).modifier(nv.background(nv.ColorRole.SURFACE_CONTAINER_LOW))

        return nv.Column(
            [header, body],
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            cross_alignment="start",
        )


# --------------------------------- Main ----------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pulse  EREADME hero showcase")
    p.add_argument("--png", type=str, default="", help="Render a single frame to PNG and exit")
    p.add_argument("--no-autoplay", action="store_true", help="Disable section auto-cycling")
    p.add_argument("--seed", type=str, default="#5B5BFF", help="MaterialThemeFactory seed color")
    p.add_argument("--dark", action="store_true", help="Use dark theme")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    theme = nv.ThemeFactory.from_seed(args.seed, mode="dark" if args.dark else "light")

    app = nv.App(
        content=PulseApp(autoplay=not args.no_autoplay),
        title="Pulse",
        width=1150,
        height=720,
        theme=theme,
        chrome=nv.CustomChrome(
            header=PulseTitleBar(),
        ),
    )

    if args.png:
        app.render_to_png(args.png)
        print(f"Rendered {args.png}")
        return

    app.run()


if __name__ == "__main__":
    main()
