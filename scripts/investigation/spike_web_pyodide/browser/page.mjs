// Runs the benchmark in the page and shows the times, rasterization included.
//
// Each frame is drawn onto the WebGL surface of the canvas, flushed, and
// followed by gl.finish(), so the time covers the Python walk, the draw calls
// and the GPU work they cause.
//
// `?stage=` cuts the frame short, to see which part of it a browser spends on:
//   walk    — Python walk into a picture recorder, no surface
//   draw    — draw calls onto the WebGL surface, no flush
//   flush   — plus surface.flush(), no wait for the GPU
//   finish  — plus gl.finish() (the default; the full frame)
//   sw      — the full frame onto a software surface, no WebGL at all
// `&count=1` also counts and times every WebGL call and the wall time of
// surface.flush() and gl.finish(). The summary carries two probes as well: the
// cost of a crossing from Python, and CanvasKit driven from JS alone.

import { loadPyodide } from "/pyodide/pyodide.mjs";
import { installHost, startScript } from "/host.mjs";

const WIDTH = 900;
const HEIGHT = 800;
const STAGES = ["walk", "draw", "flush", "finish", "sw"];
const query = new URLSearchParams(location.search);
const stage = query.get("stage") ?? "finish";
if (!STAGES.includes(stage)) throw new Error(`unknown stage: ${stage}`);
const counting = query.get("count") === "1";
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
let surface = stage === "sw" ? null : CK.MakeWebGLCanvasSurface(canvas);
const gpu = surface !== null;
if (!gpu) surface = CK.MakeSWCanvasSurface(canvas);
const gl = gpu ? canvas.getContext("webgl2") ?? canvas.getContext("webgl") : null;
// Count the WebGL calls a frame makes: Emscripten looks each method up on the
// context object per call, so wrapping the instance sees every one.
let glCalls = 0;
const glCallsPerFrame = [];
const glTime = {};
if (gl && counting) {
  for (const name of Object.getOwnPropertyNames(Object.getPrototypeOf(gl))) {
    const fn = gl[name];
    if (typeof fn !== "function") continue;
    gl[name] = function (...args) {
      glCalls++;
      const start = performance.now();
      const out = fn.apply(this, args);
      const entry = glTime[name] ?? (glTime[name] = { calls: 0, ms: 0 });
      entry.calls++;
      entry.ms += performance.now() - start;
      return out;
    };
  }
}
// Wall time of surface.flush() per frame: Skia's own work in wasm and the
// Emscripten glue, plus the WebGL calls it makes. Set on the instance, so the
// shim's call through the JsProxy finds it first.
const flushWall = [];
const finishWall = [];
if (gl && counting) {
  const flush = surface.flush.bind(surface);
  surface.flush = () => {
    const start = performance.now();
    flush();
    flushWall.push(performance.now() - start);
  };
}
const median = (list) => {
  const sorted = [...list].sort((a, b) => a - b);
  return sorted.length ? Math.round(sorted[sorted.length >> 1] * 1000) / 1000 : null;
};
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

// CanvasKit driven from JS alone, no Python: how fast its wasm runs here.
// 2000 rounded rects into a recorder, and the same onto the surface with a
// flush and a finish; the median of 7 rounds.
function ckProbe() {
  const paint = new CK.Paint();
  paint.setColorInt(0xFF6750A4);
  paint.setAntiAlias(true);
  const draw = (c) => {
    for (let i = 0; i < 2000; i++) {
      const x = (i * 37) % 860, y = (i * 53) % 760;
      c.drawRRect(CK.RRectXY(CK.LTRBRect(x, y, x + 30, y + 20), 4, 4), paint);
    }
  };
  const rounds = (fn) => {
    const times = [];
    for (let i = 0; i < 7; i++) {
      const start = performance.now();
      fn();
      times.push(performance.now() - start);
    }
    return Math.round(times.sort((a, b) => a - b)[3] * 100) / 100;
  };
  const out = {};
  out.record_ms = rounds(() => {
    const recorder = new CK.PictureRecorder();
    draw(recorder.beginRecording(CK.LTRBRect(0, 0, WIDTH, HEIGHT)));
    recorder.finishRecordingAsPicture().delete();
    recorder.delete();
  });
  if (gpu) {
    const c = surface.getCanvas();
    out.surface_draw_ms = rounds(() => { c.clear(CK.WHITE); draw(c); });
    out.surface_frame_ms = rounds(() => { c.clear(CK.WHITE); draw(c); surface.flush(); gl.finish(); });
  }
  paint.delete();
  return out;
}

// How much one crossing from Python costs in this browser: a JS no-op, a JS
// helper that builds a typed array, and an embind call into the CanvasKit wasm.
globalThis.PROBE = { noop() {} };
globalThis.CK = CK;
const ck = ckProbe();
const probe = JSON.parse(await py.runPythonAsync(`
import json, time
import js
def bench(fn, n=20000):
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return round((time.perf_counter() - start) * 1e6 / n, 3)
noop = js.PROBE.noop
rect = js.CK.LTRBRect
paint = js.CK.Paint
json.dumps({
    "py_call_us": bench(lambda: None),
    "js_noop_us": bench(noop),
    "js_rect_us": bench(lambda: rect(0, 0, 1, 1)),
    "wasm_paint_us": bench(lambda: paint.new().delete()),
})
`));

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
    surface: stage === "walk" ? undefined : surface,
    flush: stage !== "draw",
    width: WIDTH,
    height: HEIGHT,
    finish: () => {
      const start = performance.now();
      if (stage === "finish") gl?.finish();
      finishWall.push(performance.now() - start);
      glCallsPerFrame.push(glCalls);
      glCalls = 0;
    },
  });
  glCallsPerFrame.length = 0;
  flushWall.length = 0;
  finishWall.length = 0;
  for (const name of Object.keys(glTime)) delete glTime[name];
  const before = lines.length;
  await py.runPythonAsync(startScript(["/app"], "/app/web_bench.py"));
  const data = JSON.parse(lines.slice(before).reverse().find((line) => line.startsWith("{")));
  if (index === 0) {
    startup.import_ms = Math.round(data.import_ms);
    startup.build_ms = Math.round(data.build_ms);
    startup.first_frame_ms = Math.round(data.first_frame_ms);
    // The whole report of the repaint case; layout_resize_ms never calls into JS.
    startup.repaint_report = data;
  }
  const worst = item.scroll ? data.scroll_frame_max_ms : null;
  const gl_calls = median(glCallsPerFrame);
  // Time per WebGL method over the whole case, largest first, and the native
  // WebGL time of an average frame without gl.finish().
  const gl_time = Object.entries(glTime)
    .sort((a, b) => b[1].ms - a[1].ms)
    .slice(0, 12)
    .map(([name, { calls, ms }]) => ({ name, calls, ms: Math.round(ms * 100) / 100 }));
  const frames = glCallsPerFrame.length || 1;
  const gl_native_ms = Object.entries(glTime)
    .filter(([name]) => name !== "finish")
    .reduce((sum, [, { ms }]) => sum + ms, 0) / frames;
  results.push({
    name: item.name, median_ms: data[item.key], worst_ms: worst, gl_calls, gl_time,
    flush_wall_ms: median(flushWall), finish_wall_ms: median(finishWall),
    gl_native_ms: Math.round(gl_native_ms * 1000) / 1000,
  });
  const row = table.tBodies[0].insertRow();
  row.insertCell().textContent = item.name;
  row.insertCell().textContent = `${data[item.key].toFixed(2)} ms`;
  row.insertCell().textContent = worst === null ? "" : `${worst.toFixed(2)} ms`;
  table.hidden = false;
}

const summary = { userAgent: navigator.userAgent, gpu, renderer, stage, probe, ck, startup, results };
say(JSON.stringify(summary, null, 2));
status.textContent = `Done. ${gpu ? "WebGL" : "Software"} surface: ${renderer}`;
window.RESULTS = summary;
