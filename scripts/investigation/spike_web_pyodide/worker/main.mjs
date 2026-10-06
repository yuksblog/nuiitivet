// The page: the app's Pyodide. It starts workers and sends them pickled calls,
// then measures what a process pool on top of them would cost.

import { loadPyodide } from "/pyodide/pyodide.mjs";

const log = document.getElementById("log");

let frames = 0;
const countFrame = () => { frames++; requestAnimationFrame(countFrame); };
requestAnimationFrame(countFrame);

const t0 = performance.now();
const py = await loadPyodide({ indexURL: "/pyodide/" });
const mainLoadMs = performance.now() - t0;
const bundle = await fetch("/bundle.zip").then((response) => response.arrayBuffer());
py.unpackArchive(bundle, "zip", { extractDir: "/nuiitivet" });

let nextId = 0;
globalThis.NV_SPIKE = {
  frames: () => frames,
  // Start a child. Resolves once its Pyodide is loaded and the sources are unpacked.
  spawn() {
    const started = performance.now();
    const worker = new Worker("/worker.mjs", { type: "module" });
    worker.pending = new Map();
    return new Promise((resolve) => {
      worker.onmessage = ({ data }) => {
        if (data.type === "ready") {
          worker.boot = { totalMs: performance.now() - started, loadMs: data.loadMs, unpackMs: data.unpackMs };
          resolve(worker);
        } else {
          worker.pending.get(data.id)(data.payload);
          worker.pending.delete(data.id);
        }
      };
      worker.postMessage({ type: "init", bundle });
    });
  },
  call(worker, payload) {
    const id = nextId++;
    return new Promise((resolve) => {
      worker.pending.set(id, resolve);
      worker.postMessage({ type: "call", id, payload }, [payload.buffer]);
    });
  },
};

const results = await py.runPythonAsync(`
import asyncio
import json
import pickle
import sys
import time

import js
from pyodide.ffi import to_js

sys.path[:0] = ["/nuiitivet/app", "/nuiitivet/lib"]
import jobs

results = {}
spike = js.NV_SPIKE


async def call(worker, fn, *args, **kwargs):
    payload = to_js(pickle.dumps((fn, args, kwargs)))
    ok, value = pickle.loads(bytes((await spike.call(worker, payload)).to_py()))
    if not ok:
        raise value
    return value


async def timed(awaitable):
    start = time.perf_counter()
    value = await awaitable
    return value, round((time.perf_counter() - start) * 1000, 1)


# 1. What the standard entry does today.
try:
    from concurrent.futures import ProcessPoolExecutor

    pool = ProcessPoolExecutor(max_workers=1)
    try:
        pool.submit(jobs.add, 1, 2)
        results["stdlib_process_pool"] = "submit() returned"
    except Exception as error:
        results["stdlib_process_pool"] = f"submit() raised {type(error).__name__}: {error}"
except Exception as error:
    results["stdlib_process_pool"] = f"construction raised {type(error).__name__}: {error}"

# 2. Starting a child.
first = await spike.spawn()
results["first_worker_boot_ms"] = {k: round(v) for k, v in first.boot.to_py().items()}
second = await spike.spawn()
results["second_worker_boot_ms"] = {k: round(v) for k, v in second.boot.to_py().items()}

# 3. A call.
value, ms = await timed(call(first, jobs.add, 1, 2))
results["first_call"] = {"result": value, "ms": ms}
samples = [(await timed(call(first, jobs.add, 1, 2)))[1] for _ in range(20)]
results["later_call_ms_median"] = sorted(samples)[len(samples) // 2]
value, ms = await timed(call(first, jobs.norm, jobs.Point(3.0, 4.0)))
results["dataclass_argument"] = {"result": value, "ms": ms}
value, ms = await timed(call(first, jobs.framework))
results["import_framework_in_worker"] = {"names": value, "ms": ms}

# 4. A second of CPU work, with the page still alive.
ticks = 0


async def ticker():
    global ticks
    while True:
        ticks += 1
        await asyncio.sleep(0.01)


task = asyncio.ensure_future(ticker())
await asyncio.sleep(0.05)
ticks_before, frames_before = ticks, spike.frames()
count, ms = await timed(call(first, jobs.burn, 1.0))
results["one_second_of_cpu"] = {
    "ms": ms,
    "loop_ticks_meanwhile": ticks - ticks_before,
    "frames_meanwhile": spike.frames() - frames_before,
    "iterations": count,
}

# 5. Two children at once.
_, ms = await timed(asyncio.gather(call(first, jobs.burn, 1.0), call(second, jobs.burn, 1.0)))
results["two_seconds_of_cpu_on_two_workers_ms"] = ms

# 6. Errors.
try:
    await call(first, jobs.fail)
    results["exception"] = "none raised"
except Exception as error:
    results["exception"] = f"{type(error).__name__}: {error}"
try:
    await call(first, lambda: 1)
    results["lambda"] = "ran"
except Exception as error:
    results["lambda"] = f"{type(error).__name__}: {error}"

# 7. Killing a child that is busy, and replacing it.
running = asyncio.ensure_future(call(first, jobs.burn, 30.0))
await asyncio.sleep(0.2)
start = time.perf_counter()
first.terminate()
results["terminate_ms"] = round((time.perf_counter() - start) * 1000, 1)
running.cancel()
replacement = await spike.spawn()
results["replacement_boot_ms"] = {k: round(v) for k, v in replacement.boot.to_py().items()}
value, ms = await timed(call(replacement, jobs.add, 20, 22))
results["call_on_replacement"] = {"result": value, "ms": ms}

task.cancel()
json.dumps(results)
`);

const summary = { userAgent: navigator.userAgent, mainLoadMs: Math.round(mainLoadMs), ...JSON.parse(results) };
log.textContent = JSON.stringify(summary, null, 2);
window.RESULTS = summary;
