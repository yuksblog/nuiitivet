// Starts the page's worker and keeps it running, as `globalThis.NV_WORKERS`
// for the Python side of a @worker call.
//
// The worker boots while the page loads its own Pyodide. A call reaches it
// through `post`; what the worker sends back reaches Python through
// `onMessage`. A busy worker reads no message, so cancelling the call it runs
// is `restart`: end it, and boot another.

export function startWorkers(config, pageUrl) {
  const pyodide = new URL(config.pyodide, pageUrl).href;
  const bundle = new URL("bundle.zip", pageUrl).href;
  const script = new URL("worker.mjs", pageUrl);
  let worker = null;

  const pool = {
    ready: false,
    // Why the worker did not start, once it has said so.
    failure: null,
    onReady: null,
    onMessage: null,
    onExit: null,
    post(id, name, values) { worker.postMessage({ type: "call", id, name, values }); },
    restart() {
      worker.terminate();
      boot();
    },
  };

  function boot() {
    pool.ready = false;
    const started = new Worker(script, { type: "module" });
    worker = started;
    let wasReady = false;
    const exit = (reason) => {
      if (started !== worker) return;
      pool.ready = false;
      if (!wasReady) pool.failure = reason;
      pool.onExit?.(reason, wasReady);
      if (wasReady) pool.restart();
    };
    started.onmessage = ({ data }) => {
      if (typeof data === "string") pool.onMessage?.(data);
      else if (data.type === "ready") {
        wasReady = true;
        pool.ready = true;
        pool.onReady?.();
      } else exit(data.error);
    };
    started.onerror = (event) => exit(event.message || "the worker stopped");
    started.postMessage({ type: "init", pyodide, bundle, modules: config.workers });
  }

  boot();
  globalThis.NV_WORKERS = pool;
  return pool;
}
