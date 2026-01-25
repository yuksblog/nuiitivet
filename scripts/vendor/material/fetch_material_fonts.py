#!/usr/bin/env python3
"""Fetch Material Symbols font/codepoint assets for packaging.

This script downloads the latest Material Symbols variable fonts plus the
official codepoints listings into the package directory (default:
src/nuiitivet/material/symbols). Each asset has a list of candidate URLs and
the first successful download wins.

Usage:
    python scripts/vendor/material/fetch_material_fonts.py \
        --out-dir src/nuiitivet/material/symbols \
        --force

Notes:
- Download sources are configurable through --sources. By default we use the
    upstream google/material-design-icons repository raw URLs.
- Files are written atomically (tmp file + rename) to avoid partially written
    assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    # Python 3 builtin
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except Exception:
    print("urllib unavailable", file=sys.stderr)
    raise


def _gh_raw(*segments: str) -> List[str]:
    path = "".join(segments)
    base_repo = "https://github.com/google/material-design-icons/raw/master"
    raw_repo = "https://raw.githubusercontent.com/google/material-design-icons/master"
    return [f"{base_repo}/{path}", f"{raw_repo}/{path}"]


DEFAULT_ASSETS: Dict[str, List[str]] = {
    "MaterialSymbolsOutlined[FILL,GRAD,opsz,wght].ttf": _gh_raw(
        "variablefont/",
        "MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.ttf",
    ),
    "MaterialSymbolsOutlined[FILL,GRAD,opsz,wght].codepoints": _gh_raw(
        "variablefont/",
        "MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.codepoints",
    ),
    "MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf": _gh_raw(
        "variablefont/",
        "MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D.ttf",
    ),
    "MaterialSymbolsRounded[FILL,GRAD,opsz,wght].codepoints": _gh_raw(
        "variablefont/",
        "MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D.codepoints",
    ),
    "MaterialSymbolsSharp[FILL,GRAD,opsz,wght].ttf": _gh_raw(
        "variablefont/",
        "MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D.ttf",
    ),
    "MaterialSymbolsSharp[FILL,GRAD,opsz,wght].codepoints": _gh_raw(
        "variablefont/",
        "MaterialSymbolsSharp%5BFILL,GRAD,opsz,wght%5D.codepoints",
    ),
}


def atomic_write(path: str, data: bytes) -> None:
    dirpath = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def download_url(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": "nuiitivet-fetcher/1.0"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.read()
    except HTTPError:
        raise
    except URLError:
        raise


def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def fetch_fonts(
    out_dir: str,
    font_map: Dict[str, List[str]],
    force: bool = False,
    checksums: Optional[Dict[str, str]] = None,
) -> int:
    """Fetch fonts into out_dir. Returns number of fonts written and writes metadata.

    If `checksums` is provided it should map filename -> expected sha256 hex string.
    Each downloaded file is validated against the expected checksum (if present).
    A metadata file `fonts_metadata.json` is written into `out_dir` summarizing
    the actual downloaded files.
    """
    ensure_out_dir(out_dir)
    written = 0
    metadata = []
    for fname, candidates in font_map.items():
        dest = os.path.join(out_dir, fname)
        if os.path.exists(dest) and not force:
            print(f"Skip (exists): {dest}")
            continue

        expected_sha = checksums.get(fname) if checksums else None

        ok = False
        for url in candidates:
            print(f"Trying {url} ...", end=" ")
            try:
                data = download_url(url)

                # verify checksum if provided
                if expected_sha:
                    h = hashlib.sha256()
                    h.update(data)
                    got = h.hexdigest()
                    if got.lower() != expected_sha.lower():
                        print("SHA256 mismatch", file=sys.stderr)
                        print(f"  expected: {expected_sha}")
                        print(f"  got:      {got}")
                        # try next candidate URL
                        continue

                atomic_write(dest, data)
                print("OK")
                written += 1
                ok = True

                # record metadata
                meta = {
                    "filename": fname,
                    "url": url,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                }
                metadata.append(meta)

                break
            except HTTPError as he:
                try:
                    code = he.code
                except Exception:
                    code = "HTTPError"
                print(f"HTTP {code}")
            except URLError as ue:
                try:
                    reason = ue.reason
                except Exception:
                    reason = "URL error"
                print(f"URL error: {reason}")
            except Exception as e:
                print(f"error: {e}")

        if not ok:
            print(f"Failed to fetch {fname}; tried {len(candidates)} urls", file=sys.stderr)

    # write metadata file
    try:
        meta_path = os.path.join(out_dir, "fonts_metadata.json")
        atomic_write(meta_path, json.dumps({"fonts": metadata}, indent=2).encode("utf-8"))
    except Exception:
        print("Failed to write metadata file", file=sys.stderr)

    return written


def load_sources_from_json(path: str) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # expect mapping filename -> [urls]
    out: Dict[str, List[str]] = {}
    for k, v in data.items():
        if isinstance(v, list):
            out[k] = v
    return out


def load_checksums_from_json(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(v, str):
            out[k] = v
    return out


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch Material icon font files for packaging/CI")
    p.add_argument(
        "--out-dir",
        default="src/nuiitivet/material/symbols",
        help="Target directory to save font files",
    )
    p.add_argument("--force", action="store_true", help="Overwrite existing files")
    p.add_argument("--sources", help="Optional JSON file mapping filename -> [urls] to override default sources")
    p.add_argument("--checksums", help="Optional JSON file mapping filename -> expected sha256 hex string")
    p.add_argument("--list-only", action="store_true", help="List planned files/urls and exit")
    args = p.parse_args(argv)

    font_map = DEFAULT_ASSETS
    if args.sources:
        if not os.path.isfile(args.sources):
            print(f"Sources file not found: {args.sources}", file=sys.stderr)
            return 2
        font_map = load_sources_from_json(args.sources)

    checksums: Optional[Dict[str, str]] = None
    if args.checksums:
        if not os.path.isfile(args.checksums):
            print(f"Checksums file not found: {args.checksums}", file=sys.stderr)
            return 2
        checksums = load_checksums_from_json(args.checksums)

    if args.list_only:
        print("Planned downloads:")
        for fname, urls in font_map.items():
            print(f"- {fname}")
            for u in urls:
                print(f"    {u}")
        return 0

    written = fetch_fonts(args.out_dir, font_map, force=args.force, checksums=checksums)
    print(f"Assets written: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
