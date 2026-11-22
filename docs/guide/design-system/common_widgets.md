# Common Widgets

Common widgets are the widgets that are not Material components. They show
a picture, pixels or a chart, and take no Material style. Write each one as
`nv.<Name>`, like a Material widget: `nv.Image`. Layout widgets such as
`Column` are in [Layout](../layout/index.md).

| You have | Widget |
| --- | --- |
| A PNG or a JPEG, as bytes | [`Image`](#image) |
| Pixels you compute, as `bytes` or a numpy array | [`RasterSurface`](#rastersurface) |
| A matplotlib figure | [`MatplotlibFigure`](#matplotlibfigure) |

## Image

`Image` shows a PNG or JPEG from bytes in memory, scaled to the widget's
size. `fit` picks how: `"contain"`, the default, `"cover"`, `"fill"` or
`"none"`. Without `width` and `height` the widget takes the picture's size.
[API Reference](../../api/widgets.md#nuiitivet.widgets.Image)

```python
from pathlib import Path

import nuiitivet.material as nv

nv.Image(Path("photo.png").read_bytes(), width=260, height=200)
```

![Image](../../assets/material_widgets_image.png)

## RasterSurface

`RasterSurface` shows pixels you draw. You give it a `State` and a function.
The function takes the `State`'s value and the widget's size in device
pixels, and returns the RGBA pixels for that size. It runs again when either
changes. [API Reference](../../api/widgets.md#nuiitivet.widgets.RasterSurface)

Pick the call by how long the drawing takes:

| The drawing | Write |
| --- | --- |
| Takes a few milliseconds | [`draw`](#draw-in-the-frame) |
| Takes longer, inside OpenCV, numpy or I/O | [`draw_in_thread`](#draw-on-a-thread) |
| Takes longer, in pure Python or in a browser | [`draw` with a worker function](#draw-in-a-worker-function) |

### Draw in the frame

`RasterSurface.draw(state, function)` makes the widget. The window draws
nothing else until the function returns.

```python
import nuiitivet.material as nv

_FILL = bytes((101, 85, 143, 255))  # RGBA, alpha not premultiplied
_REST = bytes((232, 222, 248, 255))
_TICK = bytes((255, 255, 255, 255))


def draw_meter(level: float, width_px: int, height_px: int) -> bytes:
    filled = int(round(width_px * max(0.0, min(1.0, level))))
    row = bytearray(_FILL * filled + _REST * (width_px - filled))
    # A one-pixel tick every 16 device pixels of the filled part.
    for x in range(16, filled, 16):
        row[x * 4 : x * 4 + 4] = _TICK
    return bytes(row) * height_px


level = nv.State(0.6)

nv.RasterSurface.draw(level, draw_meter, width="wt", height=48)
```

![RasterSurface](../../assets/charts_raster_surface.png)

On a 2x display a 200x100 widget calls `draw_meter(0.6, 400, 200)`.

For a library that draws into a Pillow image, return
`image.resize((width_px, height_px)).convert("RGBA").tobytes()`.

The complete app is [`samples/charts/raster_surface.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/charts/raster_surface.py).

### Draw on a thread

A drawing that takes longer than a frame holds the window still while it
runs: a slider beside it stops following the pointer. `draw_in_thread` takes
the same arguments and calls the function on a thread.

```python
import numpy as np


def draw_ripples(wavelength: float, width_px: int, height_px: int) -> np.ndarray:
    pixels = np.empty((height_px, width_px, 4), dtype=np.uint8)
    ...  # tens of milliseconds of numpy fill it
    return pixels


wavelength = nv.State(0.02)

nv.RasterSurface.draw_in_thread(wavelength, draw_ripples, width="wt", height="wt")  # on a thread
```

The slider follows the pointer while the picture catches up. During a fast
drag the picture skips values and lands on the newest. The surface is empty
until the first call returns. A PNG from `App.render_to_png` shows it empty.

!!! warning "Read only the arguments"
    The function reads no widget and no other `State`. Put what it needs
    into the `State` you pass. [`combine`](../state-management/operators.md) makes one `State` of several.

A drawing in pure Python still makes the slider stutter. Mark it as a
[worker function](#draw-in-a-worker-function). In a browser the surface stays empty, and the log says why.

The complete app is [`samples/charts/raster_surface_thread.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/charts/raster_surface_thread.py).

### Draw in a worker function

Mark the drawing `@nv.worker(process=True)` and pass it to `draw`. It runs
in a child process on the desktop and on a Web Worker in a browser, and the
window keeps moving while it draws. [Worker and Server Functions](../web/worker_and_server_functions.md) has the
rules for such a function.

The function sits at the top level of a module, with every parameter and the
return annotated.

```python
# jobs.py
import nuiitivet.material as nv


@nv.worker(process=True)  # pure Python on a core of its own
def draw_plasma(phase: float, width_px: int, height_px: int) -> bytes:
    ...  # a pixel at a time, in pure Python
```

The app imports it and passes it to `draw`.

```python
# app.py
import nuiitivet.material as nv
from jobs import draw_plasma

phase = nv.State(0.0)

nv.RasterSurface.draw(phase, draw_plasma, width="wt", height=160)
```

During a fast drag the picture skips values and lands on the newest. The
surface is empty until the first call returns. The `State`'s value and the
returned pixels must be of a type a worker function carries: a number, a
string, `bytes`, a dataclass of these. Return `bytes`, not a numpy array.

The complete app is [`samples/charts/raster_surface_worker/`](https://github.com/yuksblog/nuiitivet/tree/main/samples/charts/raster_surface_worker).

## MatplotlibFigure

`MatplotlibFigure` shows a matplotlib `Figure` in the app's colors. The
figure's `mpl_connect` handlers run on clicks and keys. [A matplotlib figure](../charts/matplotlib.md)
is its guide.
