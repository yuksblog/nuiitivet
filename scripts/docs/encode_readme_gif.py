"""Encode a README demo recording into a docs/assets GIF.

Usage:
    python scripts/docs/encode_readme_gif.py <input.gif> <output.gif>

The README GIFs are 960x520 at 100 ms/frame. The Material container pastels
they demo sit close together in RGB, so the palette stays at the full
generated 256 colors — quantizing to 64 merges the pastels and erases the
color changes the demos show. Dithering stays off: the flat MD3 surfaces
don't need it, and dither noise between frames roughly doubles the file size.

Requires ffmpeg on PATH.
"""

from __future__ import annotations

import subprocess
import sys

FILTER = (
    "[0:v]fps=10,scale=960:520:flags=lanczos,split[a][b];"
    "[a]palettegen[p];"
    "[b][p]paletteuse=dither=none:diff_mode=rectangle"
)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    result = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", FILTER, dst],
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
