"""Driver-agnostic perception and action over a running app.

Seeing a mounted tree (:mod:`.perception`) and driving it (:mod:`.action`) are
plain calls over an ``app`` object -- no HTTP, no session, no MCP. They live here
rather than under :mod:`nuiitivet.dev` because that package is dev-session gated
and never enters a production launch, while a test harness runs against a normal
install.

Private, and stays that way: the dev bridge is the only driver today, so the
shape is still free to change.
"""

from __future__ import annotations
