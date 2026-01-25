# Third-party Dependencies Licenses

Date: 2026-01-12

This document records the license findings for project dependencies listed in `pyproject.toml`.

| Package | SPDX (inferred) | Basis / Source | Notes |
|---|---:|---|---|
| pyglet | BSD-3-Clause | GitHub license API (<https://github.com/pyglet/pyglet/blob/master/LICENSE>) — `spdx_id: BSD-3-Clause` | PyPI `info.license` was null; license file in repo confirms BSD-3-Clause. |
| PyOpenGL | BSD-3-Clause base | Repository license text (<https://raw.githubusercontent.com/mcfletch/pyopengl/master/license.txt>) — inferred BSD-3-Clause from license contents | GitHub API returned `spdx_id: NOASSERTION` for `license.txt`, but the license text matches BSD-3-Clause phrasing; recorded here as `BSD-3-Clause` after manual inference. Also contains the following advisory in its license text: "NOTE: THIS SOFTWARE IS NOT FAULT TOLERANT AND SHOULD NOT BE USED IN ANY SITUATION ENDANGERING HUMAN LIFE OR PROPERTY." |
| skia-python | BSD-3-Clause | GitHub license API (<https://github.com/kyamagu/skia-python/blob/main/LICENSE>) — `spdx_id: BSD-3-Clause` | PyPI classifiers also indicate BSD. |
| material-color-utilities | Apache-2.0 | GitHub (<https://github.com/material-foundation/material-color-utilities/blob/main/LICENSE>) PyPI metadata: `license_expression` / package metadata indicates `Apache-2.0` | |
| mypy | MIT | PyPI `info.license` and license file (MIT) | Dev dependency. |
| pytest | MIT | PyPI metadata and license file (MIT) | Dev dependency. |
| pytest-asyncio | Apache-2.0 | PyPI license expression `Apache-2.0` | Dev dependency. |

Notes and methodology

- Primary source: PyPI package metadata (`info.license`, `license_expression`, `info.classifiers`, `info.license_files`).
- When PyPI metadata was ambiguous or `info.license` was null, the repository LICENSE file (via GitHub API / raw URL) was fetched and used to determine SPDX if available.
- Large PyPI `releases` arrays were intentionally not expanded during metadata fetches to avoid excessive payload.
- For packages where the repository license file did not include an SPDX identifier (e.g. PyOpenGL returned `spdx_id: NOASSERTION`), the text appears BSD-like but requires manual confirmation to determine BSD-2-Clause vs BSD-3-Clause. Recommended action: review `https://raw.githubusercontent.com/mcfletch/pyopengl/master/license.txt` and select an SPDX identifier accordingly.
