"""Render layout demo samples to PNG files under docs/assets.

Usage:
    uv run scripts/docs/render_layout_images.py

This loader imports each sample file by path and calls its `main(png=...)` function.
It also applies a window frame style to the generated images.

To render a new sample:
1. Ensure the sample has a `main(png_path: str)` function.
2. Add the (source_path, output_filename) tuple to the `SAMPLES` list below.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import skia

ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT / "docs" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# List of (source file relative to repo root, output png name)
SAMPLES = [
    ("src/samples/layout_alignment/container_alignment.py", "layout_alignment_container.png"),
    ("src/samples/layout_alignment/row_alignment.py", "layout_alignment_row.png"),
    ("src/samples/layout_alignment/row_cross_alignment.py", "layout_alignment_row_cross.png"),
    ("src/samples/layout_alignment/column_alignment.py", "layout_alignment_column.png"),
    ("src/samples/layout_alignment/column_cross_alignment.py", "layout_alignment_column_cross.png"),
    ("src/samples/layout_basics/basic_column.py", "layout_basics_column.png"),
    ("src/samples/layout_basics/basic_row.py", "layout_basics_row.png"),
    ("src/samples/layout_basics/row_column_combination.py", "layout_basics_form.png"),
    ("src/samples/layout_sizing/fixed_size.py", "layout_sizing_fixed.png"),
    ("src/samples/layout_sizing/auto_size.py", "layout_sizing_auto.png"),
    ("src/samples/layout_sizing/flex_width.py", "layout_sizing_fullwidth.png"),
    ("src/samples/layout_spacing/padding_demo.py", "layout_spacing_padding.png"),
    ("src/samples/layout_spacing/gap_demo.py", "layout_spacing_gap.png"),
    ("src/samples/layout_spacing/spacer_demo.py", "layout_spacing_spacer.png"),
    ("src/samples/layout_spacing/container_margin.py", "layout_spacing_container.png"),
    ("src/samples/layout_overflow/default_overflow.py", "layout_overflow_default.png"),
    ("src/samples/layout_overflow/clipped_content.py", "layout_overflow_clipped.png"),
    ("src/samples/layout_overflow/scrollable_list.py", "layout_overflow_scrollable.png"),
    ("src/samples/layout_grid/step1_grid.py", "layout_grid_step1.png"),
    ("src/samples/layout_grid/step2_span.py", "layout_grid_step2.png"),
    ("src/samples/layout_grid/step3_sizing.py", "layout_grid_step3.png"),
    # Step 4 は完成形(app_layout_grid.py)の画像を使うので、専用の生成はしない（または final と同じでよい）
    # app_layout_grid.py は layout_grid_final.png として生成
    ("src/samples/layout_grid/app_layout_grid.py", "layout_grid_final.png"),
    ("src/samples/layout_grid/named_areas_grid.py", "layout_grid_named.png"),
    ("src/samples/layout_extras/stack_demo.py", "layout_extras_stack.png"),
    ("src/samples/layout_extras/flow_minimal_demo.py", "layout_extras_flow.png"),
    ("src/samples/layout_extras/uniform_flow_minimal_demo.py", "layout_extras_uniform_flow.png"),
    ("src/samples/layout_extras/deck_demo.py", "layout_extras_deck.png"),
    ("src/samples/layout_extras/spacer_flex_demo.py", "layout_extras_spacer.png"),
    ("src/samples/layout_extras/container_demo.py", "layout_extras_container.png"),
]


def load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def extract_title(source_path: Path) -> str:
    """Extract title from DefaultTitleBar(title="...") in source code."""
    try:
        content = source_path.read_text(encoding="utf-8")
        match = re.search(r'DefaultTitleBar\(.*title=["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    except Exception:
        pass

    # Fallback to readable filename
    name = source_path.stem.replace("_", " ").title()
    return name


def apply_window_frame(image_path: Path, title: str):
    """Add a macOS-like window frame and shadow to the image using Skia."""
    image = skia.Image.open(str(image_path))
    if image is None:
        print(f"Warning: Could not open {image_path} for framing")
        return

    content_width = image.width()
    content_height = image.height()

    # Window Style Config
    title_bar_height = 28
    shadow_radius = 24
    shadow_offset_y = 12
    corner_radius = 10
    padding = shadow_radius  # Space for shadow

    # Colors (macOS-like dark title bar)
    title_bar_bg_top = skia.Color(52, 52, 54, 255)
    title_bar_bg_bottom = skia.Color(42, 42, 44, 255)
    title_text = skia.Color(242, 242, 247, 235)
    title_bar_border = skia.Color(242, 242, 247, 70)
    body_border = skia.Color(60, 60, 67, 60)
    window_outer_border = skia.Color(0, 0, 0, 60)
    window_inner_highlight = skia.Color(255, 255, 255, 18)

    # Total dimensions
    total_width = content_width + padding * 2
    total_height = content_height + title_bar_height + padding * 2

    surface = skia.Surface(total_width, total_height)
    canvas = surface.getCanvas()

    # Clear transparent
    canvas.clear(skia.Color4f(0, 0, 0, 0))

    # Defines
    window_rect = skia.Rect.MakeXYWH(padding, padding, content_width, content_height + title_bar_height)

    # 1. Draw Shadow (two-layer, closer to macOS)
    shadow_rect_far = skia.Rect.MakeXYWH(
        padding,
        padding + shadow_offset_y * 0.55,
        content_width,
        content_height + title_bar_height,
    )
    shadow_paint_far = skia.Paint(
        Color=skia.Color(0, 0, 0, 28),
        AntiAlias=True,
    )
    shadow_paint_far.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow_radius / 1.2))
    canvas.drawRRect(
        skia.RRect.MakeRectXY(shadow_rect_far, corner_radius, corner_radius),
        shadow_paint_far,
    )

    shadow_rect_near = skia.Rect.MakeXYWH(
        padding,
        padding + shadow_offset_y * 0.20,
        content_width,
        content_height + title_bar_height,
    )
    shadow_paint_near = skia.Paint(
        Color=skia.Color(0, 0, 0, 52),
        AntiAlias=True,
    )
    shadow_paint_near.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow_radius / 4.0))
    canvas.drawRRect(
        skia.RRect.MakeRectXY(shadow_rect_near, corner_radius, corner_radius),
        shadow_paint_near,
    )

    # 2. Draw Window Background (White)
    bg_paint = skia.Paint(
        Color=skia.Color(255, 255, 255, 255),
        AntiAlias=True,
    )
    rrect = skia.RRect.MakeRectXY(window_rect, corner_radius, corner_radius)
    canvas.drawRRect(rrect, bg_paint)

    # Window border (outer + subtle inner highlight)
    outer_border_paint = skia.Paint(Color=window_outer_border, StrokeWidth=1, AntiAlias=True)
    outer_border_paint.setStyle(skia.Paint.kStroke_Style)
    canvas.drawRRect(rrect, outer_border_paint)

    inner_rect = skia.Rect.MakeXYWH(
        padding + 0.5,
        padding + 0.5,
        content_width - 1,
        content_height + title_bar_height - 1,
    )
    inner_rrect = skia.RRect.MakeRectXY(inner_rect, corner_radius - 0.5, corner_radius - 0.5)
    inner_border_paint = skia.Paint(Color=window_inner_highlight, StrokeWidth=1, AntiAlias=True)
    inner_border_paint.setStyle(skia.Paint.kStroke_Style)
    canvas.drawRRect(inner_rrect, inner_border_paint)

    # 3. Draw Title Bar Background
    canvas.save()
    canvas.clipRRect(rrect, True)

    title_bar_rect = skia.Rect.MakeXYWH(padding, padding, content_width, title_bar_height)
    header_paint = skia.Paint(AntiAlias=True)
    header_paint.setShader(
        skia.GradientShader.MakeLinear(
            [
                skia.Point(padding, padding),
                skia.Point(padding, padding + title_bar_height),
            ],
            [title_bar_bg_top, title_bar_bg_bottom],
            None,
            skia.TileMode.kClamp,
        )
    )
    canvas.drawRect(title_bar_rect, header_paint)

    # Title bar border (including separator line)
    title_border_paint = skia.Paint(Color=title_bar_border, StrokeWidth=1, AntiAlias=True)
    title_border_paint.setStyle(skia.Paint.kStroke_Style)
    canvas.drawRect(title_bar_rect, title_border_paint)
    canvas.drawLine(
        padding,
        padding + title_bar_height,
        padding + content_width,
        padding + title_bar_height,
        title_border_paint,
    )

    # 4. Draw Traffic Lights
    button_y = padding + title_bar_height / 2
    start_x = padding + 15
    gap = 18
    colors = [
        skia.Color(255, 95, 87),
        skia.Color(255, 189, 46),
        skia.Color(110, 110, 115),  # Disabled green
    ]
    border_colors = [
        skia.Color(224, 72, 62),
        skia.Color(224, 169, 41),
        skia.Color(84, 84, 88),
    ]

    for i, color in enumerate(colors):
        # Fill
        button_paint = skia.Paint(Color=color, AntiAlias=True)
        cx = start_x + i * gap
        canvas.drawCircle(cx, button_y, 5.5, button_paint)

        # Border
        stroke_paint = skia.Paint(
            Color=border_colors[i], AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=0.5
        )
        canvas.drawCircle(cx, button_y, 5.5, stroke_paint)

    # 5. Draw Title Text
    title_typeface = skia.Typeface.MakeFromName("SF Pro Text", skia.FontStyle.Normal())
    font = skia.Font(title_typeface, 12)
    text_paint = skia.Paint(Color=title_text, AntiAlias=True)
    text_width = font.measureText(title)
    text_x = padding + (content_width - text_width) / 2
    text_y = padding + title_bar_height / 2 + 4

    blob = skia.TextBlob.MakeFromText(title, font)
    if blob:
        canvas.drawTextBlob(blob, text_x, text_y, text_paint)

    canvas.restore()  # Unclip

    # 6. Draw Content Image (clip bottom corners)
    body_x = padding
    body_y = padding + title_bar_height
    body_w = content_width
    body_h = content_height
    r = float(corner_radius)
    x0 = float(body_x)
    y0 = float(body_y)
    x1 = float(body_x + body_w)
    y1 = float(body_y + body_h)

    body_clip_path = skia.Path()
    body_clip_path.moveTo(x0, y0)
    body_clip_path.lineTo(x1, y0)
    body_clip_path.lineTo(x1, y1 - r)
    body_clip_path.quadTo(x1, y1, x1 - r, y1)
    body_clip_path.lineTo(x0 + r, y1)
    body_clip_path.quadTo(x0, y1, x0, y1 - r)
    body_clip_path.close()

    canvas.save()
    canvas.clipPath(body_clip_path, True)
    canvas.drawImage(image, body_x, body_y)
    canvas.restore()

    # 7. Body border (bottom corners rounded like the window)
    body_border_paint = skia.Paint(Color=body_border, StrokeWidth=1, AntiAlias=True)
    body_border_paint.setStyle(skia.Paint.kStroke_Style)

    body_path = skia.Path()
    y0 = float(body_y) + 0.5
    body_path.moveTo(x0, y0)
    body_path.lineTo(x0, y1 - r)
    body_path.quadTo(x0, y1, x0 + r, y1)
    body_path.lineTo(x1 - r, y1)
    body_path.quadTo(x1, y1, x1, y1 - r)
    body_path.lineTo(x1, y0)
    canvas.drawPath(body_path, body_border_paint)

    # Overwrite original
    image = surface.makeImageSnapshot()
    image.save(str(image_path), skia.kPNG)


def render_all():
    failures = []
    for src, out_name in SAMPLES:
        src_path = ROOT / src
        out_path = ASSETS_DIR / out_name
        print(f"Rendering {src} -> {out_path}")
        try:
            mod = load_module_from_path(src_path)
            if hasattr(mod, "main"):
                # 1. Render raw content
                mod.main(str(out_path))

                # 2. Extract title
                title = extract_title(src_path)

                # 3. Apply window frame
                apply_window_frame(out_path, title)
                print(f"Framed {out_path} with title '{title}'")
            else:
                raise RuntimeError("module has no main()")
        except Exception as e:
            print(f"Failed {src}: {e}")
            failures.append((src, str(e)))
    if failures:
        print("Some renders failed:")
        for s, err in failures:
            print(s, err)
    else:
        print("All renders completed.")


if __name__ == "__main__":
    render_all()
