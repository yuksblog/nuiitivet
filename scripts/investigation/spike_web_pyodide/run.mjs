// Spike: run the nuiitivet paint benchmark on Pyodide + CanvasKit under Node.
//
// The framework source is loaded unmodified. `shim/skia.py` stands in for
// skia-python and forwards to CanvasKit, so the result is what a web target
// would pay for the Python tree walk and for crossing into JS. Rasterization is
// not measured: paint goes to a picture recorder.
//
// Setup:  npm install            (in this directory)
// Run:    node run.mjs [--rows N] [--frames N] [--profile]
//                      [--deps <site-packages>] [--font <file.ttf>]
//
// --deps  a site-packages directory that holds materialyoucolor. Defaults to
//         the repository's .venv.
// --font  the one typeface every text is drawn with. Defaults to Arial on macOS.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { loadPyodide } from "pyodide";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../../..");

function defaultDeps() {
  const lib = join(repo, ".venv/lib");
  if (!existsSync(lib)) return null;
  const python = readdirSync(lib).find((name) => name.startsWith("python3"));
  return python ? join(lib, python, "site-packages") : null;
}

const { values: args } = parseArgs({
  options: {
    rows: { type: "string", default: "100" },
    frames: { type: "string", default: "20" },
    profile: { type: "boolean", default: false },
    deps: { type: "string", default: defaultDeps() ?? "" },
    font: { type: "string", default: "/System/Library/Fonts/Supplemental/Arial.ttf" },
  },
});
for (const [flag, path] of [["--deps", args.deps], ["--font", args.font]]) {
  if (!path || !existsSync(path)) {
    console.error(`${flag}: not found: ${path || "(none)"}`);
    process.exit(1);
  }
}

const CanvasKitInit = createRequire(import.meta.url)("canvaskit-wasm");
const CK = await CanvasKitInit({
  locateFile: (file) => join(here, "node_modules/canvaskit-wasm/bin", file),
});
const font = readFileSync(args.font);

const styles = [CK.PaintStyle.Fill, CK.PaintStyle.Stroke];
const caps = [CK.StrokeCap.Butt, CK.StrokeCap.Round, CK.StrokeCap.Square];

// What the shim reaches through `js`. The helpers take plain numbers so one
// draw is one crossing from Python, with no array built on the Python side.
globalThis.CK = CK;
globalThis.FONT_DATA = font.buffer.slice(font.byteOffset, font.byteOffset + font.byteLength);
globalThis.SPIKE = { rows: Number(args.rows), frames: Number(args.frames), profile: args.profile };
globalThis.H = {
  paint(p, color, aa, style, strokeWidth, cap) {
    if (!p) p = new CK.Paint();
    p.setColorInt(color);
    p.setAntiAlias(aa);
    p.setStyle(styles[style]);
    p.setStrokeWidth(strokeWidth);
    p.setStrokeCap(caps[cap]);
    return p;
  },
  release(o) { o.delete(); },
  measure(f, text) {
    const widths = f.getGlyphWidths(f.getGlyphIDs(text));
    let sum = 0;
    for (let i = 0; i < widths.length; i++) sum += widths[i];
    return sum;
  },
  posBlob(text, xs, y, f) {
    const glyphs = f.getGlyphIDs(text);
    const rs = new Float32Array(glyphs.length * 4);
    for (let i = 0; i < glyphs.length; i++) {
      rs[i * 4] = 1;
      rs[i * 4 + 2] = xs[i] ?? 0;
      rs[i * 4 + 3] = y;
    }
    return CK.TextBlob.MakeFromRSXformGlyphs(glyphs, rs, f);
  },
  clear(c, a, r, g, b) { c.clear(CK.Color4f(r, g, b, a)); },
  clipRect(c, l, t, r, b) { c.clipRect(CK.LTRBRect(l, t, r, b), CK.ClipOp.Intersect, true); },
  drawRRect(c, l, t, r, b, rx, ry, p) { c.drawRRect(CK.RRectXY(CK.LTRBRect(l, t, r, b), rx, ry), p); },
  drawOval(c, l, t, r, b, p) { c.drawOval(CK.LTRBRect(l, t, r, b), p); },
};

const loadStart = performance.now();
const py = await loadPyodide();
console.log("pyodide_load_ms", Math.round(performance.now() - loadStart));

for (const [root, at] of [
  [join(repo, "src"), "/repo"],
  [args.deps, "/deps"],
  [resolve(here, ".."), "/bench"],
  [here, "/spike"],
]) {
  py.FS.mkdirTree(at);
  py.FS.mount(py.FS.filesystems.NODEFS, { root }, at);
}

// The shim comes first so `import skia` never reaches the native wheel in /deps.
await py.runPythonAsync(`
import runpy
import sys

sys.path[:0] = ["/spike/shim", "/repo", "/bench"]
sys.path.append("/deps")
runpy.run_path("/spike/web_bench.py", run_name="__main__")
`);
