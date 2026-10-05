"""What the web tools download: the page's text fonts, and for a build the runtimes the page runs on.

Each file is pinned by its SHA-256 and kept in a cache directory, so it is
downloaded once per machine.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PYODIDE_CDN = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/"
CANVASKIT_CDN = "https://cdn.jsdelivr.net/npm/canvaskit-wasm@0.42.0/"
_NOTO = "https://raw.githubusercontent.com/notofonts/noto-cjk/Sans2.004/"


@dataclass(frozen=True)
class Asset:
    """One downloaded file.

    Attributes:
        path: Where the file sits in a built site, relative to the page.
        url: Where it is downloaded from.
        sha256: The digest the download must have.
    """

    path: str
    url: str
    sha256: str


# The page's text typefaces, by weight. A browser gives the app no system
# fonts, and an OS font may not be put on a public server. Noto Sans JP may,
# and it covers Latin and Japanese in one face, which a text needs because it
# is drawn in a single typeface.
TEXT_FONTS: tuple[tuple[int, Asset], ...] = (
    (
        400,
        Asset(
            "fonts/NotoSansJP-Regular.otf",
            _NOTO + "Sans/SubsetOTF/JP/NotoSansJP-Regular.otf",
            "dff723ba59d57d136764a04b9b2d03205544f7cd785a711442d6d2d085ac5073",
        ),
    ),
    (
        500,
        Asset(
            "fonts/NotoSansJP-Medium.otf",
            _NOTO + "Sans/SubsetOTF/JP/NotoSansJP-Medium.otf",
            "f396a3b57256e4515be9cb41f7aac54766d654890082a9f1b5c2451b5c093d8a",
        ),
    ),
)

RUNTIME: tuple[Asset, ...] = (
    Asset(
        "pyodide/pyodide.mjs",
        PYODIDE_CDN + "pyodide.mjs",
        "6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109",
    ),
    Asset(
        "pyodide/pyodide.asm.mjs",
        PYODIDE_CDN + "pyodide.asm.mjs",
        "f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635",
    ),
    Asset(
        "pyodide/pyodide.asm.wasm",
        PYODIDE_CDN + "pyodide.asm.wasm",
        "cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6",
    ),
    Asset(
        "pyodide/python_stdlib.zip",
        PYODIDE_CDN + "python_stdlib.zip",
        "fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a",
    ),
    Asset(
        "pyodide/pyodide-lock.json",
        PYODIDE_CDN + "pyodide-lock.json",
        "5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010",
    ),
    Asset(
        "canvaskit/canvaskit.js",
        CANVASKIT_CDN + "bin/canvaskit.js",
        "443777592179808354031cf411d8d43cac9f6b98d1227123c5c22d401b0fbf7f",
    ),
    Asset(
        "canvaskit/canvaskit.wasm",
        CANVASKIT_CDN + "bin/canvaskit.wasm",
        "25ebed8e60158c5854f8dc807b936daca21354f8bfb6a2231266b0a93812f301",
    ),
)

# The licences of what a built site redistributes.
LICENSES: tuple[Asset, ...] = (
    Asset(
        "licenses/pyodide-LICENSE.txt",
        "https://raw.githubusercontent.com/pyodide/pyodide/314.0.7/LICENSE",
        "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5",
    ),
    Asset(
        "licenses/canvaskit-LICENSE.txt",
        CANVASKIT_CDN + "LICENSE",
        "d27678cba0d529e77201e2d2a053628143e986aad8f1e77f7039ad4366c8f978",
    ),
    Asset(
        "licenses/noto-sans-jp-LICENSE.txt",
        _NOTO + "LICENSE",
        "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2",
    ),
)


def cache_dir() -> Path:
    """The directory downloads are kept in. ``NUIITIVET_CACHE_DIR`` overrides the OS default."""
    override = os.environ.get("NUIITIVET_CACHE_DIR")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "nuiitivet"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "nuiitivet" / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "nuiitivet"


def fetch(asset: Asset) -> Path:
    """The local copy of ``asset``, downloaded on its first use.

    Args:
        asset: The file to get.

    Raises:
        RuntimeError: The download failed, or its digest is not the pinned one.
    """
    target = cache_dir() / "web" / asset.sha256[:16] / Path(asset.path).name
    if target.is_file():
        return target
    print(f"Downloading {asset.url}", file=sys.stderr)
    try:
        with urllib.request.urlopen(asset.url) as response:
            data = response.read()
    except OSError as error:
        raise RuntimeError(f"could not download {asset.url}: {error}") from error
    if hashlib.sha256(data).hexdigest() != asset.sha256:
        raise RuntimeError(f"{asset.url} is not the file this version of nuiitivet expects")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Written beside the target and renamed, so an interrupted download leaves no half file.
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(data)
    partial.replace(target)
    return target


__all__ = ["Asset", "CANVASKIT_CDN", "LICENSES", "PYODIDE_CDN", "RUNTIME", "TEXT_FONTS", "cache_dir", "fetch"]
