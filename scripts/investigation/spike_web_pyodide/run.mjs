// Spike: run the nuiitivet paint benchmark on Pyodide + CanvasKit under Node.
//
// The framework source is loaded unmodified. `shim/skia.py` stands in for
// skia-python and forwards to CanvasKit, so the result is what a web target
// would pay for the Python tree walk and for crossing into JS. Rasterization is
// not measured: paint goes to a picture recorder. `browser/` measures it.
//
// Setup:  npm install            (in this directory)
// Run:    node run.mjs [--rows N] [--frames N] [--profile]
//                      [--scroll PX] [--no-replay]
//                      [--deps <site-packages>] [--font <file.ttf>]
//
// --scroll     time one frame of a scroll under a viewport this tall, in place
//              of the repaint cases.
// --no-replay  turn row replay off, to compare a scroll frame with and without.
// --deps       a site-packages directory that holds materialyoucolor. Defaults
//              to the repository's .venv.
// --font       the one typeface every text is drawn with. Defaults to Arial on
//              macOS.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { loadPyodide } from "pyodide";
import { installHost, startScript } from "./host.mjs";

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
    scroll: { type: "string", default: "0" },
    "no-replay": { type: "boolean", default: false },
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

installHost(CK, font.buffer.slice(font.byteOffset, font.byteOffset + font.byteLength), {
  rows: Number(args.rows),
  frames: Number(args.frames),
  profile: args.profile,
  scroll: Number(args.scroll),
  replay: !args["no-replay"],
});

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
await py.runPythonAsync(startScript(["/spike/shim", "/repo", "/bench"], "/spike/web_bench.py") + "\n");
