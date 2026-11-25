"""Tests for BasicDialog widget."""

from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.styles.dialog_style import DialogStyle
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material import ButtonStyle


def test_basic_dialog_creation():
    """Test creating a BasicDialog."""
    dialog = BasicDialog(
        title="Test Title",
        message="Test Content",
    )

    assert dialog.title == "Test Title"
    assert dialog.message == "Test Content"
    assert dialog.actions == []


def test_basic_dialog_with_actions():
    """Test BasicDialog with action buttons."""
    from nuiitivet.material.buttons import Button

    actions = [
        Button("Cancel", style=ButtonStyle.text()),
        Button("OK", style=ButtonStyle.text()),
    ]

    dialog = BasicDialog(
        title="Confirm",
        message="Are you sure?",
        actions=actions,
    )

    assert len(dialog.actions) == 2


def test_basic_dialog_build():
    """Test building a BasicDialog."""
    dialog = BasicDialog(
        title="Title",
        message="Content",
    )

    # Build the widget tree
    built = dialog.build()

    # Should return a Box
    from nuiitivet.widgets.box import Box

    assert isinstance(built, Box)
    # Check default style usage via box properties

    # accessing via _background_color on Box because it stores it there
    # But Box might resolve it differently.
    # We can check simple properties if exposed.
    # Or just ensure it built.


def test_basic_dialog_minimal():
    """Test minimal BasicDialog (no title, content, or actions)."""
    dialog = BasicDialog()

    assert dialog.title is None
    assert dialog.message is None
    assert dialog.actions == []

    # Should still build successfully
    built = dialog.build()
    assert built is not None


def test_basic_dialog_style_override():
    """Test BasicDialog with custom style."""
    custom_style = DialogStyle(corner_radius=16.0, min_width=400.0, content_insets=32)

    dialog = BasicDialog(title="Props", style=custom_style)

    assert dialog.style.corner_radius == 16.0
    assert dialog.style.min_width == 400.0
    assert dialog.style.content_insets == 32


def test_basic_dialog_only_title():
    """Test BasicDialog with only title."""
    dialog = BasicDialog(
        title="Title only",
    )

    assert dialog.title is not None
    assert dialog.message is None
    assert dialog.actions == []


def test_basic_dialog_only_content():
    """Test BasicDialog with only content."""
    dialog = BasicDialog(
        message="Content only",
    )

    assert dialog.title is None
    assert dialog.message is not None


def test_basic_dialog_with_icon():
    """Test BasicDialog with icon."""
    dialog = BasicDialog(icon="home", title="With Icon")
    assert dialog.icon == "home"

    dialog.build()
    # Verification of built tree structure is hard without deep inspection
    # but at least it builds.


def test_basic_dialog_default_background_is_surface_container_high():
    """MD3 Basic Dialog uses surface-container-high (not highest)."""
    from nuiitivet.material.theme.color_role import ColorRole

    style = DialogStyle()
    assert style.background == ColorRole.SURFACE_CONTAINER_HIGH


def test_basic_dialog_default_width_is_md3_min():
    """BasicDialog default width is the MD3 minimum (280dp)."""
    dialog = BasicDialog(title="t")
    assert dialog.width == 280.0


def test_basic_dialog_custom_width_propagates_to_box():
    """BasicDialog forwards custom width to the underlying Box."""
    from nuiitivet.widgets.box import Box

    dialog = BasicDialog(title="t", width=420.0)
    assert dialog.width == 420.0

    built = dialog.build()
    assert isinstance(built, Box)
    # Box stores width as a Sizing("fixed", value) on width_sizing.
    sizing = built.width_sizing
    assert sizing.kind == "fixed"
    assert float(sizing.value) == 420.0


def _text_rects(dialog: BasicDialog) -> dict[str, list[int]]:
    """Lay ``dialog`` out and return the rect of each of its texts by label."""
    from nuiitivet.testing import mount

    def texts(node: dict) -> dict[str, list[int]]:
        found = {node["label"]: node["rect"]} if node["type"] == "Text" else {}
        for child in node.get("children", []):
            found.update(texts(child))
        return found

    with mount(dialog) as host:
        host.layout(600, 600)
        return texts(host.tree())


def test_basic_dialog_title_and_message_are_spaced_as_md3_line_boxes():
    """16dp from the headline's 32dp line box to the supporting text's 20dp one."""
    dialog = BasicDialog(title="Title", message="Body")

    rects = _text_rects(dialog)
    _, title_y, _, title_h = rects["Title"]
    _, body_y, _, body_h = rects["Body"]

    assert title_h == 32
    assert body_h == 20
    assert body_y - (title_y + title_h) == dialog.style.title_content_gap == 16


def test_basic_dialog_spacing_does_not_depend_on_the_glyphs():
    """A title of x-height letters and one with descenders put the message at the same place."""
    low = _text_rects(BasicDialog(title="xxxx", message="Body"))
    tall = _text_rects(BasicDialog(title="Ågjpqy", message="Body"))

    assert low["Body"][1] == tall["Body"][1]


def test_color_role_includes_md3_surface_containers():
    """ColorRole exposes the full MD3 surface container ladder."""
    from nuiitivet.material.theme.color_role import ColorRole

    assert ColorRole.SURFACE_CONTAINER_LOWEST.value == "surfaceContainerLowest"
    assert ColorRole.SURFACE_CONTAINER_LOW.value == "surfaceContainerLow"
    assert ColorRole.SURFACE_CONTAINER.value == "surfaceContainer"
    assert ColorRole.SURFACE_CONTAINER_HIGH.value == "surfaceContainerHigh"
    assert ColorRole.SURFACE_CONTAINER_HIGHEST.value == "surfaceContainerHighest"


def test_material_theme_resolves_surface_container_high():
    """A MaterialThemeFactory resolves SURFACE_CONTAINER_HIGH to a concrete color."""
    from nuiitivet.material.theme.color_role import ColorRole
    from nuiitivet.theme.resolver import resolve_color_to_rgba

    theme = MaterialThemeFactory.light("#6750A4")
    rgba = resolve_color_to_rgba(ColorRole.SURFACE_CONTAINER_HIGH, theme=theme)
    assert isinstance(rgba, tuple)
    assert len(rgba) == 4
