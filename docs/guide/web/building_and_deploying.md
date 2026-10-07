# Building and Deploying

```sh
python -m nuiitivet.web build samples/web/hello/app.py -o dist
```

Users get a built site, not the source tree that `run` serves. The build
writes two directories:

| Directory | Holds | Needs |
| --- | --- | --- |
| `dist/site` | The page, the app's sources, the fonts, Pyodide and CanvasKit, and the licences of everything redistributed | Any file server |
| `dist/server` | The app's sources, for its server functions | Python with nuiitivet |

The site loads nothing from a CDN, so it works without internet access. Every
URL in it is relative, so it serves from any path of a host.

## Deploying the site alone

An app without server functions deploys `dist/site` alone: copy it to any
static host.

## Deploying the site and the server

An app with server functions deploys both parts. The page sends a call to
`nv/call/...` next to its own URL, so the site and the calls must share one
origin and path:

```sh
python -m nuiitivet.web serve dist --host 0.0.0.0 --port 8000
```

`serve` answers both the site and the calls from one process. Behind a
reverse proxy, the static host serves `dist/site` and the proxy forwards
`nv/call/` to the process that runs `serve`.

## Next Steps

- [Web overview](index.md)
