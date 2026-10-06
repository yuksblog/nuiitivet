// Spike: what threading.Thread and asyncio.to_thread do on Pyodide.
//
// Run:  node threads.mjs

import { loadPyodide } from "pyodide";

const py = await loadPyodide();
await py.runPythonAsync(`
import asyncio
import threading
import time

def work():
    time.sleep(0.2)
    return threading.current_thread().name

thread = threading.Thread(target=work)
print("Thread(...) constructed")
try:
    thread.start()
    print("Thread.start() ok")
except Exception as error:
    print("Thread.start() raised:", type(error).__name__, error)

ticks = 0

async def ticker():
    global ticks
    while True:
        ticks += 1
        await asyncio.sleep(0.01)

task = asyncio.ensure_future(ticker())
await asyncio.sleep(0.05)
before = ticks
try:
    name = await asyncio.to_thread(work)
    print("to_thread ran on:", name, "| main is:", threading.main_thread().name)
    print("event loop ticks during the 0.2 s call:", ticks - before)
except Exception as error:
    print("to_thread raised:", type(error).__name__, error)
task.cancel()
`);
