import unittest
from unittest.mock import MagicMock
import sys
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.material.icon import Icon


class TestCheckboxIconScaling(unittest.TestCase):
    def setUp(self):
        from nuiitivet.material.theme.material_theme import MaterialTheme
        from nuiitivet.theme.manager import manager

        manager.set_theme(MaterialTheme.light("#6750A4"))

    def test_checkbox_scaling(self):
        # Checkbox with flex width (simulated by passing large rect to paint)
        c = Checkbox(size="100%")

        # Mock canvas
        canvas = MagicMock()

        # Paint with 100x100
        c.paint(canvas, 0, 0, 100, 100)

        found_large = False

        for call in canvas.drawRRect.call_args_list:
            rrect = call[0][0]  # skia.RRect
            rect = rrect.rect()  # skia.Rect
            w = rect.width()

            # If it scales (contain), it should draw close to 100x100.
            # icon_sz is approx 37.5 for 100x100 touch target
            if 30 <= w <= 50:
                found_large = True

        self.assertTrue(found_large, "Checkbox did not scale to fit allocated rect")

    def test_icon_scaling(self):
        # Icon with flex width
        icon = Icon("home", size="100%")

        canvas = MagicMock()

        # Mock skia to intercept Font creation
        mock_skia = MagicMock()
        with unittest.mock.patch.dict(sys.modules, {"skia": mock_skia}):
            # Paint with 100x100
            icon.paint(canvas, 0, 0, 100, 100)

        # Check skia.Font calls
        found_large_font = False
        for call in mock_skia.Font.call_args_list:
            args = call[0]
            if len(args) >= 2:
                size = args[1]
                if size >= 90:
                    found_large_font = True

        self.assertTrue(found_large_font, "Icon did not scale to fit allocated rect")

    def test_checkbox_hit_test_rect(self):
        c = Checkbox(size="100%")
        canvas = MagicMock()
        # Paint with 100x100
        c.paint(canvas, 0, 0, 100, 100)

        self.assertEqual(c.last_rect, (0, 0, 100, 100), "Checkbox hit test rect should match allocated rect")


if __name__ == "__main__":
    unittest.main()
