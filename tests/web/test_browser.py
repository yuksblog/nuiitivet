"""A sample painted by headless Chrome, against the same sample painted on the desktop.

The page is the built site, Pyodide and CanvasKit included, served by the
framework's own server. The two renders never match pixel for pixel: the
browser draws with CanvasKit and the page's fonts, the desktop with
skia-python and the system's. They are compared by the mean colour of 16 px
blocks, which a font swap leaves alone and a page that painted nothing, or
laid out differently, moves far past the threshold.

Needs the ``browser`` dependency group and a Chromium: ``uv sync --group browser``
and ``uv run playwright install chromium``, or an installed Chrome. Without
them the test skips, unless ``NUIITIVET_BROWSER_TESTS=required`` says CI is
running it.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
from pathlib import Path
from typing import Iterator

import pytest
import skia

from nuiitivet.web.server import make_server, site

APP = Path(__file__).resolve().parents[2] / "samples" / "web" / "hello" / "app.py"
WIDTH, HEIGHT = 320, 200
BLOCK = 16
# Measured: the two renders differ in 0.4 % of blocks; a blank page in 9 %.
MAX_DIFFERING_BLOCKS = 0.03

_REQUIRED = os.environ.get("NUIITIVET_BROWSER_TESTS") == "required"
if _REQUIRED:
    from playwright import sync_api as playwright_api
else:
    playwright_api = pytest.importorskip("playwright.sync_api", reason="the browser dependency group is not installed")


@pytest.fixture(scope="module")
def page_url() -> Iterator[str]:
    """The sample's built site, served on a free port for the whole module."""
    httpd = make_server(site(APP, bundle_runtime=True), 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()


def _launch(playwright: playwright_api.Playwright) -> playwright_api.Browser:
    """Playwright's Chromium, or the installed Chrome; skip when there is neither."""
    last: Exception | None = None
    for channel in (None, "chrome"):
        try:
            return playwright.chromium.launch(channel=channel) if channel else playwright.chromium.launch()
        except playwright_api.Error as error:
            last = error
    assert last is not None
    if _REQUIRED:
        raise last
    pytest.skip(f"no Chromium to drive: {last}")


def _browser_render(url: str, out: Path) -> str:
    with playwright_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_function("document.body.dataset.state !== undefined", timeout=180_000)
            state = page.evaluate("document.body.dataset.state")
            # One frame after the app started, so what the first paint drew is on the canvas.
            page.wait_for_timeout(500)
            page.screenshot(path=str(out))
        finally:
            browser.close()
    assert not errors, errors
    return state


def _desktop_render(out: Path) -> None:
    import nuiitivet.material as nv

    spec = importlib.util.spec_from_file_location("_hello_sample", APP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        nv.App(nv.Window(content=module.Counter, width=WIDTH, height=HEIGHT)).render_to_png(str(out))
    finally:
        sys.modules.pop(spec.name, None)


def _block_means(path: Path) -> list[tuple[float, float, float]]:
    image = skia.Image.open(str(path))
    assert (image.width(), image.height()) == (WIDTH, HEIGHT), (image.width(), image.height())
    data = image.tobytes()
    stride = len(data) // (WIDTH * HEIGHT)
    means = []
    for top in range(0, HEIGHT - BLOCK + 1, BLOCK):
        for left in range(0, WIDTH - BLOCK + 1, BLOCK):
            sums = [0, 0, 0]
            for y in range(top, top + BLOCK):
                row = (y * WIDTH + left) * stride
                for x in range(BLOCK):
                    i = row + x * stride
                    sums[0] += data[i]
                    sums[1] += data[i + 1]
                    sums[2] += data[i + 2]
            count = BLOCK * BLOCK
            means.append((sums[0] / count, sums[1] / count, sums[2] / count))
    return means


def _differing_blocks(a: list[tuple[float, float, float]], b: list[tuple[float, float, float]]) -> float:
    differing = sum(1 for p, q in zip(a, b) if max(abs(x - y) for x, y in zip(p, q)) > 16)
    return differing / len(a)


def test_the_browser_paints_the_sample_as_the_desktop_does(page_url: str, tmp_path: Path) -> None:
    state = _browser_render(page_url, tmp_path / "browser.png")
    assert state == "running"

    _desktop_render(tmp_path / "desktop.png")

    differing = _differing_blocks(_block_means(tmp_path / "desktop.png"), _block_means(tmp_path / "browser.png"))
    assert differing <= MAX_DIFFERING_BLOCKS, f"{differing:.1%} of {BLOCK} px blocks differ"
