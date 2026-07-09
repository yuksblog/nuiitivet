# Renderer Selection

`App.run()` renders the live window with Skia. By default it uses the GPU
(OpenGL) and falls back to software (raster) rendering when the GPU is
unavailable. You can control this with the `renderer` argument.

```python
import nuiitivet.material as nv

app = nv.App(content=MyScreen())

app.run(renderer="auto")  # default
app.run(renderer="gpu")   # require the GPU
app.run(renderer="cpu")   # always render in software
```

## Modes

| Mode | Behavior |
|---|---|
| `"auto"` (default) | Try the GPU, then **silently** fall back to software rendering if it cannot be initialized. Best for most apps. |
| `"gpu"` | **Require** the GPU. If the GPU backend cannot be initialized — or a frame fails to render on the GPU — a `RuntimeError` is raised. Use this when you want a missing/broken GPU to surface loudly (e.g. remote deployment sanity checks). |
| `"cpu"` | Always render in software (raster); the GPU is never touched. Use this on GPU-less machines, with software OpenGL (e.g. llvmpipe), or in remote sessions. |

The `renderer` value is typed as
[`RendererMode`](../../../src/nuiitivet/runtime/renderer.py) —
`Literal["auto", "gpu", "cpu"]`.

## When to use `"cpu"`

Choose `"cpu"` when a GPU path is unreliable but a **display** is still present:

- GPU-less machines.
- Software OpenGL (Mesa `llvmpipe`, `softpipe`).
- Remote desktops / forwarded sessions where GPU acceleration is flaky.

`"auto"` already falls back to software when the GPU cannot be initialized, so
`"cpu"` mainly matters when the GPU initializes but renders incorrectly or too
slowly — a case that cannot be detected automatically.

## Headless environments

`App.run()` always needs a display: it opens an OS window. **Truly headless
environments (no display at all) cannot use `run()` in any mode** — window
creation fails and a clear error is logged. Nuiitivet is a GUI framework, so
running without a display is not supported.

## Logging

Renderer selection emits standard `logging` records under the
`nuiitivet.backends.pyglet.runner` logger:

- `"auto"`: a one-time **warning** when the GPU is unavailable and software
  rendering is used instead.
- `"gpu"`: an **error** before the `RuntimeError` is raised.
- Window creation failure: an **error** with the underlying exception,
  regardless of mode.
