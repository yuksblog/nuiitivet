#!/usr/bin/env python3
"""
Quick test: render an Icon to PNG using the library's Icon widget.
Writes output to out/icon_render.png
"""
import sys
import os
import types
import importlib.util
import skia

# Avoid executing package __init__.py (which pulls heavy deps) by
# inserting lightweight package modules into sys.modules and loading
# the `icon.py` source directly. This preserves relative imports used
# in `icon.py` while preventing top-level initialization of the whole
# package.
pkg_root = os.path.abspath("src/nuiitivet")
sys.modules["nuiitivet"] = types.ModuleType("nuiitivet")
sys.modules["nuiitivet"].__path__ = [pkg_root]
sys.modules["nuiitivet.widgets"] = types.ModuleType("nuiitivet.widgets")
sys.modules["nuiitivet.widgets"].__path__ = [os.path.join(pkg_root, "widgets")]
sys.modules["nuiitivet.runtime"] = types.ModuleType("nuiitivet.runtime")
sys.modules["nuiitivet.runtime"].__path__ = [os.path.join(pkg_root, "runtime")]

icon_path = os.path.join(pkg_root, "widgets", "icon.py")
spec = importlib.util.spec_from_file_location("nuiitivet.widgets.icon", icon_path)
mod = importlib.util.module_from_spec(spec)
sys.modules["nuiitivet.widgets.icon"] = mod
try:
    spec.loader.exec_module(mod)
except Exception as e:
    print("Failed to load icon module:", e)
    raise

Icon = getattr(mod, "Icon")

W = H = 128
surface = skia.Surface(W, H)
canvas = surface.getCanvas()
# white background
canvas.clear(skia.ColorWHITE)

# create an icon (ligature name). size is font size in px
icon = Icon("home", size=80)
# paint into full rect
icon.paint(canvas, 0, 0, W, H)

img = surface.makeImageSnapshot()
data = img.encodeToData()
if data is None:
    print("Failed to encode image")
    sys.exit(2)

out_dir = "out"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "icon_render.png")
buf = None
if hasattr(data, "toBytes"):
    buf = data.toBytes()
elif hasattr(data, "bytes"):
    buf = data.bytes()
elif hasattr(data, "asBytes"):
    buf = data.asBytes()
else:
    # fallback: try to convert to bytes
    try:
        buf = bytes(data)
    except Exception:
        buf = None

if buf is None:
    print("Failed to extract bytes from skia.Data")
    sys.exit(2)

with open(out_path, "wb") as f:
    f.write(buf)

print("Wrote:", out_path)
