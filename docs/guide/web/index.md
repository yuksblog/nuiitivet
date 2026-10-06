# Web

The app you wrote for the desktop runs in a browser from the same source.
While you develop, `python -m nuiitivet.web run app.py` serves it from its
source tree and opens a browser. For users, `python -m nuiitivet.web build`
writes a site, and a file server or `python -m nuiitivet.web serve` delivers
it. Between the two, the browser asks for one change to the code: the work
that ran on a thread becomes a server function.

- [Running During Development](running.md): Serve the app from its source
  tree and see an edit.
- [What Differs from the Desktop](desktop_differences.md): The threads that
  must become server functions, the window features that are ignored, the
  first load and the fonts.
- [Server Functions](server_functions.md): Mark the functions that run on a
  server with `@nv.server`, report progress and cancel from the screen, and
  keep the server's code off the browser.
- [Building and Deploying](building_and_deploying.md): Build the site, and
  deploy it alone or with the server.
