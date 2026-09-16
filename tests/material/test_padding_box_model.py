"""``Widget.padding`` is the band from the allocated rect to the component.

Every MD3 component draws its container inside that band, grows its
preferred size by it, keeps its spec insets on ``content_insets`` (never on
its own ``padding``), and hit-tests on the content rect.
"""

from nuiitivet.layout.container import Container
from nuiitivet.material.badge import LargeBadge
from nuiitivet.material.buttons import Button, Fab
from nuiitivet.material.chip import AssistChip
from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.menu import Menu, MenuItem
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.material.split_button import SplitButton
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.widgets.box import Box


def _lay_out(widget):
    w, h = widget.preferred_size()
    widget.layout(w, h)
    widget.set_layout_rect(0, 0, w, h)
    return w, h


# --- Fab -----------------------------------------------------------------


def test_fab_style_has_no_padding_and_no_content_insets() -> None:
    style = FabStyle.primary()
    assert not hasattr(style, "padding")
    assert style.content_insets == 0


def test_fab_without_padding_is_the_bare_container() -> None:
    fab = Fab("add")
    w, h = _lay_out(fab)
    assert (w, h) == (56, 56)
    assert fab._container_rect(0, 0, w, h) == (0, 0, 56, 56)
    # 24dp icon centred in the 56dp container: a 16dp inset derived, not declared.
    assert fab.children[0].layout_rect == (16, 16, 24, 24)


def test_fab_padding_grows_the_allocated_rect_and_moves_the_container() -> None:
    fab = Fab("add", padding=20)
    w, h = _lay_out(fab)
    assert (w, h) == (96, 96)
    assert fab._container_rect(0, 0, w, h) == (20, 20, 56, 56)
    assert fab.children[0].layout_rect == (36, 36, 24, 24)


def test_fab_asymmetric_padding_keeps_the_icon_inside_the_container() -> None:
    fab = Fab("add", padding=(40, 0, 0, 0))
    w, h = _lay_out(fab)
    assert (w, h) == (96, 56)
    assert fab._container_rect(0, 0, w, h) == (40, 0, 56, 56)
    assert fab.children[0].layout_rect == (56, 16, 24, 24)


def _paint_rects(monkeypatch, widget):
    """Paint ``widget`` at its preferred size and return the rects its background and border were drawn on."""
    seen: dict[str, tuple] = {}

    def record(name):
        return lambda self, canvas, x, y, w, h: seen.__setitem__(name, (x, y, w, h))

    monkeypatch.setattr(Box, "draw_background", record("background"))
    monkeypatch.setattr(Box, "draw_border", record("border"))
    w, h = _lay_out(widget)
    widget.paint(None, 0, 0, w, h)
    return seen


def test_fab_paints_its_container_inside_the_padding(monkeypatch) -> None:
    seen = _paint_rects(monkeypatch, Fab("add", padding=20))
    assert seen["background"] == (20, 20, 56, 56)
    assert seen["border"] == (20, 20, 56, 56)


def test_button_paints_its_container_inside_the_padding(monkeypatch) -> None:
    button = Button("Hello", style=ButtonStyle.outlined(), padding=24)
    seen = _paint_rects(monkeypatch, button)
    w, h = button.preferred_size()
    assert seen["background"] == (24, 28, w - 48, 40)
    assert seen["border"] == seen["background"]


def test_fab_hit_test_ignores_the_padding_band() -> None:
    fab = Fab("add", padding=20)
    _lay_out(fab)
    assert fab.hit_test(2, 2) is None
    assert fab.hit_test(48, 48) is not None


# --- Button --------------------------------------------------------------


def test_button_style_carries_content_insets_not_padding() -> None:
    style = ButtonStyle.filled("s")
    assert not hasattr(style, "padding")
    assert style.content_insets == (16, 0, 16, 0)


def test_button_content_insets_are_inside_the_container() -> None:
    button = Button("Hello")
    w, h = _lay_out(button)
    cx, cy, cw, ch = button._container_rect(0, 0, w, h)
    lx, ly, lw, lh = button.children[0].layout_rect
    assert button.padding == (0, 0, 0, 0)
    assert ch == 40 and h == 48  # 40dp container floored to the 48dp touch target
    assert lx == cx + 16
    assert lx + lw == cx + cw - 16


def test_button_padding_is_added_around_the_container() -> None:
    plain = Button("Hello")
    padded = Button("Hello", padding=10)
    pw, ph = _lay_out(plain)
    w, h = _lay_out(padded)
    assert (w, h) == (pw + 20, ph + 20)
    assert padded._container_rect(0, 0, w, h) == (10, 14, pw, 40)
    assert padded.hit_test(2, 2) is None
    assert padded.hit_test(10, 14) is not None


# --- Chip ----------------------------------------------------------------


def test_chip_padding_is_outside_the_container() -> None:
    chip = AssistChip("Assist", padding=8)
    w, h = _lay_out(chip)
    assert chip.content_rect(0, 0, w, h) == (8, 8, w - 16, 32)
    assert chip.hit_test(2, 2) is None
    assert chip.hit_test(20, 20) is not None


# --- SplitButton ---------------------------------------------------------


def test_split_button_halves_keep_their_spec_insets_inside() -> None:
    button = SplitButton("Action")
    for half in (button._leading_btn, button._trailing_btn):
        assert half.padding == (0, 0, 0, 0)
        assert isinstance(half.children[0], Container)
        assert half.children[0].padding[0] > 0


# --- LargeBadge ----------------------------------------------------------


def test_large_badge_padding_wraps_the_pill() -> None:
    badge = LargeBadge("9", padding=6)
    w, h = _lay_out(badge)
    assert badge.padding == (6, 6, 6, 6)
    assert badge.bgcolor is None
    pill = badge.children[0]
    assert isinstance(pill, Box)
    assert pill.padding == (4, 0, 4, 0)
    pw, ph = pill.preferred_size()
    assert (w, h) == (pw + 12, ph + 12)


# --- Menu ----------------------------------------------------------------


def test_menu_vertical_inset_lives_on_the_column() -> None:
    menu = Menu(items=[MenuItem("Cut")])
    assert menu.padding == (0, 0, 0, 0)
    assert menu._column.padding == (0, 8, 0, 8)


# --- Snackbar ------------------------------------------------------------


def test_snackbar_padding_is_outer_and_style_insets_are_inner() -> None:
    snackbar = Snackbar("hi", padding=8)
    assert snackbar.padding == (8, 8, 8, 8)
    built = snackbar.build()
    assert built.padding == (16, 16, 16, 16)
    w, h = snackbar.preferred_size()
    bw, bh = built.preferred_size()
    assert (w, h) == (bw + 16, bh + 16)


# --- LoadingIndicator / NavigationRail ----------------------------------


def test_loading_indicator_padding_grows_the_box() -> None:
    assert LoadingIndicator(size=48).preferred_size() == (48, 48)
    assert LoadingIndicator(size=48, padding=16).preferred_size() == (80, 80)
    assert LoadingIndicator(size=48, padding=(8, 12, 8, 12)).preferred_size() == (64, 72)


def test_navigation_rail_padding_grows_the_box() -> None:
    items = [RailItem(icon="home", label="Home")]
    plain = NavigationRail(children=items)
    padded = NavigationRail(children=[RailItem(icon="home", label="Home")], padding=(4, 6, 4, 6))
    pw, ph = plain.preferred_size()
    w, h = padded.preferred_size()
    assert (w, h) == (pw + 8, ph + 12)
