"""Samples driven in headless Chrome: one painted against the desktop, two calling a worker and a server function.

The page is the built site, Pyodide and CanvasKit included, served by the
framework's own server. The two renders never match pixel for pixel: the
browser draws with CanvasKit and the page's fonts, the desktop with
skia-python and the system's. They are compared by the mean colour of 16 px
blocks, which a font swap leaves alone and a page that painted nothing, or
laid out differently, moves far past the threshold.

The worker sample is read through the page's Pyodide, and driven with the
mouse and the keyboard, so what the test sees is what the user sees.

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

from nuiitivet.web.server import load_server_functions, make_server, site

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


# -- worker functions ----------------------------------------------------------

WORKER_APP = APP.parent.parent / "worker_functions" / "app.py"
# What the sample's search finds for its default query, "word1".
WORD1_RESULT = "28 words within one edit of word1"

_IN_PAGE = """
from nuiitivet._interaction.perception import _coerce_display, find_targets
from nuiitivet.backends.web.runner import _app


def _widget(key):
    [widget] = find_targets(_app.main_window.root, key=key)
    return widget


def text_of(key):
    widget = _widget(key)
    for attr in ("label", "text", "title"):
        display = _coerce_display(getattr(widget, attr, None))
        if display is not None:
            return display
    return None


def center_of(key):
    x, y, w, h = _widget(key).global_layout_rect
    return [x + w / 2, y + h / 2]
"""


@pytest.fixture(scope="module")
def worker_page_url() -> Iterator[str]:
    """The worker sample's built site, served on a free port for the whole module."""
    httpd = make_server(site(WORKER_APP, bundle_runtime=True), 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()


class _Page:
    """Drives the running app through the page's Pyodide and Playwright's mouse and keyboard."""

    def __init__(self, page: playwright_api.Page) -> None:
        self.page = page
        page.evaluate("code => NV_PYODIDE.runPython(code)", _IN_PAGE)

    def text(self, key: str) -> str:
        return self.page.evaluate("code => NV_PYODIDE.runPython(code)", f"text_of({key!r})")

    def click(self, key: str) -> None:
        x, y = self.page.evaluate("code => NV_PYODIDE.runPython(code).toJs()", f"center_of({key!r})")
        self.page.mouse.click(x, y)

    def wait_for_text(self, key: str, expected: str, timeout: float = 60.0) -> None:
        self.page.wait_for_function(
            "([code, expected]) => NV_PYODIDE.runPython(code) === expected",
            arg=[f"text_of({key!r})", expected],
            timeout=timeout * 1000,
        )

    def wait_for_text_prefix(self, key: str, prefix: str, timeout: float = 60.0) -> None:
        self.page.wait_for_function(
            "([code, prefix]) => (NV_PYODIDE.runPython(code) ?? '').startsWith(prefix)",
            arg=[f"text_of({key!r})", prefix],
            timeout=timeout * 1000,
        )

    def set_query(self, value: str) -> None:
        self.click("query")
        self.page.keyboard.press("End")
        for _ in range(8):
            self.page.keyboard.press("Backspace")
        self.page.keyboard.type(value)


def test_a_worker_function_answers_reports_and_cancels_while_the_page_keeps_answering(worker_page_url: str) -> None:
    with playwright_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            page = browser.new_page(viewport={"width": 480, "height": 320}, device_scale_factor=1)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(worker_page_url)
            page.wait_for_function("document.body.dataset.state !== undefined", timeout=180_000)
            assert page.evaluate("document.body.dataset.state") == "running"
            app = _Page(page)

            # Progress while it runs, a click answered meanwhile, and a cancel.
            app.click("search")
            app.wait_for_text("status", "searching")
            app.click("click")
            app.wait_for_text("clicks", "1 clicks", timeout=5.0)
            assert app.text("status") == "searching"
            page.wait_for_function(
                "code => NV_PYODIDE.runPython(code) !== '0%'", arg="text_of('progress')", timeout=60_000
            )
            app.click("cancel")
            app.wait_for_text("status", "cancelled")

            # The result, from the replacement worker.
            app.click("search")
            app.wait_for_text("status", WORD1_RESULT)

            # A built-in exception, as itself.
            app.set_query("")
            app.click("search")
            app.wait_for_text("status", "type something to look for")

            # Any other exception, as RemoteError.
            app.set_query("secret")
            app.click("search")
            app.wait_for_text("status", "Rejected: not for you")
        finally:
            browser.close()
    assert not errors, errors


# -- server functions ----------------------------------------------------------

SERVER_APP = APP.parent.parent / "server_functions" / "app.py"


@pytest.fixture(scope="module")
def server_page_url() -> Iterator[str]:
    """The server sample's built site, served by the process that also answers its server function."""
    modules = load_server_functions(SERVER_APP.parent)
    httpd = make_server(site(SERVER_APP, bundle_runtime=True), 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()
    for name in modules:
        sys.modules.pop(name, None)
    sys.path.remove(str(SERVER_APP.parent.resolve()))


def test_a_server_function_in_a_plain_module_is_answered_by_the_server(server_page_url: str) -> None:
    with playwright_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            page = browser.new_page(viewport={"width": 480, "height": 320}, device_scale_factor=1)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(server_page_url)
            page.wait_for_function("document.body.dataset.state !== undefined", timeout=180_000)
            assert page.evaluate("document.body.dataset.state") == "running"
            app = _Page(page)

            # The module is in the page as written; the call still goes to the server.
            source = page.evaluate("code => NV_PYODIDE.runPython(code)", "open('/nuiitivet/app/jobs.py').read()")
            assert "@nv.server" in source
            app.click("search")
            app.wait_for_text("status", WORD1_RESULT)

            # Any other exception, as RemoteError, across the request.
            app.set_query("secret")
            app.click("search")
            app.wait_for_text("status", "Rejected: not for you")
        finally:
            browser.close()
    assert not errors, errors


# -- file dialogs ----------------------------------------------------------------

DIALOG_APP = APP.parents[2] / "window" / "file_dialogs.py"

_NO_GESTURE = """
import nuiitivet.material as nv


async def probe():
    try:
        await nv.FileDialog.open_file()
    except nv.FileDialogError:
        return "FileDialogError"
    return "no error"


await probe()
"""


@pytest.fixture(scope="module")
def dialog_page_url() -> Iterator[str]:
    """The file dialogs sample's built site, served on a free port for the whole module."""
    httpd = make_server(site(DIALOG_APP, bundle_runtime=True), 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    httpd.shutdown()
    httpd.server_close()


def _in_page(page: playwright_api.Page, code: str) -> object:
    return page.evaluate("code => NV_PYODIDE.runPython(code)", code)


def test_file_dialogs_in_a_browser_pick_cancel_and_download(dialog_page_url: str, tmp_path: Path) -> None:
    picked = tmp_path / "pic.png"
    picked.write_bytes(bytes(range(256)))
    folder = tmp_path / "photos"
    (folder / "2024").mkdir(parents=True)
    (folder / "notes.md").write_text("notes")
    (folder / "2024" / "a.png").write_bytes(b"a")
    with playwright_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            page = browser.new_page(viewport={"width": 640, "height": 240}, device_scale_factor=1)
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(dialog_page_url)
            page.wait_for_function("document.body.dataset.state !== undefined", timeout=180_000)
            assert page.evaluate("document.body.dataset.state") == "running"
            app = _Page(page)
            # The sample's heartbeat runs on the browser's clock.
            page.wait_for_function(
                "code => NV_PYODIDE.runPython(code) !== 'UI alive: 0'", arg="text_of('tick')", timeout=10_000
            )

            # Outside a click, the call raises instead of waiting for a picker that never opens.
            # Playwright evaluates with a user gesture, so the browser's own answer is stood in for.
            page.evaluate(
                "Object.defineProperty(navigator, 'userActivation', {value: {isActive: false}, configurable: true})"
            )
            assert page.evaluate("code => NV_PYODIDE.runPythonAsync(code)", _NO_GESTURE) == "FileDialogError"
            page.evaluate("delete navigator.userActivation")

            # One file: a path the app reads, holding what the user picked.
            with page.expect_file_chooser() as chooser_info:
                app.click("open")
            chooser = chooser_info.value
            assert not chooser.is_multiple()
            chooser.set_files(str(picked))
            app.wait_for_text_prefix("result", "open: ")
            shown = app.text("result").removeprefix("open: ")
            assert shown.endswith("/pic.png")
            assert bytes.fromhex(str(_in_page(page, f"open({shown!r}, 'rb').read().hex()"))) == picked.read_bytes()

            # Cancel.
            with page.expect_file_chooser() as chooser_info:
                app.click("open")
            chooser_info.value.set_files([])
            app.wait_for_text("result", "cancelled")

            # Several files.
            with page.expect_file_chooser() as chooser_info:
                app.click("open_many")
            chooser = chooser_info.value
            assert chooser.is_multiple()
            chooser.set_files([str(picked), str(folder / "notes.md")])
            app.wait_for_text("result", "open 2: pic.png, notes.md")

            # A directory: its files, under their own layout.
            with page.expect_file_chooser() as chooser_info:
                app.click("folder")
            chooser_info.value.set_files(str(folder))
            app.wait_for_text_prefix("result", "folder: ")
            shown = app.text("result").removeprefix("folder: ")
            assert shown.endswith("/photos")
            listing = _in_page(
                page,
                "import pathlib\n"
                f"sorted(str(p.relative_to({shown!r})) for p in pathlib.Path({shown!r}).rglob('*') if p.is_file())",
            )
            assert list(listing) == ["2024/a.png", "notes.md"]  # type: ignore[call-overload]

            # Save: the download carries what the handler wrote, under the default name.
            with page.expect_download() as download_info:
                app.click("save")
            download = download_info.value
            assert download.suggested_filename == "untitled.txt"
            assert Path(download.path()).read_text() == "Saved from the file dialogs sample.\n"
            app.wait_for_text_prefix("result", "save: ")
        finally:
            browser.close()
    assert not errors, errors
