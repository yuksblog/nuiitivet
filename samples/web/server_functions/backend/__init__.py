"""The server's side: nothing in this package reaches the browser."""

import nuiitivet.material as nv

nv.server_only()  # keep this package off the browser; the page gets stubs
