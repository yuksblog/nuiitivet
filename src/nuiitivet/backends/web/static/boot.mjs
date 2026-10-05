// Starts the app in the page: load CanvasKit and Pyodide, unpack the sources,
// install the host, and run the app module.
//
// Every URL is relative to the page, so a built site works under any path.
// `config.json` says where the runtimes are: a CDN, or a directory of the site.

import { installHost } from "./host.mjs";

const status = document.getElementById("status");
const label = document.getElementById("status-label");

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
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.arrayBuffer();
}

async function start() {
  const config = await fetch("config.json").then((response) => response.json());
  const pyodide = new URL(config.pyodide, location.href).href;
  const canvaskit = new URL(config.canvaskit, location.href).href;

  const [{ loadPyodide }, bundle, fonts, files] = await Promise.all([
    import(pyodide + "pyodide.mjs"),
    fetchBuffer("bundle.zip"),
    Promise.all(config.fonts.map(async (font) => ({ weight: font.weight, data: await fetchBuffer(font.url) }))),
    Promise.all(config.files.map(async (file) => ({ path: file.path, data: await fetchBuffer(file.url) }))),
    loadScript(canvaskit + "canvaskit.js"),
  ]);
  const [CK, py] = await Promise.all([
    CanvasKitInit({ locateFile: (file) => canvaskit + file }),
    loadPyodide({ indexURL: pyodide }),
  ]);

  label.textContent = "Starting…";
  installHost(CK, document.getElementById("nuiitivet"), document.getElementById("nuiitivet-input"), fonts);
  py.unpackArchive(bundle, "zip", { extractDir: "/nuiitivet" });
  for (const file of files) py.FS.writeFile(file.path, new Uint8Array(file.data));
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
  document.body.dataset.state = "running";
}

start().catch((error) => {
  status.className = "failed";
  status.textContent = String(error?.stack ?? error);
  document.body.dataset.state = "failed";
  throw error;
});
