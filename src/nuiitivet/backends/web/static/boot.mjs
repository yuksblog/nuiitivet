// Starts the app in the page: load CanvasKit and Pyodide, unpack the sources,
// install the host, and run the app module.

import { installHost } from "/host.mjs";

// The versions the browser evaluation measured.
const CANVASKIT = "https://cdn.jsdelivr.net/npm/canvaskit-wasm@0.42.0/bin/";
const PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";

const status = document.getElementById("status");

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`could not load ${src}`));
    document.head.append(script);
  });
}

async function fetchBuffer(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status} ${await response.text()}`);
  return response.arrayBuffer();
}

async function start() {
  const [{ loadPyodide }, config, bundle, font] = await Promise.all([
    import(PYODIDE + "pyodide.mjs"),
    fetch("/config.json").then((response) => response.json()),
    fetchBuffer("/bundle.zip"),
    fetchBuffer("/font.ttf"),
    loadScript(CANVASKIT + "canvaskit.js"),
  ]);
  const [CK, py] = await Promise.all([
    CanvasKitInit({ locateFile: (file) => CANVASKIT + file }),
    loadPyodide({ indexURL: PYODIDE }),
  ]);

  installHost(CK, document.getElementById("nuiitivet"), font);
  py.unpackArchive(bundle, "zip", { extractDir: "/nuiitivet" });
  await py.runPythonAsync(`
import runpy
import sys

sys.path[:0] = ["/nuiitivet/app", "/nuiitivet/lib"]

from nuiitivet.backends.web.runner import prepare

prepare()
entry = "/nuiitivet/app/" + ${JSON.stringify(config.entry)}
sys.argv = [entry]
runpy.run_path(entry, run_name="__main__")
`);
  status.remove();
}

start().catch((error) => {
  status.textContent = String(error?.stack ?? error);
  throw error;
});
