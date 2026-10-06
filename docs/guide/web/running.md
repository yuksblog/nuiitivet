# Running During Development

```sh
python -m nuiitivet.web run samples/web/hello/app.py
```

While you develop, this is the only command. It serves the app from its
source tree, opens a browser on `http://localhost:8000/`, and keeps serving
until Ctrl+C. Nothing is built; users get a built site instead, in
[Building and Deploying](building_and_deploying.md). The sample is a desktop
app unchanged: the same `main()`, the same `nv.App(nv.Window(...)).run()`.

Everything in the entry script's directory goes to the browser, so put the
app in a directory of its own. A directory holding two apps sends both, and
the server tries to import the other app's server modules.

Reload the browser to see an edit: the sources are read again at every
request. An edit to a server-only module needs the command restarted.

`--port 8001` picks another port; `--no-open` leaves the browser closed. When
the port is in use, the command says so and exits.

## Next Steps

- [What Differs from the Desktop](desktop_differences.md)
- [Web overview](index.md)
