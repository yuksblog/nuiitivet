// The page's worker: a second Pyodide with the app's sources, running the
// @worker functions one call at a time.
//
// It loads Pyodide and fetches the bundle itself, so the page's own start-up
// is not held up. A call's progress and result go back as JSON text, posted
// from Python while the function runs.

let handle = null;

async function fetchBuffer(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.arrayBuffer();
}

self.onmessage = async ({ data }) => {
  if (data.type === "init") {
    try {
      const [{ loadPyodide }, bundle] = await Promise.all([
        import(data.pyodide + "pyodide.mjs"),
        fetchBuffer(data.bundle),
      ]);
      const py = await loadPyodide({ indexURL: data.pyodide });
      py.unpackArchive(bundle, "zip", { extractDir: "/nuiitivet" });
      py.runPython(`import sys\nsys.path[:0] = ["/nuiitivet/app", "/nuiitivet/lib"]`);
      const side = py.pyimport("nuiitivet.backends.web.worker");
      side.prepare(data.modules);
      handle = side.handle;
      self.postMessage({ type: "ready" });
    } catch (error) {
      self.postMessage({ type: "failed", error: String(error?.stack ?? error) });
    }
    return;
  }
  handle(data.id, data.name, data.values);
};
