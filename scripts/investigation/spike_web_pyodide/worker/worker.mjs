// The child: a second Pyodide in a Web Worker. It unpacks the same sources as
// the page and runs what the page sends, pickled as a process pool pickles a call.

import { loadPyodide } from "/pyodide/pyodide.mjs";

let handle = null;

self.onmessage = async ({ data }) => {
  if (data.type === "init") {
    const t0 = performance.now();
    const py = await loadPyodide({ indexURL: "/pyodide/" });
    const t1 = performance.now();
    py.unpackArchive(data.bundle, "zip", { extractDir: "/nuiitivet" });
    py.runPython(`
import pickle
import sys

sys.path[:0] = ["/nuiitivet/app", "/nuiitivet/lib"]


def handle(payload):
    try:
        fn, args, kwargs = pickle.loads(bytes(payload.to_py()))
        out = (True, fn(*args, **kwargs))
    except BaseException as error:
        out = (False, error)
    try:
        return pickle.dumps(out)
    except Exception as error:
        return pickle.dumps((False, RuntimeError(f"the result does not pickle: {error!r}")))
`);
    handle = py.globals.get("handle");
    self.postMessage({ type: "ready", loadMs: t1 - t0, unpackMs: performance.now() - t1 });
    return;
  }
  const out = handle(data.payload);
  const payload = out.toJs();
  out.destroy();
  self.postMessage({ type: "result", id: data.id, payload }, [payload.buffer]);
};
