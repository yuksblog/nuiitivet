// Spike: can the standard threading API start a marked function as a remote call on Pyodide?
//
// A function marked `@server` is started with `threading.Thread(...).start()`,
// `asyncio.to_thread(...)` and `loop.run_in_executor(...)`. On Pyodide each of
// the three is redirected to an async "remote call" for a marked function, and
// left alone for any other. The remote call here is a stand-in that waits
// 0.2 s on the event loop, as a fetch would.
//
// Run:  node server_marks.mjs

import { loadPyodide } from "pyodide";

const py = await loadPyodide();
await py.runPythonAsync(`
import asyncio
import functools
import threading

# -- what the framework would install --------------------------------------

def server(fn):
    fn.__nv_server__ = True
    return fn

def is_server(fn):
    return getattr(fn, "__nv_server__", False)

calls = []

async def remote_call(fn, args, kwargs):
    """Stands in for the HTTP call: yields to the event loop, then answers."""
    calls.append(fn.__name__)
    await asyncio.sleep(0.2)
    return fn(*args, **kwargs)

_thread_start = threading.Thread.start

def thread_start(self):
    if is_server(self._target):
        asyncio.ensure_future(remote_call(self._target, self._args, self._kwargs))
        return
    _thread_start(self)

threading.Thread.start = thread_start

_to_thread = asyncio.to_thread

async def to_thread(func, /, *args, **kwargs):
    if is_server(func):
        return await remote_call(func, args, kwargs)
    return await _to_thread(func, *args, **kwargs)

asyncio.to_thread = to_thread

loop = asyncio.get_running_loop()
_run_in_executor = loop.run_in_executor

def run_in_executor(executor, func, *args):
    target = func.func if isinstance(func, functools.partial) else func
    if is_server(target):
        bound = func.args if isinstance(func, functools.partial) else ()
        keywords = func.keywords if isinstance(func, functools.partial) else {}
        return asyncio.ensure_future(remote_call(target, (*bound, *args), keywords))
    return _run_in_executor(executor, func, *args)

loop.run_in_executor = run_in_executor

# -- an app, written with the standard API ---------------------------------

@server
def add(a, b, scale=1):
    return (a + b) * scale

def plain(a, b):
    return a + b

class Progress:
    value = 0

@server
def count_to(n, progress):
    for i in range(n):
        progress.value = i + 1
    return n

ticks = 0

async def ticker():
    global ticks
    while True:
        ticks += 1
        await asyncio.sleep(0.01)

task = asyncio.ensure_future(ticker())
await asyncio.sleep(0.03)
print("loop type:", type(loop).__name__)

before = ticks
print("to_thread, marked:", await asyncio.to_thread(add, 1, 2, scale=10), "| loop ticks while waiting:", ticks - before)

before = ticks
print("to_thread, plain:", await asyncio.to_thread(plain, 1, 2), "| loop ticks while waiting:", ticks - before)

before = ticks
result = await loop.run_in_executor(None, functools.partial(add, 1, scale=3), 2)
print("run_in_executor, marked partial:", result, "| loop ticks while waiting:", ticks - before)

progress = Progress()
thread = threading.Thread(target=count_to, args=(5, progress))
thread.start()
print("Thread.start(), marked: returned at once, progress =", progress.value)
await asyncio.sleep(0.3)
print("0.3 s later, progress =", progress.value)

try:
    threading.Thread(target=plain, args=(1, 2)).start()
    print("Thread.start(), plain: ok")
except Exception as error:
    print("Thread.start(), plain: raised", type(error).__name__, "-", error)

from asyncio import to_thread as imported_later
print("from asyncio import to_thread, after the patch, is patched:", imported_later is to_thread)
print("remote calls made:", calls)
task.cancel()
`);
