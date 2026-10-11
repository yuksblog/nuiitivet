// Starts the page's workers on request, as `globalThis.NV_WORKERS` for the
// Python side of a @worker call.
//
// One worker boots while the page loads its own Pyodide, and the first
// `start` hands it over; every later `start` boots another. A call reaches a
// worker through its handle's `post`; what the worker sends back reaches
// Python through `onMessage`. A busy worker reads no message, so cancelling
// the call it runs is `end`: Python ends it and starts another when needed.

export function startWorkers(config, pageUrl) {
  const pyodide = new URL(config.pyodide, pageUrl).href;
  const bundle = new URL("bundle.zip", pageUrl).href;
  const script = new URL("worker.mjs", pageUrl);

  function boot() {
    const worker = new Worker(script, { type: "module" });
    const handle = {
      ready: false,
      // Why the worker ended, once it has.
      failure: null,
      onReady: null,
      onMessage: null,
      onExit: null,
      post(id, name, values) { worker.postMessage({ type: "call", id, name, values }); },
      end() { worker.terminate(); },
    };
    const exit = (reason) => {
      handle.ready = false;
      handle.failure = reason;
      handle.onExit?.(reason);
    };
    worker.onmessage = ({ data }) => {
      if (typeof data === "string") handle.onMessage?.(data);
      else if (data.type === "ready") {
        handle.ready = true;
        handle.onReady?.();
      } else exit(data.error);
    };
    worker.onerror = (event) => exit(event.message || "the worker stopped");
    worker.postMessage({ type: "init", pyodide, bundle, modules: config.workers });
    return handle;
  }

  let spare = boot();
  const host = {
    // How many workers may run at once on this machine.
    limit: navigator.hardwareConcurrency || 1,
    start() {
      const handle = spare !== null && spare.failure === null ? spare : boot();
      spare = null;
      return handle;
    },
  };
  globalThis.NV_WORKERS = host;
  return host;
}
