"""Benchmark what showing a camera-sized picture in ``Image`` costs, to design the ``Raster`` value.

The constructed case is a 4000x3000 picture drawn into a 2560x1440 rect, the
size of a full-screen window on a 2x display.

Six tables:

* ``first paint``: an ``Image`` painted once, from JPEG bytes and from a
  ``Raster`` built beforehand, on the CPU and on the GPU.

* ``sampling, CPU``: one ``drawImageRect`` into a raster surface, per sampling,
  for a full window (2560 wide) and a thumbnail (400 wide). ``first`` is a
  picture never drawn before, so it includes building the mipmaps a sampling
  asks for; ``later`` draws it again. A paint cache replay records the draw in
  a picture, and replaying the picture scales again: the ``replay`` column.
* ``sampling quality``: the error of each sampling against an area-averaged
  downscale (Pillow ``BOX``) of a zone plate, a pattern that shows aliasing.
* ``sampling, GPU``: the same draw into a GL render target, waited for with
  ``flushAndSubmit(GrSyncCpu.kYes)``. ``new`` draws a picture never drawn
  before, so it includes the texture upload; ``same`` draws one already on the
  GPU.
* ``live frames, GPU``: a new frame per draw for camera sizes. ``build`` is
  ``make_raster_image``, which the app runs on its own thread; the other
  columns are the UI thread's upload and draw.
* ``decode on a worker``: an encoded picture decoded on a thread while the UI
  thread spins; ``stalled`` is the longest gap between two of its iterations.

Run:  python scripts/investigation/bench_image_raster.py [--repeats N]
"""

from __future__ import annotations

import argparse
import io
import statistics
import threading
import time
from typing import Any, Callable

import numpy as np
import skia
from PIL import Image as PILImage

from nuiitivet.rendering.raster import Raster
from nuiitivet.rendering.skia import make_raster_image
from nuiitivet.widgets.image import Image

SRC_W, SRC_H = 4000, 3000
DST_W, DST_H = 2560, 1440


def _photo() -> np.ndarray:
    """Smooth gradients with noise: compresses like a photo, unlike pure noise."""
    rng = np.random.default_rng(0)
    ys, xs = np.mgrid[0:SRC_H, 0:SRC_W].astype(np.float32)
    rgba = np.empty((SRC_H, SRC_W, 4), dtype=np.uint8)
    rgba[..., 0] = (127 + 120 * np.sin(xs / 300.0)).astype(np.uint8)
    rgba[..., 1] = (127 + 120 * np.cos(ys / 211.0)).astype(np.uint8)
    rgba[..., 2] = ((xs + ys) / (SRC_W + SRC_H) * 255).astype(np.uint8)
    rgba[..., :3] = np.clip(rgba[..., :3].astype(np.int16) + rng.integers(-12, 12, (SRC_H, SRC_W, 3)), 0, 255)
    rgba[..., 3] = 255
    return rgba


def _zone_plate() -> np.ndarray:
    ys, xs = np.mgrid[0:SRC_H, 0:SRC_W].astype(np.float64)
    r2 = (xs - SRC_W / 2) ** 2 + (ys - SRC_H / 2) ** 2
    gray = (127.5 + 127.5 * np.cos(np.pi * r2 / (2.0 * SRC_W))).astype(np.uint8)
    rgba = np.empty((SRC_H, SRC_W, 4), dtype=np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = gray
    rgba[..., 3] = 255
    return rgba


SIZES = ((DST_W, DST_H), (400, 300))


def _samplings() -> dict[str, Any]:
    """Each sampling. Skia builds the mipmaps a sampling asks for at the image's first draw."""
    linear = skia.FilterMode.kLinear
    return {
        "nearest (today)": skia.SamplingOptions(),
        "linear": skia.SamplingOptions(linear),
        "linear, nearest mip": skia.SamplingOptions(linear, skia.MipmapMode.kNearest),
        "linear, linear mip": skia.SamplingOptions(linear, skia.MipmapMode.kLinear),
        "cubic Mitchell": skia.SamplingOptions(skia.CubicResampler.Mitchell()),
    }


def _ms(fn: Callable[[], Any]) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


def _draw(canvas: Any, image: Any, sampling: Any, dst: tuple[int, int]) -> None:
    # The strict constraint, the default, turns mipmaps off.
    canvas.drawImageRect(
        image,
        skia.Rect.MakeWH(SRC_W, SRC_H),
        skia.Rect.MakeWH(*dst),
        sampling,
        None,
        skia.Canvas.kFast_SrcRectConstraint,
    )


def _header(columns: list[str]) -> str:
    return f"  {'sampling':20}" + "".join(f" {column:>9}" for column in columns)


def sampling_cpu(rgba: np.ndarray, repeats: int) -> None:
    print(f"sampling, CPU: {SRC_W}x{SRC_H} into each size, ms, median of {repeats}")
    columns = [f"{label} {w}" for w, _h in SIZES for label in ("first", "later", "replay")]
    print(_header(columns))
    for name, sampling in _samplings().items():
        cells: list[float] = []
        for size in SIZES:
            surface = skia.Surface(*size)
            canvas = surface.getCanvas()

            def frame(image: Any) -> float:
                return _ms(lambda: (_draw(canvas, image, sampling, size), surface.flushAndSubmit()))

            firsts = [frame(make_raster_image(rgba, SRC_W, SRC_H)) for _ in range(repeats)]
            image = make_raster_image(rgba, SRC_W, SRC_H)
            frame(image)
            later = [frame(image) for _ in range(repeats)]
            recorder = skia.PictureRecorder()
            _draw(recorder.beginRecording(skia.Rect.MakeWH(*size)), image, sampling, size)
            picture = recorder.finishRecordingAsPicture()
            replay = [_ms(lambda: (canvas.drawPicture(picture), surface.flushAndSubmit())) for _ in range(repeats)]
            cells += [statistics.median(firsts), statistics.median(later), statistics.median(replay)]
        print(f"  {name:20}" + "".join(f" {cell:9.1f}" for cell in cells))


def sampling_quality() -> None:
    plate = _zone_plate()
    print("sampling quality: zone plate, RMSE against an area-averaged downscale (0-255, lower is closer)")
    print(_header([f"{w}x{h}" for w, h in SIZES]))
    references = [
        np.asarray(PILImage.fromarray(plate[..., 0]).resize(size, PILImage.Resampling.BOX), dtype=np.float64)
        for size in SIZES
    ]
    for name, sampling in _samplings().items():
        image = make_raster_image(plate, SRC_W, SRC_H)
        cells = []
        for size, reference in zip(SIZES, references):
            surface = skia.Surface(*size)
            canvas = surface.getCanvas()
            canvas.clear(skia.ColorBLACK)
            _draw(canvas, image, sampling, size)
            got = surface.makeImageSnapshot().toarray()[..., 0].astype(np.float64)
            cells.append(float(np.sqrt(np.mean((got - reference) ** 2))))
        print(f"  {name:20}" + "".join(f" {cell:9.1f}" for cell in cells))


def sampling_gpu(rgba: np.ndarray, repeats: int) -> None:
    import pyglet

    window = pyglet.window.Window(64, 64, visible=False)
    window.switch_to()
    context = skia.GrDirectContext.MakeGL()
    print(f"sampling, GPU (GL): {SRC_W}x{SRC_H} into each size, ms, median of {repeats}")
    print(_header([f"{label} {w}" for w, _h in SIZES for label in ("new", "same")]))
    surfaces = {
        size: skia.Surface.MakeRenderTarget(context, skia.Budgeted.kNo, skia.ImageInfo.MakeN32Premul(*size))
        for size in SIZES
    }

    def frame(image: Any, sampling: Any, size: tuple[int, int]) -> float:
        canvas = surfaces[size].getCanvas()
        return _ms(lambda: (_draw(canvas, image, sampling, size), context.flushAndSubmit(skia.GrSyncCpu.kYes)))

    # Warm the GL pipeline so the first row does not carry shader compilation.
    for sampling in _samplings().values():
        for size in SIZES:
            frame(make_raster_image(rgba, SRC_W, SRC_H), sampling, size)
    for name, sampling in _samplings().items():
        cells: list[float] = []
        for size in SIZES:
            new = [frame(make_raster_image(rgba, SRC_W, SRC_H), sampling, size) for _ in range(repeats)]
            image = make_raster_image(rgba, SRC_W, SRC_H)
            frame(image, sampling, size)
            same = [frame(image, sampling, size) for _ in range(repeats)]
            cells += [statistics.median(new), statistics.median(same)]
        print(f"  {name:20}" + "".join(f" {cell:9.1f}" for cell in cells))
    print()
    live_frames_gpu(context, surfaces[(DST_W, DST_H)], repeats)
    print()
    target = surfaces[(DST_W, DST_H)]
    first_paint("GPU (GL)", target.getCanvas(), lambda: context.flushAndSubmit(skia.GrSyncCpu.kYes), rgba, repeats)
    window.close()


def live_frames_gpu(context: Any, surface: Any, repeats: int) -> None:
    """A new frame each draw, per camera size: what a live preview costs the UI thread."""
    canvas = surface.getCanvas()
    rng = np.random.default_rng(0)
    print(f"live frames, GPU (GL): a new frame per draw into {DST_W}x{DST_H}, ms, median of {repeats}")
    print(f"  {'frame':20} {'build':>9} {'linear':>9} {'mip':>9}")
    samplings = _samplings()
    for width, height in ((SRC_W, SRC_H), (3840, 2160), (DST_W, DST_H), (1920, 1080), (1280, 720)):
        pixels = rng.integers(0, 255, (height, width, 4), dtype=np.uint8)

        def frame(sampling: Any) -> float:
            image = make_raster_image(pixels, width, height)
            src, dst = skia.Rect.MakeWH(width, height), skia.Rect.MakeWH(DST_W, DST_H)
            constraint = skia.Canvas.kFast_SrcRectConstraint
            return _ms(
                lambda: (
                    canvas.drawImageRect(image, src, dst, sampling, None, constraint),
                    context.flushAndSubmit(skia.GrSyncCpu.kYes),
                )
            )

        built = statistics.median(_ms(lambda: make_raster_image(pixels, width, height)) for _ in range(repeats))
        cells = [built]
        for name in ("linear", "linear, linear mip"):
            frame(samplings[name])
            cells.append(statistics.median(frame(samplings[name]) for _ in range(repeats)))
        print(f"  {f'{width}x{height}':20}" + "".join(f" {cell:9.1f}" for cell in cells))


def first_paint(label: str, canvas: Any, flush: Callable[[], Any], rgba: np.ndarray, repeats: int) -> None:
    """The first paint of an ``Image``: from JPEG bytes, and from a ``Raster`` the app built beforehand."""
    out = io.BytesIO()
    PILImage.fromarray(rgba[..., :3]).save(out, format="JPEG", quality=90)
    jpeg = out.getvalue()

    def paint(widget: Image) -> float:
        return _ms(lambda: (widget.paint(canvas, 0, 0, DST_W, DST_H), flush()))

    from_bytes = [paint(Image(jpeg)) for _ in range(repeats)]
    from_raster = [paint(Image(Raster.rgba(rgba, SRC_W, SRC_H))) for _ in range(repeats)]
    print(f"first paint of Image, {label}: {SRC_W}x{SRC_H} into {DST_W}x{DST_H}, ms, median of {repeats}")
    print(f"  {'JPEG bytes, decoded in the paint':44} {statistics.median(from_bytes):8.1f}")
    print(f"  {'Raster, built before the paint':44} {statistics.median(from_raster):8.1f}")


def _stall(work: Callable[[], Any]) -> tuple[float, float]:
    """The worker's time and the UI thread's longest gap while it ran, both in ms."""
    done = threading.Event()
    took: list[float] = []

    def run() -> None:
        took.append(_ms(work))
        done.set()

    thread = threading.Thread(target=run)
    longest = 0.0
    last = time.perf_counter()
    thread.start()
    while not done.is_set():
        now = time.perf_counter()
        longest = max(longest, now - last)
        last = now
    thread.join()
    return took[0], longest * 1000


def decode_on_worker(rgba: np.ndarray, repeats: int) -> None:
    encoded: dict[str, bytes] = {}
    for fmt, options in (("JPEG", {"quality": 90}), ("PNG", {"compress_level": 6})):
        out = io.BytesIO()
        PILImage.fromarray(rgba[..., :3]).save(out, format=fmt, **options)
        encoded[fmt] = out.getvalue()

    def skia_decode(data: bytes) -> Callable[[], Any]:
        return lambda: skia.Image.MakeFromEncoded(data).makeRasterImage()

    def pillow_decode(data: bytes) -> Callable[[], Any]:
        def run() -> Any:
            picture = PILImage.open(io.BytesIO(data)).convert("RGBA")
            return make_raster_image(np.asarray(picture), picture.width, picture.height)

        return run

    print(f"decode on a worker: {SRC_W}x{SRC_H}, ms, median of {repeats}")
    print(f"  {'decoder':44} {'worker':>8} {'stalled':>8}")
    for fmt, data in encoded.items():
        for name, make in (("skia MakeFromEncoded", skia_decode), ("Pillow + make_raster_image", pillow_decode)):
            runs = [_stall(make(data)) for _ in range(repeats)]
            worker = statistics.median(run[0] for run in runs)
            stalled = statistics.median(run[1] for run in runs)
            label = f"{fmt} {len(data) / 1e6:.1f} MB, {name}"
            print(f"  {label:44} {worker:8.1f} {stalled:8.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--no-gpu", action="store_true", help="skip the GL table")
    args = parser.parse_args()

    rgba = _photo()
    surface = skia.Surface(DST_W, DST_H)
    first_paint("CPU", surface.getCanvas(), surface.flushAndSubmit, rgba, args.repeats)
    print()
    sampling_cpu(rgba, args.repeats)
    print()
    sampling_quality()
    print()
    if not args.no_gpu:
        sampling_gpu(rgba, args.repeats)
        print()
    decode_on_worker(rgba, args.repeats)


if __name__ == "__main__":
    main()
