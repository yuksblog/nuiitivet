// Spike: serve the benchmark page to a browser.
//
// The page loads Pyodide and CanvasKit, unpacks the framework source, and
// paints the benchmark scene onto a WebGL canvas, so the times it reports
// include rasterization. Open it in any browser, or run `chrome.mjs` to drive
// the installed Chrome headless.
//
// Setup:  npm install            (in the parent directory)
// Run:    node browser/serve.mjs [--port N] [--deps <site-packages>] [--font <file.ttf>]
//         then open http://localhost:8765/

import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const here = dirname(fileURLToPath(import.meta.url));
const spike = resolve(here, "..");
const repo = resolve(spike, "../../..");

function defaultDeps() {
  const lib = join(repo, ".venv/lib");
  if (!existsSync(lib)) return null;
  const python = readdirSync(lib).find((name) => name.startsWith("python3"));
  return python ? join(lib, python, "site-packages") : null;
}

const { values: args } = parseArgs({
  options: {
    port: { type: "string", default: "8765" },
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

// A browser has no host directory to mount, so the sources travel as one archive.
const BUNDLE = `
import sys, zipfile
from pathlib import Path

out, src, deps, bench, spike = sys.argv[1:6]
skip = {".ttf", ".otf", ".woff", ".woff2", ".pyc", ".so"}
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    for root, package in ((src, "nuiitivet"), (deps, "materialyoucolor")):
        for path in sorted(Path(root, package).rglob("*")):
            if path.is_file() and path.suffix not in skip and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(root).as_posix())
    archive.write(Path(bench, "bench_paint_walk.py"), "bench_paint_walk.py")
    archive.write(Path(spike, "web_bench.py"), "web_bench.py")
    archive.write(Path(spike, "shim", "skia.py"), "skia.py")
`;
const bundle = join(mkdtempSync(join(tmpdir(), "nuiitivet-spike-")), "bundle.zip");
execFileSync("python3", ["-c", BUNDLE, bundle, join(repo, "src"), args.deps, resolve(spike, ".."), spike]);

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".json": "application/json",
  ".wasm": "application/wasm",
  ".zip": "application/zip",
  ".ttf": "font/ttf",
};

function resolvePath(url) {
  const path = normalize(decodeURIComponent(url.split("?")[0]));
  if (path === "/" || path === "/index.html") return join(here, "index.html");
  if (path === "/page.mjs") return join(here, "page.mjs");
  if (path === "/host.mjs") return join(spike, "host.mjs");
  if (path === "/bundle.zip") return bundle;
  if (path === "/font.ttf") return args.font;
  if (path.startsWith("/pyodide/")) return join(spike, "node_modules/pyodide", path.slice(9));
  if (path.startsWith("/canvaskit/")) return join(spike, "node_modules/canvaskit-wasm/bin", path.slice(11));
  return null;
}

createServer((request, response) => {
  const file = resolvePath(request.url ?? "/");
  if (!file || !existsSync(file)) {
    response.writeHead(404).end("not found");
    return;
  }
  const type = file === args.font ? TYPES[".ttf"] : TYPES[extname(file)] ?? "application/octet-stream";
  response.writeHead(200, { "Content-Type": type, "Cache-Control": "no-store" });
  response.end(readFileSync(file));
}).listen(Number(args.port), () => {
  console.log(`http://localhost:${args.port}/`);
});
