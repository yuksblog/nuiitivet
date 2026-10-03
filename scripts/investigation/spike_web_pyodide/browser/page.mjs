// Runs the benchmark in the page and shows the times, rasterization included.
//
// Each frame is drawn onto the WebGL surface of the canvas, flushed, and
// followed by gl.finish(), so the time covers the Python walk, the draw calls
// and the GPU work they cause.

import { loadPyodide } from "/pyodide/pyodide.mjs";
import { installHost, startScript } from "/host.mjs";

const WIDTH = 900;
const HEIGHT = 800;
const status = document.getElementById("status");
const log = document.getElementById("log");
const table = document.getElementById("results");

function say(text) {
  log.textContent += text + "\n";
}

const startup = {};
let mark = performance.now();
function lap(name) {
  const now = performance.now();
  startup[name] = Math.round(now - mark);
  mark = now;
}

status.textContent = "Loading CanvasKit…";
const CK = await CanvasKitInit({ locateFile: (file) => "/canvaskit/" + file });
lap("canvaskit_ms");

const canvas = document.getElementById("stage");
let surface = CK.MakeWebGLCanvasSurface(canvas);
const gpu = surface !== null;
if (!gpu) surface = CK.MakeSWCanvasSurface(canvas);
const gl = gpu ? canvas.getContext("webgl2") ?? canvas.getContext("webgl") : null;
const info = gl?.getExtension("WEBGL_debug_renderer_info");
const renderer = gl ? gl.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER) : "software";

status.textContent = "Loading Pyodide…";
const lines = [];
const py = await loadPyodide({
  indexURL: "/pyodide/",
  stdout: (line) => { lines.push(line); say(line); },
  stderr: (line) => say(line),
});
lap("pyodide_ms");

status.textContent = "Unpacking the framework…";
const [bundle, font] = await Promise.all([
  fetch("/bundle.zip").then((r) => r.arrayBuffer()),
  fetch("/font.ttf").then((r) => r.arrayBuffer()),
]);
py.FS.mkdirTree("/app");
py.unpackArchive(bundle, "zip", { extractDir: "/app" });
lap("unpack_ms");

const CASES = [
  { name: "Repaint the visible 800 px", scroll: 0, replay: true, key: "paint_viewport_ms" },
  { name: "Scroll frame, rows walked", scroll: HEIGHT, replay: false, key: "scroll_frame_ms" },
  { name: "Scroll frame, rows replayed", scroll: HEIGHT, replay: true, key: "scroll_frame_ms" },
];

const results = [];
for (const [index, item] of CASES.entries()) {
  status.textContent = `Running: ${item.name}…`;
  await new Promise((resolve) => setTimeout(resolve, 50));
  installHost(CK, font, {
    rows: item.scroll ? 200 : 100,
    frames: 60,
    profile: false,
    scroll: item.scroll,
    replay: item.replay,
    deps: false,
    surface,
    width: WIDTH,
    height: HEIGHT,
    finish: () => gl?.finish(),
  });
  const before = lines.length;
  await py.runPythonAsync(startScript(["/app"], "/app/web_bench.py"));
  const data = JSON.parse(lines.slice(before).reverse().find((line) => line.startsWith("{")));
  if (index === 0) {
    startup.import_ms = Math.round(data.import_ms);
    startup.build_ms = Math.round(data.build_ms);
    startup.first_frame_ms = Math.round(data.first_frame_ms);
  }
  const worst = item.scroll ? data.scroll_frame_max_ms : null;
  results.push({ name: item.name, median_ms: data[item.key], worst_ms: worst });
  const row = table.tBodies[0].insertRow();
  row.insertCell().textContent = item.name;
  row.insertCell().textContent = `${data[item.key].toFixed(2)} ms`;
  row.insertCell().textContent = worst === null ? "" : `${worst.toFixed(2)} ms`;
  table.hidden = false;
}

const summary = { userAgent: navigator.userAgent, gpu, renderer, startup, results };
say(JSON.stringify(summary, null, 2));
status.textContent = `Done. ${gpu ? "WebGL" : "Software"} surface: ${renderer}`;
window.RESULTS = summary;
